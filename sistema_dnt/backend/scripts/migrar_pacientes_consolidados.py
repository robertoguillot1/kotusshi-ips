import json
import re
from datetime import datetime, date
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion"
engine = create_engine(db_url)

print("Cargando datos de auditoría quirúrgica...")
with open(r"sistema_dnt\backend\scripts\auditoria_quirurgica_final.json", encoding="utf-8") as f:
    auditoria = json.load(f)

nuevos = auditoria["pacientes_nuevos"]
enriquecidos = auditoria["pacientes_enriquecidos"]

print(f"Total a enriquecer: {len(enriquecidos)}")
print(f"Total nuevos a insertar: {len(nuevos)}")

def parsear_fecha(val):
    if not val or pd.isna(val):
        return None
    s = str(val).strip()[:10]
    # Formato YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        try: return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception: pass
    # Formato DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', s):
        try: return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception: pass
    # Formato DD-MM-YYYY
    if re.match(r'^\d{2}-\d{2}-\d{4}$', s):
        try: return datetime.strptime(s, "%d-%m-%Y").date()
        except Exception: pass
    return None

import pandas as pd

def descomponer_nombre(nombre_completo):
    nom = re.sub(r'\s+', ' ', str(nombre_completo).strip())
    parts = nom.split()
    if len(parts) == 1:
        return parts[0], None, "SIN DATO", None
    elif len(parts) == 2:
        return parts[0], None, parts[1], None
    elif len(parts) == 3:
        return parts[0], parts[1], parts[2], None
    elif len(parts) >= 4:
        return parts[0], parts[1], parts[2], " ".join(parts[3:])
    return "SIN NOMBRE", None, "SIN APELLIDO", None

