# Especificación Técnica: Sistema de Vigilancia y Seguimiento Nutricional (IPSI Kottushi Sao Ana>a)

## 1. Contexto y Objetivo del Proyecto

Este documento define la arquitectura de base de datos, las reglas de negocio clínicas, el proceso de migración (ETL) y los requerimientos del backend para digitalizar y reemplazar el libro de Excel **`3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx`** de la **IPSI Kottushi Sao Ana>a**.

El instrumento unificado (**PM-RIA-FT-003** para notificación y **PM-RIA-FT-004** para seguimiento) gestiona la ruta de atención integral para niños y niñas de $0$ **a** $59$ **meses** con diagnóstico de **Desnutrición Aguda (Evento 113)** o **Riesgo de Desnutrición Aguda (Evento 114)**, bajo los lineamientos normativos de la **Resolución 000115 de 2026** (actualización de la Resolución 2350 de 2020) en Colombia.

### Problema Operativo Actual vs. Solución Propuesta
El problema principal de rendimiento, integridad y mantenimiento del libro de Excel actual radica en que combina **captura transaccional, cálculos clínicos en vivo y almacenamiento histórico en formato ancho** (llegando a **$596$ columnas** en una sola hoja). Al migrar a un motor relacional, pasamos de una matriz gigante llena de celdas vacías a tablas verticales ligeras, auditables y listas para integrarse con otras plataformas.

### Estrategia de Despliegue
1. **Fase 1 (Actual - Entorno Local):** Despliegue en **PostgreSQL Local** + Backend API REST + Script de migración desde Excel para validación funcional con la gerencia de la IPSI.
2. **Fase 2 (Futuro - Nube):** Migración directa hacia **Supabase** (PostgreSQL administrado) mediante respaldo estándar (`pg_dump`), sin alterar el esquema SQL ni la lógica del backend.

---

## 2. Radiografía Completa de las 7 Hojas del Libro Excel

El libro origen está compuesto por $7$ hojas interconectadas que cumplen roles operativos, de catálogo, históricos y analíticos:

| Hoja (Nombre exacto) | Rol en la operación | Volumen actual | Qué contiene exactamente |
| :--- | :--- | :--- | :--- |
| **`Portada`** | Documentación y manual operativo | $28$ filas | Explica el flujo operativo de la ruta, los cambios normativos de la Res. 000115 de 2026, qué columnas se calculan automáticamente y el código de colores de alerta clínica. |
| **`Listas`** | Catálogos maestros | $15$ listas (hasta $44$ ítems c/u) | Tablas de referencia que alimentan las listas desplegables del libro: municipios, EAPB, tipos de documento, clasificaciones nutricionales, sedes IPSI ($28$ sedes), fuentes/medios de notificación, asignaciones internas (GBAI) y novedades. |
| **`Notificados`** (`FT-003`) | Registro maestro de ingreso y valoración inicial | **$1.787$ filas** ($1.751$ docs únicos) $\times$ **$49$ cols** | Cada fila representa una notificación de caso (Evento 113 DNT o 114 Riesgo DNT). Contiene filiación del menor, datos del cuidador, georreferenciación, captación inicial, gestión de búsqueda activa (GBAI) y la **Primera Atención Clínica en la IPSI** (antropometría, prueba de apetito y entrega de FTLC). |
| **`Casos en Seguimiento `** (`FT-004`) *(nota: espacio al final)* | Evolución clínica periódica (formato ancho) | **$868$ filas** $\times$ **$596$ cols** | Trae automáticamente los datos demográficos e iniciales del paciente desde `Notificados` y despliega horizontalmente la **Atención Inicial** más **$50$ bloques repetitivos de $10$ columnas** (`SEGUIMIENTO 1` a `SEGUIMIENTO 50`, usados actualmente hasta el $47$) + columnas auxiliares de rastreo al final. |
| **`Seguimientos Cerrados `** *(nota: espacio al final)* | Archivo histórico de egresos | **$104$ filas** (valores estáticos) | Misma estructura horizontal de $50$ bloques de seguimiento, pero sin fórmulas (valores pegados estáticamente). Almacena casos cerrados por cumplimiento de edad ($\ge 60$ meses), recuperación nutricional, cambio de domicilio o renuencia. |
| **`Dashboard`** | Tablero de control en vivo | $89$ filas | Indicadores calculados dinámicamente (`COUNTIFS`, `SUMPRODUCT`) desde `Notificados` y `Casos en Seguimiento `: conteo de duplicados, alertas de ventana etaria, citas vencidas a la fecha y desgloses por diagnóstico actual, EAPB, municipio y sede IPSI. |
| **`Indicadores Mensuales`** | Reporte epidemiológico mensual | $110$ filas ($2024\text{--}2027$) | Dos matrices de conteo mensual por municipio calculadas desde `Notificados`: una agrupada por **Fecha de Notificación** y otra agrupada por **Fecha de Primera Atención**. |

