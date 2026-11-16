from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import ControlSeguimiento, NotificacionCaso, Paciente
from app.schemas import ControlSeguimientoCreate, ControlSeguimientoOut
from app.services import clasificar_estado_nutricional, calcular_proxima_cita, evaluar_ventana_etaria

router = APIRouter(prefix="/api/casos/{caso_id}/controles", tags=["Controles de Seguimiento"])

@router.get("", response_model=List[ControlSeguimientoOut])
def listar_controles_caso(
    caso_id: int,
    solo_este_caso: bool = Query(False, description="Si es True, solo retorna controles de este caso_id específico. Por defecto False (retorna toda la trazabilidad del niño)"),
    db: Session = Depends(get_db)
):
    """
    Retorna la serie temporal completa de controles periódicos del paciente (trazabilidad integral del niño),
    ordenados cronológicamente por fecha de atención.
    """
    caso = db.query(NotificacionCaso).filter(NotificacionCaso.caso_id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")

    if solo_este_caso:
        controles = (
            db.query(ControlSeguimiento)
            .filter(ControlSeguimiento.caso_id == caso_id)
            .order_by(ControlSeguimiento.fecha_control.asc(), ControlSeguimiento.numero_seguimiento.asc())
            .all()
        )
    else:
        # Trazabilidad integral: controles de todos los episodios del mismo paciente
        controles = (
            db.query(ControlSeguimiento)
            .join(NotificacionCaso, ControlSeguimiento.caso_id == NotificacionCaso.caso_id)
            .filter(NotificacionCaso.paciente_id == caso.paciente_id)
            .order_by(ControlSeguimiento.fecha_control.asc(), ControlSeguimiento.numero_seguimiento.asc())
            .all()
        )

    resultado = []
    for idx, c in enumerate(controles, start=1):
        z = float(c.z_score) if c.z_score is not None else None
        item = ControlSeguimientoOut(
            control_id=c.control_id,
            caso_id=c.caso_id,
            numero_seguimiento=c.numero_seguimiento,
            fecha_control=c.fecha_control,
            peso_kg=float(c.peso_kg) if c.peso_kg is not None else None,
            talla_cm=float(c.talla_cm) if c.talla_cm is not None else None,
            perimetro_braquial_cm=float(c.perimetro_braquial_cm) if c.perimetro_braquial_cm is not None else None,
            z_score=z,
            tratamiento=c.tratamiento,
            sobres_ftlc_entregados=c.sobres_ftlc_entregados,
            comorbilidad=c.comorbilidad,
            novedad_id=c.novedad_id,
            observaciones=c.observaciones,
            clasificacion_nutricional=clasificar_estado_nutricional(z),
            fecha_proxima_cita=calcular_proxima_cita(c.fecha_control, z),
            creado_en=c.creado_en
        )
        resultado.append(item)

    return resultado

@router.post("", response_model=ControlSeguimientoOut, status_code=201)
def registrar_control_caso(
    caso_id: int,
    control_in: ControlSeguimientoCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo control de seguimiento clínico:
    - Asigna automáticamente el consecutivo `numero_seguimiento` (N+1).
    - Evalúa la clasificación nutricional según el Puntaje Z (Res. 000115 de 2026).
    - Calcula la fecha estimada de la próxima cita.
    - Evalúa alertas de cumplimiento de edad (>= 60 meses).
    """
    caso = db.query(NotificacionCaso).filter(NotificacionCaso.caso_id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail=f"Caso {caso_id} no encontrado")

    # Obtener el último número de seguimiento del paciente para mantener la secuencia continua
    max_num = (
        db.query(func.max(ControlSeguimiento.numero_seguimiento))
        .join(NotificacionCaso, ControlSeguimiento.caso_id == NotificacionCaso.caso_id)
        .filter(NotificacionCaso.paciente_id == caso.paciente_id)
        .scalar() or 0
    )
    siguiente_num = max_num + 1

    nuevo_control = ControlSeguimiento(
        caso_id=caso_id,
        numero_seguimiento=siguiente_num,
        fecha_control=control_in.fecha_control,
        peso_kg=control_in.peso_kg,
        talla_cm=control_in.talla_cm,
        perimetro_braquial_cm=control_in.perimetro_braquial_cm,
        z_score=control_in.z_score,
        tratamiento=control_in.tratamiento,
        sobres_ftlc_entregados=control_in.sobres_ftlc_entregados,
        comorbilidad=control_in.comorbilidad,
        novedad_id=control_in.novedad_id,
        observaciones=control_in.observaciones
    )
    db.add(nuevo_control)
    db.commit()
    db.refresh(nuevo_control)

    z = float(nuevo_control.z_score) if nuevo_control.z_score is not None else None
    return ControlSeguimientoOut(
        control_id=nuevo_control.control_id,
        caso_id=nuevo_control.caso_id,
        numero_seguimiento=nuevo_control.numero_seguimiento,
        fecha_control=nuevo_control.fecha_control,
        peso_kg=float(nuevo_control.peso_kg) if nuevo_control.peso_kg is not None else None,
        talla_cm=float(nuevo_control.talla_cm) if nuevo_control.talla_cm is not None else None,
        perimetro_braquial_cm=float(nuevo_control.perimetro_braquial_cm) if nuevo_control.perimetro_braquial_cm is not None else None,
        z_score=z,
        tratamiento=nuevo_control.tratamiento,
        sobres_ftlc_entregados=nuevo_control.sobres_ftlc_entregados,
        comorbilidad=nuevo_control.comorbilidad,
        novedad_id=nuevo_control.novedad_id,
        observaciones=nuevo_control.observaciones,
        clasificacion_nutricional=clasificar_estado_nutricional(z),
        fecha_proxima_cita=calcular_proxima_cita(nuevo_control.fecha_control, z),
        creado_en=nuevo_control.creado_en
    )
