import os
import re
import json
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Conectar a PostgreSQL
db_url = "postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion"
engine = create_engine(db_url)

print("1. Cargando pacientes actuales de la base de datos PostgreSQL...")
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT 
            p.paciente_id,
            p.tipo_documento,
            p.numero_documento,
            TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) as nombre_completo,
            p.primer_nombre,
            p.segundo_nombre,
            p.primer_apellido,
            p.segundo_apellido,
            p.sexo,
            p.fecha_nacimiento,
            p.georreferenciacion,
            m.nombre as municipio,
            c.nombre_completo as cuidador,
            c.telefono as telefono_cuidador,
            c.documento_cuidador,
            nc.caso_id,
            nc.estado_caso,
            e.nombre as eapb
        FROM pacientes p
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cuidadores c ON p.cuidador_id = c.cuidador_id
        LEFT JOIN notificaciones_caso nc ON p.paciente_id = nc.paciente_id
        LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id;
    """)).mappings().all()

pacientes_db = {}
for r in rows:
    doc = str(r["numero_documento"]).strip()
    doc_clean = re.sub(r'[^0-9]', '', doc)
    if doc_clean:
        # normalizar ceros iniciales
        pacientes_db[str(int(doc_clean))] = dict(r)

print(f"Total pacientes indexados en PostgreSQL: {len(pacientes_db)}")

base_dir = Path(r"c:\Users\Roberto\Downloads\sandra")

def limpiar_dni(val):
    if pd.isna(val) or val is None:
        return ""
    if isinstance(val, float):
        if val.is_integer(): val = int(val)
        else: return ""
    s = str(val).strip()
    s_clean = re.sub(r'[^0-9]', '', s)
    if len(s_clean) >= 6 and len(s_clean) <= 11:
        return str(int(s_clean))
    return ""

def limpiar_texto(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.upper() in ["NAN", "NONE", "SIN DATO", "DESCONOCIDO", "0", "SD", "NO APLICA"]:
        return ""
    return re.sub(r'\s+', ' ', s)

def limpiar_telefono(val):
    if pd.isna(val) or val is None:
        return ""
    s = re.sub(r'[^0-9]', '', str(val))
    if len(s) == 10 and s.startswith('3'):
        return s
    if len(s) == 7:
        return s
    return ""

def normalizar_col(c):
    return str(c).strip().lower().replace(" ", "_").replace(".", "").replace("\n", "_").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

# Listar todos los archivos
archivos = list(base_dir.rglob("*.xlsx")) + list(base_dir.rglob("*.xls")) + list(base_dir.rglob("*.csv"))

pacientes_nuevos = {} # dni_clean -> {datos}
pacientes_enriquecidos = {} # dni_clean -> {mejoras: {}, fuentes: set()}
auditoria_por_archivo = []

# Mapeos exactos de columnas
posibles_cols_dni = [
    "no_identificacion", "nroidentificacion", "num_ide_", "num_ide", "numero_id", 
    "numero_documento", "documento_identidad", "identificacion", "documento", "no_id"
]

print(f"2. Procesando los {len(archivos)} archivos con extracción quirúrgica...")

for idx, fpath in enumerate(archivos, 1):
    rel_path = str(fpath.relative_to(base_dir))
    ext = fpath.suffix.lower()
    tamano_kb = round(fpath.stat().st_size / 1024, 1)
    
    registro_auditoria = {
        "id": idx,
        "nombre": fpath.name,
        "ruta": rel_path,
        "tamano_kb": tamano_kb,
        "total_filas_leidas": 0,
        "dnis_validos_encontrados": 0,
        "coinciden_bd": 0,
        "nuevos_detectados": 0,
        "campos_completados": 0,
        "clasificacion": "PENDIENTE",
        "motivo": ""
    }
    
    try:
        # Obtener hojas
        if ext == ".csv":
            hojas = [("CSV_DATA", 0)]
        else:
            xl = pd.ExcelFile(fpath)
            hojas = [(s, 0) for s in xl.sheet_names]
            
        for sname, _ in hojas:
            try:
                # Leer primero un extracto para encontrar la fila de encabezados
                if ext == ".csv":
                    try:
                        df_preview = pd.read_csv(fpath, sep=None, engine='python', nrows=15, encoding='utf-8')
                    except Exception:
                        df_preview = pd.read_csv(fpath, sep=None, engine='python', nrows=15, encoding='latin1')
                else:
                    df_preview = pd.read_excel(fpath, sheet_name=sname, nrows=15, header=None)
                
                if df_preview.empty:
                    continue
                
                header_row = 0
                found_dni_col = None
                
                if ext == ".csv":
                    # Las columnas ya están
                    cols_norm = {col: normalizar_col(col) for col in df_preview.columns}
                    for orig, n in cols_norm.items():
                        if any(k == n or k in n for k in posibles_cols_dni) and not any(bad in n for bad in ["madre", "padre", "cuidador", "autoridad", "entidad", "ips"]):
                            found_dni_col = orig
                            break
                    df = df_preview if len(df_preview) > 5 else pd.read_csv(fpath, sep=None, engine='python', encoding='utf-8', errors='ignore')
                else:
                    # Buscar qué fila tiene los encabezados
                    for r_idx in range(min(12, len(df_preview))):
                        row_vals = [str(v) for v in df_preview.iloc[r_idx] if pd.notna(v)]
                        norm_vals = {v: normalizar_col(v) for v in row_vals}
                        
                        cand = next((orig for orig, n in norm_vals.items() if any(k == n or k in n for k in posibles_cols_dni) and not any(bad in n for bad in ["madre", "padre", "cuidador", "autoridad", "entidad", "ips"])), None)
                        if cand:
                            header_row = r_idx
                            found_dni_col = cand
                            break
                    
                    if not found_dni_col:
                        continue
                    
                    df = pd.read_excel(fpath, sheet_name=sname, header=header_row)
                
                if df.empty or not found_dni_col:
                    continue
                
                # Normalizar columnas del dataframe
                col_norm_map = {c: normalizar_col(c) for c in df.columns}
                df.rename(columns=col_norm_map, inplace=True)
                target_dni_col = normalizar_col(found_dni_col)
                
                if target_dni_col not in df.columns:
                    continue
                
                # Columnas de nombres
                col_nombre_comp = next((c for c in df.columns if any(k in c for k in ["nombres_y_apellidos_del_paciente", "nombres_y_apellidos", "nombre_completo", "nombre_paciente"])), None)
                col_pri_nom = next((c for c in df.columns if any(k in c for k in ["pri_nom", "primer_nombre"]) and not any(b in c for b in ["madre", "cuidador"])), None)
                col_seg_nom = next((c for c in df.columns if any(k in c for k in ["seg_nom", "segundo_nombre"]) and not any(b in c for b in ["madre", "cuidador"])), None)
                col_pri_ape = next((c for c in df.columns if any(k in c for k in ["pri_ape", "primer_apellido"]) and not any(b in c for b in ["madre", "cuidador"])), None)
                col_seg_ape = next((c for c in df.columns if any(k in c for k in ["seg_ape", "segundo_apellido"]) and not any(b in c for b in ["madre", "cuidador"])), None)
                
                # Columnas auxiliares
                col_tel = next((c for c in df.columns if any(k in c for k in ["telefono", "celular", "contacto"]) and "ips" not in c), None)
                col_cuid = next((c for c in df.columns if any(k in c for k in ["nomb_cuidador", "cuidador", "acudiente", "madre", "nombre_cuidador"])), None)
                col_mun = next((c for c in df.columns if any(k in c for k in ["municipio", "nmun_"])), None)
                col_eapb = next((c for c in df.columns if any(k in c for k in ["nomasegurador", "eapb", "eps"])), None)
                col_fec_nto = next((c for c in df.columns if any(k in c for k in ["fec_nto", "fecha_nacimiento", "fechanacimiento"])), None)
                col_sexo = next((c for c in df.columns if any(k in c for k in ["sexo_", "sexo", "genero"])), None)
                col_geo = next((c for c in df.columns if any(k in c for k in ["georreferenciacion", "direccion", "comunidad", "direccionresidencia"])), None)
                col_dx = next((c for c in df.columns if any(k in c for k in ["dx_nutricional", "clasificacion", "diagnostico", "estado_nutricional"])), None)
                
                registro_auditoria["total_filas_leidas"] += len(df)
                
                for _, r in df.iterrows():
                    raw_dni = r.get(target_dni_col)
                    clean_dni = limpiar_dni(raw_dni)
                    if not clean_dni:
                        continue
                    
                    registro_auditoria["dnis_validos_encontrados"] += 1
                    
                    # Construir nombre completo
                    if col_nombre_comp and pd.notna(r.get(col_nombre_comp)):
                        nombre_paciente = limpiar_texto(r.get(col_nombre_comp))
                    else:
                        parts = [
                            limpiar_texto(r.get(col_pri_nom)) if col_pri_nom else "",
                            limpiar_texto(r.get(col_seg_nom)) if col_seg_nom else "",
                            limpiar_texto(r.get(col_pri_ape)) if col_pri_ape else "",
                            limpiar_texto(r.get(col_seg_ape)) if col_seg_ape else ""
                        ]
                        nombre_paciente = " ".join([p for p in parts if p]).strip()
                    
                    tel = limpiar_telefono(r.get(col_tel)) if col_tel else ""
                    cuid = limpiar_texto(r.get(col_cuid)) if col_cuid else ""
                    mun = limpiar_texto(r.get(col_mun)) if col_mun else ""
                    eapb = limpiar_texto(r.get(col_eapb)) if col_eapb else ""
                    geo = limpiar_texto(r.get(col_geo)) if col_geo else ""
                    fec_nto = r.get(col_fec_nto) if col_fec_nto and pd.notna(r.get(col_fec_nto)) else None
                    sexo = str(r.get(col_sexo)).strip().upper()[:1] if col_sexo and pd.notna(r.get(col_sexo)) else ""
                    if sexo not in ["M", "F"]: sexo = ""
                    dx = limpiar_texto(r.get(col_dx)) if col_dx else ""
                    
                    # 1. ¿Existe en PostgreSQL?
                    if clean_dni in pacientes_db:
                        registro_auditoria["coinciden_bd"] += 1
                        actual = pacientes_db[clean_dni]
                        mejoras = {}
                        
                        if tel and not actual.get("telefono_cuidador"):
                            mejoras["telefono_cuidador"] = tel
                        if cuid and not actual.get("cuidador"):
                            mejoras["cuidador"] = cuid
                        if geo and not actual.get("georreferenciacion"):
                            mejoras["georreferenciacion"] = geo
                        if mun and not actual.get("municipio"):
                            mejoras["municipio"] = mun
                        if eapb and not actual.get("eapb"):
                            mejoras["eapb"] = eapb
                        if sexo and not actual.get("sexo"):
                            mejoras["sexo"] = sexo
                            
                        if mejoras:
                            registro_auditoria["campos_completados"] += len(mejoras)
                            if clean_dni not in pacientes_enriquecidos:
                                pacientes_enriquecidos[clean_dni] = {
                                    "documento": clean_dni,
                                    "nombre": actual.get("nombre_completo"),
                                    "mejoras": {},
                                    "fuentes": set()
                                }
                            pacientes_enriquecidos[clean_dni]["mejoras"].update(mejoras)
                            pacientes_enriquecidos[clean_dni]["fuentes"].add(fpath.name)
                    else:
                        # 2. Paciente NUEVO
                        if len(nombre_paciente) >= 4:
                            registro_auditoria["nuevos_detectados"] += 1
                            if clean_dni not in pacientes_nuevos:
                                pacientes_nuevos[clean_dni] = {
                                    "documento": clean_dni,
                                    "tipo_documento": "RC" if len(clean_dni) >= 10 else "TI",
                                    "nombre_completo": nombre_paciente,
                                    "primer_nombre": nombre_paciente.split()[0] if nombre_paciente else "",
                                    "primer_apellido": nombre_paciente.split()[-1] if len(nombre_paciente.split()) > 1 else "",
                                    "sexo": sexo or "M",
                                    "fecha_nacimiento": str(fec_nto)[:10] if fec_nto else None,
                                    "telefono": tel,
                                    "cuidador": cuid,
                                    "municipio": mun,
                                    "eapb": eapb,
                                    "georreferenciacion": geo,
                                    "dx_inicial": dx,
                                    "fuentes": set()
                                }
                            else:
                                curr = pacientes_nuevos[clean_dni]
                                if not curr["telefono"] and tel: curr["telefono"] = tel
                                if not curr["cuidador"] and cuid: curr["cuidador"] = cuid
                                if not curr["municipio"] and mun: curr["municipio"] = mun
                                if not curr["eapb"] and eapb: curr["eapb"] = eapb
                                if not curr["georreferenciacion"] and geo: curr["georreferenciacion"] = geo
                                if not curr["fecha_nacimiento"] and fec_nto: curr["fecha_nacimiento"] = str(fec_nto)[:10]
                                if not curr["dx_inicial"] and dx: curr["dx_inicial"] = dx
                            
                            pacientes_nuevos[clean_dni]["fuentes"].add(fpath.name)
            except Exception as e_sh:
                registro_auditoria["motivo"] += f" [{sname}: {str(e_sh)[:60]}]"
    except Exception as e_f:
        registro_auditoria["motivo"] = str(e_f)[:80]
        
    # Clasificación
    if registro_auditoria["dnis_validos_encontrados"] == 0:
        registro_auditoria["clasificacion"] = "SIN_DATOS_O_INUTILIZABLE"
        registro_auditoria["motivo"] = "No se encontraron números de identificación válidos en sus hojas."
    elif registro_auditoria["nuevos_detectados"] > 0:
        registro_auditoria["clasificacion"] = "APORTA_USUARIOS_NUEVOS"
        registro_auditoria["motivo"] = f"Aporta {registro_auditoria['nuevos_detectados']} pacientes no registrados en la BD."
    elif registro_auditoria["campos_completados"] > 0:
        registro_auditoria["clasificacion"] = "ENRIQUECE_DATOS_FALTANTES"
        registro_auditoria["motivo"] = f"Complementa {registro_auditoria['campos_completados']} campos en pacientes existentes."
    else:
        registro_auditoria["clasificacion"] = "REDUNDANTE_CONSOLIDADO"
        registro_auditoria["motivo"] = f"Sus {registro_auditoria['dnis_validos_encontrados']} pacientes ya están en la BD y no aportan datos nuevos."
        
    auditoria_por_archivo.append(registro_auditoria)
    if idx % 20 == 0 or idx == len(archivos):
        print(f"Procesados {idx}/{len(archivos)} archivos...")

# Convertir sets a listas
for k, v in pacientes_nuevos.items():
    v["fuentes"] = list(v["fuentes"])

for k, v in pacientes_enriquecidos.items():
    v["fuentes"] = list(v["fuentes"])

res_final = {
    "total_archivos": len(auditoria_por_archivo),
    "total_pacientes_db_inicial": len(pacientes_db),
    "total_pacientes_nuevos_legitimos": len(pacientes_nuevos),
    "total_pacientes_existentes_enriquecidos": len(pacientes_enriquecidos),
    "resumen_clasificacion": {
        "APORTA_USUARIOS_NUEVOS": sum(1 for a in auditoria_por_archivo if a["clasificacion"] == "APORTA_USUARIOS_NUEVOS"),
        "ENRIQUECE_DATOS_FALTANTES": sum(1 for a in auditoria_por_archivo if a["clasificacion"] == "ENRIQUECE_DATOS_FALTANTES"),
        "REDUNDANTE_CONSOLIDADO": sum(1 for a in auditoria_por_archivo if a["clasificacion"] == "REDUNDANTE_CONSOLIDADO"),
        "SIN_DATOS_O_INUTILIZABLE": sum(1 for a in auditoria_por_archivo if a["clasificacion"] == "SIN_DATOS_O_INUTILIZABLE")
    },
    "archivos": auditoria_por_archivo,
    "pacientes_nuevos": pacientes_nuevos,
    "pacientes_enriquecidos": pacientes_enriquecidos
}

with open(r"sistema_dnt\backend\scripts\auditoria_quirurgica_final.json", "w", encoding="utf-8") as fp:
    json.dump(res_final, fp, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print("¡RESULTADOS QUIRÚRGICOS CONSOLIDADOS!")
print(f"Pacientes en BD inicial: {len(pacientes_db)}")
print(f"PACIENTES NUEVOS LEGÍTIMOS IDENTIFICADOS: {len(pacientes_nuevos)}")
print(f"Pacientes Existentes con DATOS ENRIQUECIDOS: {len(pacientes_enriquecidos)}")
print(f"Archivos que aportan usuarios nuevos: {res_final['resumen_clasificacion']['APORTA_USUARIOS_NUEVOS']}")
print(f"Archivos que enriquecen datos faltantes: {res_final['resumen_clasificacion']['ENRIQUECE_DATOS_FALTANTES']}")
print(f"Archivos redundantes/ya consolidados: {res_final['resumen_clasificacion']['REDUNDANTE_CONSOLIDADO']}")
print(f"Archivos sin datos clínicos / plantillas / inutilizables: {res_final['resumen_clasificacion']['SIN_DATOS_O_INUTILIZABLE']}")
print("="*70)