---

## 3. Flujo Técnico, Relación entre Hojas y Puntos Críticos

Para que el agente IA diseñe correctamente el script de migración (ETL) y la lógica de negocio, debe comprender cómo fluyen los datos actualmente dentro del Excel:

### A. Cómo se relacionan las hojas entre sí
1. **La llave primaria de cruce es el `Número de Documento` del menor:**
   * Todo caso nace obligatoriamente en **`Notificados`**. Los **$868$ pacientes** registrados en `Casos en Seguimiento ` y los **$104$** en `Seguimientos Cerrados ` existen previamente en `Notificados` ($100\%$ de integridad referencial).
2. **Dependencia mediante fórmulas de búsqueda (`INDEX/MATCH`):**
   * En **`Casos en Seguimiento `**, las columnas `B` a `W` (datos demográficos, municipio, EAPB, cuidador) y `AC` a `AM` (datos de la Primera Atención IPSI) **no se digitan manualmente**: se autocompletan buscando el documento en `Notificados`.
3. **Mecanismo de rastreo del último control (`TY:VX`):**
   * Al final de las $596$ columnas de `Casos en Seguimiento ` (rango `TY:VX`), existen $50$ columnas auxiliares que detectan cuál es el último bloque de seguimiento diligenciado (`MATCH(MAX(...))`). Con base en el Puntaje Z de ese último bloque, las fórmulas calculan el estado nutricional actual y la fecha de la próxima cita.

### B. Puntos críticos y anomalías que el ETL debe resolver
1. **Explosión horizontal de columnas ($50$ bloques de seguimiento):**
   * Mantener `SEGUIMIENTO 1` hasta `SEGUIMIENTO 50` en columnas multiplica cientos de fórmulas por fila y genera miles de celdas vacías. En PostgreSQL, estos $50$ bloques se **despivotan** hacia una única tabla vertical (`controles_seguimiento`), transformando las $868$ filas activas + $104$ cerradas en aproximadamente **$4.227$ registros individuales de control** ($3.807$ activos + $420$ cerrados).
2. **Solapamiento entre casos activos y cerrados ($48$ pacientes duplicados):**
   * En la operación manual actual, el cierre de casos se realiza copiando y pegando filas hacia `Seguimientos Cerrados `. Como resultado, **$48$ de los $104$ casos cerrados siguen apareciendo simultáneamente en `Casos en Seguimiento `**.
   * *Regla para el ETL:* Unificar todo el historial de controles de esos pacientes en `controles_seguimiento` (sin duplicar controles idénticos) y marcar su episodio en `notificaciones_caso` con `estado_caso = 'Cerrado'`.
3. **Documentos repetidos en `Notificados` ($36$ casos):**
   * Existen $36$ números de documento digitados más de una vez en `Notificados`.
   * *Regla para el ETL:* Insertar un único registro maestro en `pacientes` (conservando la georreferenciación y teléfono más recientes) y crear múltiples episodios en `notificaciones_caso` únicamente si corresponden a fechas de notificación o eventos distintos (descartando filas $100\%$ idénticas).
