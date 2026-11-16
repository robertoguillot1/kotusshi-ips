from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

# ------------------------------------------------------------------------------
# CATÁLOGOS
# ------------------------------------------------------------------------------
class CatalogoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str

class NovedadItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    novedad_id: int
    descripcion: str

# ------------------------------------------------------------------------------
# CUIDADOR
# ------------------------------------------------------------------------------
class CuidadorBase(BaseModel):
    documento_cuidador: Optional[str] = None
    nombre_completo: str
    telefono: Optional[str] = None
    notas_contacto: Optional[str] = None

class CuidadorCreate(CuidadorBase):
    pass

class CuidadorOut(CuidadorBase):
    model_config = ConfigDict(from_attributes=True)
    cuidador_id: int

# ------------------------------------------------------------------------------
# PACIENTE
# ------------------------------------------------------------------------------
class PacienteBase(BaseModel):
    tipo_documento: str = "RC"
    numero_documento: str
    primer_nombre: str
    segundo_nombre: Optional[str] = None
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    sexo: Optional[str] = None
    fecha_nacimiento: date
    municipio_id: Optional[int] = None
    georreferenciacion: Optional[str] = None

class PacienteCreate(PacienteBase):
    cuidador: Optional[CuidadorCreate] = None

class PacienteOut(PacienteBase):
    model_config = ConfigDict(from_attributes=True)
    paciente_id: int
    cuidador_id: Optional[int] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

# ------------------------------------------------------------------------------
# CONTROL DE SEGUIMIENTO
# ------------------------------------------------------------------------------
class ControlSeguimientoBase(BaseModel):
    fecha_control: date
    peso_kg: Optional[float] = None
    talla_cm: Optional[float] = None
    perimetro_braquial_cm: Optional[float] = None
    z_score: Optional[float] = None
    tratamiento: Optional[str] = None
    sobres_ftlc_entregados: Optional[int] = None
    comorbilidad: Optional[str] = None
    novedad_id: Optional[int] = None
    observaciones: Optional[str] = None

class ControlSeguimientoCreate(ControlSeguimientoBase):
    pass

class ControlSeguimientoOut(ControlSeguimientoBase):
    model_config = ConfigDict(from_attributes=True)
    control_id: int
    caso_id: int
    numero_seguimiento: int
    clasificacion_nutricional: Optional[str] = None
    fecha_proxima_cita: Optional[date] = None
    creado_en: Optional[datetime] = None

# ------------------------------------------------------------------------------
# NOTIFICACIÓN DE CASO
# ------------------------------------------------------------------------------
class NotificacionCasoBase(BaseModel):
    fuente_notificacion: Optional[str] = None
    fecha_notificacion: Optional[date] = None
    cooperante_notificador: Optional[str] = None
    medio_notificacion: Optional[str] = None
    eapb_id: Optional[int] = None
    tipo_afiliacion: Optional[str] = None
    ips_primaria_id: Optional[int] = None

    # Captación inicial
    fecha_captacion: Optional[date] = None
    peso_inicial_kg: Optional[float] = None
    talla_inicial_cm: Optional[float] = None
    pb_inicial_cm: Optional[float] = None
    zscore_inicial: Optional[float] = None

    # GBAI
    fecha_busqueda_gbai: Optional[date] = None
    asignacion_interna: Optional[str] = None
    estado_busqueda: Optional[str] = None

    # Primera atención
    fecha_primera_atencion: Optional[date] = None
    peso_atencion_kg: Optional[float] = None
    talla_atencion_cm: Optional[float] = None
    pb_atencion_cm: Optional[float] = None
    zscore_atencion: Optional[float] = None
    prueba_apetito: Optional[str] = None
    tratamiento_inicial: Optional[str] = None
    sobres_ftlc_inicial: Optional[int] = None
    comorbilidad_inicial: Optional[str] = None
    escenario_manejo: Optional[str] = None

    # Estado
    estado_caso: str = "En seguimiento"
    motivo_egreso: Optional[str] = None
    fecha_egreso: Optional[date] = None
    observaciones: Optional[str] = None

class NotificacionCasoCreate(NotificacionCasoBase):
    paciente: PacienteCreate

class CasoCerrarRequest(BaseModel):
    motivo_egreso: str
    fecha_egreso: Optional[date] = Field(default_factory=date.today)
    observaciones: Optional[str] = None

class NotificacionCasoOut(NotificacionCasoBase):
    model_config = ConfigDict(from_attributes=True)
    caso_id: int
    paciente_id: int
    paciente: PacienteOut
    creado_en: Optional[datetime] = None

class CasoResumenVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    caso_id: int
    paciente_id: int
    tipo_documento: str
    numero_documento: str
    nombre_completo: str
    sexo: Optional[str]
    fecha_nacimiento: date
    edad_meses_actual: Optional[int]
    municipio: Optional[str]
    eapb: Optional[str]
    sede_ipsi: Optional[str]
    cuidador: Optional[str]
    telefono_cuidador: Optional[str]
    fuente_notificacion: Optional[str]
    fecha_notificacion: Optional[date]
    estado_caso: str
    total_controles: int
    fecha_ultima_atencion: Optional[date]
    ultimo_zscore: Optional[float]
    clasificacion_nutricional_actual: Optional[str]
    fecha_proxima_cita: Optional[date]
    nutricionista_asignado: Optional[str] = None
    alerta_cita_vencida: Optional[bool] = False
    alerta_egreso_edad: Optional[bool] = False

# ------------------------------------------------------------------------------
# DASHBOARD E INDICADORES
# ------------------------------------------------------------------------------
class DashboardKPIs(BaseModel):
    total_notificados: int
    total_en_seguimiento: int
    total_cerrados: int
    citas_vencidas_hoy: int
    alertas_egreso_edad: int
    distribucion_diagnostico: dict
    distribucion_municipio: dict
    distribucion_eapb: dict
    distribucion_sede: dict
