import json

with open(r'sistema_dnt\backend\scripts\inventario_archivos_sandra.json', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total analizados: {len(data)}')
con_datos = [d for d in data if d.get('tiene_datos_clinicos')]
sin_datos = [d for d in data if not d.get('tiene_datos_clinicos')]
con_error = [d for d in data if d.get('error')]

print(f'Archivos CON datos clínicos (DNI/pacientes detectados): {len(con_datos)}')
print(f'Archivos SIN columnas de pacientes o vacíos: {len(sin_datos)}')
print(f'Archivos con error de lectura: {len(con_error)}')

con_datos.sort(key=lambda x: x.get('total_filas_estimadas', 0), reverse=True)
print('\n--- TOP 20 ARCHIVOS CON MÁS FILAS ---')
for d in con_datos[:20]:
    hojas_desc = []
    for h in d.get('hojas', []):
        if h.get('tiene_columna_doc'):
            hojas_desc.append(f"{h.get('nombre')}: {h.get('filas')} filas")
    print(f"ID {d['id']:3d} | {d['nombre'][:55]:55s} | {d['tamano_kb']:8.1f} KB | Total: {d.get('total_filas_estimadas', 0):6d} filas | Hojas: {hojas_desc[:3]}")

print('\n--- ARCHIVOS SIN DATOS CLÍNICOS O VACÍOS (MUESTRA) ---')
for d in sin_datos[:15]:
    print(f"ID {d['id']:3d} | {d['nombre'][:55]:55s} | {d['tamano_kb']:8.1f} KB | Filas: {d.get('total_filas_estimadas', 0)} | Error: {d.get('error')}")
