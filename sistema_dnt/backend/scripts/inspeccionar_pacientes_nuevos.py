import json
import re
import pandas as pd

with open(r"sistema_dnt\backend\scripts\resultado_auditoria_cruce_completo.json", encoding="utf-8") as f:
    data = json.load(f)

nuevos = data["pacientes_nuevos"]
print(f"Total pacientes nuevos extraídos: {len(nuevos)}")

validos = {}
invalidos = {}

for doc, p in nuevos.items():
    # Validaciones de calidad:
    # 1. Documento debe tener al menos 6 caracteres o ser numerico valido
    # 2. Debe tener un nombre con al menos 2 letras
    nom = p.get("nombre_completo", "").strip()
    doc_str = str(doc).strip()
    
    es_invalido = False
    motivo = ""
    
    if len(doc_str) < 5 or doc_str in ["0", "00", "000", "0000", "1234", "12345", "SINDATO", "SD", "NOAPLICA"]:
        es_invalido = True
        motivo = "Documento no válido o ficticio"
    elif not nom or len(nom) < 3 or nom.upper() in ["NAN", "SIN DATO", "DESCONOCIDO", "NO APLICA", "NONE"]:
        es_invalido = True
        motivo = "Nombre vacío o inválido"
        
    if es_invalido:
        invalidos[doc] = {**p, "motivo": motivo}
    else:
        validos[doc] = p

print(f"Pacientes nuevos VÁLIDOS (con documento y nombre legítimo): {len(validos)}")
print(f"Registros descartados por inconsistencia o falsos documentos: {len(invalidos)}")

# Muestra de válidos
print("\n--- MUESTRA DE 10 PACIENTES NUEVOS VÁLIDOS ---")
for idx, (doc, p) in enumerate(list(validos.items())[:10], 1):
    print(f"{idx:2d}. DNI: {doc:12s} | Nombre: {p['nombre_completo'][:30]:30s} | Mun: {p['municipio'] or 'S/D':12s} | EPS: {p['eapb'] or 'S/D':15s} | Fuentes: {p['fuentes'][:2]}")

# Archivos que más aportan
conteo_fuentes = {}
for doc, p in validos.items():
    for f in p["fuentes"]:
        conteo_fuentes[f] = conteo_fuentes.get(f, 0) + 1

print("\n--- TOP 15 ARCHIVOS QUE APORTAN MÁS PACIENTES NUEVOS VÁLIDOS ---")
sorted_fuentes = sorted(conteo_fuentes.items(), key=lambda x: x[1], reverse=True)
for f, cnt in sorted_fuentes[:15]:
    print(f"- {f[:60]:60s} -> {cnt:5d} pacientes nuevos")