4. **Datos híbridos en campos numéricos y teléfonos:**
   * En columnas como `Teléfono` (ej. `"3205282553 (AGENTE EDUCATIVO)"`), `Fórmula Terapéutica entregada` (`"Sin Dato"`, `"N/A"`) y `Z-Score`, el ETL debe limpiar el dato numérico/telefónico, trasladar las notas textuales a `observaciones` / `notas_contacto` y convertir textos vacíos o `"Sin Dato"` en `NULL` real de base de datos.

---

## 4. Stack Tecnológico Recomendado para el Agente

* **Motor de Base de Datos:** PostgreSQL 15+ (Local).
* **Backend API (elegir según ecosistema preferido del proyecto):**
  * *Opción A (Recomendada por facilidad con datos/Excel):* **Python 3.11+ con FastAPI**, SQLAlchemy / SQLModel y `pandas` + `openpyxl` para el ETL.
  * *Opción B:* **Node.js (TypeScript) con NestJS o Express**, Prisma ORM y `xlsx` para el ETL.
* **Documentación API:** Swagger / OpenAPI automático (`/docs`).

---

## 5. Diseño del Esquema Relacional (PostgreSQL DDL)

El esquema normaliza las $7$ hojas del Excel en tablas catálogos, entidades maestras y una tabla vertical de controles clínicos:

```sql
-- ============================================================================
-- 1. TABLAS CATÁLOGO (Pobladas desde la hoja 'Listas')
-- ============================================================================
CREATE TABLE cat_municipios (
    municipio_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE cat_eapb (
    eapb_id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE cat_sedes_ipsi (
    sede_id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE cat_novedades (
    novedad_id SERIAL PRIMARY KEY,
    descripcion VARCHAR(120) UNIQUE NOT NULL
);

-- ============================================================================
-- 2. CUIDADORES Y PACIENTES (Entidades Maestras)
-- ============================================================================
CREATE TABLE cuidadores (
    cuidador_id SERIAL PRIMARY KEY,
    documento_cuidador VARCHAR(30) UNIQUE,
    nombre_completo VARCHAR(150) NOT NULL,
    telefono VARCHAR(50),
    notas_contacto TEXT
);

CREATE TABLE pacientes (
    paciente_id SERIAL PRIMARY KEY,
    tipo_documento VARCHAR(15) NOT NULL, -- RC, CN, MS, PT, PPT
    numero_documento VARCHAR(30) UNIQUE NOT NULL,
    primer_nombre VARCHAR(60) NOT NULL,
    segundo_nombre VARCHAR(60),
    primer_apellido VARCHAR(60) NOT NULL,
    segundo_apellido VARCHAR(60),
    sexo CHAR(1) CHECK (sexo IN ('M', 'F')),
    fecha_nacimiento DATE NOT NULL,
    cuidador_id INT REFERENCES cuidadores(cuidador_id) ON DELETE SET NULL,
    municipio_id INT REFERENCES cat_municipios(municipio_id),
    georreferenciacion TEXT,
    creado_en TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 3. EPISODIOS DE NOTIFICACIÓN Y PRIMERA ATENCIÓN (Reemplaza 'Notificados')
-- ============================================================================
CREATE TABLE notificaciones_caso (
    caso_id SERIAL PRIMARY KEY,
    paciente_id INT NOT NULL REFERENCES pacientes(paciente_id) ON DELETE CASCADE,
    fuente_notificacion VARCHAR(60), -- Evento 113: DNT, Evento 114: Riesgo DNT, Otro Dx
    fecha_notificacion DATE,
    cooperante_notificador VARCHAR(200),
    medio_notificacion VARCHAR(50),
    eapb_id INT REFERENCES cat_eapb(eapb_id),
    tipo_afiliacion VARCHAR(40),
    ips_primaria_id INT REFERENCES cat_sedes_ipsi(sede_id),
    
    -- Captación inicial (entidad notificadora / búsqueda)
    fecha_captacion DATE,
    peso_inicial_kg NUMERIC(5,2),
    talla_inicial_cm NUMERIC(5,1),
    pb_inicial_cm NUMERIC(4,1),
    zscore_inicial NUMERIC(4,2),
    
    -- Gestión de Búsqueda Activa Institucional (GBAI)
    fecha_busqueda_gbai DATE,
    asignacion_interna VARCHAR(80),
    estado_busqueda VARCHAR(50),
    
    -- Primera Atención Clínica en IPSI
    fecha_primera_atencion DATE,
    peso_atencion_kg NUMERIC(5,2),
    talla_atencion_cm NUMERIC(5,1),
    pb_atencion_cm NUMERIC(4,1),
    zscore_atencion NUMERIC(4,2),
    prueba_apetito VARCHAR(30),
    tratamiento_inicial VARCHAR(120),
    sobres_ftlc_inicial INT,
    comorbilidad_inicial TEXT,
    escenario_manejo VARCHAR(30), -- Ambulatorio / Hospitalario
    
    -- Ciclo de vida del caso (absorbe 'Seguimientos Cerrados ')
    estado_caso VARCHAR(30) NOT NULL DEFAULT 'En seguimiento', -- En seguimiento, Cerrado, En Búsqueda, Descartado
    motivo_egreso VARCHAR(100),
    fecha_egreso DATE,
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 4. CONTROLES DE SEGUIMIENTO PERIÓDICOS (Reemplaza los 50 bloques horizontales)
-- ============================================================================
CREATE TABLE controles_seguimiento (
    control_id SERIAL PRIMARY KEY,
    caso_id INT NOT NULL REFERENCES notificaciones_caso(caso_id) ON DELETE CASCADE,
    numero_seguimiento INT NOT NULL,
    fecha_control DATE NOT NULL,
    peso_kg NUMERIC(5,2),
    talla_cm NUMERIC(5,1),
    perimetro_braquial_cm NUMERIC(4,1),
    z_score NUMERIC(4,2),
    tratamiento VARCHAR(120),
    sobres_ftlc_entregados INT,
    comorbilidad TEXT,
    novedad_id INT REFERENCES cat_novedades(novedad_id),
    observaciones TEXT,
    creado_en TIMESTAMP DEFAULT NOW(),
    UNIQUE (caso_id, numero_seguimiento)
);

-- ============================================================================
-- 5. ÍNDICES DE RENDIMIENTO
-- ============================================================================
CREATE INDEX idx_pacientes_documento ON pacientes(numero_documento);
CREATE INDEX idx_casos_paciente ON notificaciones_caso(paciente_id);
CREATE INDEX idx_casos_estado ON notificaciones_caso(estado_caso);
CREATE INDEX idx_controles_caso_fecha ON controles_seguimiento(caso_id, fecha_control DESC);
```

