#!/usr/bin/env python3
"""
Script de Migración ETL de Alto Rendimiento: Excel a PostgreSQL
Sistema de Vigilancia y Seguimiento Nutricional
IPSI Kottushi Sao Ana>a
"""

import os
import re
import sys
import time
import logging
from datetime import datetime, date
import openpyxl
import psycopg
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_IPSI")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion")
EXCEL_PATH = os.getenv("EXCEL_FILE_PATH", "../3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx")

if not os.path.exists(EXCEL_PATH):
    alt_paths = [
        "3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx",
        os.path.join("..", "3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx"),
        os.path.join(os.path.dirname(__file__), "..", "3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx"),
        os.path.join(os.path.dirname(__file__), "..", "..", "3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx"),
    ]
    for p in alt_paths:
        if os.path.exists(p):
            EXCEL_PATH = os.path.abspath(p)
            break

logger.info(f"Ruta de archivo Excel seleccionada: {EXCEL_PATH}")

# ==============================================================================
# FUNCIONES DE LIMPIEZA Y PARSEO
# ==============================================================================

def clean_str(val):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ["sin dato", "sin datos", "n/a", "sd", "none", "nan", "null"]:
        return None
    return s

def parse_date(val):
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

def parse_numeric(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # Proteger contra inf o nan
        if val != val:  # NaN check
            return None
        return round(float(val), 2)
    s = str(val).strip().replace(",", ".")
    if s.lower() in ["sin dato", "sin datos", "n/a", "sd", "", "none", "nan", "#div/0!", "#value!", "#n/a", "#ref!"]:
        return None
    m = re.search(r'[-+]?\d*\.?\d+', s)
    if m:
        try:
            num = float(m.group(0))
            return round(num, 2)
        except ValueError:
            pass
    return None

def parse_int(val):
    num = parse_numeric(val)
    return int(round(num)) if num is not None else None

def parse_phone_and_notes(val):
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
# PIPELINE ETL DE ALTO RENDIMIENTO
# ==============================================================================

def ejecutar_migracion():
    t_inicio = time.time()
    logger.info("Iniciando migración ETL optimizada (lectura en memoria) a PostgreSQL...")
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # ------------------------------------------------------------------
            # 1. CATÁLOGOS MAESTROS DESDE 'Listas'
            # ------------------------------------------------------------------
            logger.info("Poblando tablas catálogo desde 'Listas'...")
            rows_listas = list(wb['Listas'].iter_rows(values_only=True))

            # Extraer columnas
            # Base 0: Col 4: Municipio, Col 10: EAPB, Col 24: Sede, Col 26: Novedad
            def extraer_col(col_idx):
                res = []
                for r in rows_listas[1:]:
                    if col_idx < len(r):
                        v = clean_str(r[col_idx])
                        if v and v not in res:
                            res.append(v)
                return res

            for m in extraer_col(4):
                cur.execute("INSERT INTO cat_municipios (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (m,))
            for e in extraer_col(10):
                cur.execute("INSERT INTO cat_eapb (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (e,))
            for s in extraer_col(24):
                cur.execute("INSERT INTO cat_sedes_ipsi (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (s,))
            for n in extraer_col(26):
                cur.execute("INSERT INTO cat_novedades (descripcion) VALUES (%s) ON CONFLICT (descripcion) DO NOTHING", (n,))

            # Cargar mapas en memoria
            cur.execute("SELECT nombre, municipio_id FROM cat_municipios")
            map_municipios = {row[0].strip().lower(): row[1] for row in cur.fetchall()}

            cur.execute("SELECT nombre, eapb_id FROM cat_eapb")
            map_eapb = {row[0].strip().lower(): row[1] for row in cur.fetchall()}

            cur.execute("SELECT nombre, sede_id FROM cat_sedes_ipsi")
            map_sedes = {row[0].strip().lower(): row[1] for row in cur.fetchall()}

            cur.execute("SELECT descripcion, novedad_id FROM cat_novedades")
            map_novedades = {row[0].strip().lower(): row[1] for row in cur.fetchall()}

            def get_or_create_municipio(nombre):
                if not nombre:
                    return None
                k = nombre.strip().lower()
                if k in map_municipios:
                    return map_municipios[k]
                cur.execute("INSERT INTO cat_municipios (nombre) VALUES (%s) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING municipio_id", (nombre.strip(),))
                nid = cur.fetchone()[0]
                map_municipios[k] = nid
                return nid

            def get_or_create_eapb(nombre):
                if not nombre:
                    return None
                k = nombre.strip().lower()
                if k in map_eapb:
                    return map_eapb[k]
                cur.execute("INSERT INTO cat_eapb (nombre) VALUES (%s) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING eapb_id", (nombre.strip(),))
                nid = cur.fetchone()[0]
                map_eapb[k] = nid
                return nid

            def get_or_create_sede(nombre):
                if not nombre:
                    return None
                k = nombre.strip().lower()
                if k in map_sedes:
                    return map_sedes[k]
                cur.execute("INSERT INTO cat_sedes_ipsi (nombre) VALUES (%s) ON CONFLICT (nombre) DO UPDATE SET nombre=EXCLUDED.nombre RETURNING sede_id", (nombre.strip(),))
                nid = cur.fetchone()[0]
                map_sedes[k] = nid
                return nid

            def get_or_create_novedad(desc):
                if not desc:
                    return None
                k = desc.strip().lower()
                if k in map_novedades:
                    return map_novedades[k]
                cur.execute("INSERT INTO cat_novedades (descripcion) VALUES (%s) ON CONFLICT (descripcion) DO UPDATE SET descripcion=EXCLUDED.descripcion RETURNING novedad_id", (desc.strip(),))
                nid = cur.fetchone()[0]
                map_novedades[k] = nid
                return nid

            # ------------------------------------------------------------------
            # 2. PROCESAMIENTO EN MEMORIA DE 'Notificados'
            # ------------------------------------------------------------------
            logger.info("Cargando y procesando hoja 'Notificados'...")
            rows_notif = list(wb['Notificados'].iter_rows(values_only=True))

            pacientes_creados = 0
            pacientes_actualizados = 0
            casos_creados = 0
            doc_to_caso_id = {}

            # Datos inician en la fila 9 (índice 8)
            for row in rows_notif[8:]:
                if not row or len(row) < 8:
                    continue
                raw_doc = row[7]  # Col 8 (índice 7): Numero Id
                doc = clean_str(raw_doc)
                if not doc:
                    continue

                tipo_doc = clean_str(row[6]) or "RC"
                primer_nombre = clean_str(row[8]) or "SIN NOMBRE"
                segundo_nombre = clean_str(row[9])
                primer_apellido = clean_str(row[10]) or "SIN APELLIDO"
                segundo_apellido = clean_str(row[11])
                sexo = clean_str(row[12])
                if sexo:
                    sexo = sexo.upper()
                    if sexo not in ['M', 'F']:
                        sexo = 'M' if 'M' in sexo else ('F' if 'F' in sexo else None)
                fecha_nac = parse_date(row[13]) or date(2024, 1, 1)

                municipio_id = get_or_create_municipio(clean_str(row[5]))
                georref = clean_str(row[19])

                # Cuidador
                nombre_cuidador = clean_str(row[20])
                doc_cuidador = clean_str(row[21])
                telefono, notas_tel = parse_phone_and_notes(row[22])

                cuidador_id = None
                if nombre_cuidador:
                    if doc_cuidador:
                        cur.execute(
                            """
                            INSERT INTO cuidadores (documento_cuidador, nombre_completo, telefono, notas_contacto)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (documento_cuidador) DO UPDATE 
                            SET nombre_completo = EXCLUDED.nombre_completo,
                                telefono = COALESCE(EXCLUDED.telefono, cuidadores.telefono)
                            RETURNING cuidador_id
                            """,
                            (doc_cuidador, nombre_cuidador, telefono, notas_tel)
                        )
                        cuidador_id = cur.fetchone()[0]
                    else:
                        cur.execute("SELECT cuidador_id FROM cuidadores WHERE documento_cuidador IS NULL AND nombre_completo = %s LIMIT 1", (nombre_cuidador,))
                        r_c = cur.fetchone()
                        if r_c:
                            cuidador_id = r_c[0]
                        else:
                            cur.execute(
                                "INSERT INTO cuidadores (nombre_completo, telefono, notas_contacto) VALUES (%s, %s, %s) RETURNING cuidador_id",
                                (nombre_cuidador, telefono, notas_tel)
                            )
                            cuidador_id = cur.fetchone()[0]

                # Paciente
                cur.execute("SELECT paciente_id FROM pacientes WHERE numero_documento = %s", (doc,))
                r_p = cur.fetchone()
                if r_p:
                    paciente_id = r_p[0]
                    pacientes_actualizados += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO pacientes (tipo_documento, numero_documento, primer_nombre, segundo_nombre,
                                               primer_apellido, segundo_apellido, sexo, fecha_nacimiento,
                                               cuidador_id, municipio_id, georreferenciacion)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING paciente_id
                        """,
                        (tipo_doc, doc, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
                         sexo, fecha_nac, cuidador_id, municipio_id, georref)
                    )
                    paciente_id = cur.fetchone()[0]
                    pacientes_creados += 1

                # Caso
                fuente_notif = clean_str(row[1])
                fecha_notif = parse_date(row[2])
                cooperante = clean_str(row[3])
                medio_notif = clean_str(row[4])
                eapb_id = get_or_create_eapb(clean_str(row[16]))
                tipo_afil = clean_str(row[17])
                ips_primaria_id = get_or_create_sede(clean_str(row[18]))

                # Captación
                fecha_captacion = parse_date(row[23])
                peso_ini = parse_numeric(row[24])
                talla_ini = parse_numeric(row[25])
                pb_ini = parse_numeric(row[26])
                zscore_ini = parse_numeric(row[27])

                # GBAI
                fecha_gbai = parse_date(row[29])
                asig_interna = clean_str(row[31])
                estado_busq = clean_str(row[32])

                # Primera Atención
                fecha_pri_atenc = parse_date(row[33])
                peso_atenc = parse_numeric(row[34])
                talla_atenc = parse_numeric(row[35])
                pb_atenc = parse_numeric(row[36])
                zscore_atenc = parse_numeric(row[37])
                prueba_apet = clean_str(row[39])
                tratam_ini = clean_str(row[40])
                sobres_ftlc_ini = parse_int(row[41])
                comorb_ini = clean_str(row[42])
                estado_actual_str = clean_str(row[43]) or "En seguimiento"
                conducta = clean_str(row[44])
                obs_notif = clean_str(row[45])

                cur.execute(
                    """
                    INSERT INTO notificaciones_caso (
                        paciente_id, fuente_notificacion, fecha_notificacion, cooperante_notificador,
                        medio_notificacion, eapb_id, tipo_afiliacion, ips_primaria_id,
                        fecha_captacion, peso_inicial_kg, talla_inicial_cm, pb_inicial_cm, zscore_inicial,
                        fecha_busqueda_gbai, asignacion_interna, estado_busqueda,
                        fecha_primera_atencion, peso_atencion_kg, talla_atencion_cm, pb_atencion_cm,
                        zscore_atencion, prueba_apetito, tratamiento_inicial, sobres_ftlc_inicial,
                        comorbilidad_inicial, escenario_manejo, estado_caso, observaciones
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING caso_id
                    """,
                    (paciente_id, fuente_notif, fecha_notif, cooperante, medio_notif, eapb_id, tipo_afil,
                     ips_primaria_id, fecha_captacion, peso_ini, talla_ini, pb_ini, zscore_ini,
                     fecha_gbai, asig_interna, estado_busq, fecha_pri_atenc, peso_atenc, talla_atenc,
                     pb_atenc, zscore_atenc, prueba_apet, tratam_ini, sobres_ftlc_ini, comorb_ini,
                     conducta, estado_actual_str, obs_notif)
                )
                caso_id = cur.fetchone()[0]
                casos_creados += 1
                doc_to_caso_id[doc] = caso_id

            logger.info(f"Notificados: {pacientes_creados} pacientes nuevos, {pacientes_actualizados} duplicados resueltos, {casos_creados} casos.")

            # ------------------------------------------------------------------
            # 3. DESPIVOTADO ULTRA RÁPIDO EN MEMORIA (50 BLOQUES)
            # ------------------------------------------------------------------
            total_controles_despivotados = 0

            def despivotar_hoja_memoria(nombre_hoja, fila_inicio_idx, es_cerrado=False):
                nonlocal total_controles_despivotados
                logger.info(f"Despivotando en memoria '{nombre_hoja}'...")
                rows = list(wb[nombre_hoja].iter_rows(values_only=True))
                lista_controles = []

                for row in rows[fila_inicio_idx:]:
                    if not row or len(row) < 8:
                        continue
                    doc = clean_str(row[7])  # Num Documento (índice 7)
                    if not doc:
                        continue

                    caso_id = doc_to_caso_id.get(doc)
                    if not caso_id:
                        cur.execute(
                            "SELECT c.caso_id FROM notificaciones_caso c JOIN pacientes p ON c.paciente_id = p.paciente_id WHERE p.numero_documento = %s ORDER BY c.caso_id DESC LIMIT 1",
                            (doc,)
                        )
                        r_c = cur.fetchone()
                        if r_c:
                            caso_id = r_c[0]
                            doc_to_caso_id[doc] = caso_id
                        else:
                            continue

                    if es_cerrado:
                        cur.execute("UPDATE notificaciones_caso SET estado_caso = 'Cerrado', motivo_egreso = 'Egresado/Cerrado' WHERE caso_id = %s", (caso_id,))

                    # Recorrer 50 bloques
                    # Bloque 1 empieza en col 40 (índice 39)
                    for k in range(1, 51):
                        base_idx = 39 + (k - 1) * 10
                        if base_idx >= len(row):
                            break
                        raw_fecha = row[base_idx]
                        fecha_ctrl = parse_date(raw_fecha)
                        if not fecha_ctrl:
                            continue

                        peso_k = parse_numeric(row[base_idx + 1]) if base_idx + 1 < len(row) else None
                        talla_k = parse_numeric(row[base_idx + 2]) if base_idx + 2 < len(row) else None
                        pb_k = parse_numeric(row[base_idx + 3]) if base_idx + 3 < len(row) else None
                        zscore_k = parse_numeric(row[base_idx + 4]) if base_idx + 4 < len(row) else None
                        tratam_k = clean_str(row[base_idx + 6]) if base_idx + 6 < len(row) else None
                        sobres_k = parse_int(row[base_idx + 7]) if base_idx + 7 < len(row) else None
                        comorb_k = clean_str(row[base_idx + 8]) if base_idx + 8 < len(row) else None
                        novedad_str = clean_str(row[base_idx + 9]) if base_idx + 9 < len(row) else None
                        novedad_id = get_or_create_novedad(novedad_str)

                        lista_controles.append((
                            caso_id, k, fecha_ctrl, peso_k, talla_k, pb_k, zscore_k, tratam_k, sobres_k, comorb_k, novedad_id
                        ))

                # Inserción por lotes
                if lista_controles:
                    cur.executemany(
                        """
                        INSERT INTO controles_seguimiento (
                            caso_id, numero_seguimiento, fecha_control, peso_kg, talla_cm,
                            perimetro_braquial_cm, z_score, tratamiento, sobres_ftlc_entregados,
                            comorbilidad, novedad_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (caso_id, numero_seguimiento) DO UPDATE
                        SET fecha_control = EXCLUDED.fecha_control,
                            peso_kg = COALESCE(EXCLUDED.peso_kg, controles_seguimiento.peso_kg),
                            talla_cm = COALESCE(EXCLUDED.talla_cm, controles_seguimiento.talla_cm),
                            perimetro_braquial_cm = COALESCE(EXCLUDED.perimetro_braquial_cm, controles_seguimiento.perimetro_braquial_cm),
                            z_score = COALESCE(EXCLUDED.z_score, controles_seguimiento.z_score),
                            tratamiento = COALESCE(EXCLUDED.tratamiento, controles_seguimiento.tratamiento),
                            sobres_ftlc_entregados = COALESCE(EXCLUDED.sobres_ftlc_entregados, controles_seguimiento.sobres_ftlc_entregados),
                            novedad_id = COALESCE(EXCLUDED.novedad_id, controles_seguimiento.novedad_id)
                        """,
                        lista_controles
                    )
                    total_controles_despivotados += len(lista_controles)
                    logger.info(f"Hoja '{nombre_hoja}': {len(lista_controles)} controles insertados en bloque.")

            # Casos en Seguimiento (inicia en fila 9 -> índice 8)
            despivotar_hoja_memoria('Casos en Seguimiento ', 8, es_cerrado=False)

            # Seguimientos Cerrados (inicia en fila 4 -> índice 3)
            despivotar_hoja_memoria('Seguimientos Cerrados ', 3, es_cerrado=True)

            conn.commit()

            # ------------------------------------------------------------------
            # 4. REPORTE FINAL DE AUDITORÍA
            # ------------------------------------------------------------------
            t_total = time.time() - t_inicio
            logger.info("=" * 60)
            logger.info(f"MIGRACIÓN ETL EXITOSA EN {t_total:.2f} SEGUNDOS")
            logger.info("=" * 60)
            cur.execute("SELECT COUNT(*) FROM pacientes")
            logger.info(f"Total Pacientes Únicos en BD: {cur.fetchone()[0]}")

            cur.execute("SELECT COUNT(*) FROM notificaciones_caso")
            logger.info(f"Total Casos de Notificación en BD: {cur.fetchone()[0]}")

            cur.execute("SELECT estado_caso, COUNT(*) FROM notificaciones_caso GROUP BY estado_caso")
            for est, cnt in cur.fetchall():
                logger.info(f"  - Estado Caso '{est}': {cnt}")

            cur.execute("SELECT COUNT(*) FROM controles_seguimiento")
            logger.info(f"Total Controles de Seguimiento Despivotados: {cur.fetchone()[0]}")

            cur.execute("SELECT COUNT(*) FROM vw_estado_actual_casos")
            logger.info(f"Total Casos Evaluados en Vista Clínica: {cur.fetchone()[0]}")
            logger.info("=" * 60)

    wb.close()

if __name__ == "__main__":
    ejecutar_migracion()
