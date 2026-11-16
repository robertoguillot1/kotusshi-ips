import json
import re

with open(r"sistema_dnt\backend\scripts\resultado_auditoria_cruce_completo.json", encoding="utf-8") as f:
    data = json.load(f)

nuevos = data["pacientes_nuevos"]

legitimos = {}
for doc, p in nuevos.items():
    doc_str = str(doc).strip()
    # Debe ser numérico de 6 a 11 dígitos
    if doc_str.isdigit() and 6 <= len(doc_str) <= 11:
        nom = p.get("nombre_completo", "").strip()
        # Limpiar si nom empieza con palabras de encabezado o es solo números
        if len(nom) >= 4 and not nom.isdigit() and nom.upper() not in ["NAN", "NONE", "SIN DATO", "DESCONOCIDO"]:
            legitimos[doc_str] = p

print(f"Total pacientes NUEVOS con DNI numérico legítimo y nombre real: {len(legitimos)}")
print("\n--- MUESTRA DE 15 PACIENTES NUEVOS LEGÍTIMOS ---")
for idx, (doc, p) in enumerate(list(legitimos.items())[:15], 1):
    mun = p['municipio'] or 'S/D'
    eps = p['eapb'] or 'S/D'
    print(f"{idx:2d}. DNI: {doc:11s} | Nombre: {p['nombre_completo'][:32]:32s} | Mun: {mun:12s} | EPS: {eps:15s} | Fuentes: {p['fuentes'][:2]}")
