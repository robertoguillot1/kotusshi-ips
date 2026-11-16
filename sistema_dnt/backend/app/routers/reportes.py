from fastapi import APIRouter, Depends, Query, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List
from io import BytesIO
from datetime import date, datetime
import subprocess
import gzip
import pandas as pd
from app.database import get_db
from app.schemas import DashboardKPIs

router = APIRouter(prefix="/api/reportes", tags=["Dashboard y Reportes Epidemiológicos"])

@router.get("/dashboard", response_model=DashboardKPIs)
def obtener_dashboard_kpis(db: Session = Depends(get_db)):
    """
    Retorna el consolidado epidemiológico en tiempo real (reemplaza la hoja 'Dashboard' de Excel).
    """
    # Total notificados
    tot_notif = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso")).scalar() or 0

    # Total en seguimiento y cerrados
    tot_seg = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE estado_caso = 'En seguimiento'")).scalar() or 0
    tot_cerr = db.execute(text("SELECT COUNT(*) FROM notificaciones_caso WHERE estado_caso = 'Cerrado'")).scalar() or 0

    # Citas vencidas hoy
    citas_venc = db.execute(
        text("SELECT COUNT(*) FROM vw_estado_actual_casos WHERE fecha_proxima_cita IS NOT NULL AND fecha_proxima_cita < CURRENT_DATE AND estado_caso = 'En seguimiento'")
    ).scalar() or 0

    # Alertas egreso por edad (>= 60 meses)
    alertas_edad = db.execute(
        text("SELECT COUNT(*) FROM vw_estado_actual_casos WHERE edad_meses_actual >= 60 AND estado_caso = 'En seguimiento'")
    ).scalar() or 0

    # Distribución por diagnóstico actual
    rows_dx = db.execute(
        text("SELECT clasificacion_nutricional_actual, COUNT(*) FROM vw_estado_actual_casos WHERE estado_caso = 'En seguimiento' GROUP BY clasificacion_nutricional_actual")
    ).fetchall()
    dist_dx = {r[0] or "Sin dato": r[1] for r in rows_dx}

    # Distribución por municipio
    rows_mun = db.execute(
        text("SELECT COALESCE(municipio, 'Sin Dato'), COUNT(*) FROM vw_estado_actual_casos GROUP BY municipio")
    ).fetchall()
    dist_mun = {r[0]: r[1] for r in rows_mun}

    # Distribución por EAPB
    rows_eapb = db.execute(
        text("SELECT COALESCE(eapb, 'Sin Dato'), COUNT(*) FROM vw_estado_actual_casos GROUP BY eapb")
    ).fetchall()
    dist_eapb = {r[0]: r[1] for r in rows_eapb}

    # Distribución por Sede IPSI
    rows_sede = db.execute(
        text("SELECT COALESCE(sede_ipsi, 'Sin Dato'), COUNT(*) FROM vw_estado_actual_casos GROUP BY sede_ipsi")
    ).fetchall()
    dist_sede = {r[0]: r[1] for r in rows_sede}

    return DashboardKPIs(
        total_notificados=tot_notif,
        total_en_seguimiento=tot_seg,
        total_cerrados=tot_cerr,
        citas_vencidas_hoy=citas_venc,
        alertas_egreso_edad=alertas_edad,
        distribucion_diagnostico=dist_dx,
        distribucion_municipio=dist_mun,
        distribucion_eapb=dist_eapb,
        distribucion_sede=dist_sede
    )

@router.get("/indicadores-mensuales")
def obtener_indicadores_mensuales(
    anio: Optional[int] = Query(None, description="Año a consultar (si se omite, toma el más reciente disponible)"),
    db: Session = Depends(get_db)
):
    """
    Retorna la matriz mensual por municipio según fecha de notificación, primera atención y controles,
    además de la lista de todos los años disponibles en el sistema (detección automática de 2024, 2025, 2026, 2027...).
    """
    # 1. Detectar automáticamente todos los años presentes en los datos
    query_anios = """
        SELECT DISTINCT anio FROM (
            SELECT EXTRACT(YEAR FROM fecha_notificacion)::INT AS anio FROM notificaciones_caso WHERE fecha_notificacion IS NOT NULL
            UNION
            SELECT EXTRACT(YEAR FROM fecha_primera_atencion)::INT AS anio FROM notificaciones_caso WHERE fecha_primera_atencion IS NOT NULL
            UNION
            SELECT EXTRACT(YEAR FROM fecha_control)::INT AS anio FROM controles_seguimiento WHERE fecha_control IS NOT NULL
        ) sub
        WHERE anio IS NOT NULL
        ORDER BY anio DESC
    """
    anios_db = [r[0] for r in db.execute(text(query_anios)).fetchall() if r[0] is not None]
    if not anios_db:
        anios_db = [date.today().year]

    # Si no se pasó año o no está en la BD, tomar el año más reciente registrado
    anio_activo = anio if (anio is not None and anio in anios_db) else anios_db[0]

    # Matriz por fecha de notificación
    query_notif = """
        SELECT 
            COALESCE(m.nombre, 'Sin Municipio') AS municipio,
            EXTRACT(MONTH FROM c.fecha_notificacion)::INT AS mes,
            COUNT(*) AS total
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        WHERE EXTRACT(YEAR FROM c.fecha_notificacion) = :anio
        GROUP BY COALESCE(m.nombre, 'Sin Municipio'), EXTRACT(MONTH FROM c.fecha_notificacion)
        ORDER BY municipio, mes
    """
    rows_notif = db.execute(text(query_notif), {"anio": anio_activo}).fetchall()

    # Matriz por fecha de primera atención
    query_atenc = """
        SELECT 
            COALESCE(m.nombre, 'Sin Municipio') AS municipio,
            EXTRACT(MONTH FROM c.fecha_primera_atencion)::INT AS mes,
            COUNT(*) AS total
        FROM notificaciones_caso c
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        WHERE EXTRACT(YEAR FROM c.fecha_primera_atencion) = :anio
        GROUP BY COALESCE(m.nombre, 'Sin Municipio'), EXTRACT(MONTH FROM c.fecha_primera_atencion)
        ORDER BY municipio, mes
    """
    rows_atenc = db.execute(text(query_atenc), {"anio": anio_activo}).fetchall()

    # Matriz por fecha de controles de seguimiento
    query_ctrl = """
        SELECT 
            COALESCE(m.nombre, 'Sin Municipio') AS municipio,
            EXTRACT(MONTH FROM s.fecha_control)::INT AS mes,
            COUNT(*) AS total
        FROM controles_seguimiento s
        JOIN notificaciones_caso c ON s.caso_id = c.caso_id
        JOIN pacientes p ON c.paciente_id = p.paciente_id
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        WHERE EXTRACT(YEAR FROM s.fecha_control) = :anio
        GROUP BY COALESCE(m.nombre, 'Sin Municipio'), EXTRACT(MONTH FROM s.fecha_control)
        ORDER BY municipio, mes
    """
    rows_ctrl = db.execute(text(query_ctrl), {"anio": anio_activo}).fetchall()

    def procesar_matriz(rows):
        matriz = {}
        for r in rows:
            mun = r[0] or "Sin Municipio"
            mes = r[1]
            cnt = r[2]
            if mun not in matriz:
                matriz[mun] = {m: 0 for m in range(1, 13)}
            matriz[mun][mes] = cnt
        return matriz

    return {
        "anio": anio_activo,
        "anios_disponibles": anios_db,
        "por_fecha_notificacion": procesar_matriz(rows_notif),
        "por_fecha_primera_atencion": procesar_matriz(rows_atenc),
        "por_controles_seguimiento": procesar_matriz(rows_ctrl)
    }

