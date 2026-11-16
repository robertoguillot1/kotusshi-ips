"""
Router para Importación y Sincronización Masiva de Reportes Excel EPS
Sistema de Vigilancia y Seguimiento Nutricional
IPSI Kottushi Sao Ana>a
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.services_importacion import procesar_excel_eps

router = APIRouter(prefix="/api/importacion", tags=["Importación y Sincronización Masiva EPS"])

@router.post("/subir-excel")
async def subir_excel_eps(
    file: UploadFile = File(..., description="Archivo Excel (.xlsx o .xls) remitido por la EPS"),
    db: Session = Depends(get_db)
):
    """
    Recibe el archivo Excel periódico remitido por las trabajadoras de las EPS,
    extrae de forma inteligente toda la información demográfica y clínica,
    e implementa lógica incremental de sincronización (Upsert):
    - Si el paciente ya existe: actualiza sus datos y agrega automáticamente sus nuevos controles.
    - Si el paciente es nuevo: lo crea en el sistema con su ficha completa y carga su historial.
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo no válido. Debe cargar un archivo de hoja de cálculo Excel (.xlsx o .xls)."
        )

    try:
        contenido = await file.read()
        if len(contenido) == 0:
            raise HTTPException(status_code=400, detail="El archivo cargado está vacío.")

        resultado = procesar_excel_eps(contenido, file.filename, db)
        return resultado
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error durante el procesamiento del archivo Excel: {str(e)}"
        )
