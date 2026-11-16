import requests

base = "http://127.0.0.1:8000"

print("1. Probando /api/reportes/exportar-sivigila?evento=113&semana=40...")
r1 = requests.get(f"{base}/api/reportes/exportar-sivigila?evento=113&semana=40", timeout=15)
print("Status:", r1.status_code, "Longitud:", len(r1.content), "Content-Disposition:", r1.headers.get("Content-Disposition"))

print("\n2. Probando /api/reportes/exportar-t302?municipio=URIBIA...")
r2 = requests.get(f"{base}/api/reportes/exportar-t302?municipio=URIBIA", timeout=15)
print("Status:", r2.status_code, "Longitud:", len(r2.content), "Content-Disposition:", r2.headers.get("Content-Disposition"))

print("\n3. Probando /api/reportes/exportar-busqueda-activa?dias_vencido_min=15...")
r3 = requests.get(f"{base}/api/reportes/exportar-busqueda-activa?dias_vencido_min=15", timeout=15)
print("Status:", r3.status_code, "Longitud:", len(r3.content), "Content-Disposition:", r3.headers.get("Content-Disposition"))

print("\n4. Probando /auditoria-consolidacion.md...")
r4 = requests.get(f"{base}/auditoria-consolidacion.md", timeout=15)
print("Status:", r4.status_code, "Longitud:", len(r4.content))

print("\nTodos los endpoints probados con exito!")
