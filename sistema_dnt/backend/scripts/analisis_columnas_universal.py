import os
import glob
from pathlib import Path
import openpyxl
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

base_dir = Path(r"c:\Users\Roberto\Downloads\sandra")
archivos = list(base_dir.rglob("*.xlsx")) + list(base_dir.rglob("*.xls")) + list(base_dir.rglob("*.csv"))

def normalizar(s):
    if not isinstance(s, str):
        return ""
    return s.strip().lower().replace(" ", "_").replace(".", "").replace("\n", "_").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

doc_aliases = [
    "num_ide_", "num_ide", "numero_id", "numero_identificacion", "numero_documento", 
    "no_identificacion", "documento", "identificacion", "doc_identidad", "num_ident", "id_usuario", "id"
]

nombre_aliases = [
    "pri_nom_", "primer_nombre", "nombres", "nombre_paciente", "nombre_del_menor", "nombre_completo", "nombres_y_apellidos"
]

archivos_con_pacientes = []

print(f"Examinando los {len(archivos)} archivos con detector universal...")

for idx, f in enumerate(archivos, 1):
    rel = str(f.relative_to(base_dir))
    ext = f.suffix.lower()
    info_archivo = {
        "id": idx,
        "ruta": rel,
        "nombre": f.name,
        "tamano_kb": round(f.stat().st_size / 1024, 1),
        "hojas_validas": []
    }
    
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(f, sep=None, engine='python', nrows=5, encoding='utf-8')
            except Exception:
                df = pd.read_csv(f, sep=None, engine='python', nrows=5, encoding='latin1')
            
            cols_norm = {col: normalizar(col) for col in df.columns}
            col_doc = next((orig for orig, n in cols_norm.items() if any(a == n or a in n for a in doc_aliases)), None)
            col_nom = next((orig for orig, n in cols_norm.items() if any(a == n or a in n for a in nombre_aliases)), None)
            
            if col_doc:
                info_archivo["hojas_validas"].append({
                    "hoja": "CSV_DATA",
                    "col_doc": col_doc,
                    "col_nombre": col_nom,
                    "total_cols": len(df.columns)
                })
        
        elif ext in [".xlsx", ".xls"]:
            # Obtener nombres de hojas
            if ext == ".xlsx":
                try:
                    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
                    snames = wb.sheetnames
                    wb.close()
                except Exception:
                    xl = pd.ExcelFile(f)
                    snames = xl.sheet_names
            else:
                xl = pd.ExcelFile(f)
                snames = xl.sheet_names
            
            for sname in snames:
                try:
                    df_s = pd.read_excel(f, sheet_name=sname, nrows=12, header=None)
                    if df_s.empty:
                        continue
                    
                    # Buscar en las primeras 12 filas cuál tiene encabezados
                    for r_idx in range(min(10, len(df_s))):
                        row_vals = [str(v) for v in df_s.iloc[r_idx] if pd.notna(v)]
                        norm_vals = {v: normalizar(v) for v in row_vals}
                        
                        found_doc = next((orig for orig, n in norm_vals.items() if any(a == n or a in n for a in doc_aliases)), None)
                        found_nom = next((orig for orig, n in norm_vals.items() if any(a == n or a in n for a in nombre_aliases)), None)
                        
                        if found_doc:
                            info_archivo["hojas_validas"].append({
                                "hoja": sname,
                                "fila_header": r_idx,
                                "col_doc": found_doc,
                                "col_nombre": found_nom,
                                "total_cols": len(row_vals)
                            })
                            break
                except Exception:
                    continue
    except Exception:
        pass
    
    if info_archivo["hojas_validas"]:
        archivos_con_pacientes.append(info_archivo)

print(f"\n¡Total archivos con columnas de pacientes confirmadas: {len(archivos_con_pacientes)} de {len(archivos)}!")

import json
with open(r"sistema_dnt\backend\scripts\archivos_con_pacientes.json", "w", encoding="utf-8") as fp:
    json.dump(archivos_con_pacientes, fp, indent=2, ensure_ascii=False)

print("Guardado en sistema_dnt\\backend\\scripts\\archivos_con_pacientes.json")