---

## 6. Reglas de Negocio Clínicas (Resolución 000115 de 2026) y Vista SQL

El backend y las vistas SQL deben implementar exactamente estas reglas clínicas que anteriormente residían en las fórmulas del Excel:

1. **Clasificación Nutricional Automática según Puntaje Z (Peso/Talla):**
   * Si $Z < -3.0 \rightarrow$ `'Desnutrición aguda severa'`
   * Si $-3.0 \le Z < -2.0 \rightarrow$ `'Desnutrición aguda moderada'`
   * Si $-2.0 \le Z < -1.0 \rightarrow$ `'Riesgo de desnutrición aguda'` *(categoría clave incorporada en la Res. 000115 de 2026)*
   * Si $-1.0 \le Z \le 1.0 \rightarrow$ `'Peso adecuado para la talla'`
   * Si $Z > 1.0 \rightarrow$ `'Sobrepeso / Obesidad'`

2. **Cálculo Automático de Próxima Cita (Frecuencia de Control):**
   A partir de la fecha del último control registrado (o la `fecha_primera_atencion` si aún no tiene controles periódicos) y su último `z_score`:
   * Si $Z < -2.0$ (DNT Severa o Moderada) $\rightarrow$ `fecha_ultimo_control + 7 días`.
   * Si $-2.0 \le Z < -1.0$ (Riesgo de DNT) $\rightarrow$ `fecha_ultimo_control + 15 días`.
   * Si $Z \ge -1.0$ (Peso adecuado) $\rightarrow$ `fecha_ultimo_control + 1 mes` (equivalente a `EDATE(..., 1)` en Excel).