with engine.begin() as conn:
    # 1. Obtener catálogos existentes
    mun_rows = conn.execute(text("SELECT municipio_id, UPPER(nombre) FROM cat_municipios")).fetchall()
    map_muns = {r[1].strip(): r[0] for r in mun_rows}

    eapb_rows = conn.execute(text("SELECT eapb_id, UPPER(nombre) FROM cat_eapb")).fetchall()
    map_eapbs = {r[1].strip(): r[0] for r in eapb_rows}

    def get_or_create_mun(mun_name):
        if not mun_name: return None
        m_clean = mun_name.strip().upper()
        if m_clean in map_muns: return map_muns[m_clean]
        # Si contiene partes de los municipios guajiros
        for k, v in map_muns.items():
            if k in m_clean or m_clean in k:
                return v
        # Crear nuevo
        res = conn.execute(text("INSERT INTO cat_municipios (nombre) VALUES (:nom) RETURNING municipio_id"), {"nom": m_clean.title()}).scalar()
        map_muns[m_clean] = res
        return res

    def get_or_create_eapb(eapb_name):
        if not eapb_name: return None
        e_clean = eapb_name.strip().upper()
        if e_clean in map_eapbs: return map_eapbs[e_clean]
        for k, v in map_eapbs.items():
            if k in e_clean or e_clean in k:
                return v
        res = conn.execute(text("INSERT INTO cat_eapb (nombre) VALUES (:nom) RETURNING eapb_id"), {"nom": e_clean.title()}).scalar()
        map_eapbs[e_clean] = res
        return res

    # 2. ENRIQUECER PACIENTES EXISTENTES
    print("Enriqueciendo pacientes existentes...")
    actualizados_cnt = 0
    for dni, p_data in enriquecidos.items():
        mejoras = p_data.get("mejoras", {})
        if not mejoras: continue
        
        # Buscar paciente
        p_row = conn.execute(
            text("SELECT paciente_id, cuidador_id FROM pacientes WHERE numero_documento = :doc OR numero_documento ILIKE :doc_like"),
            {"doc": dni, "doc_like": f"%{dni}%"}
        ).mappings().first()
        
        if not p_row: continue
        pid = p_row["paciente_id"]
        cid = p_row["cuidador_id"]
        
        # Actualizar cuidador
        if "telefono_cuidador" in mejoras or "cuidador" in mejoras:
            tel = mejoras.get("telefono_cuidador")
            nom_cuid = mejoras.get("cuidador") or "Acudiente / Cuidador"
            if cid:
                conn.execute(
                    text("UPDATE cuidadores SET telefono = COALESCE(telefono, :tel), nombre_completo = COALESCE(nombre_completo, :nom) WHERE cuidador_id = :cid"),
                    {"tel": tel, "nom": nom_cuid, "cid": cid}
                )
            else:
                cid = conn.execute(
                    text("INSERT INTO cuidadores (nombre_completo, telefono) VALUES (:nom, :tel) RETURNING cuidador_id"),
                    {"nom": nom_cuid, "tel": tel}
                ).scalar()
                conn.execute(text("UPDATE pacientes SET cuidador_id = :cid WHERE paciente_id = :pid"), {"cid": cid, "pid": pid})
                
        # Actualizar georreferenciación
        if "georreferenciacion" in mejoras and mejoras["georreferenciacion"]:
            conn.execute(
                text("UPDATE pacientes SET georreferenciacion = COALESCE(georreferenciacion, :geo) WHERE paciente_id = :pid"),
                {"geo": mejoras["georreferenciacion"], "pid": pid}
            )
            
        actualizados_cnt += 1

    print(f"Total pacientes existentes actualizados con datos enriquecidos: {actualizados_cnt}")

    # 3. INSERTAR PACIENTES NUEVOS
    print("Insertando pacientes nuevos...")
    insertados_cnt = 0
    batch_pacientes = []
    
    # Obtener max IDs para inserción eficiente o autoincremento
    for dni, p in nuevos.items():
        # Verificar si ya existe por si acaso
        existe = conn.execute(text("SELECT 1 FROM pacientes WHERE numero_documento = :doc"), {"doc": dni}).scalar()
        if existe: continue
        
        mun_id = get_or_create_mun(p.get("municipio"))
        eapb_id = get_or_create_eapb(p.get("eapb"))
        
        # Cuidador
        cid = None
        if p.get("cuidador") or p.get("telefono"):
            cid = conn.execute(
                text("INSERT INTO cuidadores (nombre_completo, telefono) VALUES (:nom, :tel) RETURNING cuidador_id"),
                {"nom": p.get("cuidador") or "Cuidador Wayuu", "tel": p.get("telefono")}
            ).scalar()
            
        p1_nom, p2_nom, p1_ape, p2_ape = descomponer_nombre(p.get("nombre_completo"))
        f_nac = parsear_fecha(p.get("fecha_nacimiento")) or date(2023, 1, 1)
        
        pid = conn.execute(
            text("""
                INSERT INTO pacientes (
                    tipo_documento, numero_documento, primer_nombre, segundo_nombre, 
                    primer_apellido, segundo_apellido, sexo, fecha_nacimiento, 
                    cuidador_id, municipio_id, georreferenciacion
                ) VALUES (
                    :tdoc, :ndoc, :p1, :p2, :a1, :a2, :sexo, :fnac, :cid, :mid, :geo
                ) RETURNING paciente_id
            """),
            {
                "tdoc": p.get("tipo_documento") or "RC",
                "ndoc": dni,
                "p1": p1_nom,
                "p2": p2_nom,
                "a1": p1_ape,
                "a2": p2_ape,
                "sexo": p.get("sexo") or "M",
                "fnac": f_nac,
                "cid": cid,
                "mid": mun_id,
                "geo": p.get("georreferenciacion")
            }
        ).scalar()
        
        # Crear caso en notificaciones_caso
        primera_fuente = p.get("fuentes", ["Consolidado Histórico"])[0]
        obs = f"Caso consolidado desde libro externo: {primera_fuente}"
        
        conn.execute(
            text("""
                INSERT INTO notificaciones_caso (
                    paciente_id, fuente_notificacion, fecha_notificacion,
                    eapb_id, estado_caso, observaciones
                ) VALUES (
                    :pid, :fuente, :fnot, :eid, 'En seguimiento', :obs
                )
            """),
            {
                "pid": pid,
                "fuente": primera_fuente[:140],
                "fnot": f_nac,
                "eid": eapb_id,
                "obs": obs
            }
        )
        
        insertados_cnt += 1
        if insertados_cnt % 1000 == 0:
            print(f"Insertados {insertados_cnt}/{len(nuevos)} pacientes nuevos...")

    print(f"\n¡ÉXITO TOTAL! Total pacientes nuevos insertados: {insertados_cnt}")

print("Transacción cerrada y confirmada en la base de datos PostgreSQL.")
