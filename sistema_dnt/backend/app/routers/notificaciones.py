"""
Router para el Libro y Registro de Notificados (Formato FT-003)
Sistema de Vigilancia y Seguimiento Nutricional
IPSI Kottushi Sao Ana>a
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from io import BytesIO
import os
import xlsxwriter
import pandas as pd
from pydantic import BaseModel

from app.database import get_db
from app.models import NotificacionCaso, Paciente, Cuidador
from app.services import clasificar_estado_nutricional

router = APIRouter(prefix="/api/notificaciones", tags=["Libro de Notificados (FT-003)"])

class NotificacionUpdateRequest(BaseModel):
    fuente_notificacion: Optional[str] = None
    fecha_notificacion: Optional[date] = None
    cooperante_notificador: Optional[str] = None
    medio_notificacion: Optional[str] = None
    fecha_captacion: Optional[date] = None
    peso_inicial_kg: Optional[float] = None
    talla_inicial_cm: Optional[float] = None
    pb_inicial_cm: Optional[float] = None
    zscore_inicial: Optional[float] = None
    fecha_busqueda_gbai: Optional[date] = None
    asignacion_interna: Optional[str] = None
    estado_busqueda: Optional[str] = None
    fecha_primera_atencion: Optional[date] = None
    peso_atencion_kg: Optional[float] = None
    talla_atencion_cm: Optional[float] = None
    pb_atencion_cm: Optional[float] = None
    zscore_atencion: Optional[float] = None
    prueba_apetito: Optional[str] = None
    tratamiento_inicial: Optional[str] = None
    sobres_ftlc_inicial: Optional[int] = None
    comorbilidad_inicial: Optional[str] = None
    escenario_manejo: Optional[str] = None
    estado_caso: Optional[str] = None
    observaciones: Optional[str] = None
    telefono_cuidador: Optional[str] = None
    cuidador: Optional[str] = None
    georreferenciacion: Optional[str] = None

@router.get("/resumen-kpis")
def obtener_resumen_kpis_notificados(db: Session = Depends(get_db)):
    """
    Retorna métricas clave del libro de notificados:
    Total de notificaciones, distribución por evento SIVIGILA (113 vs 114),
    primera atención y gestión comunitaria GBAI.
    """
    tot_notif = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso")).scalar() or 0
    tot_113 = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE fuente_notificacion ILIKE '%113%'")).scalar() or 0
    tot_114 = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE fuente_notificacion ILIKE '%114%'")).scalar() or 0
    
    con_1ra = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE fecha_primera_atencion IS NOT NULL")).scalar() or 0
    sin_1ra = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE fecha_primera_atencion IS NULL")).scalar() or 0
    
    en_gbai = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE estado_busqueda ILIKE '%busqueda%' OR estado_busqueda ILIKE '%búsqueda%' OR estado_caso = 'En Busqueda'")).scalar() or 0
    en_seg = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE estado_caso = 'En seguimiento'")).scalar() or 0
    cerrados = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE estado_caso = 'Cerrado'")).scalar() or 0

    return {
        "total_notificados": tot_notif,
        "evento_113_dnt": tot_113,
        "evento_114_riesgo": tot_114,
        "con_primera_atencion": con_1ra,
        "sin_primera_atencion": sin_1ra,
        "en_busqueda_gbai": en_gbai,
        "en_seguimiento": en_seg,
        "cerrados": cerrados
    }

@router.get("")
def listar_notificados(
    response: Response,
    evento: Optional[str] = Query(None, description="Filtro por evento SIVIGILA: '113' o '114'"),
    municipio: Optional[str] = Query(None, description="Filtro por municipio"),
    eapb: Optional[str] = Query(None, description="Filtro por EAPB / EPS"),
    estado_caso: Optional[str] = Query(None, description="Filtro por estado: 'En seguimiento', 'Cerrado', etc."),
    primera_atencion: Optional[str] = Query(None, description="'con' o 'sin' primera atención"),
    busqueda: Optional[str] = Query(None, description="Búsqueda por documento, nombre o cooperante"),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de notificaciones del libro oficial FT-003 con todos los campos clínicos,
    demográficos, de captación inicial, GBAI y primera atención.
    """
    where_clauses = ["1=1"]
    params = {}

    if evento:
        where_clauses.append("c.fuente_notificacion ILIKE :evento")
        params["evento"] = f"%{evento}%"

    if municipio:
        where_clauses.append("m.nombre ILIKE :municipio")
        params["municipio"] = f"%{municipio}%"

    if eapb:
        where_clauses.append("e.nombre ILIKE :eapb")
        params["eapb"] = f"%{eapb}%"

    if estado_caso:
        where_clauses.append("c.estado_caso ILIKE :estado_caso")
        params["estado_caso"] = f"%{estado_caso}%"

    if primera_atencion == "con":
        where_clauses.append("c.fecha_primera_atencion IS NOT NULL")
    elif primera_atencion == "sin":
        where_clauses.append("c.fecha_primera_atencion IS NULL")

    if busqueda:
        where_clauses.append("""(
            p.numero_documento ILIKE :busq OR
            CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido) ILIKE :busq OR
            cu.nombre_completo ILIKE :busq OR
            c.cooperante_notificador ILIKE :busq
        )""")
        params["busq"] = f"%{busqueda}%"

    where_sql = " AND ".join(where_clauses)

    # Conteo total real
    count_sql = f"""
        SELECT COUNT(*)
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cat_eapb e ON c.eapb_id = e.eapb_id
        LEFT JOIN cuidadores cu ON p.cuidador_id = cu.cuidador_id
        WHERE {where_sql}
    """
    total_count = db.execute(text(count_sql), params).scalar() or 0

    # Consulta paginada
    select_sql = f"""
        SELECT 
            c.caso_id,
            c.paciente_id,
            c.fuente_notificacion,
            c.fecha_notificacion,
            c.cooperante_notificador,
            c.medio_notificacion,
            c.tipo_afiliacion,
            e.nombre AS eapb,
            s.nombre AS sede_ipsi,
            m.nombre AS municipio,
            p.tipo_documento,
            p.numero_documento,
            CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido) AS nombre_completo,
            p.sexo,
            p.fecha_nacimiento,
            p.georreferenciacion,
            EXTRACT(YEAR FROM age(c.fecha_notificacion, p.fecha_nacimiento)) * 12 + 
            EXTRACT(MONTH FROM age(c.fecha_notificacion, p.fecha_nacimiento)) AS edad_meses_notificacion,
            EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + 
            EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)) AS edad_meses_actual,
            cu.nombre_completo AS cuidador,
            cu.documento_cuidador,
            cu.telefono AS telefono_cuidador,
            c.fecha_captacion,
            c.peso_inicial_kg,
            c.talla_inicial_cm,
            c.pb_inicial_cm,
            c.zscore_inicial,
            c.fecha_busqueda_gbai,
            c.asignacion_interna,
            c.estado_busqueda,
            c.fecha_primera_atencion,
            c.peso_atencion_kg,
            c.talla_atencion_cm,
            c.pb_atencion_cm,
            c.zscore_atencion,
            c.prueba_apetito,
            c.tratamiento_inicial,
            c.sobres_ftlc_inicial,
            c.comorbilidad_inicial,
            c.escenario_manejo,
            c.estado_caso,
            c.motivo_egreso,
            c.fecha_egreso,
            c.observaciones
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cat_eapb e ON c.eapb_id = e.eapb_id
        LEFT JOIN cat_sedes_ipsi s ON c.ips_primaria_id = s.sede_id
        LEFT JOIN cuidadores cu ON p.cuidador_id = cu.cuidador_id
        WHERE {where_sql}
        ORDER BY c.caso_id DESC
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(text(select_sql), params).mappings().fetchall()
    
    items = []
    for r in rows:
        d = dict(r)
        z_ini = float(d["zscore_inicial"]) if d["zscore_inicial"] is not None else None
        z_atn = float(d["zscore_atencion"]) if d["zscore_atencion"] is not None else None
        
        d["clasificacion_inicial"] = clasificar_estado_nutricional(z_ini)
        d["clasificacion_atencion"] = clasificar_estado_nutricional(z_atn)
        
        # Alertas normativas
        edad_notif = d.get("edad_meses_notificacion")
        edad_act = d.get("edad_meses_actual")
        d["alerta_ingreso_fuera_rango"] = bool(edad_notif is not None and edad_notif > 59)
        d["alerta_egreso_edad"] = bool(edad_act is not None and edad_act >= 60 and d.get("estado_caso") == "En seguimiento")
        
        items.append(d)

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count, X-Limit, X-Offset"

    return items

@router.get("/exportar-excel")
def exportar_notificados_excel(db: Session = Depends(get_db)):
    """
    Genera la exportación en Excel estructurada del Libro de Notificados (FT-003)
    fiel al formato original institucional, incluyendo cabecera institucional,
    logo de la IPSI, numeración de columnas y paleta de colores por bloque.
    """
    query = """
        SELECT 
            c.caso_id,
            c.fuente_notificacion,
            c.fecha_notificacion,
            c.cooperante_notificador,
            c.medio_notificacion,
            m.nombre AS municipio,
            p.tipo_documento,
            p.numero_documento,
            p.primer_nombre,
            p.segundo_nombre,
            p.primer_apellido,
            p.segundo_apellido,
            p.sexo,
            p.fecha_nacimiento,
            EXTRACT(YEAR FROM age(c.fecha_notificacion, p.fecha_nacimiento)) * 12 + 
            EXTRACT(MONTH FROM age(c.fecha_notificacion, p.fecha_nacimiento)) AS edad_meses_notificacion,
            EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + 
            EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)) AS edad_meses_actual,
            e.nombre AS eapb,
            c.tipo_afiliacion,
            s.nombre AS sede_ipsi,
            p.georreferenciacion,
            cu.nombre_completo AS cuidador,
            cu.documento_cuidador,
            cu.telefono AS telefono_cuidador,
            c.fecha_captacion,
            c.peso_inicial_kg,
            c.talla_inicial_cm,
            c.pb_inicial_cm,
            c.zscore_inicial,
            c.fecha_busqueda_gbai,
            c.asignacion_interna,
            c.estado_busqueda,
            c.fecha_primera_atencion,
            c.peso_atencion_kg,
            c.talla_atencion_cm,
            c.pb_atencion_cm,
            c.zscore_atencion,
            c.prueba_apetito,
            c.tratamiento_inicial,
            c.sobres_ftlc_inicial,
            c.comorbilidad_inicial,
            c.estado_caso,
            c.observaciones
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cat_eapb e ON c.eapb_id = e.eapb_id
        LEFT JOIN cat_sedes_ipsi s ON c.ips_primaria_id = s.sede_id
        LEFT JOIN cuidadores cu ON p.cuidador_id = cu.cuidador_id
        ORDER BY c.caso_id ASC
    """
    rows = db.execute(text(query)).mappings().fetchall()

    columnas_def = [
        {"nombre": "Num", "ancho": 7, "color": "#7F7F7F"},
        {"nombre": "Fuente de Notificación ", "ancho": 18, "color": "#15A7A0"},
        {"nombre": "Fecha Notificación ", "ancho": 13, "color": "#15A7A0"},
        {"nombre": "Nombre del cooperante o fundacion que realiza la Notificación", "ancho": 28, "color": "#15A7A0"},
        {"nombre": "Medio de Notificación ", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Municipio", "ancho": 16, "color": "#15A7A0"},
        {"nombre": "Tipo ID", "ancho": 10, "color": "#15A7A0"},
        {"nombre": "Numero Id", "ancho": 15, "color": "#15A7A0"},
        {"nombre": "Primer Nombre", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Segundo Nombre", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Primer Apellido", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Segundo Apellido", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Sexo", "ancho": 8, "color": "#15A7A0"},
        {"nombre": "Fecha Nacimiento", "ancho": 13, "color": "#15A7A0"},
        {"nombre": "Edad Meses Notificacion", "ancho": 13, "color": "#7F7F7F"},
        {"nombre": "Edad Actual Meses", "ancho": 13, "color": "#7F7F7F"},
        {"nombre": "EAPB", "ancho": 20, "color": "#15A7A0"},
        {"nombre": "Tipo Afiliacion", "ancho": 13, "color": "#15A7A0"},
        {"nombre": "IPS Atencion Primaria", "ancho": 26, "color": "#15A7A0"},
        {"nombre": "Georeferenciacion Notificada", "ancho": 24, "color": "#15A7A0"},
        {"nombre": "Nombre Cuidador", "ancho": 18, "color": "#15A7A0"},
        {"nombre": "Doc Cuidador", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Telefono", "ancho": 18, "color": "#15A7A0"},
        {"nombre": "Fecha Captación Inicial", "ancho": 14, "color": "#F79646"},
        {"nombre": "Peso Inicial kg", "ancho": 12, "color": "#F79646"},
        {"nombre": "Talla Inicial cm", "ancho": 12, "color": "#F79646"},
        {"nombre": "PB Inicial cm", "ancho": 11, "color": "#F79646"},
        {"nombre": "Zscore Inicial", "ancho": 11, "color": "#F79646"},
        {"nombre": "Clasificacion Nutricional Inicial", "ancho": 26, "color": "#7F7F7F"},
        {"nombre": "Fecha  de Busquedad por la IPSI\nGBAI", "ancho": 14, "color": "#15A7A0"},
        {"nombre": "Actualizacion y/o Confirmación\n Georreferenciacion por la IPSI", "ancho": 26, "color": "#15A7A0"},
        {"nombre": "Asignacion interna ", "ancho": 16, "color": "#15A7A0"},
        {"nombre": "Estado de a BUSQUEDA", "ancho": 16, "color": "#C66B24"},
        {"nombre": "Fecha de la Primera Atención por la IPSI ", "ancho": 14, "color": "#C66B24"},
        {"nombre": "Peso\n(kg)", "ancho": 11, "color": "#C66B24"},
        {"nombre": "Talla\n(cm)", "ancho": 11, "color": "#C66B24"},
        {"nombre": "Perímetro braquial (cm)", "ancho": 12, "color": "#C66B24"},
        {"nombre": "Z-Score", "ancho": 11, "color": "#C66B24"},
        {"nombre": "Diagnóstico Nutricional Primera Atención por la IPSI", "ancho": 28, "color": "#7F7F7F"},
        {"nombre": "Prueba de Apetito", "ancho": 14, "color": "#C66B24"},
        {"nombre": "Tratamiento Inicial ", "ancho": 16, "color": "#C66B24"},
        {"nombre": "Formula Terapeutica entregada \n(Num. Sobres)", "ancho": 15, "color": "#C66B24"},
        {"nombre": "Comorbilidad - Observacaion ", "ancho": 18, "color": "#C66B24"},
        {"nombre": "Estado Actual ", "ancho": 14, "color": "#C66B24"},
        {"nombre": "Conducta ", "ancho": 16, "color": "#C66B24"},
        {"nombre": "Observaciones", "ancho": 28, "color": "#C66B24"},
        {"nombre": "Ingresó con edad > 59 meses", "ancho": 16, "color": "#7F7F7F"},
        {"nombre": "Debe salir de la Ruta (edad actual ≥ 60 meses)", "ancho": 16, "color": "#7F7F7F"}
    ]

    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('Notificados')

    # Configuración de página y vista
    ws.hide_gridlines(False)
    ws.set_tab_color('#15A7A0')

    # Formatos de cabecera institucional
    fmt_titulo = wb.add_format({
        'bold': True, 'font_size': 13, 'font_name': 'Calibri',
        'align': 'center', 'valign': 'vcenter', 'border': 1
    })
    fmt_macro = wb.add_format({
        'bold': True, 'font_size': 9, 'font_name': 'Calibri',
        'align': 'left', 'valign': 'vcenter', 'border': 1
    })
    fmt_calidad = wb.add_format({
        'font_size': 8, 'font_name': 'Calibri',
        'align': 'left', 'valign': 'vcenter', 'border': 1
    })
    fmt_calidad_bold = wb.add_format({
        'bold': True, 'font_size': 8, 'font_name': 'Calibri',
        'align': 'left', 'valign': 'vcenter', 'border': 1
    })
    fmt_num_col = wb.add_format({
        'bold': True, 'font_size': 9, 'font_name': 'Calibri',
        'align': 'center', 'valign': 'vcenter', 'bg_color': '#F2F2F2', 'border': 1
    })
    fmt_subtotal = wb.add_format({
        'bold': True, 'font_size': 9, 'font_name': 'Calibri',
        'align': 'center', 'valign': 'vcenter'
    })

    # Logo institucional en A1:B4
    logo_path = os.path.abspath('sistema_dnt/backend/app/static/logo_ipsi.png')
    if os.path.exists(logo_path):
        ws.merge_range('A1:B4', '', fmt_titulo)
        ws.insert_image('A1', logo_path, {'x_scale': 0.75, 'y_scale': 0.75, 'x_offset': 8, 'y_offset': 6})
    else:
        ws.merge_range('A1:B4', 'IPSI KOTTUSHI SAO ANA>A', fmt_titulo)

    # Título central y Macroproceso
    ws.merge_range('C1:O3', 'REGISTRO DE NOTIFICACION DE PACIENTES CON DESNUTRICIÓN Y RIESGO DE DESNUTRICIÓN', fmt_titulo)
    ws.merge_range('C4:F4', 'MACROPROCESO:  MISIONAL', fmt_macro)
    ws.merge_range('G4:O4', 'PROCESO:  RUTAS INTEGRALES DE ATENCIÓN', fmt_macro)

    # Bloque de calidad P1:R4
    ws.merge_range('P1:R1', 'DESCRIPCION', fmt_calidad_bold)
    ws.merge_range('P2:R2', 'Fecha: 2026-08-26', fmt_calidad)
    ws.merge_range('P3:R3', 'Versión: 02', fmt_calidad)
    ws.merge_range('P4:R4', 'Codigo: PM-RIA-FT-003', fmt_calidad_bold)

    # Fila 5: Separador
    ws.set_row(4, 12)

    # Fila 6: Numeración de columnas (1..48)
    ws.set_row(5, 14.25)
    for idx in range(len(columnas_def)):
        ws.write(5, idx, idx + 1, fmt_num_col)

    # Fila 7: Subtotal dinámico de conteo
    ws.set_row(6, 14.25)
    total_filas = len(rows) + 8
    ws.write_formula(6, 7, f'=SUBTOTAL(3,H9:H{total_filas})', fmt_subtotal)

    # Fila 8: Encabezados de Columna oficiales con sus colores
    ws.set_row(7, 54.75)
    header_formats = {}
    for idx, c in enumerate(columnas_def):
        bg = c['color']
        if bg not in header_formats:
            header_formats[bg] = wb.add_format({
                'bold': True, 'font_size': 9, 'font_name': 'Calibri',
                'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
                'bg_color': bg, 'font_color': '#FFFFFF', 'border': 1
            })
        ws.write(7, idx, c['nombre'], header_formats[bg])
        ws.set_column(idx, idx, c['ancho'])

    # Formatos de celdas de datos
    fmt_text_left = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9'})
    fmt_text_center = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9'})
    fmt_text_right = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9'})
    fmt_num_dec2 = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9', 'num_format': '0.00'})
    fmt_num_dec1 = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'right', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9', 'num_format': '0.0'})
    fmt_num_int = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9', 'num_format': '0'})
    fmt_date = wb.add_format({'font_size': 9, 'font_name': 'Segoe UI', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#D9D9D9', 'num_format': 'yyyy-mm-dd'})

    # Llenado de Filas de Pacientes (Fila 9 en adelante)
    for r_idx, r in enumerate(rows):
        row_num = 8 + r_idx
        ws.set_row(row_num, 18)

        z_ini = float(r["zscore_inicial"]) if r["zscore_inicial"] is not None else None
        clasif_ini = clasificar_estado_nutricional(z_ini) if z_ini is not None else ""

        z_atn = float(r["zscore_atencion"]) if r["zscore_atencion"] is not None else None
        clasif_atn = clasificar_estado_nutricional(z_atn) if z_atn is not None else ""

        fuente = r.get("fuente_notificacion") or ""
        conducta = "Control en 8 días" if "113" in fuente else ("Control en 15 días" if "114" in fuente else "Seguimiento normativo")

        edad_notif = r.get("edad_meses_notificacion")
        ingreso_59 = "SI" if edad_notif is not None and edad_notif > 59 else "NO"

        edad_act = r.get("edad_meses_actual")
        egreso_60 = "SI" if edad_act is not None and edad_act >= 60 else "NO"

        # 1. Num
        ws.write_number(row_num, 0, r_idx + 1, fmt_num_int)
        # 2. Fuente Notificación
        ws.write_string(row_num, 1, str(r.get("fuente_notificacion") or ""), fmt_text_left)
        # 3. Fecha Notificación
        if r.get("fecha_notificacion"):
            ws.write_string(row_num, 2, str(r["fecha_notificacion"]), fmt_date)
        else:
            ws.write_blank(row_num, 2, None, fmt_text_center)
        # 4. Cooperante
        ws.write_string(row_num, 3, str(r.get("cooperante_notificador") or ""), fmt_text_left)
        # 5. Medio
        ws.write_string(row_num, 4, str(r.get("medio_notificacion") or ""), fmt_text_center)
        # 6. Municipio
        ws.write_string(row_num, 5, str(r.get("municipio") or ""), fmt_text_left)
        # 7. Tipo ID
        ws.write_string(row_num, 6, str(r.get("tipo_documento") or "RC"), fmt_text_center)
        # 8. Numero Id
        ws.write_string(row_num, 7, str(r.get("numero_documento") or ""), fmt_text_center)
        # 9-12. Nombres
        ws.write_string(row_num, 8, str(r.get("primer_nombre") or ""), fmt_text_left)
        ws.write_string(row_num, 9, str(r.get("segundo_nombre") or ""), fmt_text_left)
        ws.write_string(row_num, 10, str(r.get("primer_apellido") or ""), fmt_text_left)
        ws.write_string(row_num, 11, str(r.get("segundo_apellido") or ""), fmt_text_left)
        # 13. Sexo
        ws.write_string(row_num, 12, str(r.get("sexo") or ""), fmt_text_center)
        # 14. Fecha Nacimiento
        if r.get("fecha_nacimiento"):
            ws.write_string(row_num, 13, str(r["fecha_nacimiento"]), fmt_date)
        else:
            ws.write_blank(row_num, 13, None, fmt_text_center)
        # 15. Edad Meses Notif
        if edad_notif is not None:
            ws.write_number(row_num, 14, int(edad_notif), fmt_num_int)
        else:
            ws.write_blank(row_num, 14, None, fmt_text_center)
        # 16. Edad Actual Meses
        if edad_act is not None:
            ws.write_number(row_num, 15, int(edad_act), fmt_num_int)
        else:
            ws.write_blank(row_num, 15, None, fmt_text_center)
        # 17. EAPB
        ws.write_string(row_num, 16, str(r.get("eapb") or ""), fmt_text_left)
        # 18. Tipo Afiliación
        ws.write_string(row_num, 17, str(r.get("tipo_afiliacion") or ""), fmt_text_center)
        # 19. Sede IPS Primaria
        ws.write_string(row_num, 18, str(r.get("sede_ipsi") or ""), fmt_text_left)
        # 20. Georreferenciación
        ws.write_string(row_num, 19, str(r.get("georreferenciacion") or ""), fmt_text_left)
        # 21. Nombre Cuidador
        ws.write_string(row_num, 20, str(r.get("cuidador") or ""), fmt_text_left)
        # 22. Doc Cuidador
        ws.write_string(row_num, 21, str(r.get("documento_cuidador") or ""), fmt_text_center)
        # 23. Teléfono
        ws.write_string(row_num, 22, str(r.get("telefono_cuidador") or ""), fmt_text_center)
        # 24. Fecha Captación
        if r.get("fecha_captacion"):
            ws.write_string(row_num, 23, str(r["fecha_captacion"]), fmt_date)
        else:
            ws.write_blank(row_num, 23, None, fmt_text_center)
        # 25. Peso Inicial
        if r.get("peso_inicial_kg") is not None:
            ws.write_number(row_num, 24, float(r["peso_inicial_kg"]), fmt_num_dec2)
        else:
            ws.write_blank(row_num, 24, None, fmt_text_right)
        # 26. Talla Inicial
        if r.get("talla_inicial_cm") is not None:
            ws.write_number(row_num, 25, float(r["talla_inicial_cm"]), fmt_num_dec1)
        else:
            ws.write_blank(row_num, 25, None, fmt_text_right)
        # 27. PB Inicial
        if r.get("pb_inicial_cm") is not None:
            ws.write_number(row_num, 26, float(r["pb_inicial_cm"]), fmt_num_dec1)
        else:
            ws.write_blank(row_num, 26, None, fmt_text_right)
        # 28. Z-Score Inicial
        if z_ini is not None:
            ws.write_number(row_num, 27, z_ini, fmt_num_dec2)
        else:
            ws.write_blank(row_num, 27, None, fmt_text_right)
        # 29. Clasificación Inicial
        ws.write_string(row_num, 28, clasif_ini, fmt_text_center)
        # 30. Fecha Búsqueda GBAI
        if r.get("fecha_busqueda_gbai"):
            ws.write_string(row_num, 29, str(r["fecha_busqueda_gbai"]), fmt_date)
        else:
            ws.write_blank(row_num, 29, None, fmt_text_center)
        # 31. Actualización Georreferenciación
        ws.write_string(row_num, 30, str(r.get("georreferenciacion") or ""), fmt_text_left)
        # 32. Asignación Interna
        ws.write_string(row_num, 31, str(r.get("asignacion_interna") or ""), fmt_text_left)
        # 33. Estado Búsqueda
        ws.write_string(row_num, 32, str(r.get("estado_busqueda") or ""), fmt_text_center)
        # 34. Fecha 1ra Atención
        if r.get("fecha_primera_atencion"):
            ws.write_string(row_num, 33, str(r["fecha_primera_atencion"]), fmt_date)
        else:
            ws.write_blank(row_num, 33, None, fmt_text_center)
        # 35. Peso 1ra Atención
        if r.get("peso_atencion_kg") is not None:
            ws.write_number(row_num, 34, float(r["peso_atencion_kg"]), fmt_num_dec2)
        else:
            ws.write_blank(row_num, 34, None, fmt_text_right)
        # 36. Talla 1ra Atención
        if r.get("talla_atencion_cm") is not None:
            ws.write_number(row_num, 35, float(r["talla_atencion_cm"]), fmt_num_dec1)
        else:
            ws.write_blank(row_num, 35, None, fmt_text_right)
        # 37. PB 1ra Atención
        if r.get("pb_atencion_cm") is not None:
            ws.write_number(row_num, 36, float(r["pb_atencion_cm"]), fmt_num_dec1)
        else:
            ws.write_blank(row_num, 36, None, fmt_text_right)
        # 38. Z-Score 1ra Atención
        if z_atn is not None:
            ws.write_number(row_num, 37, z_atn, fmt_num_dec2)
        else:
            ws.write_blank(row_num, 37, None, fmt_text_right)
        # 39. Diagnóstico 1ra Atención
        ws.write_string(row_num, 38, clasif_atn, fmt_text_center)
        # 40. Prueba Apetito
        ws.write_string(row_num, 39, str(r.get("prueba_apetito") or ""), fmt_text_center)
        # 41. Tratamiento Inicial
        ws.write_string(row_num, 40, str(r.get("tratamiento_inicial") or ""), fmt_text_left)
        # 42. Sobres FTLC
        if r.get("sobres_ftlc_inicial") is not None:
            ws.write_number(row_num, 41, int(r["sobres_ftlc_inicial"]), fmt_num_int)
        else:
            ws.write_blank(row_num, 41, None, fmt_text_center)
        # 43. Comorbilidad
        ws.write_string(row_num, 42, str(r.get("comorbilidad_inicial") or ""), fmt_text_left)
        # 44. Estado Actual
        ws.write_string(row_num, 43, str(r.get("estado_caso") or ""), fmt_text_center)
        # 45. Conducta
        ws.write_string(row_num, 44, conducta, fmt_text_left)
        # 46. Observaciones
        ws.write_string(row_num, 45, str(r.get("observaciones") or ""), fmt_text_left)
        # 47. Ingresó > 59m
        ws.write_string(row_num, 46, ingreso_59, fmt_text_center)
        # 48. Debe salir ≥ 60m
        ws.write_string(row_num, 47, egreso_60, fmt_text_center)

    # =========================================================================
    # REGLAS DE FORMATO CONDICIONAL OFICIALES (IDÉNTICAS AL EXCEL ORIGINAL)
    # =========================================================================
    first_data_row = 8
    last_data_row = total_filas - 1

    # Formatos de estilos diferenciales para diagnósticos
    fmt_cf_severa = wb.add_format({'bg_color': '#F8D0CE', 'font_color': '#9B1C13', 'bold': True})
    fmt_cf_moderada = wb.add_format({'bg_color': '#FDECC8', 'font_color': '#E46C0A', 'bold': True})
    fmt_cf_riesgo = wb.add_format({'bg_color': '#FCF3CF', 'font_color': '#7A5B00', 'bold': True})
    fmt_cf_adecuado = wb.add_format({'bg_color': '#D9EFE9', 'font_color': '#0E6E6A', 'bold': True})
    fmt_cf_fuera_rango = wb.add_format({'bg_color': '#F2F2F2', 'font_color': '#808080', 'bold': True})

    # Formatos para edad
    fmt_cf_edad_egreso = wb.add_format({'bg_color': '#F8D0CE', 'font_color': '#953735', 'bold': True})
    fmt_cf_edad_norma = wb.add_format({'bg_color': '#D9EFE9', 'font_color': '#008080', 'bold': False})

    # Formatos para alertas SI / NO
    fmt_cf_alerta_roja = wb.add_format({'bg_color': '#F8D0CE', 'font_color': '#9B1C13', 'bold': True})
    fmt_cf_alerta_naranja = wb.add_format({'bg_color': '#FDECC8', 'font_color': '#8A5A00', 'bold': True})

    # Formato para valores duplicados
    fmt_cf_duplicado = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

    # Formatos para Estado Actual
    fmt_cf_estado_seg = wb.add_format({'bg_color': '#E0F2FE', 'font_color': '#0369A1', 'bold': True})
    fmt_cf_estado_cerrado = wb.add_format({'bg_color': '#F1F5F9', 'font_color': '#475569', 'bold': True})
    fmt_cf_estado_busq = wb.add_format({'bg_color': '#FEF3C7', 'font_color': '#B45309', 'bold': True})

    # 1. Duplicados en Documento Paciente (Columna H -> índice 7) y Documento Cuidador (Columna V -> índice 21)
    ws.conditional_format(first_data_row, 7, last_data_row, 7, {'type': 'duplicate', 'format': fmt_cf_duplicado})
    ws.conditional_format(first_data_row, 21, last_data_row, 21, {'type': 'duplicate', 'format': fmt_cf_duplicado})

    # 2. Edad Actual Meses (Columna P -> índice 15)
    ws.conditional_format(first_data_row, 15, last_data_row, 15, {'type': 'cell', 'criteria': '>=', 'value': 60, 'format': fmt_cf_edad_egreso})
    ws.conditional_format(first_data_row, 15, last_data_row, 15, {'type': 'cell', 'criteria': '<=', 'value': 59, 'format': fmt_cf_edad_norma})

    # 3. Clasificación Inicial (Columna AC -> índice 28) y Diagnóstico 1ra Atención (Columna AM -> índice 38)
    for col_idx in [28, 38]:
        ws.conditional_format(first_data_row, col_idx, last_data_row, col_idx, {
            'type': 'cell', 'criteria': 'equal to', 'value': '="Desnutrición aguda severa"', 'format': fmt_cf_severa
        })
        ws.conditional_format(first_data_row, col_idx, last_data_row, col_idx, {
            'type': 'cell', 'criteria': 'equal to', 'value': '="Desnutrición aguda moderada"', 'format': fmt_cf_moderada
        })
        ws.conditional_format(first_data_row, col_idx, last_data_row, col_idx, {
            'type': 'cell', 'criteria': 'equal to', 'value': '="Riesgo de desnutrición aguda"', 'format': fmt_cf_riesgo
        })
        ws.conditional_format(first_data_row, col_idx, last_data_row, col_idx, {
            'type': 'cell', 'criteria': 'equal to', 'value': '="Peso adecuado para la talla"', 'format': fmt_cf_adecuado
        })
        ws.conditional_format(first_data_row, col_idx, last_data_row, col_idx, {
            'type': 'cell', 'criteria': 'equal to', 'value': '="Fuera de rango / por verificar"', 'format': fmt_cf_fuera_rango
        })

    # 4. Estado de la Búsqueda (Columna AG -> índice 32)
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Atendido', 'format': fmt_cf_adecuado})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Efectiva', 'format': fmt_cf_adecuado})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Pendiente', 'format': fmt_cf_riesgo})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Búsqueda', 'format': fmt_cf_riesgo})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Busqueda', 'format': fmt_cf_riesgo})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Fallida', 'format': fmt_cf_severa})
    ws.conditional_format(first_data_row, 32, last_data_row, 32, {'type': 'text', 'criteria': 'containing', 'value': 'Descartado', 'format': fmt_cf_fuera_rango})

    # 5. Prueba de Apetito (Columna AN -> índice 39)
    ws.conditional_format(first_data_row, 39, last_data_row, 39, {'type': 'text', 'criteria': 'containing', 'value': 'Positiva', 'format': fmt_cf_adecuado})
    ws.conditional_format(first_data_row, 39, last_data_row, 39, {'type': 'text', 'criteria': 'containing', 'value': 'Sí', 'format': fmt_cf_adecuado})
    ws.conditional_format(first_data_row, 39, last_data_row, 39, {'type': 'text', 'criteria': 'containing', 'value': 'Negativa', 'format': fmt_cf_severa})
    ws.conditional_format(first_data_row, 39, last_data_row, 39, {'type': 'text', 'criteria': 'containing', 'value': 'No aplica', 'format': fmt_cf_fuera_rango})

    # 6. Estado Actual (Columna AR -> índice 43)
    ws.conditional_format(first_data_row, 43, last_data_row, 43, {'type': 'text', 'criteria': 'containing', 'value': 'En seguimiento', 'format': fmt_cf_estado_seg})
    ws.conditional_format(first_data_row, 43, last_data_row, 43, {'type': 'text', 'criteria': 'containing', 'value': 'Cerrado', 'format': fmt_cf_estado_cerrado})
    ws.conditional_format(first_data_row, 43, last_data_row, 43, {'type': 'text', 'criteria': 'containing', 'value': 'Busqueda', 'format': fmt_cf_estado_busq})
    ws.conditional_format(first_data_row, 43, last_data_row, 43, {'type': 'text', 'criteria': 'containing', 'value': 'Búsqueda', 'format': fmt_cf_estado_busq})

    # 7. Alertas normativas de edad (Columna AU -> índice 46, Columna AV -> índice 47)
    ws.conditional_format(first_data_row, 46, last_data_row, 46, {'type': 'cell', 'criteria': 'equal to', 'value': '="SI"', 'format': fmt_cf_alerta_naranja})
    ws.conditional_format(first_data_row, 47, last_data_row, 47, {'type': 'cell', 'criteria': 'equal to', 'value': '="SI"', 'format': fmt_cf_alerta_roja})

    # Congelar paneles: Filas 1 a 8 fijas y Columnas A a D fijas
    ws.freeze_panes(8, 4)

    # Autofiltro en la fila 8 (índice 7) para todas las columnas
    ws.autofilter(7, 0, total_filas - 1, len(columnas_def) - 1)

    wb.close()
    output.seek(0)
    fecha_str = date.today().strftime("%Y%m%d")
    filename = f"Libro_Notificados_PM_RIA_FT_003_{fecha_str}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{caso_id}")
def obtener_notificacion_individual(caso_id: int, db: Session = Depends(get_db)):
    """Retorna los datos completos de una notificación específica."""
    select_sql = """
        SELECT 
            c.*,
            p.tipo_documento,
            p.numero_documento,
            CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido) AS nombre_completo,
            p.sexo,
            p.fecha_nacimiento,
            p.georreferenciacion,
            m.nombre AS municipio,
            e.nombre AS eapb,
            s.nombre AS sede_ipsi,
            cu.nombre_completo AS cuidador,
            cu.documento_cuidador,
            cu.telefono AS telefono_cuidador
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cat_eapb e ON c.eapb_id = e.eapb_id
        LEFT JOIN cat_sedes_ipsi s ON c.ips_primaria_id = s.sede_id
        LEFT JOIN cuidadores cu ON p.cuidador_id = cu.cuidador_id
        WHERE c.caso_id = :caso_id
    """
    row = db.execute(text(select_sql), {"caso_id": caso_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return dict(row)

@router.put("/{caso_id}")
def actualizar_notificacion(
    caso_id: int,
    body: NotificacionUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Actualiza la información de una notificación, incluyendo datos de captación,
    búsqueda GBAI, primera atención y contacto del cuidador.
    """
    caso = db.query(NotificacionCaso).filter(NotificacionCaso.caso_id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    # Actualizar campos de NotificacionCaso
    if body.fuente_notificacion is not None: caso.fuente_notificacion = body.fuente_notificacion
    if body.fecha_notificacion is not None: caso.fecha_notificacion = body.fecha_notificacion
    if body.cooperante_notificador is not None: caso.cooperante_notificador = body.cooperante_notificador
    if body.medio_notificacion is not None: caso.medio_notificacion = body.medio_notificacion
    if body.fecha_captacion is not None: caso.fecha_captacion = body.fecha_captacion
    if body.peso_inicial_kg is not None: caso.peso_inicial_kg = body.peso_inicial_kg
    if body.talla_inicial_cm is not None: caso.talla_inicial_cm = body.talla_inicial_cm
    if body.pb_inicial_cm is not None: caso.pb_inicial_cm = body.pb_inicial_cm
    if body.zscore_inicial is not None: caso.zscore_inicial = body.zscore_inicial
    if body.fecha_busqueda_gbai is not None: caso.fecha_busqueda_gbai = body.fecha_busqueda_gbai
    if body.asignacion_interna is not None: caso.asignacion_interna = body.asignacion_interna
    if body.estado_busqueda is not None: caso.estado_busqueda = body.estado_busqueda
    if body.fecha_primera_atencion is not None: caso.fecha_primera_atencion = body.fecha_primera_atencion
    if body.peso_atencion_kg is not None: caso.peso_atencion_kg = body.peso_atencion_kg
    if body.talla_atencion_cm is not None: caso.talla_atencion_cm = body.talla_atencion_cm
    if body.pb_atencion_cm is not None: caso.pb_atencion_cm = body.pb_atencion_cm
    if body.zscore_atencion is not None: caso.zscore_atencion = body.zscore_atencion
    if body.prueba_apetito is not None: caso.prueba_apetito = body.prueba_apetito
    if body.tratamiento_inicial is not None: caso.tratamiento_inicial = body.tratamiento_inicial
    if body.sobres_ftlc_inicial is not None: caso.sobres_ftlc_inicial = body.sobres_ftlc_inicial
    if body.comorbilidad_inicial is not None: caso.comorbilidad_inicial = body.comorbilidad_inicial
    if body.escenario_manejo is not None: caso.escenario_manejo = body.escenario_manejo
    if body.estado_caso is not None: caso.estado_caso = body.estado_caso
    if body.observaciones is not None: caso.observaciones = body.observaciones

    # Actualizar datos de georreferenciación en Paciente
    if body.georreferenciacion is not None and caso.paciente:
        caso.paciente.georreferenciacion = body.georreferenciacion

    # Actualizar datos de cuidador si aplica
    if (body.cuidador or body.telefono_cuidador) and caso.paciente:
        if caso.paciente.cuidador:
            if body.cuidador: caso.paciente.cuidador.nombre_completo = body.cuidador
            if body.telefono_cuidador: caso.paciente.cuidador.telefono = body.telefono_cuidador
        elif body.cuidador:
            nuevo_c = Cuidador(nombre_completo=body.cuidador, telefono=body.telefono_cuidador)
            db.add(nuevo_c)
            db.flush()
            caso.paciente.cuidador_id = nuevo_c.cuidador_id

    db.commit()
    return {"status": "success", "mensaje": f"Notificación #{caso_id} actualizada correctamente"}