@router.get("/exportar-excel")
def exportar_casos_excel(
    municipio: Optional[str] = Query(None),
    eapb: Optional[str] = Query(None),
    estado_caso: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Genera y descarga un libro Excel (.xlsx) altamente estilizado y profesional
    con la información consolidada de casos de desnutrición según la Res. 000115 de 2026.
    Incluye:
    - Hoja 1: 'Casos en Seguimiento' con banner corporativo, encabezados coloreados,
      filas cebra, semaforización clínica, inmovilización de paneles y autofiltros.
    - Hoja 2: 'Resumen Epidemiológico' con tarjetas de KPI y tablas de distribución.
    """
    filtros = []
    params = {}
    if municipio and municipio != "TODOS":
        filtros.append("municipio ILIKE :municipio")
        params["municipio"] = f"%{municipio}%"
    if eapb and eapb != "TODAS":
        filtros.append("eapb ILIKE :eapb")
        params["eapb"] = f"%{eapb}%"
    if estado_caso and estado_caso != "TODOS":
        filtros.append("estado_caso ILIKE :estado_caso")
        params["estado_caso"] = f"%{estado_caso}%"

    where_sql = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    query = f"SELECT * FROM vw_estado_actual_casos {where_sql} ORDER BY caso_id ASC"
    df = pd.read_sql_query(text(query), db.connection(), params=params)

    hoy = date.today()
    output = BytesIO()

    columnas_def = [
        ("caso_id", "No. Caso", 10, "center"),
        ("tipo_documento", "Tipo Doc", 10, "center"),
        ("numero_documento", "Documento Identidad", 20, "center"),
        ("nombre_completo", "Nombre Completo del Menor", 34, "left"),
        ("sexo", "Sexo", 8, "center"),
        ("fecha_nacimiento", "Fecha Nacimiento", 16, "center"),
        ("edad_meses_actual", "Edad (Meses)", 14, "center"),
        ("municipio", "Municipio", 16, "left"),
        ("eapb", "EAPB / EPS", 26, "left"),
        ("sede_ipsi", "Sede IPSI Primaria", 24, "left"),
        ("cuidador", "Nombre Cuidador(a)", 28, "left"),
        ("telefono_cuidador", "Teléfono Contacto", 18, "center"),
        ("fuente_notificacion", "Evento Notificación", 22, "left"),
        ("fecha_notificacion", "Fecha Notificación", 16, "center"),
        ("estado_caso", "Estado del Caso", 18, "center"),
        ("total_controles", "Total Controles", 15, "center"),
        ("fecha_ultima_atencion", "Última Atención", 16, "center"),
        ("ultimo_zscore", "Puntaje Z (P/T)", 16, "center"),
        ("clasificacion_nutricional_actual", "Clasificación Nutricional (Res. 000115)", 32, "center"),
        ("fecha_proxima_cita", "Próxima Cita", 16, "center"),
        ("alerta_cita", "Alerta Cita", 18, "center"),
    ]

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book

        # -------------------------------------------------------------
        # ESTILOS Y FORMATOS TIPOGRÁFICOS Y DE COLOR
        # -------------------------------------------------------------
        fmt_title = wb.add_format({
            'bold': True, 'font_size': 13, 'font_name': 'Segoe UI',
            'bg_color': '#0369a1', 'font_color': '#ffffff',
            'align': 'center', 'valign': 'vcenter'
        })
        fmt_subtitle = wb.add_format({
            'italic': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#e0f2fe', 'font_color': '#0369a1',
            'align': 'center', 'valign': 'vcenter'
        })
        fmt_header = wb.add_format({
            'bold': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#0284c7', 'font_color': '#ffffff',
            'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#0369a1', 'text_wrap': True
        })

        # Celdas regulares fondo blanco (#ffffff)
        fmt_left_white = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#ffffff'})
        fmt_center_white = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#ffffff'})
        fmt_date_white = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#ffffff', 'num_format': 'yyyy-mm-dd'})
        fmt_dec_white = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#ffffff', 'num_format': '0.00'})
        fmt_int_white = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#ffffff', 'num_format': '#,##0'})

        # Celdas cebra gris suave (#f8fafc)
        fmt_left_zebra = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc'})
        fmt_center_zebra = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc'})
        fmt_date_zebra = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc', 'num_format': 'yyyy-mm-dd'})
        fmt_dec_zebra = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc', 'num_format': '0.00'})
        fmt_int_zebra = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc', 'num_format': '#,##0'})

        # Semáforo de Clasificación Nutricional
        fmt_dx_severa = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#fee2e2', 'font_color': '#991b1b', 'border': 1, 'border_color': '#f87171'})
        fmt_dx_moderada = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#ffedd5', 'font_color': '#c2410c', 'border': 1, 'border_color': '#fb923c'})
        fmt_dx_riesgo = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#fef3c7', 'font_color': '#b45309', 'border': 1, 'border_color': '#fcd34d'})
        fmt_dx_adecuado = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#dcfce7', 'font_color': '#166534', 'border': 1, 'border_color': '#86efac'})
        fmt_dx_sobrepeso = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#f3e8ff', 'font_color': '#6b21a8', 'border': 1, 'border_color': '#d8b4fe'})

        # Estados de caso
        fmt_st_seguimiento = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#e0f2fe', 'font_color': '#0369a1', 'border': 1, 'border_color': '#7dd3fc'})
        fmt_st_cerrado = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#f1f5f9', 'font_color': '#475569', 'border': 1, 'border_color': '#cbd5e1'})
        fmt_st_busqueda = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#fef9c3', 'font_color': '#854d0e', 'border': 1, 'border_color': '#fde047'})

        # Alerta de citas
        fmt_alerta_vencida = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#fee2e2', 'font_color': '#b91c1c', 'border': 1, 'border_color': '#f87171'})
        fmt_alerta_aldia = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#ecfdf5', 'font_color': '#047857', 'border': 1, 'border_color': '#a7f3d0'})

        # -------------------------------------------------------------
        # HOJA 1: CASOS EN SEGUIMIENTO
        # -------------------------------------------------------------
        ws1 = wb.add_worksheet('Casos en Seguimiento')
        writer.sheets['Casos en Seguimiento'] = ws1

        num_cols = len(columnas_def)
        # Encabezado Institucional
        ws1.merge_range(0, 0, 0, num_cols - 1, 'IPSI KOTTUSHI SAO ANA>A • SISTEMA DE VIGILANCIA NUTRICIONAL Y SEGUIMIENTO DNT', fmt_title)
        ws1.set_row(0, 28)
        ws1.merge_range(1, 0, 1, num_cols - 1, f'Consolidado Clínico y Operativo Longitudinal • Conforme a Resolución 000115 de 2026 • Generado el {hoy.strftime("%d/%m/%Y")}', fmt_subtitle)
        ws1.set_row(1, 20)
        ws1.set_row(2, 6)  # Separador visual

        # Fila 3: Encabezados de Columna
        ws1.set_row(3, 28)
        for c_idx, (col_id, col_name, width, align) in enumerate(columnas_def):
            ws1.write(3, c_idx, col_name, fmt_header)
            ws1.set_column(c_idx, c_idx, width)

        # Filas de Datos
        row_idx = 4
        for _, r in df.iterrows():
            is_zebra = (row_idx % 2 == 1)
            ws1.set_row(row_idx, 20)

            # Cálculo de estado de alerta de cita
            estado = r.get('estado_caso')
            f_cita = r.get('fecha_proxima_cita')
            if estado == 'En seguimiento' and f_cita is not None:
                if pd.to_datetime(f_cita).date() < hoy:
                    alerta_cita = "🚨 VENCIDA"
                else:
                    alerta_cita = "Al día"
            else:
                alerta_cita = "-"

            for c_idx, (col_id, col_name, width, align) in enumerate(columnas_def):
                if col_id == 'alerta_cita':
                    val = alerta_cita
                else:
                    val = r.get(col_id)
                    if pd.isna(val):
                        val = None

                # Asignación de formato visual según semántica
                if col_id == 'clasificacion_nutricional_actual' and val:
                    v_low = str(val).lower()
                    if 'severa' in v_low:
                        cell_fmt = fmt_dx_severa
                    elif 'moderada' in v_low:
                        cell_fmt = fmt_dx_moderada
                    elif 'riesgo' in v_low:
                        cell_fmt = fmt_dx_riesgo
                    elif 'adecuado' in v_low:
                        cell_fmt = fmt_dx_adecuado
                    elif 'sobrepeso' in v_low:
                        cell_fmt = fmt_dx_sobrepeso
                    else:
                        cell_fmt = fmt_center_zebra if is_zebra else fmt_center_white
                elif col_id == 'estado_caso' and val:
                    v_low = str(val).lower()
                    if 'seguimiento' in v_low:
                        cell_fmt = fmt_st_seguimiento
                    elif 'cerrado' in v_low:
                        cell_fmt = fmt_st_cerrado
                    elif 'squeda' in v_low:
                        cell_fmt = fmt_st_busqueda
                    else:
                        cell_fmt = fmt_center_zebra if is_zebra else fmt_center_white
                elif col_id == 'alerta_cita':
                    if 'VENCIDA' in val:
                        cell_fmt = fmt_alerta_vencida
                    elif 'Al día' in val:
                        cell_fmt = fmt_alerta_aldia
                    else:
                        cell_fmt = fmt_center_zebra if is_zebra else fmt_center_white
                elif 'fecha' in col_id:
                    cell_fmt = fmt_date_zebra if is_zebra else fmt_date_white
                    if val is not None:
                        val = str(val)
                elif col_id in ('ultimo_zscore',):
                    cell_fmt = fmt_dec_zebra if is_zebra else fmt_dec_white
                elif col_id in ('caso_id', 'edad_meses_actual', 'total_controles'):
                    cell_fmt = fmt_int_zebra if is_zebra else fmt_int_white
                elif align == 'center':
                    cell_fmt = fmt_center_zebra if is_zebra else fmt_center_white
                else:
                    cell_fmt = fmt_left_zebra if is_zebra else fmt_left_white

                if val is None:
                    ws1.write_blank(row_idx, c_idx, None, cell_fmt)
                else:
                    ws1.write(row_idx, c_idx, val, cell_fmt)

            row_idx += 1

        # Inmovilizar encabezados y columnas clave de identificación (Filas 1-4, Cols A-D)
        ws1.freeze_panes(4, 4)

        # Autofiltro nativo en fila de encabezados
        if row_idx > 4:
            ws1.autofilter(3, 0, row_idx - 1, num_cols - 1)

        # -------------------------------------------------------------
        # HOJA 2: RESUMEN EPIDEMIOLÓGICO Y OPERATIVO
        # -------------------------------------------------------------
        ws2 = wb.add_worksheet('Resumen Epidemiológico')
        writer.sheets['Resumen Epidemiológico'] = ws2

        ws2.merge_range(0, 0, 0, 6, 'IPSI KOTTUSHI SAO ANA>A • RESUMEN EPIDEMIOLÓGICO Y OPERATIVO', fmt_title)
        ws2.set_row(0, 26)
        ws2.merge_range(1, 0, 1, 6, f'Indicadores Clave y Distribuciones Epidemiológicas • Generado el {hoy.strftime("%d/%m/%Y")}', fmt_subtitle)
        ws2.set_row(1, 18)

        fmt_kpi_label = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#f1f5f9', 'font_color': '#475569', 'border': 1, 'border_color': '#cbd5e1'})
        fmt_kpi_val_blue = wb.add_format({'font_name': 'Segoe UI', 'font_size': 14, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#e0f2fe', 'font_color': '#0369a1', 'border': 1, 'border_color': '#7dd3fc'})
        fmt_kpi_val_red = wb.add_format({'font_name': 'Segoe UI', 'font_size': 14, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#fee2e2', 'font_color': '#b91c1c', 'border': 1, 'border_color': '#f87171'})
        fmt_kpi_val_green = wb.add_format({'font_name': 'Segoe UI', 'font_size': 14, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#ecfdf5', 'font_color': '#047857', 'border': 1, 'border_color': '#a7f3d0'})

        total_casos = len(df)
        total_seguimiento = len(df[df['estado_caso'] == 'En seguimiento']) if 'estado_caso' in df.columns else 0
        total_cerrados = len(df[df['estado_caso'] == 'Cerrado']) if 'estado_caso' in df.columns else 0

        total_vencidas = 0
        for _, r in df.iterrows():
            if r.get('estado_caso') == 'En seguimiento' and pd.notna(r.get('fecha_proxima_cita')):
                if pd.to_datetime(r.get('fecha_proxima_cita')).date() < hoy:
                    total_vencidas += 1

        # Tarjetas de KPI
        ws2.merge_range(3, 0, 3, 1, 'TOTAL CASOS REGISTRADOS', fmt_kpi_label)
        ws2.merge_range(4, 0, 4, 1, total_casos, fmt_kpi_val_blue)

        ws2.merge_range(3, 2, 3, 3, 'CASOS EN SEGUIMIENTO ACTIVO', fmt_kpi_label)
        ws2.merge_range(4, 2, 4, 3, total_seguimiento, fmt_kpi_val_blue)

        ws2.write(3, 4, 'CITAS VENCIDAS', fmt_kpi_label)
        ws2.write(4, 4, total_vencidas, fmt_kpi_val_red)

        ws2.merge_range(3, 5, 3, 6, 'CASOS CERRADOS / COMPLETADOS', fmt_kpi_label)
        ws2.merge_range(4, 5, 4, 6, total_cerrados, fmt_kpi_val_green)

        ws2.set_row(3, 18)
        ws2.set_row(4, 26)

        # Tablas de Distribución
        fmt_th_sub = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#0284c7', 'font_color': '#ffffff', 'border': 1, 'border_color': '#0369a1'})
        fmt_total_row = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'right', 'valign': 'vcenter', 'bg_color': '#e2e8f0', 'border': 1, 'border_color': '#cbd5e1'})
        fmt_total_val = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#e2e8f0', 'border': 1, 'border_color': '#cbd5e1', 'num_format': '#,##0'})

        # Tabla 1: Distribución Nutricional
        ws2.merge_range(6, 0, 6, 2, 'DISTRIBUCIÓN POR CLASIFICACIÓN NUTRICIONAL', fmt_th_sub)
        ws2.write(7, 0, 'Clasificación', fmt_header)
        ws2.write(7, 1, 'Casos', fmt_header)
        ws2.write(7, 2, '% Participación', fmt_header)

        dx_counts = df['clasificacion_nutricional_actual'].fillna('Sin Clasificación').value_counts()
        cur_row_dx = 8
        for dx_name, cnt in dx_counts.items():
            pct = (cnt / total_casos) * 100 if total_casos > 0 else 0
            ws2.write(cur_row_dx, 0, dx_name, fmt_left_white)
            ws2.write(cur_row_dx, 1, cnt, fmt_int_white)
            ws2.write(cur_row_dx, 2, f"{pct:.1f}%", fmt_center_white)
            cur_row_dx += 1

        ws2.write(cur_row_dx, 0, 'TOTAL', fmt_total_row)
        ws2.write(cur_row_dx, 1, total_casos, fmt_total_val)
        ws2.write(cur_row_dx, 2, '100.0%', fmt_total_val)

        # Tabla 2: Distribución por Municipio
        ws2.merge_range(6, 4, 6, 6, 'DISTRIBUCIÓN POR MUNICIPIO', fmt_th_sub)
        ws2.write(7, 4, 'Municipio', fmt_header)
        ws2.write(7, 5, 'Casos', fmt_header)
        ws2.write(7, 6, '% Participación', fmt_header)

        mun_counts = df['municipio'].fillna('Sin Municipio').value_counts()
        cur_row_mun = 8
        for mun_name, cnt in mun_counts.items():
            pct = (cnt / total_casos) * 100 if total_casos > 0 else 0
            ws2.write(cur_row_mun, 4, mun_name, fmt_left_white)
            ws2.write(cur_row_mun, 5, cnt, fmt_int_white)
            ws2.write(cur_row_mun, 6, f"{pct:.1f}%", fmt_center_white)
            cur_row_mun += 1

        ws2.write(cur_row_mun, 4, 'TOTAL', fmt_total_row)
        ws2.write(cur_row_mun, 5, total_casos, fmt_total_val)
        ws2.write(cur_row_mun, 6, '100.0%', fmt_total_val)

        # Anchos de columna Hoja 2
        ws2.set_column(0, 0, 32)
        ws2.set_column(1, 1, 14)
        ws2.set_column(2, 2, 16)
        ws2.set_column(3, 3, 5)
        ws2.set_column(4, 4, 24)
        ws2.set_column(5, 5, 14)
        ws2.set_column(6, 6, 16)

    output.seek(0)
    fecha_hoy = date.today().strftime("%Y%m%d")
    filename = f"Reporte_Vigilancia_DNT_{fecha_hoy}.xlsx"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@router.get("/alertas-rescate")
def obtener_alertas_rescate_nutricional(db: Session = Depends(get_db)):
    """
    Centro de Alertas de Rescate Nutricional y Vigilancia Epidemiológica Temprana.
    Detecta automáticamente:
    1. Pérdida de Peso: Menores en seguimiento activo cuyo último control tuvo peso inferior al anterior (desmejora clínica).
    2. Estancamiento Ponderal: Niños con 2 o más controles sin ganancia de peso adecuada (< 5 g/kg/día).
    3. Riesgo de Abandono: Citas con más de 15 días de vencimiento sin reporte.
    4. Próximos Egresos por Edad: Niños que cumplirán 60 meses en los próximos 30 días (edad 59 meses) para coordinar remisión a ICBF/Escolar.
    """
    # 1. Pérdida de Peso
    sql_perdida = """
    WITH ranked_controles AS (
        SELECT 
            c.caso_id,
            c.numero_seguimiento,
            c.fecha_control,
            c.peso_kg,
            LAG(c.peso_kg) OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento ASC) AS peso_anterior,
            LAG(c.fecha_control) OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento ASC) AS fecha_anterior,
            ROW_NUMBER() OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento DESC) AS rn
        FROM controles_seguimiento c
        WHERE c.peso_kg IS NOT NULL
    ),
    ultimos AS (
        SELECT *
        FROM ranked_controles
        WHERE rn = 1 AND peso_anterior IS NOT NULL
    )
    SELECT 
        u.caso_id,
        p.paciente_id,
        p.tipo_documento,
        p.numero_documento,
        TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) AS nombre_completo,
        p.sexo,
        u.peso_anterior,
        u.peso_kg AS peso_actual,
        ROUND((u.peso_kg - u.peso_anterior)::numeric, 2) AS delta_peso_kg,
        u.fecha_anterior,
        u.fecha_control AS fecha_ultimo_control,
        (u.fecha_control - u.fecha_anterior) AS dias_lapso,
        m.nombre AS municipio,
        e.nombre AS eapb,
        cuid.nombre_completo AS cuidador,
        cuid.telefono AS telefono_cuidador
    FROM ultimos u
    JOIN notificaciones_caso nc ON u.caso_id = nc.caso_id
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    WHERE (u.peso_kg - u.peso_anterior) < 0
      AND nc.estado_caso ILIKE '%seguimiento%'
    ORDER BY delta_peso_kg ASC;
    """
    rows_perdida = [dict(r) for r in db.execute(text(sql_perdida)).mappings().all()]

    # 2. Estancamiento Ponderal (< 5 g/kg/dia)
    sql_estancamiento = """
    WITH ranked_controles AS (
        SELECT 
            c.caso_id,
            c.numero_seguimiento,
            c.fecha_control,
            c.peso_kg,
            LAG(c.peso_kg) OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento ASC) AS peso_anterior,
            LAG(c.fecha_control) OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento ASC) AS fecha_anterior,
            ROW_NUMBER() OVER (PARTITION BY c.caso_id ORDER BY c.numero_seguimiento DESC) AS rn
        FROM controles_seguimiento c
        WHERE c.peso_kg IS NOT NULL
    ),
    ultimos AS (
        SELECT 
            u.*,
            (u.peso_kg - u.peso_anterior) AS delta_peso,
            (u.fecha_control - u.fecha_anterior) AS dias_lapso
        FROM ranked_controles u
        WHERE rn = 1 
          AND peso_anterior IS NOT NULL 
          AND peso_anterior > 0
    )
    SELECT 
        u.caso_id,
        p.paciente_id,
        p.tipo_documento,
        p.numero_documento,
        TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) AS nombre_completo,
        p.sexo,
        u.peso_anterior,
        u.peso_kg AS peso_actual,
        ROUND(u.delta_peso::numeric, 2) AS delta_peso_kg,
        u.fecha_anterior,
        u.fecha_control AS fecha_ultimo_control,
        u.dias_lapso,
        ROUND((((u.delta_peso * 1000.0) / (u.peso_anterior * NULLIF(u.dias_lapso, 0))))::numeric, 2) AS ganancia_g_kg_dia,
        m.nombre AS municipio,
        e.nombre AS eapb,
        cuid.nombre_completo AS cuidador,
        cuid.telefono AS telefono_cuidador
    FROM ultimos u
    JOIN notificaciones_caso nc ON u.caso_id = nc.caso_id
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    WHERE nc.estado_caso ILIKE '%seguimiento%'
      AND u.delta_peso >= 0
      AND u.dias_lapso > 0
      AND (((u.delta_peso * 1000.0) / (u.peso_anterior * u.dias_lapso))) < 5.0
    ORDER BY ganancia_g_kg_dia ASC;
    """
    rows_estancamiento = [dict(r) for r in db.execute(text(sql_estancamiento)).mappings().all()]

    # 3. Riesgo de Abandono (> 15 días vencido)
    sql_abandono = """
    SELECT 
        v.caso_id,
        v.paciente_id,
        v.tipo_documento,
        v.numero_documento,
        v.nombre_completo,
        v.sexo,
        v.municipio,
        v.eapb,
        v.sede_ipsi,
        v.cuidador,
        v.telefono_cuidador,
        v.clasificacion_nutricional_actual,
        v.fecha_ultima_atencion,
        v.fecha_proxima_cita,
        (CURRENT_DATE - v.fecha_proxima_cita) AS dias_vencido
    FROM vw_estado_actual_casos v
    WHERE v.estado_caso = 'En seguimiento'
      AND v.fecha_proxima_cita IS NOT NULL
      AND v.fecha_proxima_cita < (CURRENT_DATE - INTERVAL '15 days')
    ORDER BY dias_vencido DESC;
    """
    rows_abandono = [dict(r) for r in db.execute(text(sql_abandono)).mappings().all()]

    # 4. Próximos Egresos por Edad (cumplen 60 meses en los próximos 30 días o tienen 59 meses)
    sql_egresos = """
    SELECT 
        nc.caso_id,
        p.paciente_id,
        p.tipo_documento,
        p.numero_documento,
        TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) AS nombre_completo,
        p.sexo,
        p.fecha_nacimiento,
        FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento))) AS edad_meses_actual,
        (p.fecha_nacimiento + INTERVAL '60 months')::date AS fecha_cumple_60,
        ((p.fecha_nacimiento + INTERVAL '60 months')::date - CURRENT_DATE) AS dias_para_60,
        m.nombre AS municipio,
        e.nombre AS eapb,
        cuid.nombre_completo AS cuidador,
        cuid.telefono AS telefono_cuidador
    FROM notificaciones_caso nc
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    WHERE nc.estado_caso ILIKE '%seguimiento%'
      AND FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento))) >= 59
      AND ((p.fecha_nacimiento + INTERVAL '60 months')::date - CURRENT_DATE) BETWEEN -30 AND 45
    ORDER BY dias_para_60 ASC;
    """
    rows_egresos = [dict(r) for r in db.execute(text(sql_egresos)).mappings().all()]

    return {
        "resumen": {
            "total_alertas": len(rows_perdida) + len(rows_estancamiento) + len(rows_abandono) + len(rows_egresos),
            "total_perdida_peso": len(rows_perdida),
            "total_estancamiento": len(rows_estancamiento),
            "total_abandono": len(rows_abandono),
            "total_proximos_egresos": len(rows_egresos)
        },
        "perdida_peso": rows_perdida,
        "estancamiento": rows_estancamiento,
        "abandono": rows_abandono,
        "proximos_egresos": rows_egresos
    }


@router.get("/backup-bd")
def descargar_copia_seguridad_bd():
    """
    Genera y descarga en vivo una copia de seguridad comprimida (.sql.gz)
    de la base de datos institucional PostgreSQL 'ipsi_nutricion'.
    Garantiza continuidad de servicio y respaldo institucional en 1 solo clic.
    """
    sql_bytes = None
    errores = []

    # 1. Intentar con docker exec
    try:
        cmd_docker = ["docker", "exec", "ipsi_postgres", "pg_dump", "-U", "postgres", "-d", "ipsi_nutricion", "--schema=public"]
        proc = subprocess.run(cmd_docker, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if proc.returncode == 0 and len(proc.stdout) > 100:
            sql_bytes = proc.stdout
        else:
            errores.append(f"Docker pg_dump: {proc.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        errores.append(f"Docker exc: {str(e)}")

    # 2. Fallback con pg_dump local si docker no respondió
    if sql_bytes is None:
        try:
            import os
            env = os.environ.copy()
            env["PGPASSWORD"] = "postgrespassword"
            cmd_local = ["pg_dump", "-h", "localhost", "-p", "5432", "-U", "postgres", "-d", "ipsi_nutricion", "--schema=public"]
            proc2 = subprocess.run(cmd_local, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
            if proc2.returncode == 0 and len(proc2.stdout) > 100:
                sql_bytes = proc2.stdout
            else:
                errores.append(f"Local pg_dump: {proc2.stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            errores.append(f"Local exc: {str(e)}")

    if sql_bytes is None:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar la copia de seguridad de la base de datos. Detalles: {' | '.join(errores)}"
        )

    # Comprimir en gzip
    sql_gz = gzip.compress(sql_bytes)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ipsi_nutricion_backup_{timestamp}.sql.gz"

    return Response(
        content=sql_gz,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Backup-Size-Raw": str(len(sql_bytes)),
            "X-Backup-Size-Gzip": str(len(sql_gz))
        }
    )


# ==============================================================================
# NUEVOS REPORTES OFICIALES ESPECIALIZADOS (CENTRO DE INFORMES)
# ==============================================================================

@router.get("/exportar-sivigila")
def exportar_reporte_sivigila(
    evento: Optional[str] = Query(None, description="113 (Desnutrición), 114 (Morbilidad) o None para ambos"),
    semana: Optional[int] = Query(None, description="Semana epidemiológica 1 a 52"),
    anio: Optional[int] = Query(None, description="Año de notificación"),
    municipio: Optional[str] = Query(None, description="Municipio"),
    db: Session = Depends(get_db)
):
    """
    Genera el archivo epidemiológico oficial SIVIGILA (Eventos 113 / 114)
    para el Instituto Nacional de Salud (INS) y la Secretaría de Salud Departamental.
    """
    filtros = []
    params = {}

    if evento and evento in ("113", "114"):
        filtros.append("nc.fuente_notificacion ILIKE :evento")
        params["evento"] = f"%{evento}%"

    if semana and 1 <= semana <= 53:
        filtros.append("EXTRACT(WEEK FROM nc.fecha_notificacion) = :semana")
        params["semana"] = semana

    if anio:
        filtros.append("EXTRACT(YEAR FROM nc.fecha_notificacion) = :anio")
        params["anio"] = anio

    if municipio and municipio != "TODOS":
        filtros.append("m.nombre ILIKE :municipio")
        params["municipio"] = f"%{municipio}%"

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    sql = f"""
    SELECT 
        '113' AS cod_eve,
        nc.fecha_notificacion AS fec_not,
        EXTRACT(WEEK FROM nc.fecha_notificacion)::INT AS semana,
        EXTRACT(YEAR FROM nc.fecha_notificacion)::INT AS anio,
        p.tipo_documento AS tip_ide_,
        p.numero_documento AS num_ide_,
        p.primer_nombre AS pri_nom_,
        COALESCE(p.segundo_nombre, '') AS seg_nom_,
        p.primer_apellido AS pri_ape_,
        COALESCE(p.segundo_apellido, '') AS seg_ape_,
        p.sexo AS sexo_,
        p.fecha_nacimiento AS fec_nac_,
        FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)))::INT AS edad_meses,
        m.nombre AS municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_vereda,
        e.nombre AS eapb,
        COALESCE(v.clasificacion_nutricional_actual, 'Desnutrición Aguda') AS diagnostico_inicial,
        nc.estado_caso AS estado_actual,
        nc.fuente_notificacion AS fuente_captacion
    FROM notificaciones_caso nc
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN vw_estado_actual_casos v ON nc.caso_id = v.caso_id
    {where_clause}
    ORDER BY nc.fecha_notificacion DESC, nc.caso_id DESC
    LIMIT 10000;
    """

    df = pd.read_sql_query(text(sql), db.connection(), params=params)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        ws = wb.add_worksheet('Reporte SIVIGILA')
        writer.sheets['Reporte SIVIGILA'] = ws

        fmt_title = wb.add_format({
            'bold': True, 'font_size': 12, 'font_name': 'Segoe UI',
            'bg_color': '#1e3a8a', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_sub = wb.add_format({
            'italic': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#dbeafe', 'font_color': '#1e40af', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_hdr = wb.add_format({
            'bold': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#2563eb', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#1d4ed8'
        })
        fmt_cell = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'valign': 'vcenter'})
        fmt_center = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'align': 'center', 'valign': 'vcenter'})
        fmt_date = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'align': 'center', 'valign': 'vcenter', 'num_format': 'yyyy-mm-dd'})

        cols = [
            ("cod_eve", "Evento", 10),
            ("fec_not", "Fecha Notif.", 12),
            ("semana", "S.E.", 8),
            ("anio", "Año", 8),
            ("tip_ide_", "Tipo Doc", 10),
            ("num_ide_", "No. Documento", 15),
            ("pri_nom_", "Primer Nombre", 15),
            ("seg_nom_", "Segundo Nombre", 15),
            ("pri_ape_", "Primer Apellido", 15),
            ("seg_ape_", "Segundo Apellido", 15),
            ("sexo_", "Sexo", 8),
            ("fec_nac_", "Fecha Nac.", 12),
            ("edad_meses", "Edad (m)", 10),
            ("municipio", "Municipio", 16),
            ("comunidad_vereda", "Comunidad / Ranchería", 24),
            ("eapb", "EAPB / EPS", 20),
            ("diagnostico_inicial", "Diagnóstico Inicial", 22),
            ("estado_actual", "Estado Actual", 15),
            ("fuente_captacion", "Fuente de Captación", 20)
        ]

        ws.merge_range(0, 0, 0, len(cols) - 1, 'INSTITUTO NACIONAL DE SALUD • SIVIGILA — IPSI KOTTUSHI SAO ANA>A', fmt_title)
        ws.set_row(0, 24)
        sub_text = f"Reporte Epidemiológico Oficial • Evento: {evento or '113 / 114'} • Semana: {semana or 'Todas'} • Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_range(1, 0, 1, len(cols) - 1, sub_text, fmt_sub)
        ws.set_row(1, 18)

        # Encabezados
        ws.set_row(2, 22)
        for i, (cid, cname, width) in enumerate(cols):
            ws.write(2, i, cname, fmt_hdr)
            ws.set_column(i, i, width)

        # Datos
        for r_idx, row in df.iterrows():
            row_num = r_idx + 3
            ws.set_row(row_num, 18)
            for c_idx, (cid, _, _) in enumerate(cols):
                val = row[cid] if cid in row else ""
                if pd.isna(val) or val is None:
                    val = ""
                if "fec" in cid and val != "":
                    try:
                        ws.write(row_num, c_idx, str(val)[:10], fmt_date)
                    except:
                        ws.write(row_num, c_idx, str(val), fmt_center)
                elif cid in ("cod_eve", "semana", "anio", "tip_ide_", "num_ide_", "sexo_", "edad_meses"):
                    ws.write(row_num, c_idx, val, fmt_center)
                else:
                    ws.write(row_num, c_idx, str(val), fmt_cell)

        ws.autofilter(2, 0, len(df) + 2, len(cols) - 1)
        ws.freeze_panes(3, 0)

    output.seek(0)
    tag_semana = f"SE{semana}" if semana else "CONSOLIDADO"
    tag_eve = f"EVE{evento}" if evento else "EVE113_114"
    filename = f"reporte_sivigila_{tag_eve}_{tag_semana}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exportar-t302")
def exportar_dossier_sentencia_t302(
    municipio: Optional[str] = Query(None, description="Riohacha, Manaure, Maicao, Uribia"),
    eapb: Optional[str] = Query(None, description="EPS / EAPB"),
    db: Session = Depends(get_db)
):
    """
    Genera el dossier institucional para comités de la Sentencia T-302 de la Corte Constitucional
    y mesas de emergencia nutricional (Defensoría del Pueblo, ICBF, Supersalud).
    """
    filtros = []
    params = {}

    if municipio and municipio != "TODOS":
        filtros.append("m.nombre ILIKE :municipio")
        params["municipio"] = f"%{municipio}%"

    if eapb and eapb != "TODAS":
        filtros.append("e.nombre ILIKE :eapb")
        params["eapb"] = f"%{eapb}%"

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    sql = f"""
    SELECT 
        nc.caso_id,
        m.nombre AS municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_rancheria,
        COALESCE(cuid.nombre_completo, 'Sin Cuidador') AS nombre_cuidador,
        COALESCE(cuid.telefono, 'Sin Teléfono') AS telefono_contacto,
        p.tipo_documento,
        p.numero_documento,
        TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) AS nombre_menor,
        p.sexo,
        p.fecha_nacimiento,
        FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)))::INT AS edad_meses,
        e.nombre AS eapb,
        nc.fecha_notificacion,
        nc.peso_inicial_kg,
        nc.talla_inicial_cm,
        nc.zscore_inicial,
        COALESCE(v.clasificacion_nutricional_actual, 'Desnutrición Aguda') AS clasificacion_nutricional_inicial,
        nc.fecha_primera_atencion,
        v.fecha_ultima_atencion,
        v.clasificacion_nutricional_actual,
        nc.sobres_ftlc_inicial AS formula_terapeutica_sobres,
        nc.estado_caso,
        COALESCE(nc.observaciones, 'Seguimiento por Equipo Extramural GBAI') AS conducta
    FROM notificaciones_caso nc
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    LEFT JOIN vw_estado_actual_casos v ON nc.caso_id = v.caso_id
    {where_clause}
    ORDER BY m.nombre ASC, nc.estado_caso ASC, nc.caso_id DESC
    LIMIT 10000;
    """

    df = pd.read_sql_query(text(sql), db.connection(), params=params)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        ws = wb.add_worksheet('Dossier Sentencia T-302')
        writer.sheets['Dossier Sentencia T-302'] = ws

        fmt_title = wb.add_format({
            'bold': True, 'font_size': 12, 'font_name': 'Segoe UI',
            'bg_color': '#4a044e', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_sub = wb.add_format({
            'italic': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#fdf4ff', 'font_color': '#701a75', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_hdr = wb.add_format({
            'bold': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#86198f', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#701a75', 'text_wrap': True
        })
        fmt_cell = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'valign': 'vcenter'})
        fmt_center = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'align': 'center', 'valign': 'vcenter'})
        fmt_num = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'align': 'center', 'valign': 'vcenter', 'num_format': '0.00'})

        cols = [
            ("caso_id", "Caso ID", 10),
            ("municipio", "Municipio T-302", 15),
            ("comunidad_rancheria", "Comunidad / Ranchería Wayuu", 26),
            ("nombre_cuidador", "Acudiente / Autoridad", 22),
            ("telefono_contacto", "Teléfono", 14),
            ("tipo_documento", "Tipo", 8),
            ("numero_documento", "Documento Menor", 16),
            ("nombre_menor", "Nombre Completo del Menor", 28),
            ("sexo", "Sexo", 8),
            ("edad_meses", "Edad (m)", 10),
            ("eapb", "EPS / EAPB", 20),
            ("fecha_notificacion", "Fecha Notif.", 12),
            ("peso_inicial_kg", "Peso Inic.", 10),
            ("talla_inicial_cm", "Talla Inic.", 10),
            ("zscore_inicial", "Z-Score Inic.", 12),
            ("clasificacion_nutricional_inicial", "Diagnóstico Inicial", 22),
            ("fecha_primera_atencion", "1ra Atención", 12),
            ("fecha_ultima_atencion", "Último Control", 12),
            ("clasificacion_nutricional_actual", "Diagnóstico Actual", 22),
            ("formula_terapeutica_sobres", "Sobres FTLC", 12),
            ("estado_caso", "Estado Caso", 14),
            ("conducta", "Conducta / Manejo", 26)
        ]

        ws.merge_range(0, 0, 0, len(cols) - 1, 'IPSI KOTTUSHI SAO ANA>A • DOSSIER EPIDEMIOLÓGICO SENTENCIA T-302 CORTE CONSTITUCIONAL', fmt_title)
        ws.set_row(0, 24)
        sub_text = f"Mesa Técnica de Emergencia Nutricional • Territorio: {municipio or 'Todos (Riohacha, Manaure, Maicao, Uribia)'} • Casos reportados: {len(df)} • Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        ws.merge_range(1, 0, 1, len(cols) - 1, sub_text, fmt_sub)
        ws.set_row(1, 18)

        ws.set_row(2, 24)
        for i, (cid, cname, width) in enumerate(cols):
            ws.write(2, i, cname, fmt_hdr)
            ws.set_column(i, i, width)

        for r_idx, row in df.iterrows():
            row_num = r_idx + 3
            ws.set_row(row_num, 18)
            for c_idx, (cid, _, _) in enumerate(cols):
                val = row[cid] if cid in row else ""
                if pd.isna(val) or val is None:
                    val = ""
                if cid in ("peso_inicial_kg", "talla_inicial_cm", "zscore_inicial"):
                    try: ws.write(row_num, c_idx, float(val), fmt_num)
                    except: ws.write(row_num, c_idx, str(val), fmt_center)
                elif cid in ("caso_id", "tipo_documento", "numero_documento", "sexo", "edad_meses", "fecha_notificacion", "fecha_primera_atencion", "fecha_ultima_atencion", "estado_caso"):
                    ws.write(row_num, c_idx, str(val)[:10] if "fecha" in cid else val, fmt_center)
                else:
                    ws.write(row_num, c_idx, str(val), fmt_cell)

        ws.autofilter(2, 0, len(df) + 2, len(cols) - 1)
        ws.freeze_panes(3, 0)

    output.seek(0)
    tag_mun = municipio.replace(" ", "_").upper() if municipio else "TUTELA_T302"
    filename = f"dossier_sentencia_t302_{tag_mun}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exportar-busqueda-activa")
def exportar_planilla_busqueda_activa(
    dias_vencido_min: int = Query(15, description="Días mínimos de vencimiento de cita"),
    municipio: Optional[str] = Query(None, description="Municipio"),
    db: Session = Depends(get_db)
):
    """
    Genera la planilla operativa de campo para las brigadas de Búsqueda Activa Institucional (GBAI).
    Lista a los menores con citas vencidas, riesgo de abandono y datos del cuidador/comunidad.
    """
    filtros = [
        "v.estado_caso = 'En seguimiento'",
        "v.fecha_proxima_cita IS NOT NULL",
        f"v.fecha_proxima_cita < (CURRENT_DATE - INTERVAL '{dias_vencido_min} days')"
    ]
    params = {}

    if municipio and municipio != "TODOS":
        filtros.append("v.municipio ILIKE :municipio")
        params["municipio"] = f"%{municipio}%"

    where_clause = f"WHERE {' AND '.join(filtros)}"

    sql = f"""
    SELECT 
        v.caso_id,
        v.municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_rancheria,
        COALESCE(p.georreferenciacion, 'Sin Dato') AS georreferenciacion,
        COALESCE(cuid.nombre_completo, 'Sin Cuidador') AS nombre_cuidador,
        COALESCE(cuid.telefono, 'Sin Teléfono') AS telefono_cuidador,
        v.tipo_documento,
        v.numero_documento,
        v.nombre_completo AS nombre_menor,
        v.edad_meses_actual,
        v.eapb,
        v.clasificacion_nutricional_actual,
        v.fecha_ultima_atencion,
        v.fecha_proxima_cita,
        (CURRENT_DATE - v.fecha_proxima_cita) AS dias_vencido,
        CASE 
            WHEN (CURRENT_DATE - v.fecha_proxima_cita) >= 30 THEN 'CRÍTICA (>30 días)'
            ELSE 'ALTA (15-29 días)'
        END AS prioridad_rescate
    FROM vw_estado_actual_casos v
    JOIN notificaciones_caso nc ON v.caso_id = nc.caso_id
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    {where_clause}
    ORDER BY dias_vencido DESC, v.municipio ASC
    LIMIT 10000;
    """

    df = pd.read_sql_query(text(sql), db.connection(), params=params)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        ws = wb.add_worksheet('Búsqueda Activa GBAI')
        writer.sheets['Búsqueda Activa GBAI'] = ws

        fmt_title = wb.add_format({
            'bold': True, 'font_size': 12, 'font_name': 'Segoe UI',
            'bg_color': '#78350f', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_sub = wb.add_format({
            'italic': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#fef3c7', 'font_color': '#92400e', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_hdr = wb.add_format({
            'bold': True, 'font_size': 9, 'font_name': 'Segoe UI',
            'bg_color': '#d97706', 'font_color': '#ffffff', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#b45309', 'text_wrap': True
        })
        fmt_crit = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'bg_color': '#fee2e2', 'font_color': '#b91c1c', 'border': 1, 'align': 'center'})
        fmt_alta = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'bg_color': '#ffedd5', 'font_color': '#c2410c', 'border': 1, 'align': 'center'})
        fmt_cell = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'valign': 'vcenter'})
        fmt_center = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#cbd5e1', 'align': 'center', 'valign': 'vcenter'})
        fmt_blank = wb.add_format({'font_name': 'Segoe UI', 'font_size': 9, 'border': 1, 'border_color': '#94a3b8', 'bg_color': '#ffffff'})

        cols = [
            ("caso_id", "Caso ID", 10),
            ("municipio", "Municipio", 14),
            ("comunidad_rancheria", "Comunidad / Ranchería", 24),
            ("nombre_cuidador", "Acudiente / Cuidador", 22),
            ("telefono_cuidador", "Teléfono Cuidador", 15),
            ("numero_documento", "Documento Menor", 15),
            ("nombre_menor", "Nombre Completo del Menor", 26),
            ("edad_meses_actual", "Edad (m)", 10),
            ("eapb", "EPS / EAPB", 18),
            ("clasificacion_nutricional_actual", "Último Diagnóstico", 20),
            ("fecha_proxima_cita", "Cita Vencida", 12),
            ("dias_vencido", "Días Vencido", 12),
            ("prioridad_rescate", "Prioridad", 16),
            ("campo_visita", "Resultado de Visita (Efectiva / No Hallado)", 26),
            ("campo_peso", "Nuevo Peso (kg)", 14),
            ("campo_observaciones", "Observaciones Brigada GBAI", 30)
        ]

        ws.merge_range(0, 0, 0, len(cols) - 1, 'IPSI KOTTUSHI SAO ANA>A • PLANILLA DE RESCATE NUTRICIONAL EXTRAMURAL (GBAI)', fmt_title)
        ws.set_row(0, 24)
        sub_text = f"Búsqueda Activa Comunitaria • Niños con inasistencia ≥ {dias_vencido_min} días • Total casos a rescatar: {len(df)} • Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        ws.merge_range(1, 0, 1, len(cols) - 1, sub_text, fmt_sub)
        ws.set_row(1, 18)

        ws.set_row(2, 26)
        for i, (cid, cname, width) in enumerate(cols):
            ws.write(2, i, cname, fmt_hdr)
            ws.set_column(i, i, width)

        for r_idx, row in df.iterrows():
            row_num = r_idx + 3
            ws.set_row(row_num, 20)
            for c_idx, (cid, _, _) in enumerate(cols):
                if cid == "campo_visita" or cid == "campo_peso" or cid == "campo_observaciones":
                    ws.write(row_num, c_idx, "", fmt_blank)
                elif cid == "prioridad_rescate":
                    prior = str(row[cid])
                    ws.write(row_num, c_idx, prior, fmt_crit if "CRÍTICA" in prior else fmt_alta)
                else:
                    val = row[cid] if cid in row else ""
                    if pd.isna(val) or val is None: val = ""
                    if cid in ("caso_id", "numero_documento", "edad_meses_actual", "fecha_proxima_cita", "dias_vencido"):
                        ws.write(row_num, c_idx, str(val)[:10] if "fecha" in cid else val, fmt_center)
                    else:
                        ws.write(row_num, c_idx, str(val), fmt_cell)

        ws.autofilter(2, 0, len(df) + 2, len(cols) - 1)
        ws.freeze_panes(3, 0)

    output.seek(0)
    tag_mun = municipio.replace(" ", "_").upper() if municipio else "GUAJIRA"
    filename = f"busqueda_activa_gbai_{tag_mun}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