3. **Control de Ventana Etaria ($0$ a $59$ meses):**
   * **Alerta de ingreso fuera de rango:** Si la edad en meses a la `fecha_notificacion` es $> 59$ meses.
   * **Alerta de egreso obligatorio por edad:** Si la edad actual en meses (`CURRENT_DATE` vs `fecha_nacimiento`) es $\ge 60$ meses y el `estado_caso` sigue activo (`'En seguimiento'`), marcar alerta `'Egreso por edad (>= 60 meses)'`.

### Vista SQL Clínica (`vw_estado_actual_casos`)
Esta vista reemplaza las columnas auxiliares `TY:VX` y alimenta en tiempo real tanto los listados operativos como los indicadores del `Dashboard`:

```sql
CREATE OR REPLACE VIEW vw_estado_actual_casos AS
WITH ultimo_control AS (
    SELECT DISTINCT ON (caso_id)
        caso_id,
        numero_seguimiento,
        fecha_control,
        peso_kg,
        talla_cm,
        perimetro_braquial_cm,
        z_score,
        tratamiento,
        sobres_ftlc_entregados,
        novedad_id
    FROM controles_seguimiento
    ORDER BY caso_id, numero_seguimiento DESC, fecha_control DESC
)
SELECT 
    c.caso_id,
    p.paciente_id,
    p.tipo_documento,
    p.numero_documento,
    CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido) AS nombre_completo,
    p.sexo,
    p.fecha_nacimiento,
    EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + 
    EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)) AS edad_meses_actual,
    m.nombre AS municipio,
    e.nombre AS eapb,
    s.nombre AS sede_ipsi,
    cu.nombre_completo AS cuidador,
    cu.telefono AS telefono_cuidador,
    c.fuente_notificacion,
    c.fecha_notificacion,
    c.estado_caso,
    COALESCE(uc.numero_seguimiento, 0) AS total_controles,
    COALESCE(uc.fecha_control, c.fecha_primera_atencion) AS fecha_ultima_atencion,
    COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) AS ultimo_zscore,
    CASE 
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < -3.0 THEN 'Desnutrición aguda severa'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < -2.0 THEN 'Desnutrición aguda moderada'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < -1.0 THEN 'Riesgo de desnutrición aguda'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) <= 1.0 THEN 'Peso adecuado para la talla'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) > 1.0 THEN 'Sobrepeso / Obesidad'
        ELSE 'Sin dato antropométrico'
    END AS clasificacion_nutricional_actual,
    CASE 
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < -2.0 
            THEN COALESCE(uc.fecha_control, c.fecha_primera_atencion) + INTERVAL '7 days'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < -1.0 
            THEN COALESCE(uc.fecha_control, c.fecha_primera_atencion) + INTERVAL '15 days'
        WHEN COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) IS NOT NULL 
            THEN COALESCE(uc.fecha_control, c.fecha_primera_atencion) + INTERVAL '1 month'
        ELSE NULL
    END::DATE AS fecha_proxima_cita
FROM notificaciones_caso c
JOIN pacientes p ON c.paciente_id = p.paciente_id
LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
LEFT JOIN cat_eapb e ON c.eapb_id = e.eapb_id
LEFT JOIN cat_sedes_ipsi s ON c.ips_primaria_id = s.sede_id
LEFT JOIN cuidadores cu ON p.cuidador_id = cu.cuidador_id
LEFT JOIN ultimo_control uc ON c.caso_id = uc.caso_id;
```

---

## 7. Requerimientos de Endpoints del Backend (API REST)

El backend debe exponer los siguientes módulos para replicar todas las funcionalidades del libro de Excel:

1. **Catálogos (`/api/catalogos`) — Reemplaza hoja `Listas`:**
   * `GET /api/catalogos/{tipo}` (`municipios`, `eapb`, `sedes`, `novedades`) para poblar selectores sin errores de digitación.
