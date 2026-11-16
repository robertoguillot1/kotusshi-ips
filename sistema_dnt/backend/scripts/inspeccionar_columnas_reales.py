import pandas as pd
from pathlib import Path

base_dir = Path(r"c:\Users\Roberto\Downloads\sandra")

archivos_clave = [
    "PACIENTES_NOTIFICADOS_DNT_ MATRIZ 2025 - 2026 F.C - NEP (77).xlsx",
    "BASE DE DATOS F.C 2026\\PLAN DE CHOQUE RIOHACHA.xlsx",
    "BASE DE DATOS F.C 2026\\2026 SEGUIMIENTO NOMINAL - SSM URIBIA (1).xlsx",
    "BASE DE DATOS F.C 2026\\SISPRO 01- 16 DE MARZO (1).xlsx",
    "BASE DE DATOS F.C 2026\\CASOS A PRESENTAR COMITE DE SENTENCIA T-302 URIBIA (3).xlsx",
    "3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx"
]

for rel in archivos_clave:
    fp = base_dir / rel
    if not fp.exists():
        continue
    print(f"\n=======================================================")
    print(f"ARCHIVO: {fp.name}")
    try:
        xl = pd.ExcelFile(fp)
        for s in xl.sheet_names[:4]:
            df = pd.read_excel(fp, sheet_name=s, nrows=4)
            cols = list(df.columns)
            # Buscar columnas que parezcan de nombres o documentos
            cols_nom = [c for c in cols if any(k in str(c).lower() for k in ["nom", "ape", "paciente", "menor"])]
            cols_doc = [c for c in cols if any(k in str(c).lower() for k in ["ide", "doc", "cedula"])]
            print(f"  Hoja: {s:25s} | Filas aprox: {len(df)} | Cols: {len(cols)}")
            print(f"    Cols Doc: {cols_doc[:4]}")
            print(f"    Cols Nom: {cols_nom[:6]}")
            if len(df) > 0 and cols_doc and cols_nom:
                doc_col = cols_doc[0]
                nom_col = cols_nom[0]
                val_doc = df[doc_col].iloc[0]
                val_nom = df[nom_col].iloc[0]
                print(f"    Ejemplo registro: doc={val_doc}, nom={val_nom}")
    except Exception as e:
        print(f"  Error: {e}")
