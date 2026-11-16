-- ============================================================================
-- BASE DE DATOS: Sistema de Vigilancia y Seguimiento Nutricional
-- IPSI Kottushi Sao Ana>a
-- Esquema DDL de Tablas e Índices (Actualizado con Tipos Numéricos Amplios)
-- ============================================================================

-- 1. TABLAS CATÁLOGO (Pobladas desde la hoja 'Listas')
CREATE TABLE IF NOT EXISTS cat_municipios (
    municipio_id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS cat_eapb (
    eapb_id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS cat_sedes_ipsi (
    sede_id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS cat_novedades (
    novedad_id SERIAL PRIMARY KEY,
    descripcion VARCHAR(200) UNIQUE NOT NULL
);

-- 2. CUIDADORES Y PACIENTES (Entidades Maestras)
CREATE TABLE IF NOT EXISTS cuidadores (
    cuidador_id SERIAL PRIMARY KEY,
    documento_cuidador VARCHAR(100) UNIQUE,
    nombre_completo VARCHAR(255) NOT NULL,
    telefono VARCHAR(100),
    notas_contacto TEXT
);

CREATE TABLE IF NOT EXISTS pacientes (
    paciente_id SERIAL PRIMARY KEY,
    tipo_documento VARCHAR(50) NOT NULL, -- RC, CN, MS, PT, PPT
    numero_documento VARCHAR(100) UNIQUE NOT NULL,
    primer_nombre VARCHAR(100) NOT NULL,
    segundo_nombre VARCHAR(100),
    primer_apellido VARCHAR(100) NOT NULL,
    segundo_apellido VARCHAR(100),
    sexo CHAR(1) CHECK (sexo IN ('M', 'F')),
    fecha_nacimiento DATE NOT NULL,
    cuidador_id INT REFERENCES cuidadores(cuidador_id) ON DELETE SET NULL,
    municipio_id INT REFERENCES cat_municipios(municipio_id),
    georreferenciacion TEXT,
    creado_en TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

-- 3. EPISODIOS DE NOTIFICACIÓN Y PRIMERA ATENCIÓN (Reemplaza 'Notificados')
CREATE TABLE IF NOT EXISTS notificaciones_caso (
    caso_id SERIAL PRIMARY KEY,
    paciente_id INT NOT NULL REFERENCES pacientes(paciente_id) ON DELETE CASCADE,
    fuente_notificacion VARCHAR(150),
    fecha_notificacion DATE,
    cooperante_notificador VARCHAR(255),
    medio_notificacion VARCHAR(100),
    eapb_id INT REFERENCES cat_eapb(eapb_id),
    tipo_afiliacion VARCHAR(100),
    ips_primaria_id INT REFERENCES cat_sedes_ipsi(sede_id),
    
    -- Captación inicial
    fecha_captacion DATE,
    peso_inicial_kg NUMERIC(8,2),
    talla_inicial_cm NUMERIC(8,2),
    pb_inicial_cm NUMERIC(8,2),
    zscore_inicial NUMERIC(8,2),
    
    -- GBAI
    fecha_busqueda_gbai DATE,
    asignacion_interna VARCHAR(150),
    estado_busqueda VARCHAR(100),
    
    -- Primera Atención Clínica en IPSI
    fecha_primera_atencion DATE,
    peso_atencion_kg NUMERIC(8,2),
    talla_atencion_cm NUMERIC(8,2),
    pb_atencion_cm NUMERIC(8,2),
    zscore_atencion NUMERIC(8,2),
    prueba_apetito VARCHAR(100),
    tratamiento_inicial VARCHAR(255),
    sobres_ftlc_inicial INT,
    comorbilidad_inicial TEXT,
    escenario_manejo VARCHAR(100),
    
    -- Ciclo de vida del caso
    estado_caso VARCHAR(100) NOT NULL DEFAULT 'En seguimiento',
    motivo_egreso VARCHAR(255),
    fecha_egreso DATE,
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);

-- 4. CONTROLES DE SEGUIMIENTO PERIÓDICOS (Reemplaza los 50 bloques horizontales)
CREATE TABLE IF NOT EXISTS controles_seguimiento (
    control_id SERIAL PRIMARY KEY,
    caso_id INT NOT NULL REFERENCES notificaciones_caso(caso_id) ON DELETE CASCADE,
    numero_seguimiento INT NOT NULL,
    fecha_control DATE NOT NULL,
    peso_kg NUMERIC(8,2),
    talla_cm NUMERIC(8,2),
    perimetro_braquial_cm NUMERIC(8,2),
    z_score NUMERIC(8,2),
    tratamiento VARCHAR(255),
    sobres_ftlc_entregados INT,
    comorbilidad TEXT,
    novedad_id INT REFERENCES cat_novedades(novedad_id),
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT NOW(),
    UNIQUE (caso_id, numero_seguimiento)
);

-- 5. ÍNDICES DE RENDIMIENTO
CREATE INDEX IF NOT EXISTS idx_pacientes_documento ON pacientes(numero_documento);
CREATE INDEX IF NOT EXISTS idx_casos_paciente ON notificaciones_caso(paciente_id);
CREATE INDEX IF NOT EXISTS idx_casos_estado ON notificaciones_caso(estado_caso);
CREATE INDEX IF NOT EXISTS idx_controles_caso_fecha ON controles_seguimiento(caso_id, fecha_control DESC);
CREATE INDEX IF NOT EXISTS idx_controles_caso_num ON controles_seguimiento(caso_id, numero_seguimiento DESC);