2. **Pacientes y Notificaciones (`/api/pacientes`, `/api/casos`) — Reemplaza `Notificados` y `Seguimientos Cerrados `:**
   * `GET /api/casos`: Listado paginado con filtros por `estado_caso`, `municipio_id`, `eapb_id`, `clasificacion_nutricional`, `citas_vencidas=true`, y búsqueda por `numero_documento` o nombre.
   * `POST /api/casos`: Crea o vincula un `paciente` existente (validando si ya existe por `numero_documento`) y abre un nuevo episodio `notificaciones_caso`.
   * `PATCH /api/casos/{caso_id}/cerrar`: Cierra el caso registrando `motivo_egreso` y `fecha_egreso`.
3. **Controles de Seguimiento (`/api/casos/{caso_id}/controles`) — Reemplaza `Casos en Seguimiento `:**
   * `GET /api/casos/{caso_id}/controles`: Retorna la línea de tiempo vertical ordenada cronológicamente (curva de evolución de peso, talla, PB y Z-Score).
   * `POST /api/casos/{caso_id}/controles`: Registra un nuevo control asignando automáticamente el `numero_seguimiento` consecutivo, calculando la clasificación nutricional y retornando la `fecha_proxima_cita` y alertas etarias si el niño cumplió $60$ meses.
4. **Dashboard e Indicadores Epidemiológicos (`/api/reportes`) — Reemplaza hojas `Dashboard` e `Indicadores Mensuales`:**
   * `GET /api/reportes/dashboard`: KPIs en vivo (total notificados, activos, cerrados, distribución por diagnóstico actual, citas vencidas hoy, alertas de edad $\ge 60$ meses, desglose por EAPB, municipio y sede).
   * `GET /api/reportes/indicadores-mensuales`: Matriz mensual por municipio agrupada por `fecha_notificacion` y `fecha_primera_atencion`.
   * `GET /api/reportes/exportar-excel`: Genera y descarga un archivo `.xlsx` limpio con los datos actualizados para entrega institucional a entes de control.

---

## 8. Instrucciones de Ejecución Paso a Paso para el Agente IA

Ejecuta las siguientes tareas en orden estricto:

1. **Inicializar estructura del proyecto:** Crear carpetas `/database`, `/etl`, y `/backend` junto con un archivo `.env.example` configurado para PostgreSQL local (`DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ipsi_nutricion`).
2. **Crear scripts SQL:** Guardar en `/database/01_schema.sql` y `/database/02_views.sql` las tablas, índices y la vista `vw_estado_actual_casos` definidas en las secciones 5 y 6.
3. **Desarrollar el script de migración ETL (`/etl/migrar_excel.py`):**
   * Leer el archivo Excel ubicado en la raíz o ruta configurada (`3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx`).
   * Poblar primero las tablas `cat_*` desde `'Listas'` y valores únicos encontrados.
   * Migrar `'Notificados'` hacia `cuidadores`, `pacientes` y `notificaciones_caso` aplicando las reglas de deduplicación y limpieza de `NULL` de la Sección 3.
   * Iterar sobre `'Casos en Seguimiento '` y `'Seguimientos Cerrados '` (respetando el espacio final en el nombre de ambas pestañas), despivotando los bloques horizontales `SEGUIMIENTO 1` a `SEGUIMIENTO 50` hacia filas individuales en `controles_seguimiento`, y actualizando el estado a `'Cerrado'` para los registros provenientes de `'Seguimientos Cerrados '`.
   * Imprimir al finalizar un reporte de auditoría en consola (total pacientes únicos migrados, total casos, total controles despivotados y registros omitidos/limpiados).
4. **Construir el Backend API:** Implementar los modelos ORM, esquemas de validación (Pydantic/Zod), reglas clínicas de la Resolución 000115 de 2026 y todos los endpoints descritos en la Sección 7.
5. **Validación:** Verificar que el servidor arranque correctamente y que la documentación Swagger (`/docs`) responda con todos los endpoints operativos.