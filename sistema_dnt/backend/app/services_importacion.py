"""
Servicio de Ingesta, Sincronización Incremental y Upsert de Reportes Excel EPS
Sistema de Vigilancia y Seguimiento Nutricional
IPSI Kottushi Sao Ana>a
"""

import io
import re
import time
import openpyxl
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# ==============================================================================
# FUNCIONES AUXILIARES DE PARSEO Y LIMPIEZA
# ==============================================================================

def clean_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ["sin dato", "sin datos", "n/a", "sd", "none", "nan", "null"]:
        return None
    return s

def parse_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    if s.lower() in ["sin dato", "sin datos", "n/a", "sd", "", "none", "nan"]:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None

def parse_numeric(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if val != val:  # NaN check
            return None
        return round(float(val), 2)
    s = str(val).strip().replace(",", ".")
    if s.lower() in ["sin dato", "sin datos", "n/a", "sd", "", "none", "nan", "#div/0!", "#value!", "#n/a", "#ref!"]:
        return None
    m = re.search(r'[-+]?\d*\.?\d+', s)
    if m:
        try:
            return round(float(m.group(0)), 2)
        except ValueError:
            pass
    return None

def parse_int(val: Any) -> Optional[int]:
    num = parse_numeric(val)
    return int(round(num)) if num is not None else None

def parse_phone_and_notes(val: Any) -> tuple:
    if val is None:
        return None, None
    s = str(val).strip()
    if s.lower() in ["sin dato", "sin datos", "n/a", "sd", "", "none"]:
        return None, None
    digits = re.findall(r'\b\d{7,12}\b', s)
    phone = digits[0] if digits else None
    notes = s if not phone or phone != s else None
    return phone, notes

# ==============================================================================
# PROCESAMIENTO PRINCIPAL DE EXCEL (UPSERT INCREMENTAL)
# ==============================================================================

def procesar_excel_eps(file_bytes: bytes, filename: str, db: Session) -> Dict[str, Any]:
    t_inicio = time.time()
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    
    hojas_disponibles = wb.sheetnames
    map_hojas_norm = {h.strip().lower(): h for h in hojas_disponibles}

    # 1. Catálogos en memoria
    cur_mun = db.execute(text("SELECT LOWER(nombre), municipio_id FROM cat_municipios")).fetchall()
    map_municipios = {r[0]: r[1] for r in cur_mun}

    cur_eapb = db.execute(text("SELECT LOWER(nombre), eapb_id FROM cat_eapb")).fetchall()
    map_eapb = {r[0]: r[1] for r in cur_eapb}

    cur_sedes = db.execute(text("SELECT LOWER(nombre), sede_id FROM cat_sedes_ipsi")).fetchall()
    map_sedes = {r[0]: r[1] for r in cur_sedes}

    cur_nov = db.execute(text("SELECT LOWER(descripcion), novedad_id FROM cat_novedades")).fetchall()
    map_novedades = {r[0]: r[1] for r in cur_nov}

    def get_or_create_municipio(nombre: Optional[str]) -> Optional[int]:
        if not nombre:
            return None
        k = nombre.strip().lower()
        if k in map_municipios:
            return map_municipios[k]
        res = db.execute(
            text("INSERT INTO cat_municipios (nombre) VALUES (:nombre) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING municipio_id"),
            {"nombre": nombre.strip()}
        ).scalar()
        map_municipios[k] = res
        return res

    def get_or_create_eapb(nombre: Optional[str]) -> Optional[int]:
        if not nombre:
            return None
        k = nombre.strip().lower()
        if k in map_eapb:
            return map_eapb[k]
        res = db.execute(
            text("INSERT INTO cat_eapb (nombre) VALUES (:nombre) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING eapb_id"),
            {"nombre": nombre.strip()}
        ).scalar()
        map_eapb[k] = res
        return res

    def get_or_create_sede(nombre: Optional[str]) -> Optional[int]:
        if not nombre:
            return None
        k = nombre.strip().lower()
        if k in map_sedes:
            return map_sedes[k]
        res = db.execute(
            text("INSERT INTO cat_sedes_ipsi (nombre) VALUES (:nombre) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING sede_id"),
            {"nombre": nombre.strip()}
        ).scalar()
        map_sedes[k] = res
        return res

    def get_or_create_novedad(desc: Optional[str]) -> Optional[int]:
        if not desc:
            return None
        k = desc.strip().lower()
        if k in map_novedades:
            return map_novedades[k]
        res = db.execute(
            text("INSERT INTO cat_novedades (descripcion) VALUES (:desc) ON CONFLICT (descripcion) DO UPDATE SET descripcion=EXCLUDED.descripcion RETURNING novedad_id"),
            {"desc": desc.strip()}
        ).scalar()
        map_novedades[k] = res
        return res

    # Sincronizar listas maestras si la hoja 'Listas' está presente
    if "listas" in map_hojas_norm:
        ws_listas = wb[map_hojas_norm["listas"]]
        rows_l = list(ws_listas.iter_rows(values_only=True))
        for r in rows_l[1:]:
            if len(r) > 4 and r[4]: get_or_create_municipio(clean_str(r[4]))
            if len(r) > 10 and r[10]: get_or_create_eapb(clean_str(r[10]))
            if len(r) > 24 and r[24]: get_or_create_sede(clean_str(r[24]))
            if len(r) > 26 and r[26]: get_or_create_novedad(clean_str(r[26]))

    # Contadores de auditoría
    pacientes_creados = 0
    pacientes_actualizados = 0
    casos_creados = 0
    casos_actualizados = 0
    controles_nuevos = 0
    controles_actualizados = 0
    advertencias = []
    hojas_procesadas = []

    doc_to_caso_id = {}

    # --------------------------------------------------------------------------
    # ESTRATEGIA A: Hoja 'Notificados' (Plantilla FT-003 / FT-004 de EPS)
    # --------------------------------------------------------------------------
    if "notificados" in map_hojas_norm:
        hoja_real = map_hojas_norm["notificados"]
        hojas_procesadas.append(hoja_real)
        rows_notif = list(wb[hoja_real].iter_rows(values_only=True))

        for row_num, row in enumerate(rows_notif[8:], start=9):
            if not row or len(row) < 8:
                continue
            doc = clean_str(row[7])
            if not doc:
                continue

            tipo_doc = clean_str(row[6]) or "RC"
            p_nom = clean_str(row[8]) or "SIN NOMBRE"
            s_nom = clean_str(row[9])
            p_ape = clean_str(row[10]) or "SIN APELLIDO"
            s_ape = clean_str(row[11])
            sexo = clean_str(row[12])
            if sexo:
                sexo = sexo.upper()
                sexo = 'M' if 'M' in sexo else ('F' if 'F' in sexo else None)
            f_nac = parse_date(row[13]) or date(2024, 1, 1)

            mun_id = get_or_create_municipio(clean_str(row[5]))
            georref = clean_str(row[19])

            # Cuidador
            nom_cuid = clean_str(row[20])
            doc_cuid = clean_str(row[21])
            tel_cuid, notas_tel = parse_phone_and_notes(row[22])

            cuidador_id = None
            if nom_cuid:
                if doc_cuid:
                    cuidador_id = db.execute(
                        text("""
                            INSERT INTO cuidadores (documento_cuidador, nombre_completo, telefono, notas_contacto)
                            VALUES (:doc, :nom, :tel, :notas)
                            ON CONFLICT (documento_cuidador) DO UPDATE 
                            SET nombre_completo = EXCLUDED.nombre_completo,
                                telefono = COALESCE(EXCLUDED.telefono, cuidadores.telefono),
                                notas_contacto = COALESCE(EXCLUDED.notas_contacto, cuidadores.notas_contacto)
                            RETURNING cuidador_id
                        """),
                        {"doc": doc_cuid, "nom": nom_cuid, "tel": tel_cuid, "notas": notas_tel}
                    ).scalar()
                else:
                    c_row = db.execute(
                        text("SELECT cuidador_id FROM cuidadores WHERE documento_cuidador IS NULL AND nombre_completo = :nom LIMIT 1"),
                        {"nom": nom_cuid}
                    ).first()
                    if c_row:
                        cuidador_id = c_row[0]
                    else:
                        cuidador_id = db.execute(
                            text("INSERT INTO cuidadores (nombre_completo, telefono, notas_contacto) VALUES (:nom, :tel, :notas) RETURNING cuidador_id"),
                            {"nom": nom_cuid, "tel": tel_cuid, "notas": notas_tel}
                        ).scalar()

            # Upsert Paciente
            p_row = db.execute(
                text("SELECT paciente_id FROM pacientes WHERE numero_documento = :doc"),
                {"doc": doc}
            ).first()

            if p_row:
                paciente_id = p_row[0]
                db.execute(
                    text("""
                        UPDATE pacientes 
                        SET primer_nombre = COALESCE(:p_nom, primer_nombre),
                            segundo_nombre = COALESCE(:s_nom, segundo_nombre),
                            primer_apellido = COALESCE(:p_ape, primer_apellido),
                            segundo_apellido = COALESCE(:s_ape, segundo_apellido),
                            cuidador_id = COALESCE(:c_id, cuidador_id),
                            municipio_id = COALESCE(:m_id, municipio_id),
                            georreferenciacion = COALESCE(:geo, georreferenciacion)
                        WHERE paciente_id = :p_id
                    """),
                    {
                        "p_nom": p_nom, "s_nom": s_nom, "p_ape": p_ape, "s_ape": s_ape,
                        "c_id": cuidador_id, "m_id": mun_id, "geo": georref, "p_id": paciente_id
                    }
                )
                pacientes_actualizados += 1
            else:
                paciente_id = db.execute(
                    text("""
                        INSERT INTO pacientes (tipo_documento, numero_documento, primer_nombre, segundo_nombre,
                                               primer_apellido, segundo_apellido, sexo, fecha_nacimiento,
                                               cuidador_id, municipio_id, georreferenciacion)
                        VALUES (:td, :doc, :pn, :sn, :pa, :sa, :sx, :fn, :cid, :mid, :geo)
                        RETURNING paciente_id
                    """),
                    {
                        "td": tipo_doc, "doc": doc, "pn": p_nom, "sn": s_nom, "pa": p_ape, "sa": s_ape,
                        "sx": sexo, "fn": f_nac, "cid": cuidador_id, "mid": mun_id, "geo": georref
                    }
                ).scalar()
                pacientes_creados += 1

            # Caso de Notificación
            f_notif = parse_date(row[2])
            cooperante = clean_str(row[3])
            medio_notif = clean_str(row[4])
            fuente_notif = clean_str(row[1]) or "Evento 114: Riesgo DNT"
            eapb_id = get_or_create_eapb(clean_str(row[16]))
            tipo_afil = clean_str(row[17])
            ips_prim_id = get_or_create_sede(clean_str(row[18]))

            f_cap = parse_date(row[23])
            p_ini = parse_numeric(row[24])
            t_ini = parse_numeric(row[25])
            pb_ini = parse_numeric(row[26])
            z_ini = parse_numeric(row[27])

            f_gbai = parse_date(row[29])
            asig_int = clean_str(row[31])
            est_busq = clean_str(row[32])

            f_1ra = parse_date(row[33])
            p_1ra = parse_numeric(row[34])
            t_1ra = parse_numeric(row[35])
            pb_1ra = parse_numeric(row[36])
            z_1ra = parse_numeric(row[37])
            p_apet = clean_str(row[39])
            tratam = clean_str(row[40])
            ftlc = parse_int(row[41])
            comorb = clean_str(row[42])
            estado_str = clean_str(row[43]) or "En seguimiento"
            conducta = clean_str(row[44])
            obs = clean_str(row[45])

            # Buscar caso activo para este paciente
            caso_exist = db.execute(
                text("SELECT caso_id FROM notificaciones_caso WHERE paciente_id = :pid ORDER BY caso_id DESC LIMIT 1"),
                {"pid": paciente_id}
            ).first()

            if caso_exist:
                caso_id = caso_exist[0]
                db.execute(
                    text("""
                        UPDATE notificaciones_caso
                        SET cooperante_notificador = COALESCE(:coop, cooperante_notificador),
                            eapb_id = COALESCE(:eapb, eapb_id),
                            ips_primaria_id = COALESCE(:ips, ips_primaria_id),
                            fecha_captacion = COALESCE(:f_cap, fecha_captacion),
                            peso_inicial_kg = COALESCE(:p_ini, peso_inicial_kg),
                            talla_inicial_cm = COALESCE(:t_ini, talla_inicial_cm),
                            pb_inicial_cm = COALESCE(:pb_ini, pb_inicial_cm),
                            zscore_inicial = COALESCE(:z_ini, zscore_inicial),
                            fecha_busqueda_gbai = COALESCE(:f_gbai, fecha_busqueda_gbai),
                            asignacion_interna = COALESCE(:asig, asignacion_interna),
                            estado_busqueda = COALESCE(:est_b, estado_busqueda),
                            fecha_primera_atencion = COALESCE(:f_1ra, fecha_primera_atencion),
                            peso_atencion_kg = COALESCE(:p_1ra, peso_atencion_kg),
                            talla_atencion_cm = COALESCE(:t_1ra, talla_atencion_cm),
                            pb_atencion_cm = COALESCE(:pb_1ra, pb_atencion_cm),
                            zscore_atencion = COALESCE(:z_1ra, zscore_atencion),
                            prueba_apetito = COALESCE(:p_apet, prueba_apetito),
                            tratamiento_inicial = COALESCE(:tratam, tratamiento_inicial),
                            sobres_ftlc_inicial = COALESCE(:ftlc, sobres_ftlc_inicial),
                            comorbilidad_inicial = COALESCE(:comorb, comorbilidad_inicial),
                            escenario_manejo = COALESCE(:esc, escenario_manejo),
                            estado_caso = COALESCE(:est, estado_caso),
                            observaciones = COALESCE(:obs, observaciones)
                        WHERE caso_id = :cid
                    """),
                    {
                        "coop": cooperante, "eapb": eapb_id, "ips": ips_prim_id,
                        "f_cap": f_cap, "p_ini": p_ini, "t_ini": t_ini, "pb_ini": pb_ini, "z_ini": z_ini,
                        "f_gbai": f_gbai, "asig": asig_int, "est_b": est_busq,
                        "f_1ra": f_1ra, "p_1ra": p_1ra, "t_1ra": t_1ra, "pb_1ra": pb_1ra, "z_1ra": z_1ra,
                        "p_apet": p_apet, "tratam": tratam, "ftlc": ftlc, "comorb": comorb,
                        "esc": conducta, "est": estado_str, "obs": obs, "cid": caso_id
                    }
                )
                casos_actualizados += 1
            else:
                caso_id = db.execute(
                    text("""
                        INSERT INTO notificaciones_caso (
                            paciente_id, fuente_notificacion, fecha_notificacion, cooperante_notificador,
                            medio_notificacion, eapb_id, tipo_afiliacion, ips_primaria_id,
                            fecha_captacion, peso_inicial_kg, talla_inicial_cm, pb_inicial_cm, zscore_inicial,
                            fecha_busqueda_gbai, asignacion_interna, estado_busqueda,
                            fecha_primera_atencion, peso_atencion_kg, talla_atencion_cm, pb_atencion_cm,
                            zscore_atencion, prueba_apetito, tratamiento_inicial, sobres_ftlc_inicial,
                            comorbilidad_inicial, escenario_manejo, estado_caso, observaciones
                        )
                        VALUES (
                            :pid, :f_not, :fec_not, :coop, :med, :eapb, :taf, :ips,
                            :f_cap, :p_ini, :t_ini, :pb_ini, :z_ini,
                            :f_gbai, :asig, :est_b,
                            :f_1ra, :p_1ra, :t_1ra, :pb_1ra, :z_1ra,
                            :p_apet, :tratam, :ftlc, :comorb, :esc, :est, :obs
                        )
                        RETURNING caso_id
                    """),
                    {
                        "pid": paciente_id, "f_not": fuente_notif, "fec_not": f_notif, "coop": cooperante,
                        "med": medio_notif, "eapb": eapb_id, "taf": tipo_afil, "ips": ips_prim_id,
                        "f_cap": f_cap, "p_ini": p_ini, "t_ini": t_ini, "pb_ini": pb_ini, "z_ini": z_ini,
                        "f_gbai": f_gbai, "asig": asig_int, "est_b": est_busq,
                        "f_1ra": f_1ra, "p_1ra": p_1ra, "t_1ra": t_1ra, "pb_1ra": pb_1ra, "z_1ra": z_1ra,
                        "p_apet": p_apet, "tratam": tratam, "ftlc": ftlc, "comorb": comorb,
                        "esc": conducta, "est": estado_str, "obs": obs
                    }
                ).scalar()
                casos_creados += 1

            doc_to_caso_id[doc] = caso_id

    # --------------------------------------------------------------------------
    # ESTRATEGIA B: Despivotado de los 50 Bloques de Seguimiento
    # --------------------------------------------------------------------------
    def despivotar_hoja_seguimientos(nombre_hoja_key: str, fila_inicio: int, es_cerrado: bool = False):
        nonlocal controles_nuevos, controles_actualizados, advertencias
        if nombre_hoja_key not in map_hojas_norm:
            return
        
        hoja_real = map_hojas_norm[nombre_hoja_key]
        hojas_procesadas.append(hoja_real)
        rows_seg = list(wb[hoja_real].iter_rows(values_only=True))

        for row_num, row in enumerate(rows_seg[fila_inicio:], start=fila_inicio + 1):
            if not row or len(row) < 8:
                continue
            doc = clean_str(row[7])
            if not doc:
                continue

            caso_id = doc_to_caso_id.get(doc)
            if not caso_id:
                # Buscar caso en base de datos
                c_row = db.execute(
                    text("""
                        SELECT c.caso_id FROM notificaciones_caso c
                        JOIN pacientes p ON c.paciente_id = p.paciente_id
                        WHERE p.numero_documento = :doc
                        ORDER BY c.caso_id DESC LIMIT 1
                    """),
                    {"doc": doc}
                ).first()
                if c_row:
                    caso_id = c_row[0]
                    doc_to_caso_id[doc] = caso_id
                else:
                    # Crear paciente y caso preliminar si venía en seguimiento pero no en notificados
                    p_nom = clean_str(row[8]) if len(row) > 8 else "PACIENTE"
                    p_ape = clean_str(row[10]) if len(row) > 10 else "EPS"
                    p_id = db.execute(
                        text("INSERT INTO pacientes (tipo_documento, numero_documento, primer_nombre, primer_apellido) VALUES ('RC', :doc, :pn, :pa) RETURNING paciente_id"),
                        {"doc": doc, "pn": p_nom, "pa": p_ape}
                    ).scalar()
                    caso_id = db.execute(
                        text("INSERT INTO notificaciones_caso (paciente_id, estado_caso) VALUES (:pid, 'En seguimiento') RETURNING caso_id"),
                        {"pid": p_id}
                    ).scalar()
                    doc_to_caso_id[doc] = caso_id

            if es_cerrado:
                db.execute(
                    text("UPDATE notificaciones_caso SET estado_caso = 'Cerrado', motivo_egreso = COALESCE(motivo_egreso, 'Cerrado en reporte EPS') WHERE caso_id = :cid"),
                    {"cid": caso_id}
                )

            # Recorrer 50 bloques horizontales
            for k in range(1, 51):
                base_idx = 39 + (k - 1) * 10
                if base_idx >= len(row):
                    break
                raw_fecha = row[base_idx]
                f_ctrl = parse_date(raw_fecha)
                if not f_ctrl:
                    continue

                peso_k = parse_numeric(row[base_idx + 1]) if base_idx + 1 < len(row) else None
                talla_k = parse_numeric(row[base_idx + 2]) if base_idx + 2 < len(row) else None
                pb_k = parse_numeric(row[base_idx + 3]) if base_idx + 3 < len(row) else None
                z_k = parse_numeric(row[base_idx + 4]) if base_idx + 4 < len(row) else None
                trat_k = clean_str(row[base_idx + 6]) if base_idx + 6 < len(row) else None
                sobres_k = parse_int(row[base_idx + 7]) if base_idx + 7 < len(row) else None
                comorb_k = clean_str(row[base_idx + 8]) if base_idx + 8 < len(row) else None
                nov_str = clean_str(row[base_idx + 9]) if base_idx + 9 < len(row) else None
                nov_id = get_or_create_novedad(nov_str)

                # Verificar si el control k ya existe para este caso
                ctrl_exist = db.execute(
                    text("SELECT control_id FROM controles_seguimiento WHERE caso_id = :cid AND numero_seguimiento = :num"),
                    {"cid": caso_id, "num": k}
                ).first()

                if ctrl_exist:
                    db.execute(
                        text("""
                            UPDATE controles_seguimiento
                            SET fecha_control = :fec,
                                peso_kg = COALESCE(:p, peso_kg),
                                talla_cm = COALESCE(:t, talla_cm),
                                perimetro_braquial_cm = COALESCE(:pb, perimetro_braquial_cm),
                                z_score = COALESCE(:z, z_score),
                                tratamiento = COALESCE(:tr, tratamiento),
                                sobres_ftlc_entregados = COALESCE(:ftlc, sobres_ftlc_entregados),
                                comorbilidad = COALESCE(:com, comorbilidad),
                                novedad_id = COALESCE(:nid, novedad_id)
                            WHERE caso_id = :cid AND numero_seguimiento = :num
                        """),
                        {
                            "fec": f_ctrl, "p": peso_k, "t": talla_k, "pb": pb_k, "z": z_k,
                            "tr": trat_k, "ftlc": sobres_k, "com": comorb_k, "nid": nov_id,
                            "cid": caso_id, "num": k
                        }
                    )
                    controles_actualizados += 1
                else:
                    db.execute(
                        text("""
                            INSERT INTO controles_seguimiento (
                                caso_id, numero_seguimiento, fecha_control, peso_kg, talla_cm,
                                perimetro_braquial_cm, z_score, tratamiento, sobres_ftlc_entregados,
                                comorbilidad, novedad_id
                            )
                            VALUES (:cid, :num, :fec, :p, :t, :pb, :z, :tr, :ftlc, :com, :nid)
                        """),
                        {
                            "cid": caso_id, "num": k, "fec": f_ctrl, "p": peso_k, "t": talla_k,
                            "pb": pb_k, "z": z_k, "tr": trat_k, "ftlc": sobres_k, "com": comorb_k, "nid": nov_id
                        }
                    )
                    controles_nuevos += 1

    # Despivotar 'Casos en Seguimiento'
    despivotar_hoja_seguimientos("casos en seguimiento", fila_inicio=8, es_cerrado=False)
    # Despivotar 'Seguimientos Cerrados'
    despivotar_hoja_seguimientos("seguimientos cerrados", fila_inicio=3, es_cerrado=True)

    # Confirmar transacción
    db.commit()
    t_fin = time.time()
    duracion = round(t_fin - t_inicio, 2)

    return {
        "status": "success",
        "archivo": filename,
        "tamano_kb": round(len(file_bytes) / 1024, 1),
        "hojas_procesadas": list(set(hojas_procesadas)),
        "pacientes_creados": pacientes_creados,
        "pacientes_actualizados": pacientes_actualizados,
        "casos_creados": casos_creados,
        "casos_actualizados": casos_actualizados,
        "controles_nuevos": controles_nuevos,
        "controles_actualizados": controles_actualizados,
        "total_movimientos": (pacientes_creados + pacientes_actualizados + controles_nuevos + controles_actualizados),
        "tiempo_segundos": duracion,
        "advertencias": advertencias
    }
