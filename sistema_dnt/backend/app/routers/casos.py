from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import NotificacionCaso, Paciente, Cuidador, ControlSeguimiento
from app.schemas import (
    NotificacionCasoCreate,
    NotificacionCasoOut,
    CasoResumenVista,
    CasoCerrarRequest
)
from app.services import clasificar_estado_nutricional, calcular_proxima_cita
from app.reporte_expediente import generar_html_expediente_imprimible

router = APIRouter(prefix="/api/casos", tags=["Pacientes y Casos"])

@router.get("", response_model=List[CasoResumenVista])
def listar_casos(
    response: Response,
    estado_caso: Optional[str] = Query(None, description="Filtro por estado: 'En seguimiento', 'Cerrado', etc."),
    municipio: Optional[str] = Query(None, description="Filtro por nombre de municipio"),
    eapb: Optional[str] = Query(None, description="Filtro por nombre de EAPB"),
    clasificacion: Optional[str] = Query(None, description="Filtro por clasificación nutricional actual"),
    citas_vencidas: Optional[bool] = Query(None, description="Filtrar solo citas vencidas a la fecha"),
    busqueda: Optional[str] = Query(None, description="Búsqueda por número de documento o nombre"),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retorna el listado paginado de casos clínicos calculado en vivo desde la vista `vw_estado_actual_casos`.
    Retorna en encabezados HTTP:
    - `X-Total-Count`: Conteo real total de casos en la BD que cumplen con los filtros.
    - `X-Limit`: Límite solicitado.
    - `X-Offset`: Desplazamiento actual.
    """
    where_sql = " WHERE 1=1"
    params = {}

    if estado_caso:
        where_sql += " AND estado_caso ILIKE :estado_caso"
        params["estado_caso"] = f"%{estado_caso}%"

    if municipio:
        where_sql += " AND municipio ILIKE :municipio"
        params["municipio"] = f"%{municipio}%"

    if eapb:
        where_sql += " AND eapb ILIKE :eapb"
        params["eapb"] = f"%{eapb}%"

    if clasificacion:
        where_sql += " AND clasificacion_nutricional_actual ILIKE :clasificacion"
        params["clasificacion"] = f"%{clasificacion}%"

    if citas_vencidas is True:
        where_sql += " AND fecha_proxima_cita IS NOT NULL AND fecha_proxima_cita < CURRENT_DATE AND estado_caso = 'En seguimiento'"

    if busqueda:
        where_sql += " AND (numero_documento ILIKE :busq OR nombre_completo ILIKE :busq)"
        params["busq"] = f"%{busqueda}%"

    # Conteo total real en base de datos con los filtros activos
    count_sql = f"SELECT count(*) FROM vw_estado_actual_casos {where_sql}"
    total_filtrado = db.execute(text(count_sql), params).scalar() or 0

    # Consulta paginada de registros
    query = f"SELECT * FROM vw_estado_actual_casos {where_sql} ORDER BY fecha_notificacion DESC NULLS LAST, caso_id DESC LIMIT :limit OFFSET :offset"
    query_params = dict(params)
    query_params["limit"] = limit
    query_params["offset"] = offset

    result = db.execute(text(query), query_params).mappings().all()

    casos_out = []
    hoy = date.today()
    for row in result:
        item = dict(row)
        item["alerta_cita_vencida"] = bool(
            item.get("fecha_proxima_cita") and item["fecha_proxima_cita"] < hoy and item.get("estado_caso") == "En seguimiento"
        )
        item["alerta_egreso_edad"] = bool(
            item.get("edad_meses_actual") is not None and item["edad_meses_actual"] >= 60 and item.get("estado_caso") == "En seguimiento"
        )
        casos_out.append(CasoResumenVista(**item))

    response.headers["X-Total-Count"] = str(total_filtrado)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count, X-Limit, X-Offset"

    return casos_out

@router.get("/busqueda-global")
def busqueda_global(
    q: str = Query(..., min_length=1, description="Número de documento, nombre o cuidador"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda global rápida optimizada para el atajo universal (Ctrl + K).
    Permite encontrar a cualquier paciente de forma instantánea por documento,
    nombres o cuidador, y abrir de inmediato su ficha/expediente clínico.
    """
    termino = q.strip()
    if not termino:
        return []

    sql = """
    SELECT 
        caso_id,
        paciente_id,
        tipo_documento,
        numero_documento,
        nombre_completo,
        sexo,
        edad_meses_actual,
        municipio,
        eapb,
        estado_caso,
        clasificacion_nutricional_actual,
        ultimo_zscore,
        cuidador,
        telefono_cuidador
    FROM vw_estado_actual_casos
    WHERE numero_documento ILIKE :term
       OR nombre_completo ILIKE :term
       OR cuidador ILIKE :term
    ORDER BY 
        CASE 
            WHEN numero_documento = :exact THEN 1
            WHEN numero_documento ILIKE :exact_start THEN 2
            WHEN nombre_completo ILIKE :exact_start THEN 3
            ELSE 4
        END,
        nombre_completo ASC
    LIMIT 15;
    """
    params = {
        "term": f"%{termino}%",
        "exact": termino,
        "exact_start": f"{termino}%"
    }
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]

