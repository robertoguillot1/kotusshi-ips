from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from app.database import get_db
from app.models import CatMunicipio, CatEAPB, CatSedeIPSI, CatNovedad

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])

@router.get("/{tipo}")
def obtener_catalogo(tipo: str, db: Session = Depends(get_db)):
    """
    Retorna los ítems de catálogos maestros para poblar selectores:
    - 'municipios'
    - 'eapb'
    - 'sedes'
    - 'novedades'
    """
    t = tipo.lower()
    if t == "municipios":
        items = db.query(CatMunicipio).order_by(CatMunicipio.nombre).all()
        return [{"id": m.municipio_id, "nombre": m.nombre} for m in items]
    elif t == "eapb":
        items = db.query(CatEAPB).order_by(CatEAPB.nombre).all()
        return [{"id": e.eapb_id, "nombre": e.nombre} for e in items]
    elif t in ["sedes", "sedes-ipsi"]:
        items = db.query(CatSedeIPSI).order_by(CatSedeIPSI.nombre).all()
        return [{"id": s.sede_id, "nombre": s.nombre} for s in items]
    elif t == "novedades":
        items = db.query(CatNovedad).order_by(CatNovedad.descripcion).all()
        return [{"id": n.novedad_id, "descripcion": n.descripcion} for n in items]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Catálogo '{tipo}' no reconocido. Tipos válidos: municipios, eapb, sedes, novedades"
        )
