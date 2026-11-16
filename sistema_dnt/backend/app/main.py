import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import catalogos, casos, controles, reportes, importacion, notificaciones
from app.config import API_DEBUG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "frontend"))

app = FastAPI(
    title="API de Vigilancia y Seguimiento Nutricional (IPSI Kottushi Sao Ana>a)",
    description=(
        "Sistema integral de gestión de la ruta de atención para desnutrición aguda (Evento 113) "
        "y riesgo de desnutrición aguda (Evento 114) en niños y niñas de 0 a 59 meses, "
        "bajo los lineamientos de la Resolución 000115 de 2026."
    ),
    version="1.0.0",
    debug=API_DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos del Frontend si existe el directorio
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Registro de Routers API
app.include_router(catalogos.router)
app.include_router(casos.router)
app.include_router(controles.router)
app.include_router(reportes.router)
app.include_router(importacion.router)
app.include_router(notificaciones.router)

@app.get("/", tags=["Interfaz Web"])
def servir_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "sistema": "Vigilancia y Seguimiento Nutricional IPSI Kottushi Sao Ana>a",
        "estado": "Activo y Operativo",
        "documentacion": "/docs"
    }

@app.get("/health", tags=["Salud del Sistema"])
def healthcheck():
    return {"status": "ok"}

@app.get("/auditoria-consolidacion.md", tags=["Documentación"])
def servir_informe_auditoria():
    doc_path = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", "auditoria_y_consolidacion_excels_sandra.md"))
    if os.path.exists(doc_path):
        return FileResponse(doc_path, media_type="text/markdown; charset=utf-8")
    return {"error": "Documento de auditoría no encontrado"}