@router.get("/{caso_id}")
def obtener_caso(caso_id: int, db: Session = Depends(get_db)):
    """
    Retorna el expediente clínico integral y toda la trazabilidad histórica del niño
    a lo largo de todos sus episodios de notificación y controles periódicos.
    """
    query = "SELECT * FROM vw_estado_actual_casos WHERE caso_id = :caso_id"
    row = db.execute(text(query), {"caso_id": caso_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")
    
    caso_db = db.query(NotificacionCaso).filter(NotificacionCaso.caso_id == caso_id).first()
    resumen = dict(row)
    hoy = date.today()
    resumen["alerta_cita_vencida"] = bool(
        resumen.get("fecha_proxima_cita") and resumen["fecha_proxima_cita"] < hoy and resumen.get("estado_caso") == "En seguimiento"
    )
    resumen["alerta_egreso_edad"] = bool(
        resumen.get("edad_meses_actual") is not None and resumen["edad_meses_actual"] >= 60 and resumen.get("estado_caso") == "En seguimiento"
    )
    p_obj = caso_db.paciente
    resumen["georreferenciacion"] = p_obj.georreferenciacion if p_obj else None
    resumen["documento_cuidador"] = p_obj.cuidador.documento_cuidador if (p_obj and p_obj.cuidador) else None

    # 1. Obtener todos los episodios históricos de este paciente
    todos_episodios = (
        db.query(NotificacionCaso)
        .filter(NotificacionCaso.paciente_id == caso_db.paciente_id)
        .order_by(NotificacionCaso.fecha_notificacion.asc().nulls_last(), NotificacionCaso.caso_id.asc())
        .all()
    )

    lista_episodios = []
    # Consolidar datos de primera atención y captación de referencia (por si este episodio puntual venía en blanco)
    mejor_captacion = None
    mejor_gbai = None
    mejor_atencion = None

    for ep in todos_episodios:
        cap = {
            "fecha": ep.fecha_captacion,
            "peso_kg": float(ep.peso_inicial_kg) if ep.peso_inicial_kg else None,
            "talla_cm": float(ep.talla_inicial_cm) if ep.talla_inicial_cm else None,
            "pb_cm": float(ep.pb_inicial_cm) if ep.pb_inicial_cm else None,
            "zscore": float(ep.zscore_inicial) if ep.zscore_inicial else None,
        }
        if not mejor_captacion and (cap["fecha"] or cap["peso_kg"]):
            mejor_captacion = cap

        gbai = {
            "fecha": ep.fecha_busqueda_gbai,
            "asignacion": ep.asignacion_interna,
            "estado": ep.estado_busqueda
        }
        if not mejor_gbai and (gbai["fecha"] or gbai["asignacion"]):
            mejor_gbai = gbai

        aten = {
            "fecha": ep.fecha_primera_atencion,
            "peso_kg": float(ep.peso_atencion_kg) if ep.peso_atencion_kg else None,
            "talla_cm": float(ep.talla_atencion_cm) if ep.talla_atencion_cm else None,
            "pb_cm": float(ep.pb_atencion_cm) if ep.pb_atencion_cm else None,
            "zscore": float(ep.zscore_atencion) if ep.zscore_atencion else None,
            "prueba_apetito": ep.prueba_apetito,
            "tratamiento": ep.tratamiento_inicial,
            "sobres_ftlc": ep.sobres_ftlc_inicial,
            "comorbilidad": ep.comorbilidad_inicial,
            "escenario_manejo": ep.escenario_manejo
        }
        if not mejor_atencion and (aten["fecha"] or aten["peso_kg"]):
            mejor_atencion = aten

        lista_episodios.append({
            "caso_id": ep.caso_id,
            "fuente_notificacion": ep.fuente_notificacion,
            "fecha_notificacion": ep.fecha_notificacion,
            "cooperante_notificador": ep.cooperante_notificador,
            "medio_notificacion": ep.medio_notificacion,
            "estado_caso": ep.estado_caso,
            "motivo_egreso": ep.motivo_egreso,
            "fecha_egreso": ep.fecha_egreso,
            "captacion_inicial": cap,
            "gbai": gbai,
            "primera_atencion": aten
        })

    # Datos específicos del caso consultado
    det_captacion = {
        "fecha": caso_db.fecha_captacion,
        "peso_kg": float(caso_db.peso_inicial_kg) if caso_db.peso_inicial_kg else None,
        "talla_cm": float(caso_db.talla_inicial_cm) if caso_db.talla_inicial_cm else None,
        "pb_cm": float(caso_db.pb_inicial_cm) if caso_db.pb_inicial_cm else None,
        "zscore": float(caso_db.zscore_inicial) if caso_db.zscore_inicial else None,
    }
    if not (det_captacion["fecha"] or det_captacion["peso_kg"]) and mejor_captacion:
        det_captacion = mejor_captacion

    det_gbai = {
        "fecha": caso_db.fecha_busqueda_gbai,
        "asignacion": caso_db.asignacion_interna,
        "estado": caso_db.estado_busqueda
    }
    if not (det_gbai["fecha"] or det_gbai["asignacion"]) and mejor_gbai:
        det_gbai = mejor_gbai

    det_atencion = {
        "fecha": caso_db.fecha_primera_atencion,
        "peso_kg": float(caso_db.peso_atencion_kg) if caso_db.peso_atencion_kg else None,
        "talla_cm": float(caso_db.talla_atencion_cm) if caso_db.talla_atencion_cm else None,
        "pb_cm": float(caso_db.pb_atencion_cm) if caso_db.pb_atencion_cm else None,
        "zscore": float(caso_db.zscore_atencion) if caso_db.zscore_atencion else None,
        "prueba_apetito": caso_db.prueba_apetito,
        "tratamiento": caso_db.tratamiento_inicial,
        "sobres_ftlc": caso_db.sobres_ftlc_inicial,
        "comorbilidad": caso_db.comorbilidad_inicial,
        "escenario_manejo": caso_db.escenario_manejo
    }
    if not (det_atencion["fecha"] or det_atencion["peso_kg"]) and mejor_atencion:
        det_atencion = mejor_atencion

    # 2. Controles de seguimiento de todo el paciente
    controles_paciente = (
        db.query(ControlSeguimiento)
        .join(NotificacionCaso, ControlSeguimiento.caso_id == NotificacionCaso.caso_id)
        .filter(NotificacionCaso.paciente_id == caso_db.paciente_id)
        .order_by(ControlSeguimiento.fecha_control.asc(), ControlSeguimiento.numero_seguimiento.asc())
        .all()
    )

    # 3. Construir Timeline de Trazabilidad Unificada (todos los hitos ordenados cronológicamente)
    timeline = []

    # Hito: Notificación / Captación Inicial
    fec_cap = det_captacion.get("fecha") or caso_db.fecha_notificacion
    if fec_cap:
        zk = det_captacion.get("zscore")
        prox = calcular_proxima_cita(fec_cap, zk)
        timeline.append({
            "tipo_hito": "Captación Inicial",
            "icono": "📍",
            "fecha": fec_cap,
            "peso_kg": det_captacion.get("peso_kg"),
            "talla_cm": det_captacion.get("talla_cm"),
            "pb_cm": det_captacion.get("pb_cm"),
            "zscore": zk,
            "clasificacion": clasificar_estado_nutricional(zk),
            "detalle": f"Notificado por {caso_db.cooperante_notificador or caso_db.fuente_notificacion or 'Comunidad'}. Medio: {caso_db.medio_notificacion or 'Sin dato'}.",
            "fuente_notificacion": caso_db.fuente_notificacion,
            "cooperante": caso_db.cooperante_notificador,
            "medio_notificacion": caso_db.medio_notificacion,
            "tipo_afiliacion": caso_db.tipo_afiliacion,
            "tratamiento": None,
            "sobres_ftlc": 0,
            "comorbilidad": None,
            "prueba_apetito": None,
            "escenario_manejo": None,
            "asignacion_interna": None,
            "estado_busqueda": None,
            "novedad": None,
            "observaciones": caso_db.observaciones,
            "fecha_proxima_cita": prox,
            "dias_proxima_cita": 7 if (zk is not None and zk < -2.0) else (15 if (zk is not None and zk < -1.0) else (30 if zk is not None else None))
        })

    # Hito: Búsqueda Activa (GBAI)
    if det_gbai.get("fecha"):
        timeline.append({
            "tipo_hito": "Búsqueda Activa (GBAI)",
            "icono": "🔍",
            "fecha": det_gbai.get("fecha"),
            "detalle": f"Asignación: {det_gbai.get('asignacion') or 'Promotor territorial'}. Estado: {det_gbai.get('estado') or 'Efectiva'}.",
            "peso_kg": None,
            "talla_cm": None,
            "pb_cm": None,
            "zscore": None,
            "clasificacion": None,
            "fuente_notificacion": caso_db.fuente_notificacion,
            "cooperante": None,
            "medio_notificacion": None,
            "tipo_afiliacion": None,
            "tratamiento": None,
            "sobres_ftlc": 0,
            "comorbilidad": None,
            "prueba_apetito": None,
            "escenario_manejo": None,
            "asignacion_interna": det_gbai.get("asignacion"),
            "estado_busqueda": det_gbai.get("estado"),
            "novedad": None,
            "observaciones": None,
            "fecha_proxima_cita": None,
            "dias_proxima_cita": None
        })

    # Hito: Primera Atención Clínica IPSI
    if det_atencion.get("fecha"):
        zk = det_atencion.get("zscore")
        prox = calcular_proxima_cita(det_atencion.get("fecha"), zk)
        timeline.append({
            "tipo_hito": "Primera Atención IPSI",
            "icono": "🏥",
            "fecha": det_atencion.get("fecha"),
            "peso_kg": det_atencion.get("peso_kg"),
            "talla_cm": det_atencion.get("talla_cm"),
            "pb_cm": det_atencion.get("pb_cm"),
            "zscore": zk,
            "clasificacion": clasificar_estado_nutricional(zk),
            "detalle": f"Tratamiento: {det_atencion.get('tratamiento') or 'FTLC'}. Prueba apetito: {det_atencion.get('prueba_apetito') or 'Positiva'}. Escenario: {det_atencion.get('escenario_manejo') or 'Ambulatorio'}.",
            "fuente_notificacion": caso_db.fuente_notificacion,
            "cooperante": caso_db.cooperante_notificador,
            "medio_notificacion": None,
            "tipo_afiliacion": caso_db.tipo_afiliacion,
            "tratamiento": det_atencion.get("tratamiento"),
            "sobres_ftlc": det_atencion.get("sobres_ftlc") or 0,
            "comorbilidad": det_atencion.get("comorbilidad"),
            "prueba_apetito": det_atencion.get("prueba_apetito"),
            "escenario_manejo": det_atencion.get("escenario_manejo"),
            "asignacion_interna": None,
            "estado_busqueda": None,
            "novedad": None,
            "observaciones": None,
            "fecha_proxima_cita": prox,
            "dias_proxima_cita": 7 if (zk is not None and zk < -2.0) else (15 if (zk is not None and zk < -1.0) else (30 if zk is not None else None))
        })

    # Hito: Controles de Seguimiento
    for c in controles_paciente:
        zk = float(c.z_score) if c.z_score is not None else None
        prox = calcular_proxima_cita(c.fecha_control, zk)
        desc_novedad = c.novedad.descripcion if c.novedad else None
        timeline.append({
            "tipo_hito": f"Seguimiento #{c.numero_seguimiento}",
            "icono": "📈",
            "numero_seguimiento": c.numero_seguimiento,
            "fecha": c.fecha_control,
            "peso_kg": float(c.peso_kg) if c.peso_kg else None,
            "talla_cm": float(c.talla_cm) if c.talla_cm else None,
            "pb_cm": float(c.perimetro_braquial_cm) if c.perimetro_braquial_cm else None,
            "zscore": zk,
            "clasificacion": clasificar_estado_nutricional(zk),
            "detalle": f"Tratamiento: {c.tratamiento or 'Continuación'}. {c.observaciones or ''}".strip(),
            "fuente_notificacion": None,
            "cooperante": None,
            "medio_notificacion": None,
            "tipo_afiliacion": None,
            "tratamiento": c.tratamiento,
            "sobres_ftlc": c.sobres_ftlc_entregados or 0,
            "comorbilidad": c.comorbilidad,
            "prueba_apetito": None,
            "escenario_manejo": None,
            "asignacion_interna": None,
            "estado_busqueda": None,
            "novedad": desc_novedad,
            "observaciones": c.observaciones,
            "fecha_proxima_cita": prox,
            "dias_proxima_cita": 7 if (zk is not None and zk < -2.0) else (15 if (zk is not None and zk < -1.0) else (30 if zk is not None else None))
        })

    # Hito: Cierre si aplica
    if caso_db.estado_caso == "Cerrado" and caso_db.fecha_egreso:
        timeline.append({
            "tipo_hito": "Cierre / Egreso",
            "icono": "🏁",
            "fecha": caso_db.fecha_egreso,
            "detalle": f"Motivo: {caso_db.motivo_egreso or 'Cierre formal'}. {caso_db.observaciones or ''}".strip(),
            "peso_kg": None,
            "talla_cm": None,
            "pb_cm": None,
            "zscore": None,
            "clasificacion": None,
            "fuente_notificacion": None,
            "cooperante": None,
            "medio_notificacion": None,
            "tipo_afiliacion": None,
            "tratamiento": None,
            "sobres_ftlc": 0,
            "comorbilidad": None,
            "prueba_apetito": None,
            "escenario_manejo": None,
            "asignacion_interna": None,
            "estado_busqueda": None,
            "motivo_egreso": caso_db.motivo_egreso,
            "novedad": None,
            "observaciones": caso_db.observaciones,
            "fecha_proxima_cita": None,
            "dias_proxima_cita": None
        })

    # Ordenar estrictamente la línea de tiempo por fecha cronológica
    timeline.sort(key=lambda x: str(x["fecha"]))

    # Calcular variaciones acumuladas (delta_peso_kg y delta_zscore) respecto al hito previo
    ultimo_peso = None
    ultimo_z = None
    for h in timeline:
        if h.get("peso_kg") is not None:
            if ultimo_peso is not None:
                h["delta_peso_kg"] = round(h["peso_kg"] - ultimo_peso, 2)
            else:
                h["delta_peso_kg"] = 0.0
            ultimo_peso = h["peso_kg"]
        else:
            h["delta_peso_kg"] = None

        if h.get("zscore") is not None:
            if ultimo_z is not None:
                h["delta_zscore"] = round(h["zscore"] - ultimo_z, 2)
            else:
                h["delta_zscore"] = 0.0
            ultimo_z = h["zscore"]
        else:
            h["delta_zscore"] = None

    # Actualizar conteo de controles en el resumen si había desfasaje
    resumen["total_controles"] = len(controles_paciente)

    return {
        "resumen": resumen,
        "total_episodios_paciente": len(todos_episodios),
        "episodios": lista_episodios,
        "detalle_notificacion": {
            "caso_id": caso_db.caso_id,
            "paciente_id": caso_db.paciente_id,
            "fuente_notificacion": caso_db.fuente_notificacion,
            "fecha_notificacion": caso_db.fecha_notificacion,
            "cooperante_notificador": caso_db.cooperante_notificador,
            "medio_notificacion": caso_db.medio_notificacion,
            "tipo_afiliacion": caso_db.tipo_afiliacion,
            "captacion_inicial": det_captacion,
            "gbai": det_gbai,
            "primera_atencion": det_atencion,
            "estado_caso": caso_db.estado_caso,
            "motivo_egreso": caso_db.motivo_egreso,
            "fecha_egreso": caso_db.fecha_egreso,
            "observaciones": caso_db.observaciones
        },
        "timeline_trazabilidad": timeline
    }

@router.get("/{caso_id}/imprimir", response_class=HTMLResponse)
def imprimir_expediente_clinico(
    caso_id: int,
    autoprint: bool = Query(False, description="Activa el diálogo de impresión automáticamente al abrir"),
    db: Session = Depends(get_db)
):
    """
    Genera y retorna la vista oficial de Historia Clínica e Informe Longitudinal Imprimible (PDF/Papel)
    conforme a la Resolución 000115 de 2026 para la IPSI Kottushi Sao Ana>a.
    """
    data = obtener_caso(caso_id, db)
    html_content = generar_html_expediente_imprimible(data, autoprint=autoprint)
    return HTMLResponse(content=html_content)

@router.post("", status_code=201)
def crear_caso(caso_in: NotificacionCasoCreate, db: Session = Depends(get_db)):
    """
    Crea o vincula un paciente existente por `numero_documento` y abre un nuevo episodio en `notificaciones_caso`.
    """
    paciente_data = caso_in.paciente
    cuidador_id = None
    if paciente_data.cuidador:
        c_data = paciente_data.cuidador
        if c_data.documento_cuidador:
            cuidador = db.query(Cuidador).filter(Cuidador.documento_cuidador == c_data.documento_cuidador).first()
            if cuidador:
                cuidador.nombre_completo = c_data.nombre_completo
                cuidador.telefono = c_data.telefono or cuidador.telefono
                cuidador.notas_contacto = c_data.notas_contacto or cuidador.notas_contacto
                cuidador_id = cuidador.cuidador_id
        if not cuidador_id:
            nuevo_c = Cuidador(
                documento_cuidador=c_data.documento_cuidador,
                nombre_completo=c_data.nombre_completo,
                telefono=c_data.telefono,
                notas_contacto=c_data.notas_contacto
            )
            db.add(nuevo_c)
            db.flush()
            cuidador_id = nuevo_c.cuidador_id

    paciente = db.query(Paciente).filter(Paciente.numero_documento == paciente_data.numero_documento).first()
    if paciente:
        paciente.primer_nombre = paciente_data.primer_nombre
        paciente.segundo_nombre = paciente_data.segundo_nombre
        paciente.primer_apellido = paciente_data.primer_apellido
        paciente.segundo_apellido = paciente_data.segundo_apellido
        paciente.sexo = paciente_data.sexo
        paciente.municipio_id = paciente_data.municipio_id or paciente.municipio_id
        paciente.georreferenciacion = paciente_data.georreferenciacion or paciente.georreferenciacion
        if cuidador_id:
            paciente.cuidador_id = cuidador_id
        db.flush()
    else:
        paciente = Paciente(
            tipo_documento=paciente_data.tipo_documento,
            numero_documento=paciente_data.numero_documento,
            primer_nombre=paciente_data.primer_nombre,
            segundo_nombre=paciente_data.segundo_nombre,
            primer_apellido=paciente_data.primer_apellido,
            segundo_apellido=paciente_data.segundo_apellido,
            sexo=paciente_data.sexo,
            fecha_nacimiento=paciente_data.fecha_nacimiento,
            cuidador_id=cuidador_id,
            municipio_id=paciente_data.municipio_id,
            georreferenciacion=paciente_data.georreferenciacion
        )
        db.add(paciente)
        db.flush()

    nuevo_caso = NotificacionCaso(
        paciente_id=paciente.paciente_id,
        fuente_notificacion=caso_in.fuente_notificacion,
        fecha_notificacion=caso_in.fecha_notificacion or date.today(),
        cooperante_notificador=caso_in.cooperante_notificador,
        medio_notificacion=caso_in.medio_notificacion,
        eapb_id=caso_in.eapb_id,
        tipo_afiliacion=caso_in.tipo_afiliacion,
        ips_primaria_id=caso_in.ips_primaria_id,
        fecha_captacion=caso_in.fecha_captacion,
        peso_inicial_kg=caso_in.peso_inicial_kg,
        talla_inicial_cm=caso_in.talla_inicial_cm,
        pb_inicial_cm=caso_in.pb_inicial_cm,
        zscore_inicial=caso_in.zscore_inicial,
        fecha_busqueda_gbai=caso_in.fecha_busqueda_gbai,
        asignacion_interna=caso_in.asignacion_interna,
        estado_busqueda=caso_in.estado_busqueda,
        fecha_primera_atencion=caso_in.fecha_primera_atencion,
        peso_atencion_kg=caso_in.peso_atencion_kg,
        talla_atencion_cm=caso_in.talla_atencion_cm,
        pb_atencion_cm=caso_in.pb_atencion_cm,
        zscore_atencion=caso_in.zscore_atencion,
        prueba_apetito=caso_in.prueba_apetito,
        tratamiento_inicial=caso_in.tratamiento_inicial,
        sobres_ftlc_inicial=caso_in.sobres_ftlc_inicial,
        comorbilidad_inicial=caso_in.comorbilidad_inicial,
        escenario_manejo=caso_in.escenario_manejo,
        estado_caso=caso_in.estado_caso or "En seguimiento",
        observaciones=caso_in.observaciones
    )
    db.add(nuevo_caso)
    db.commit()
    db.refresh(nuevo_caso)

    return {"mensaje": "Caso creado exitosamente", "caso_id": nuevo_caso.caso_id, "paciente_id": paciente.paciente_id}

@router.patch("/{caso_id}/cerrar")
def cerrar_caso(caso_id: int, request: CasoCerrarRequest, db: Session = Depends(get_db)):
    """
    Cierra formalmente un caso clínico registrando `motivo_egreso` y `fecha_egreso`.
    """
    caso = db.query(NotificacionCaso).filter(NotificacionCaso.caso_id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")

    caso.estado_caso = "Cerrado"
    caso.motivo_egreso = request.motivo_egreso
    caso.fecha_egreso = request.fecha_egreso or date.today()
    if request.observaciones:
        caso.observaciones = f"{caso.observaciones or ''}\n[Cierre]: {request.observaciones}".strip()

    db.commit()
    return {"mensaje": f"Caso {caso_id} cerrado exitosamente", "estado_caso": caso.estado_caso, "fecha_egreso": caso.fecha_egreso}
