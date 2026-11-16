"""
Generador de Expediente Clínico Imprimible e Historial de Trazabilidad Integral
Conforme a la Resolución 000115 de 2026 (Ministerio de Salud y Protección Social)
IPSI Kottushi Sao Ana>a
"""

from datetime import datetime, date
from typing import Dict, Any, List

def obtener_color_badge_dx(clasificacion: str) -> tuple:
    """Retorna (bg_color, text_color, border_color) según la clasificación."""
    if not clasificacion:
        return ("#f1f5f9", "#475569", "#cbd5e1")
    c = clasificacion.lower()
    if "severa" in c:
        return ("#fee2e2", "#991b1b", "#f87171")
    elif "moderada" in c:
        return ("#ffedd5", "#c2410c", "#fb923c")
    elif "riesgo" in c:
        return ("#fef3c7", "#b45309", "#fcd34d")
    elif "adecuado" in c:
        return ("#dcfce7", "#166534", "#86efac")
    elif "sobrepeso" in c:
        return ("#f3e8ff", "#6b21a8", "#d8b4fe")
    return ("#f1f5f9", "#475569", "#cbd5e1")

def generar_html_expediente_imprimible(data: Dict[str, Any], autoprint: bool = False) -> str:
    resumen = data.get("resumen", {})
    detalle_notif = data.get("detalle_notificacion", {})
    timeline = data.get("timeline_trazabilidad", [])
    total_episodios = data.get("total_episodios_paciente", 1)
    
    ahora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    hoy = date.today()

    caso_id = resumen.get("caso_id", "-")
    paciente_id = resumen.get("paciente_id", "-")
    nombre_completo = resumen.get("nombre_completo", "Sin Nombre")
    tipo_doc = resumen.get("tipo_documento", "-")
    num_doc = resumen.get("numero_documento", "-")
    sexo = "Masculino (M)" if resumen.get("sexo") == "M" else ("Femenino (F)" if resumen.get("sexo") == "F" else "-")
    f_nac = str(resumen.get("fecha_nacimiento") or "-")
    edad_meses = resumen.get("edad_meses_actual", "-")
    municipio = resumen.get("municipio", "-")
    eapb = resumen.get("eapb", "-")
    sede_ipsi = resumen.get("sede_ipsi", "IPSI Kottushi Sao Ana>a")
    cuidador = resumen.get("cuidador", "No registrado")
    doc_cuidador = resumen.get("documento_cuidador", "No registrado")
    tel_cuidador = resumen.get("telefono_cuidador", "No registrado")
    georref = resumen.get("georreferenciacion", "No registrada")

    evento = resumen.get("fuente_notificacion", "Evento 114: Riesgo DNT")
    f_notif = str(resumen.get("fecha_notificacion") or "-")
    cooperante = detalle_notif.get("cooperante_notificador") or "Comunidad / IPSI"
    medio_notif = detalle_notif.get("medio_notificacion") or "Sin dato"
    estado_caso = resumen.get("estado_caso", "En seguimiento")
    total_controles = resumen.get("total_controles", 0)
    ultimo_zscore = resumen.get("ultimo_zscore")
    zscore_str = f"{float(ultimo_zscore):.2f}" if ultimo_zscore is not None else "Sin dato"
    dx_actual = resumen.get("clasificacion_nutricional_actual") or "Sin dato antropométrico"
    bg_dx, tx_dx, bd_dx = obtener_color_badge_dx(dx_actual)
    
    f_prox_cita = resumen.get("fecha_proxima_cita")
    if estado_caso == "En seguimiento" and f_prox_cita:
        f_prox_str = str(f_prox_cita)
        cita_vencida = bool(resumen.get("alerta_cita_vencida"))
        cita_badge_html = f'<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #f87171;">🚨 CITA VENCIDA ({f_prox_str})</span>' if cita_vencida else f'<span style="background-color: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #a7f3d0;">Al día ({f_prox_str})</span>'
    else:
        cita_badge_html = '<span style="color: #64748b;">-</span>'

    # Filas de la tabla resumen de evolución antropométrica
    filas_tabla_evolucion = []
    for idx, h in enumerate(timeline, 1):
        z = h.get("zscore")
        z_fmt = f"{float(z):.2f}" if z is not None else "-"
        p_kg = f"{float(h.get('peso_kg')):.2f}" if h.get("peso_kg") is not None else "-"
        t_cm = f"{float(h.get('talla_cm')):.1f}" if h.get("talla_cm") is not None else "-"
        pb_cm = f"{float(h.get('pb_cm')):.1f}" if h.get("pb_cm") is not None else "-"
        
        dp = h.get("delta_peso_kg")
        if dp is not None:
            dp_str = f"+{dp:.2f} kg" if dp > 0 else (f"{dp:.2f} kg" if dp < 0 else "0.00")
            dp_color = '#166534' if dp > 0 else ('#991b1b' if dp < 0 else '#64748b')
        else:
            dp_str = "-"
            dp_color = '#64748b'

        dz = h.get("delta_zscore")
        if dz is not None:
            dz_str = f"+{dz:.2f}" if dz > 0 else (f"{dz:.2f}" if dz < 0 else "0.00")
            dz_color = '#166534' if dz > 0 else ('#991b1b' if dz < 0 else '#64748b')
        else:
            dz_str = "-"
            dz_color = '#64748b'
        
        dx_h = h.get("clasificacion") or "-"
        bg_h, tx_h, bd_h = obtener_color_badge_dx(dx_h)
        badge_h = f'<span style="background:{bg_h}; color:{tx_h}; border:1px solid {bd_h}; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:bold;">{dx_h}</span>'
        
        trat = h.get("tratamiento") or "-"
        ftlc = h.get("sobres_ftlc")
        ftlc_str = str(ftlc) if ftlc else "-"
        prox_c = str(h.get("fecha_proxima_cita") or "-")

        filas_tabla_evolucion.append(f"""
        <tr>
            <td style="text-align: center; font-weight: bold;">{idx}</td>
            <td style="font-weight: 600;">{h.get('tipo_hito', '-')}</td>
            <td style="text-align: center;">{h.get('fecha', '-')}</td>
            <td style="text-align: center; font-weight: bold;">{p_kg}</td>
            <td style="text-align: center;">{t_cm}</td>
            <td style="text-align: center;">{pb_cm}</td>
            <td style="text-align: center; font-weight: bold;">{z_fmt}</td>
            <td style="text-align: center; font-size: 10px; color: {dp_color};">{dp_str}</td>
            <td style="text-align: center; font-size: 10px; color: {dz_color};">{dz_str}</td>
            <td>{badge_h}</td>
            <td style="font-size: 10px;">{trat}</td>
            <td style="text-align: center; font-weight: bold;">{ftlc_str}</td>
            <td style="text-align: center; font-size: 10px;">{prox_c}</td>
        </tr>
        """)

    # Fichas detalladas de cada hito
    fichas_hitos_html = []
    for idx, h in enumerate(timeline, 1):
        z = h.get("zscore")
        z_fmt = f"{float(z):.2f}" if z is not None else "Sin dato"
        p_kg = f"{float(h.get('peso_kg')):.2f} kg" if h.get("peso_kg") is not None else "Sin dato"
        t_cm = f"{float(h.get('talla_cm')):.1f} cm" if h.get("talla_cm") is not None else "Sin dato"
        pb_cm = f"{float(h.get('pb_cm')):.1f} cm" if h.get("pb_cm") is not None else "Sin dato"
        
        dp = h.get("delta_peso_kg")
        if dp is not None:
            dp_str = f" (Δ +{dp:.2f} kg)" if dp > 0 else (f" (Δ {dp:.2f} kg)" if dp < 0 else " (Δ 0.00 kg)")
        else:
            dp_str = ""

        dz = h.get("delta_zscore")
        if dz is not None:
            dz_str = f" (Δ +{dz:.2f})" if dz > 0 else (f" (Δ {dz:.2f})" if dz < 0 else " (Δ 0.00)")
        else:
            dz_str = ""
        
        dx_h = h.get("clasificacion") or "Sin clasificación"
        bg_h, tx_h, bd_h = obtener_color_badge_dx(dx_h)
        badge_h = f'<span style="background:{bg_h}; color:{tx_h}; border:1px solid {bd_h}; padding:3px 8px; border-radius:12px; font-size:11px; font-weight:bold;">{dx_h}</span>'
        
        coop = h.get("cooperante") or h.get("fuente_notificacion") or "IPSI Kottushi Sao Ana>a"
        medio = h.get("medio_notificacion") or "-"
        trat = h.get("tratamiento") or "No aplica / No formulado"
        ftlc = h.get("sobres_ftlc") or 0
        p_apetito = h.get("prueba_apetito") or "-"
        escenario = h.get("escenario_manejo") or "-"
        comorb = h.get("comorbilidad") or "Ninguna registrada"
        novedad = h.get("novedad") or "-"
        obs = h.get("observaciones") or "Sin observaciones registradas."
        
        dias_prox = h.get("dias_proxima_cita")
        prox_c = str(h.get("fecha_proxima_cita") or "-")
        prox_info = f"Cada {dias_prox} días (Fecha: {prox_c})" if dias_prox else (prox_c if prox_c != "-" else "No programada")

        fichas_hitos_html.append(f"""
        <div class="card-hito avoid-break">
            <div class="card-hito-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">{h.get('icono', '📌')}</span>
                    <strong style="font-size: 13px; color: #0f172a;">Hito {idx}: {h.get('tipo_hito', 'Intervención')}</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 600; color: #0369a1; font-size: 12px;">📅 Fecha: {h.get('fecha', '-')}</span>
                    {badge_h}
                </div>
            </div>
            
            <div class="grid-4" style="margin-top: 8px; padding-bottom: 6px; border-bottom: 1px dashed #e2e8f0;">
                <div><span class="lbl">Peso:</span> <strong class="val">{p_kg}</strong> <span style="font-size: 10px; color: #64748b;">{dp_str}</span></div>
                <div><span class="lbl">Talla:</span> <strong class="val">{t_cm}</strong></div>
                <div><span class="lbl">Perímetro Braquial:</span> <strong class="val">{pb_cm}</strong></div>
                <div><span class="lbl">Puntaje Z (P/T):</span> <strong class="val">{z_fmt}</strong> <span style="font-size: 10px; color: #64748b;">{dz_str}</span></div>
            </div>

            <div class="grid-3" style="margin-top: 8px;">
                <div><span class="lbl">Tratamiento / Esquema:</span> <span class="val-sm">{trat}</span></div>
                <div><span class="lbl">Sobres FTLC Entregados:</span> <strong class="val-sm">{ftlc} sobres</strong></div>
                <div><span class="lbl">Prueba de Apetito:</span> <span class="val-sm">{p_apetito}</span></div>
            </div>

            <div class="grid-3" style="margin-top: 6px;">
                <div><span class="lbl">Escenario de Manejo:</span> <span class="val-sm">{escenario}</span></div>
                <div><span class="lbl">Comorbilidades:</span> <span class="val-sm">{comorb}</span></div>
                <div><span class="lbl">Próxima Cita Estimada:</span> <strong class="val-sm" style="color: #0369a1;">{prox_info}</strong></div>
            </div>

            <div style="margin-top: 6px; background-color: #f8fafc; padding: 6px 8px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <div style="margin-bottom: 2px;"><span class="lbl">Responsable / Cooperante / Medio:</span> <span class="val-sm">{coop} • Medio: {medio} • Novedad: {novedad}</span></div>
                <div><span class="lbl">Observaciones Clínicas:</span> <span class="val-sm" style="font-style: italic; color: #334155;">"{obs}"</span></div>
            </div>
        </div>
        """)

    # HTML Completo Autocontenido
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expediente Clínico DNT - Caso #{caso_id} - {nombre_completo}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            background-color: #f8fafc;
            line-height: 1.4;
            font-size: 11px;
            padding: 20px;
        }}
        .no-print {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0f172a;
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .btn-print {{
            background: #0284c7;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: background 0.2s;
        }}
        .btn-print:hover {{
            background: #0369a1;
        }}
        .btn-close {{
            background: #475569;
            color: #ffffff;
            border: none;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            margin-left: 8px;
        }}
        .sheet-container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            padding: 24px 30px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .header-box {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #0369a1;
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .ipsi-title {{
            font-size: 16px;
            font-weight: 900;
            color: #0369a1;
            letter-spacing: 0.5px;
        }}
        .ipsi-sub {{
            font-size: 10px;
            color: #334155;
            font-weight: 600;
            margin-top: 2px;
        }}
        .ipsi-reps {{
            font-size: 9px;
            color: #64748b;
        }}
        .doc-badge-box {{
            text-align: right;
        }}
        .doc-badge-title {{
            background: #0369a1;
            color: #ffffff;
            font-weight: bold;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            display: inline-block;
        }}
        .doc-badge-norm {{
            font-size: 9px;
            color: #0369a1;
            font-weight: bold;
            margin-top: 3px;
        }}
        .doc-badge-date {{
            font-size: 9px;
            color: #64748b;
        }}
        .sec-title {{
            font-size: 12px;
            font-weight: bold;
            color: #0369a1;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 4px;
            margin-top: 14px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        table.tbl-info {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
            font-size: 10.5px;
        }}
        table.tbl-info th, table.tbl-info td {{
            padding: 5px 8px;
            border: 1px solid #cbd5e1;
            vertical-align: middle;
        }}
        table.tbl-info th {{
            background-color: #f1f5f9;
            color: #334155;
            font-weight: 700;
            width: 18%;
        }}
        table.tbl-info td {{
            color: #0f172a;
            width: 32%;
        }}
        table.tbl-matrix {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            margin-bottom: 14px;
            font-size: 9.5px;
        }}
        table.tbl-matrix th, table.tbl-matrix td {{
            padding: 5px 6px;
            border: 1px solid #cbd5e1;
            vertical-align: middle;
        }}
        table.tbl-matrix th {{
            background-color: #0284c7;
            color: #ffffff;
            font-weight: bold;
            text-align: center;
        }}
        table.tbl-matrix tbody tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        .card-hito {{
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 10px;
            background: #ffffff;
        }}
        .card-hito-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 6px;
        }}
        .grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}
        .lbl {{
            font-size: 9.5px;
            color: #64748b;
            display: block;
        }}
        .val {{
            font-size: 11.5px;
            font-weight: 700;
            color: #0f172a;
        }}
        .val-sm {{
            font-size: 10.5px;
            font-weight: 600;
            color: #1e293b;
        }}
        .firmas-container {{
            margin-top: 24px;
            padding-top: 14px;
            border-top: 1px solid #cbd5e1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
        }}
        .firma-box {{
            text-align: center;
        }}
        .firma-linea {{
            border-top: 1px solid #0f172a;
            margin-top: 45px;
            margin-bottom: 4px;
        }}
        .legal-footer {{
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px dashed #cbd5e1;
            font-size: 8.5px;
            color: #64748b;
            text-align: justify;
            line-height: 1.3;
        }}
        .avoid-break {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        @media print {{
            .no-print {{
                display: none !important;
            }}
            body {{
                background-color: #ffffff !important;
                padding: 0 !important;
                font-size: 10px !important;
            }}
            .sheet-container {{
                max-width: 100% !important;
                border: none !important;
                padding: 0 !important;
                box-shadow: none !important;
            }}
            @page {{
                size: letter portrait;
                margin: 10mm 12mm 12mm 12mm;
            }}
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
        }}
    </style>
</head>
<body>

    <div class="no-print">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 18px;">📄</span>
            <div>
                <strong style="font-size: 13px;">Expediente Clínico Longitudinal - Modo de Impresión Oficial</strong>
                <p style="font-size: 10.5px; color: #94a3b8;">Generado según los lineamientos de la Resolución 000115 de 2026. Listo para imprimir o guardar en PDF.</p>
            </div>
        </div>
        <div>
            <button class="btn-print" onclick="window.print()">
                <span>🖨️ Imprimir / Guardar en PDF</span>
            </button>
            <button class="btn-close" onclick="window.close()">Cerrar</button>
        </div>
    </div>

    <div class="sheet-container">
        <!-- Encabezado Institucional Oficial -->
        <div class="header-box">
            <div>
                <div class="ipsi-title">IPSI KOTTUSHI SAO ANA&gt;A</div>
                <div class="ipsi-sub">INSTITUCIÓN PRESTADORA DE SERVICIOS DE SALUD INDÍGENA</div>
                <div class="ipsi-reps">NIT: 900.584.231-8 • Vigilancia Epidemiológica y Nutricional Comunitaria e Institucional</div>
                <div class="ipsi-reps">Sede: {sede_ipsi} • Municipio: {municipio}, La Guajira</div>
            </div>
            <div class="doc-badge-box">
                <div class="doc-badge-title">HISTORIA CLÍNICA INTEGRAL</div>
                <div class="doc-badge-norm">Resolución 000115 de 2026</div>
                <div class="doc-badge-date">Caso No. <strong>#{caso_id}</strong> • Paciente ID: <strong>#{paciente_id}</strong></div>
                <div class="doc-badge-date">Emisión: {ahora_str}</div>
            </div>
        </div>

        <!-- Bloque 1: Identificación del Paciente y Familia -->
        <div class="sec-title">
            <span>1. Datos de Filiación del Menor y Núcleo Familiar</span>
            <span style="font-size: 10px; font-weight: normal; color: #64748b;">Notificaciones Históricas: {total_episodios}</span>
        </div>
        <table class="tbl-info">
            <tr>
                <th>Nombre del Menor:</th>
                <td colspan="3"><strong style="font-size: 12px; color: #0369a1;">{nombre_completo}</strong></td>
            </tr>
            <tr>
                <th>Tipo y Documento:</th>
                <td><strong>{tipo_doc} {num_doc}</strong></td>
                <th>Sexo:</th>
                <td>{sexo}</td>
            </tr>
            <tr>
                <th>Fecha Nacimiento:</th>
                <td>{f_nac}</td>
                <th>Edad Actual:</th>
                <td><strong>{edad_meses} meses</strong></td>
            </tr>
            <tr>
                <th>Municipio Residencia:</th>
                <td>{municipio}</td>
                <th>Aseguradora (EAPB):</th>
                <td>{eapb}</td>
            </tr>
            <tr>
                <th>Cuidador(a) / Madre:</th>
                <td>{cuidador}</td>
                <th>Doc. Cuidador(a):</th>
                <td>{doc_cuidador}</td>
            </tr>
            <tr>
                <th>Teléfono Contacto:</th>
                <td>{tel_cuidador}</td>
                <th>Comunidad / Dirección:</th>
                <td>{georref}</td>
            </tr>
        </table>

        <!-- Bloque 2: Estado Clínico y Resumen Epidemiológico -->
        <div class="sec-title">
            <span>2. Resumen del Caso y Estado Nutricional Actual</span>
            <span style="font-size: 10px; font-weight: normal; color: #64748b;">Conforme a Res. 000115/2026</span>
        </div>
        <table class="tbl-info">
            <tr>
                <th>Evento SIVIGILA:</th>
                <td><strong>{evento}</strong></td>
                <th>Fecha Notificación:</th>
                <td>{f_notif}</td>
            </tr>
            <tr>
                <th>Fuente / Cooperante:</th>
                <td>{cooperante}</td>
                <th>Medio Notificación:</th>
                <td>{medio_notif}</td>
            </tr>
            <tr>
                <th>Estado del Caso:</th>
                <td><strong>{estado_caso}</strong></td>
                <th>Total Controles:</th>
                <td><strong>{total_controles} citas registradas</strong></td>
            </tr>
            <tr>
                <th>Último Puntaje Z (P/T):</th>
                <td><strong style="font-size: 12px;">{zscore_str}</strong></td>
                <th>Diagnóstico Nutricional:</th>
                <td><span style="background:{bg_dx}; color:{tx_dx}; border:1px solid {bd_dx}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px;">{dx_actual}</span></td>
            </tr>
            <tr>
                <th>Seguimiento Citas:</th>
                <td>{cita_badge_html}</td>
                <th>Sede de Atención:</th>
                <td>{sede_ipsi}</td>
            </tr>
        </table>

        <!-- Bloque 3: Tabla Cronológica de Controles -->
        <div class="sec-title avoid-break">
            <span>3. Matriz Longitudinal de Evolución Antropométrica</span>
            <span style="font-size: 10px; font-weight: normal; color: #64748b;">{len(timeline)} hitos clínicos</span>
        </div>
        <table class="tbl-matrix avoid-break">
            <thead>
                <tr>
                    <th style="width: 25px;">#</th>
                    <th>Hito / Tipo Consulta</th>
                    <th style="width: 65px;">Fecha</th>
                    <th style="width: 50px;">Peso</th>
                    <th style="width: 45px;">Talla</th>
                    <th style="width: 45px;">P.B.</th>
                    <th style="width: 50px;">Puntaje Z</th>
                    <th style="width: 45px;">Δ Peso</th>
                    <th style="width: 45px;">Δ Z</th>
                    <th>Clasificación Nutricional</th>
                    <th>Tratamiento</th>
                    <th style="width: 40px;">FTLC</th>
                    <th style="width: 65px;">Próx. Cita</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas_tabla_evolucion)}
            </tbody>
        </table>

        <!-- Bloque 4: Ruta de Atención y Trazabilidad Detallada Hito a Hito -->
        <div class="sec-title avoid-break">
            <span>4. Trazabilidad Detallada de la Ruta de Atención e Intervenciones</span>
            <span style="font-size: 10px; font-weight: normal; color: #64748b;">Captación ➔ GBAI ➔ Atención IPSI ➔ Controles</span>
        </div>
        <div class="timeline-detail-box">
            {''.join(fichas_hitos_html)}
        </div>

        <!-- Bloque 5: Firmas de Responsabilidad Médica y Auditoría -->
        <div class="firmas-container avoid-break">
            <div class="firma-box">
                <div class="firma-linea"></div>
                <strong style="font-size: 11px; color: #0f172a;">Profesional de la Salud Tratante / Nutricionista</strong><br>
                <span style="font-size: 9.5px; color: #64748b;">Registro Médico / Tarjeta Profesional</span><br>
                <span style="font-size: 9px; color: #64748b;">IPSI Kottushi Sao Ana&gt;a</span>
            </div>
            <div class="firma-box">
                <div class="firma-linea"></div>
                <strong style="font-size: 11px; color: #0f172a;">Coordinación de Vigilancia Epidemiológica</strong><br>
                <span style="font-size: 9.5px; color: #64748b;">Auditoría de Ruta de Desnutrición Aguda (DNT)</span><br>
                <span style="font-size: 9px; color: #64748b;">IPSI Kottushi Sao Ana&gt;a</span>
            </div>
        </div>

        <!-- Pie Legal y de Confidencialidad -->
        <div class="legal-footer avoid-break">
            <strong>CERTIFICADO Y CUSTODIA DE INFORMACIÓN CLÍNICA:</strong> El presente documento constituye copia fidedigna del expediente clínico y la ruta de seguimiento longitudinal registrado en el Sistema de Vigilancia Nutricional de la IPSI Kottushi Sao Ana&gt;a, en estricto cumplimiento de los lineamientos técnicos y operativos de la Resolución 000115 de 2026 del Ministerio de Salud y Protección Social. Esta información es de carácter estrictamente confidencial y reservado, amparada por la Ley Estatutaria 1581 de 2012 (Protección de Datos Personales) y la Resolución 1995 de 1999 (Custodia y Manejo de Historias Clínicas). Prohibida su reproducción no autorizada.
        </div>
    </div>

    {'<script>window.onload = function() { window.print(); };</script>' if autoprint else ''}
</body>
</html>
"""
    return html
