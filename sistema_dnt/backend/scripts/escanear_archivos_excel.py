import os
import sys
import json
import glob
from pathlib import Path
import openpyxl
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

base_dir = Path(r"c:\Users\Roberto\Downloads\sandra")
output_json = Path(r"sistema_dnt\backend\scripts\inventario_archivos_sandra.json")

archivos = list(base_dir.rglob("*.xlsx")) + list(base_dir.rglob("*.xls")) + list(base_dir.rglob("*.csv"))
print(f"Total archivos a procesar: {len(archivos)}")

resultados = []

def normalizar_col(c):
    return str(c).strip().lower().replace(" ", "_").replace(".", "").replace("\n", "_")

doc_keywords = ["numero_id", "numero_documento", "num_identificacion", "documento", "no_identificacion", "identificacion", "identificación", "doc", "cedula", "tarjeta", "registro_civil"]

for idx, f in enumerate(archivos, 1):
    rel_path = str(f.relative_to(base_dir))
    size_kb = round(f.stat().st_size / 1024, 2)
    ext = f.suffix.lower()
    
    item = {
        "id": idx,
        "nombre": f.name,
        "ruta_relativa": rel_path,
        "extension": ext,
        "tamano_kb": size_kb,
        "hojas": [],
        "total_filas_estimadas": 0,
        "tiene_datos_clinicos": False,
        "error": None
    }
    
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(f, sep=None, engine='python', nrows=5, encoding='utf-8')
            except Exception:
                try:
                    df = pd.read_csv(f, sep=None, engine='python', nrows=5, encoding='latin1')
                except Exception as e:
                    df = None
                    item["error"] = str(e)
            
            if df is not None:
                cols_norm = [normalizar_col(c) for c in df.columns]
                has_doc = any(any(k in c for k in doc_keywords) for c in cols_norm)
                # contar lineas
                try:
                    with open(f, 'rb') as fp:
                        total_lines = sum(1 for _ in fp) - 1
                except Exception:
                    total_lines = len(df)
                
                item["hojas"].append({
                    "nombre": "CSV_DATA",
                    "filas": max(0, total_lines),
                    "columnas": list(df.columns)[:25],
                    "tiene_columna_doc": has_doc
                })
                item["total_filas_estimadas"] = max(0, total_lines)
                item["tiene_datos_clinicos"] = has_doc
        
        elif ext in [".xlsx", ".xls"]:
            # Leer nombres de hojas
            if ext == ".xlsx":
                try:
                    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
                    sheet_names = wb.sheetnames
                    wb.close()
                except Exception:
                    xl = pd.ExcelFile(f)
                    sheet_names = xl.sheet_names
            else:
                xl = pd.ExcelFile(f)
                sheet_names = xl.sheet_names
            
            total_filas = 0
            tiene_clinicos = False
            
            for sname in sheet_names:
                try:
                    # Leer primeras 10 filas para detectar encabezados reales
                    df_sample = pd.read_excel(f, sheet_name=sname, nrows=15, header=None)
                    if df_sample.empty:
                        item["hojas"].append({
                            "nombre": sname,
                            "filas": 0,
                            "columnas": [],
                            "tiene_columna_doc": False
                        })
                        continue
                    
                    # Buscar qué fila tiene los encabezados
                    header_row_idx = 0
                    has_doc = False
                    best_cols = []
                    
                    for r_idx in range(min(12, len(df_sample))):
                        row_vals = [normalizar_col(val) for val in df_sample.iloc[r_idx] if pd.notna(val)]
                        if any(any(k in val for k in doc_keywords) for val in row_vals):
                            has_doc = True
                            header_row_idx = r_idx
                            best_cols = [str(v) for v in df_sample.iloc[r_idx] if pd.notna(v)]
                            break
                    
                    if not has_doc:
                        # Si no encontramos por keywords, tomar la fila 0 como encabezado
                        best_cols = [str(v) for v in df_sample.iloc[0] if pd.notna(v)]
                    
                    # Estimar filas
                    if ext == ".xlsx":
                        try:
                            wb = openpyxl.load_workbook(f, read_only=True)
                            ws = wb[sname]
                            filas_hoja = ws.max_row or 0
                            wb.close()
                        except Exception:
                            filas_hoja = len(pd.read_excel(f, sheet_name=sname))
                    else:
                        filas_hoja = len(pd.read_excel(f, sheet_name=sname))
                    
                    filas_datos = max(0, filas_hoja - (header_row_idx + 1))
                    total_filas += filas_datos
                    if has_doc and filas_datos > 0:
                        tiene_clinicos = True
                    
                    item["hojas"].append({
                        "nombre": sname,
                        "filas": filas_datos,
                        "fila_encabezado": header_row_idx,
                        "columnas": [str(c)[:50] for c in best_cols[:30]],
                        "tiene_columna_doc": has_doc
                    })
                except Exception as e_sheet:
                    item["hojas"].append({
                        "nombre": sname,
                        "error": str(e_sheet)
                    })
            
            item["total_filas_estimadas"] = total_filas
            item["tiene_datos_clinicos"] = tiene_clinicos
            
    except Exception as e_file:
        item["error"] = str(e_file)
    
    resultados.append(item)
    if idx % 20 == 0 or idx == len(archivos):
        print(f"Procesados {idx}/{len(archivos)} archivos...")

with open(output_json, "w", encoding="utf-8") as fp:
    json.dump(resultados, fp, indent=2, ensure_ascii=False)

print(f"¡Inventario completado y guardado en {output_json}!")
