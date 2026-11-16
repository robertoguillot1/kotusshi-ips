import json
import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Conectar a PostgreSQL
db_url = "postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion"
engine = create_engine(db_url)

print("Cargando pacientes actuales de la base de datos PostgreSQL...")
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
            nc.fuente_notificacion,
            nc.fecha_notificacion,
            nc.fecha_captacion,
            nc.fecha_primera_atencion,
            nc.peso_atencion_kg,
            nc.talla_atencion_cm,
            e.nombre as eapb
        FROM pacientes p
        LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
        LEFT JOIN cuidadores c ON p.cuidador_id = c.cuidador_id
        LEFT JOIN notificaciones_caso nc ON p.paciente_id = nc.paciente_id
        LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id;
    """)).mappings().all()

pacientes_db = {}
for r in rows:
    doc = str(r["numero_documento"]).strip().upper()
    # limpiar no alfanumericos
    doc_clean = re.sub(r'[^A-Z0-9]', '', doc)
    pacientes_db[doc_clean] = dict(r)

print(f"Total pacientes únicos en BD actual: {len(pacientes_db)}")

# Cargar inventario de archivos con pacientes
with open(r"sistema_dnt\backend\scripts\archivos_con_pacientes.json", encoding="utf-8") as f:
    archivos_info = json.load(f)

base_dir = Path(r"c:\Users\Roberto\Downloads\sandra")

def limpiar_doc(val):
    if pd.isna(val) or val is None:
        return ""
    # Si viene en notacion cientifica o float
    if isinstance(val, float):
        if val.is_integer():
            val = int(val)
        else:
            return ""
    s = str(val).strip().upper()
    # Si viene con prefijo tipo RC12345 o TI12345 separar
    s = re.sub(r'^(RC|TI|CC|MS|CN|PT|PA|NV|AS|PE)', '', s)
    s = re.sub(r'[^A-Z0-9]', '', s)
    # Quitar ceros a la izquierda innecesarios si son solo numeros
    if s.isdigit():
        s = str(int(s))
    return s

def normalizar_col(c):
    return str(c).strip().lower().replace(" ", "_").replace(".", "").replace("\n", "_").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

# Estructuras para recolectar el análisis
pacientes_nuevos_totales = {} # doc_clean -> {datos_consolidados, archivos_fuente: []}
enriquecimiento_existentes = {} # doc_clean -> {campos_a_actualizar: {campo: valor}, archivos_fuente: []}
auditoria_archivos = []

print(f"Iniciando análisis comparativo sobre {len(archivos_info)} archivos...")

for a_idx, a in enumerate(archivos_info, 1):
    fpath = base_dir / a["ruta"]
    archivo_resumen = {
        "id": a["id"],
        "nombre": a["nombre"],
        "ruta": a["ruta"],
        "tamano_kb": a["tamano_kb"],
        "total_registros_procesados": 0,
        "registros_validos_doc": 0,
        "coinciden_con_bd": 0,
        "nuevos_para_bd": 0,
        "campos_enriquecidos_aportados": 0,
        "clasificacion": "PENDIENTE",
        "motivo": ""
    }
    
    if not fpath.exists():
        archivo_resumen["clasificacion"] = "NO_EXISTE"
        auditoria_archivos.append(archivo_resumen)
        continue
    
    ext = fpath.suffix.lower()
    
    for h in a["hojas_validas"]:
        sheet_name = h["hoja"]
        fila_hdr = h.get("fila_header", 0)
        col_doc_orig = h["col_doc"]
        
        try:
            if ext == ".csv":
                try:
                    df = pd.read_csv(fpath, sep=None, engine='python', encoding='utf-8')
                except Exception:
                    df = pd.read_csv(fpath, sep=None, engine='python', encoding='latin1')
            else:
                df = pd.read_excel(fpath, sheet_name=sheet_name, header=fila_hdr)
            
            if df.empty or len(df.columns) < 2:
                continue
            
            # Normalizar nombres de columnas
            cols_map = {c: normalizar_col(c) for c in df.columns}
            df.rename(columns=cols_map, inplace=True)
            col_doc = normalizar_col(col_doc_orig)
            
            if col_doc not in df.columns:
                # buscar columna doc
                col_doc = next((c for c in df.columns if any(k in c for k in ["num_ide", "numero_id", "identificacion", "documento"])), None)
            
            if not col_doc:
                continue
            
            # Columnas auxiliares
            col_nom = next((c for c in df.columns if any(k in c for k in ["pri_nom", "primer_nombre", "nombre"])), None)
            col_ape = next((c for c in df.columns if any(k in c for k in ["pri_ape", "primer_apellido", "apellido"])), None)
            col_tel = next((c for c in df.columns if any(k in c for k in ["telefono", "tel", "celular", "contacto"])), None)
            col_cuid = next((c for c in df.columns if any(k in c for k in ["cuidador", "acudiente", "madre", "padre"])), None)
            col_mun = next((c for c in df.columns if any(k in c for k in ["municipio", "nmun_"])), None)
            col_eapb = next((c for c in df.columns if any(k in c for k in ["eapb", "eps"])), None)
            col_fec_nto = next((c for c in df.columns if any(k in c for k in ["fec_nto", "fecha_nacimiento", "nacimiento"])), None)
            col_geo = next((c for c in df.columns if any(k in c for k in ["georreferenciacion", "direccion", "comunidad", "ubicacion"])), None)
            
            archivo_resumen["total_registros_procesados"] += len(df)
            
            for _, row in df.iterrows():
                val_doc = row.get(col_doc)
                doc_clean = limpiar_doc(val_doc)
                if not doc_clean or len(doc_clean) < 4:
                    continue
                
                archivo_resumen["registros_validos_doc"] += 1
                
                # Extraer nombre
                nom_val = ""
                if col_nom and pd.notna(row.get(col_nom)):
                    nom_val = str(row.get(col_nom)).strip()
                if col_ape and pd.notna(row.get(col_ape)):
                    nom_val += " " + str(row.get(col_ape)).strip()
                nom_val = nom_val.strip()
                
                # Extraer campos enriquecedores
                tel_val = str(row.get(col_tel)).strip() if col_tel and pd.notna(row.get(col_tel)) else ""
                # limpiar telefono
                tel_clean = re.sub(r'[^0-9]', '', tel_val)
                if len(tel_clean) < 7: tel_clean = ""
                
                cuid_val = str(row.get(col_cuid)).strip() if col_cuid and pd.notna(row.get(col_cuid)) else ""
                mun_val = str(row.get(col_mun)).strip() if col_mun and pd.notna(row.get(col_mun)) else ""
                eapb_val = str(row.get(col_eapb)).strip() if col_eapb and pd.notna(row.get(col_eapb)) else ""
                geo_val = str(row.get(col_geo)).strip() if col_geo and pd.notna(row.get(col_geo)) else ""
                fec_nto_val = row.get(col_fec_nto) if col_fec_nto and pd.notna(row.get(col_fec_nto)) else None
                
                # 1. ¿Existe en la BD?
                if doc_clean in pacientes_db:
                    archivo_resumen["coinciden_con_bd"] += 1
                    p_actual = pacientes_db[doc_clean]
                    mejoras = {}
                    
                    if tel_clean and not p_actual.get("telefono_cuidador"):
                        mejoras["telefono_cuidador"] = tel_clean
                    if cuid_val and not p_actual.get("cuidador"):
                        mejoras["cuidador"] = cuid_val
                    if geo_val and not p_actual.get("georreferenciacion"):
                        mejoras["georreferenciacion"] = geo_val
                    if mun_val and not p_actual.get("municipio"):
                        mejoras["municipio"] = mun_val
                    if eapb_val and not p_actual.get("eapb"):
                        mejoras["eapb"] = eapb_val
                    
                    if mejoras:
                        archivo_resumen["campos_enriquecidos_aportados"] += len(mejoras)
                        if doc_clean not in enriquecimiento_existentes:
                            enriquecimiento_existentes[doc_clean] = {"mejoras": {}, "fuentes": set()}
                        enriquecimiento_existentes[doc_clean]["mejoras"].update(mejoras)
                        enriquecimiento_existentes[doc_clean]["fuentes"].add(a["nombre"])
                        
                else:
                    # 2. No existe en BD -> Paciente Nuevo
                    archivo_resumen["nuevos_para_bd"] += 1
                    if doc_clean not in pacientes_nuevos_totales:
                        pacientes_nuevos_totales[doc_clean] = {
                            "documento": doc_clean,
                            "nombre_completo": nom_val,
                            "telefono": tel_clean,
                            "cuidador": cuid_val,
                            "municipio": mun_val,
                            "eapb": eapb_val,
                            "georreferenciacion": geo_val,
                            "fecha_nacimiento": str(fec_nto_val) if fec_nto_val else None,
                            "fuentes": set()
                        }
                    else:
                        # complementar datos si están vacíos
                        curr = pacientes_nuevos_totales[doc_clean]
                        if not curr["nombre_completo"] and nom_val: curr["nombre_completo"] = nom_val
                        if not curr["telefono"] and tel_clean: curr["telefono"] = tel_clean
                        if not curr["cuidador"] and cuid_val: curr["cuidador"] = cuid_val
                        if not curr["municipio"] and mun_val: curr["municipio"] = mun_val
                        if not curr["eapb"] and eapb_val: curr["eapb"] = eapb_val
                        if not curr["georreferenciacion"] and geo_val: curr["georreferenciacion"] = geo_val
                    
                    pacientes_nuevos_totales[doc_clean]["fuentes"].add(a["nombre"])

        except Exception as e_sheet:
            archivo_resumen["motivo"] += f" [{sheet_name}: {str(e_sheet)[:80]}]"
            
    # Determinar clasificación final del archivo
    if archivo_resumen["registros_validos_doc"] == 0:
        archivo_resumen["clasificacion"] = "VACIO_O_SIN_DATOS_VALIDOS"
        archivo_resumen["motivo"] = "No contiene registros con documento de identidad legible."
    elif archivo_resumen["nuevos_para_bd"] > 0:
        archivo_resumen["clasificacion"] = "APORTA_USUARIOS_NUEVOS"
        archivo_resumen["motivo"] = f"Aporta {archivo_resumen['nuevos_para_bd']} usuarios no registrados en la BD actual."
    elif archivo_resumen["campos_enriquecidos_aportados"] > 0:
        archivo_resumen["clasificacion"] = "ENRIQUECE_DATOS_EXISTENTES"
        archivo_resumen["motivo"] = f"Complementa {archivo_resumen['campos_enriquecidos_aportados']} campos faltantes (teléfonos, acudientes, ubicación)."
    else:
        archivo_resumen["clasificacion"] = "REDUNDANTE_CONSOLIDADO"
        archivo_resumen["motivo"] = f"Los {archivo_resumen['registros_validos_doc']} registros ya existen íntegramente en la BD sin datos nuevos."
        
    auditoria_archivos.append(archivo_resumen)
    if a_idx % 20 == 0 or a_idx == len(archivos_info):
        print(f"Analizados {a_idx}/{len(archivos_info)} archivos...")

# Guardar resultados
# Convertir sets a listas para serializar en JSON
for k, v in pacientes_nuevos_totales.items():
    v["fuentes"] = list(v["fuentes"])

for k, v in enriquecimiento_existentes.items():
    v["fuentes"] = list(v["fuentes"])

resultado_final = {
    "total_archivos_auditados": len(auditoria_archivos),
    "total_pacientes_db_inicial": len(pacientes_db),
    "total_pacientes_nuevos_detectados": len(pacientes_nuevos_totales),
    "total_pacientes_existentes_enriquecidos": len(enriquecimiento_existentes),
    "resumen_clasificacion_archivos": {
        "APORTA_USUARIOS_NUEVOS": sum(1 for a in auditoria_archivos if a["clasificacion"] == "APORTA_USUARIOS_NUEVOS"),
        "ENRIQUECE_DATOS_EXISTENTES": sum(1 for a in auditoria_archivos if a["clasificacion"] == "ENRIQUECE_DATOS_EXISTENTES"),
        "REDUNDANTE_CONSOLIDADO": sum(1 for a in auditoria_archivos if a["clasificacion"] == "REDUNDANTE_CONSOLIDADO"),
        "VACIO_O_SIN_DATOS_VALIDOS": sum(1 for a in auditoria_archivos if a["clasificacion"] == "VACIO_O_SIN_DATOS_VALIDOS"),
    },
    "archivos": auditoria_archivos,
    "pacientes_nuevos": pacientes_nuevos_totales,
    "enriquecimiento_existentes": enriquecimiento_existentes
}

out_path = Path(r"sistema_dnt\backend\scripts\resultado_auditoria_cruce_completo.json")
with open(out_path, "w", encoding="utf-8") as fp:
    json.dump(resultado_final, fp, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print("¡CRUCE Y AUDITORÍA GLOBAL COMPLETADOS!")
print(f"Total Pacientes en BD Inicial: {len(pacientes_db)}")
print(f"Total PACIENTES NUEVOS encontrados: {len(pacientes_nuevos_totales)}")
print(f"Total Pacientes Existentes con DATOS ENRIQUECIDOS: {len(enriquecimiento_existentes)}")
print(f"Archivos que aportan usuarios nuevos: {resultado_final['resumen_clasificacion_archivos']['APORTA_USUARIOS_NUEVOS']}")
print(f"Archivos que enriquecen campos faltantes: {resultado_final['resumen_clasificacion_archivos']['ENRIQUECE_DATOS_EXISTENTES']}")
print(f"Archivos redundantes/ya consolidados: {resultado_final['resumen_clasificacion_archivos']['REDUNDANTE_CONSOLIDADO']}")
print(f"Archivos vacíos o sin datos clínicos: {resultado_final['resumen_clasificacion_archivos']['VACIO_O_SIN_DATOS_VALIDOS']}")
print(f"Guardado reporte completo en: {out_path}")
print("="*70)
