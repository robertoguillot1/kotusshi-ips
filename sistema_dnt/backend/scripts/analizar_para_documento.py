import json
from collections import defaultdict

with open('sistema_dnt/backend/scripts/auditoria_quirurgica_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

archivos = data['archivos']

grupos = defaultdict(list)
for a in archivos:
    grupos[a['clasificacion']].append(a)

print(f"Total archivos: {len(archivos)}")
for k, v in grupos.items():
    print(f"- {k}: {len(v)} archivos")

print('\n=============================================')
print('GRUPO 1: ENRIQUECEN DATOS FALTANTES (3)')
print('=============================================')
for a in grupos['ENRIQUECE_DATOS_FALTANTES']:
    print(f"* [{a['id']}] {a['ruta']}")
    print(f"  Filas: {a['total_filas_leidas']} | Coinciden BD: {a['coinciden_bd']} | Campos enriquecidos: {a['campos_completados']}")
    print(f"  Motivo: {a['motivo']}\n")

print('=============================================')
print('GRUPO 2: REDUNDANTE CONSOLIDADO (3)')
print('=============================================')
for a in grupos['REDUNDANTE_CONSOLIDADO']:
    print(f"* [{a['id']}] {a['ruta']}")
    print(f"  Filas: {a['total_filas_leidas']} | Coinciden BD: {a['coinciden_bd']} | Nuevos: {a['nuevos_detectados']}")
    print(f"  Motivo: {a['motivo']}\n")

print('=============================================')
print('GRUPO 3: SIN DATOS O INUTILIZABLE (29)')
print('=============================================')
for a in grupos['SIN_DATOS_O_INUTILIZABLE']:
    print(f"* [{a['id']}] {a['ruta']} | Filas: {a['total_filas_leidas']} | Motivo: {a['motivo']}")

print('\n=============================================')
print('GRUPO 4: TOP APORTANTES DE USUARIOS NUEVOS (de 93)')
print('=============================================')
aportantes = sorted(grupos['APORTA_USUARIOS_NUEVOS'], key=lambda x: x['nuevos_detectados'], reverse=True)
for a in aportantes[:25]:
    print(f"* [{a['id']}] {a['ruta']} -> Nuevos: {a['nuevos_detectados']} (de {a['dnis_validos_encontrados']} DNIs validos, {a['total_filas_leidas']} filas)")


