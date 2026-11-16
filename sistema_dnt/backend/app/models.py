from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class CatMunicipio(Base):
    __tablename__ = "cat_municipios"
    municipio_id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), unique=True, nullable=False)

class CatEAPB(Base):
    __tablename__ = "cat_eapb"
    eapb_id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, nullable=False)

class CatSedeIPSI(Base):
    __tablename__ = "cat_sedes_ipsi"
    sede_id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), unique=True, nullable=False)

class CatNovedad(Base):
    __tablename__ = "cat_novedades"
    novedad_id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(200), unique=True, nullable=False)

class Cuidador(Base):
    __tablename__ = "cuidadores"
    cuidador_id = Column(Integer, primary_key=True, index=True)
    documento_cuidador = Column(String(100), unique=True, nullable=True)
    nombre_completo = Column(String(255), nullable=False)
    telefono = Column(String(100), nullable=True)
    notas_contacto = Column(Text, nullable=True)

    pacientes = relationship("Paciente", back_populates="cuidador")

class Paciente(Base):
    __tablename__ = "pacientes"
    paciente_id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String(50), nullable=False)
    numero_documento = Column(String(100), unique=True, nullable=False, index=True)
    primer_nombre = Column(String(100), nullable=False)
    segundo_nombre = Column(String(100), nullable=True)
    primer_apellido = Column(String(100), nullable=False)
    segundo_apellido = Column(String(100), nullable=True)
    sexo = Column(String(1), CheckConstraint("sexo IN ('M', 'F')"), nullable=True)
    fecha_nacimiento = Column(Date, nullable=False)
    cuidador_id = Column(Integer, ForeignKey("cuidadores.cuidador_id", ondelete="SET NULL"), nullable=True)
    municipio_id = Column(Integer, ForeignKey("cat_municipios.municipio_id"), nullable=True)
    georreferenciacion = Column(Text, nullable=True)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cuidador = relationship("Cuidador", back_populates="pacientes")
    municipio = relationship("CatMunicipio")
    casos = relationship("NotificacionCaso", back_populates="paciente", cascade="all, delete-orphan")

class NotificacionCaso(Base):
    __tablename__ = "notificaciones_caso"
    caso_id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.paciente_id", ondelete="CASCADE"), nullable=False, index=True)
    fuente_notificacion = Column(String(150), nullable=True)
    fecha_notificacion = Column(Date, nullable=True)
    cooperante_notificador = Column(String(255), nullable=True)
    medio_notificacion = Column(String(100), nullable=True)
    eapb_id = Column(Integer, ForeignKey("cat_eapb.eapb_id"), nullable=True)
    tipo_afiliacion = Column(String(100), nullable=True)
    ips_primaria_id = Column(Integer, ForeignKey("cat_sedes_ipsi.sede_id"), nullable=True)

    # Captación inicial
    fecha_captacion = Column(Date, nullable=True)
    peso_inicial_kg = Column(Numeric(5, 2), nullable=True)
    talla_inicial_cm = Column(Numeric(5, 1), nullable=True)
    pb_inicial_cm = Column(Numeric(4, 1), nullable=True)
    zscore_inicial = Column(Numeric(4, 2), nullable=True)

    # GBAI
    fecha_busqueda_gbai = Column(Date, nullable=True)
    asignacion_interna = Column(String(150), nullable=True)
    estado_busqueda = Column(String(100), nullable=True)

    # Primera Atención
    fecha_primera_atencion = Column(Date, nullable=True)
    peso_atencion_kg = Column(Numeric(5, 2), nullable=True)
    talla_atencion_cm = Column(Numeric(5, 1), nullable=True)
    pb_atencion_cm = Column(Numeric(4, 1), nullable=True)
    zscore_atencion = Column(Numeric(4, 2), nullable=True)
    prueba_apetito = Column(String(100), nullable=True)
    tratamiento_inicial = Column(String(255), nullable=True)
    sobres_ftlc_inicial = Column(Integer, nullable=True)
    comorbilidad_inicial = Column(Text, nullable=True)
    escenario_manejo = Column(String(100), nullable=True)

    # Estado del caso
    estado_caso = Column(String(100), nullable=False, default="En seguimiento", index=True)
    motivo_egreso = Column(String(255), nullable=True)
    fecha_egreso = Column(Date, nullable=True)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    paciente = relationship("Paciente", back_populates="casos")
    eapb = relationship("CatEAPB")
    ips_primaria = relationship("CatSedeIPSI")
    controles = relationship("ControlSeguimiento", back_populates="caso", cascade="all, delete-orphan", order_by="ControlSeguimiento.numero_seguimiento")

class ControlSeguimiento(Base):
    __tablename__ = "controles_seguimiento"
    control_id = Column(Integer, primary_key=True, index=True)
    caso_id = Column(Integer, ForeignKey("notificaciones_caso.caso_id", ondelete="CASCADE"), nullable=False, index=True)
    numero_seguimiento = Column(Integer, nullable=False)
    fecha_control = Column(Date, nullable=False)
    peso_kg = Column(Numeric(5, 2), nullable=True)
    talla_cm = Column(Numeric(5, 1), nullable=True)
    perimetro_braquial_cm = Column(Numeric(4, 1), nullable=True)
    z_score = Column(Numeric(4, 2), nullable=True)
    tratamiento = Column(String(255), nullable=True)
    sobres_ftlc_entregados = Column(Integer, nullable=True)
    comorbilidad = Column(Text, nullable=True)
    novedad_id = Column(Integer, ForeignKey("cat_novedades.novedad_id"), nullable=True)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("caso_id", "numero_seguimiento", name="uq_caso_numero_seguimiento"),
    )

    caso = relationship("NotificacionCaso", back_populates="controles")
    novedad = relationship("CatNovedad")
