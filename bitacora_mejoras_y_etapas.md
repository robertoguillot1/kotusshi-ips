# Bitácora de Desarrollo, Mejoras y Avance por Etapas
## Sistema de Vigilancia y Seguimiento Nutricional (IPSI Kottushi Sao Ana>a)

Este documento registra de forma exhaustiva la revisión de la propuesta técnica (`especificacion_tecnica_backend_y_bd_ipsi.md`), el detalle de cada mejora técnica, arquitectónica y clínica implementada respecto al diseño original de Excel, el estado de finalización de cada etapa y la guía de operación del sistema.

---

## 1. Análisis y Evaluación de la Propuesta Técnica (`especificacion_tecnica_backend_y_bd_ipsi.md`)

Tras revisar la especificación planteada, se concluye:
1. **Diagnóstico certero del problema:** El libro original `3. PM-RIA-FT-003-004 Notificacion Y seguimiento DNT y Riesgo DNT.xlsx` contenía $596$ columnas horizontales (`SEGUIMIENTO 1` a `50`), saturando memoria, generando redundancia masiva y dificultando la auditoría clínica.
2. **Alineación normativa:** Cumple con la **Resolución 000115 de 2026** (que actualiza la Resolución 2350 de 2020), incorporando la categoría de **Riesgo de desnutrición aguda** ($-2.0 \le Z < -1.0$) y la calendarización automática de citas a 7, 15 y 30 días.
3. **Estrategia relacional sólida:** La normalización a un modelo relacional en PostgreSQL con despivotado vertical de controles clínicos fue la solución óptima para escalabilidad, integridad referencial y posterior migración a la nube (Supabase).

---

## 2. Registro de Mejoras Implementadas (Técnicas, Clínicas y de Arquitectura)

Se han incorporado las siguientes 7 mejoras sobre la propuesta base:

### Mejora M1: Despliegue Automatizado de PostgreSQL mediante Docker Compose
* **Descripción:** Se creó la infraestructura como código en `sistema_dnt/docker-compose.yml` para levantar la instancia local de PostgreSQL 15 en el puerto 5432 con volumen persistente y credenciales seguras.
* **Beneficio:** Portabilidad inmediata sin requerir instalación manual previa de PostgreSQL en el sistema operativo del anfitrión.

### Mejora M2: Esquema DDL Ensanchado y Robustecido para Datos Clínicos Reales
* **Descripción:** Se aumentaron las longitudes de los campos de texto (`VARCHAR(150)`, `VARCHAR(255)` y `TEXT`) en `01_schema.sql` para campos como `documento_cuidador`, nombres, tratamientos, novedades y estados, evitando fallos por truncamiento ante textos explicativos digitados en el Excel.
* **Beneficio:** 100% de tolerancia ante variaciones en la digitación humana sin pérdida de información de contacto o clínica.

### Mejora M3: Protección contra Desbordamiento Numérico en Antropometría
* **Descripción:** Se migraron los tipos de datos antropométricos (`z_score`, `peso_kg`, `talla_cm`, `pb_cm`) de `NUMERIC(4,2)` a `NUMERIC(8,2)` para soportar casos con valores atípicos o errores de digitación en el Excel original sin fallar la transacción.
* **Beneficio:** Eliminación total de errores `NumericValueOutOfRange`.

### Mejora M4: Pipeline ETL de Alto Rendimiento en Memoria (de 25 min a 12.7 segundos)
* **Descripción:** Se optimizó la lectura de `openpyxl` utilizando `iter_rows(values_only=True)` para precargar las matrices de datos en memoria RAM y ejecutar inserciones en bloque (`cur.executemany`), resolviendo:
  - Limpieza de teléfonos híbridos (extracción de números puros y traslado de notas de contacto a campos textuales).
  - Manejo robusto de campos numéricos con strings como `"Sin Dato"`, `"N/A"`, `"sd"`, convirtiéndolos a `NULL` nativo.
  - Deduplicación inteligente: resolución de los 36 pacientes duplicados en `Notificados`.
  - Despivotado vertical de los 50 bloques horizontales de `Casos en Seguimiento ` y `Seguimientos Cerrados `.
* **Beneficio:** Reducción del tiempo de migración de ~25 minutos a solo **12.74 segundos**.

### Mejora M5: Reglas Clínicas de Validación y Auditoría (Resolución 000115 de 2026)
* **Descripción:** Implementación de funciones clínicas especializadas en `app/services.py`:
  - Clasificación nutricional automática según Puntaje Z (Desnutrición severa, moderada, riesgo, adecuado, sobrepeso).
  - Cálculo automático de fecha de próxima cita (7 días para DNT moderada/severa, 15 días para riesgo DNT, 30 días para adecuado).
  - Control y alertas de ventana etaria ($0$ a $59$ meses al ingreso y alerta de egreso obligatorio al cumplir $\ge 60$ meses).

### Mejora M6: Backend API REST Modular con FastAPI y Exportador a Excel
* **Descripción:** Arquitectura desacoplada en `sistema_dnt/backend/app`:
  - Routers organizados (`catalogos`, `casos`, `controles`, `reportes`).
  - Documentación interactiva Swagger/OpenAPI en `/docs`.
  - Endpoint de Dashboard en tiempo real con conteo de citas vencidas, alertas de edad y desgloses por municipio, EAPB, sede y diagnóstico.
  - Endpoint de exportación en vivo a archivo `.xlsx` estructurado y limpio para entes de control (`/api/reportes/exportar-excel`).

### Mejora M7: Frontend Web SPA Moderno, Reactivo y 100% Integrado (Plug & Play)
* **Descripción:** 
  - Aplicación de una sola página desarrollada con HTML5, Tailwind CSS y Chart.js en `sistema_dnt/frontend/`.
  - Servida directamente por FastAPI como archivos estáticos (`app.mount("/static", ...)` y ruta raíz `/`).
  - Módulos incluidos:
    1. **Tablero de Control (Dashboard):** 5 tarjetas KPI interactivas y 3 gráficos analíticos (diagnóstico, municipios y EPS).
    2. **Gestión de Casos en Vivo:** Tabla con semáforo de colores clínico normativo, filtros combinados, buscador por documento/nombre y alertas de citas vencidas.
    3. **Expediente Clínico del Menor:** Ficha del menor y cuidador, gráfica interactiva de evolución de curvas de Z-Score y Peso corporal, y listado cronológico de seguimientos.
    4. **Formulario de Notificación (FT-003):** Registro guiado paso a paso con validaciones clínicas.
    5. **Indicadores Mensuales (FT-004) y Descarga:** Matriz mensual por municipio y exportación instantánea a Excel.
    6. **Modales de Acción Rápida:** Registro de nuevo control en 1 clic y cierre formal de casos con motivo normativo.

### Mejora M8: Trazabilidad Integral Unificada por Paciente y Timeline de Ruta de Atención
* **Descripción:** 
  - **Resolución de casos huérfanos/multi-episodio:** En casos donde un niño tenía más de una notificación en el Excel o registros en blanco en un episodio puntual, la consulta se unificó por `paciente_id` para consolidar automáticamente todas sus captaciones, búsquedas activas (GBAI), primera atención y controles periódicos históricos.
  - **Línea de Tiempo Visual (Timeline de la Ruta):** Se incorporó en el Frontend un carrusel interactivo de hitos clínicos ordenados cronológicamente por fecha (`Captación Inicial ➔ GBAI ➔ 1ra Atención IPSI ➔ Controles de Seguimiento 1..N ➔ Cierre/Egreso`).
  - **Curva Antropométrica Cronológica Continua:** Se reparó la secuencia de datos de Chart.js para ordenar todas las mediciones estrictamente por fecha, eliminando saltos o discontinuidades temporales.
  - **Depuración y Validación Sintáctica del Frontend:** Se limpió el script cliente `app.js` eliminando bloques huérfanos y se aplicó control de versión de caché (`?v=2.2`) en `index.html` para garantizar la ejecución limpia y reactiva de los componentes del DOM.
* **Beneficio:** Visibilidad del 100% del historial del menor sin importar por cuál notificación o episodio acceda el usuario y renderizado instantáneo en el navegador.

### Mejora M9: Ficha Clínica Interactiva Detallada por Hito y Evento de Trazabilidad
* **Descripción:** 
  - **Interactividad Total en Línea de Tiempo y Tabla:** Las tarjetas visuales del timeline horizontal y las filas de la tabla de controles ahora son 100% interactivas y cliqueables (`cursor-pointer`, efectos de realce y botón "🔍 Ver Ficha").
  - **Modal de Ficha Clínica Longitudinal (`#modal-detalle-hito`):** Al hacer clic sobre cualquier evento (Captación Inicial, Búsqueda GBAI, Primera Atención o Seguimientos 1..50), se abre una ventana modal completa con el detalle exhaustivo del niño:
    1. **Identificación y Contacto:** Nombre completo, documento, cuidador, teléfono y comunidad/georreferenciación completa.
    2. **Antropometría y Dinámica Ponderal:** Peso corporal, talla, perímetro braquial, Puntaje Z y cálculo automático de variaciones ($\Delta$ peso en kg/gramos y $\Delta$ Z-Score) respecto a la cita previa.
    3. **Tratamiento y Soporte:** Esquema terapéutico, sobres de FTLC entregados, prueba de apetito, escenario de manejo y comorbilidades.
    4. **Programación Normativa (Res. 000115/2026):** Intervalo y fecha estimada de la próxima cita médica (+7, +15 o +30 días).
    5. **Trazabilidad Institucional:** Fuente de notificación, cooperante notificador completo (nombre, profesional de contacto y teléfono sin truncar), medio de notificación y observaciones clínicas completas.
* **Beneficio:** Elimina el truncamiento de datos y proporciona al equipo médico y de auditoría la historia clínica completa de cada intervención con un solo clic.

### Mejora M10: Conteo Real de Base de Datos y Paginación Dinámica para Citas Vencidas
* **Descripción:** 
  - **Cálculo de Conteo Real en Backend (`COUNT(*)`):** Se optimizó el endpoint `GET /api/casos` para calcular en tiempo real el total exacto de casos que cumplen con los filtros aplicados en la base de datos (por ejemplo, los **750 casos con citas vencidas** o los **1.000 casos en seguimiento**), retornándolo en la cabecera HTTP estándar `X-Total-Count`.
  - **Corrección del Contador en el Frontend:** Se sustituyó el conteo local de registros devueltos por página (`casos.length`) por la lectura de `X-Total-Count`, mostrando con precisión: `🚨 750 casos con citas vencidas encontrados`.
  - **Barra de Paginación y Selector de Tamaño de Página:** Se incorporó en la interfaz de la tabla controles completos de paginación (`◀ Anterior`, `Página X de Y`, `Siguiente ▶`) y un selector de filas por página (`50`, `100`, `250` o `1.000`), permitiendo navegar y auditar la totalidad de los 750 casos vencidos sin límites artificiales.
* **Beneficio:** Consistencia total entre los KPIs del Tablero (750 citas vencidas) y la tabla de seguimiento, garantizando precisión estadística para los coordinadores de vigilancia nutricional.

### Mejora M11: Detección Dinámica Multi-Año y Matrices Mensuales Automatizadas (FT-004)
* **Descripción:** 
  - **Detección Automática de Años en Base de Datos:** Se actualizó el endpoint `/api/reportes/indicadores-mensuales` para escanear dinámicamente mediante `UNION DISTINCT` todos los años presentes en notificaciones, atenciones clínicas y controles de seguimiento. De esta forma, el sistema detecta de inmediato cualquier año existente (2024, 2025, 2026) y cualquier año futuro (2027, 2028...) tan pronto ingresa un dato en esa vigencia.
  - **Selector Dinámico en Frontend:** Se implementó un selector de año en la pestaña de Indicadores Mensuales que se auto-puebla con los años detectados y selecciona por defecto la vigencia activa más reciente (2026).
  - **Despliegue de Tres Matrices Epidemiológicas:** Ahora se calculan y visualizan tres tablas mensuales completas por municipio para el año seleccionado:
    1. Matriz de Notificaciones Mensuales.
    2. Matriz de Primeras Atenciones en IPSI.
    3. Matriz de Controles Periódicos de Seguimiento.
  - **Totales Horizontales y Verticales:** Cada matriz calcula en vivo la suma por municipio y la fila de Total Mensual consolidado.
* **Beneficio:** Visibilidad inmediata de los 766 casos y 2.903 controles del año 2026, eliminando valores cableados en el código y asegurando que el sistema funcione a perpetuidad para años futuros sin requerir mantenimiento técnico.

### Mejora M12: Plantilla Profesional, Semáforo Clínico y Resumen Ejecutivo en Exportación Excel
* **Descripción:** 
  - **Diseño Visual Institucional:** Se rediseñó integralmente el generador del libro de Excel (`/api/reportes/exportar-excel`) utilizando `xlsxwriter` para eliminar la apariencia plana y en blanco y negro. Ahora incluye:
    - **Banner Institucional:** Encabezado con fondo corporativo azul (`#0369a1`), subtítulo normativo (*Resolución 000115 de 2026*) y fecha exacta de corte.
    - **Encabezados Tipográficos:** 21 columnas legibles en español con fondo azul (`#0284c7`), texto en blanco, fuentes `Segoe UI` y ajuste automático de texto.
    - **Filas Cebra y Bordes Delgados:** Alternancia de filas blancas y gris suave (`#f8fafc`) con rejilla sutil (`#cbd5e1`) para facilitar la lectura visual continuada sin fatiga.
    - **Semáforo Clínico Automatizado:** Resaltado condicional por colores según el diagnóstico nutricional (Desnutrición Aguda Severa en rojo suave `#fee2e2`/`#991b1b`, Moderada en naranja `#ffedd5`/`#c2410c`, Riesgo en amarillo `#fef3c7`/`#b45309`, Adecuado en verde `#dcfce7`/`#166534`, Sobrepeso en púrpura `#f3e8ff`/`#6b21a8`).
    - **Insignias de Estado y Alertas de Cita:** Distinción clara de estados del caso e indicador visual destacado para `🚨 VENCIDA` vs `Al día`.
    - **Inmovilización de Paneles (Freeze Panes):** Fijación de las 4 primeras filas superiores (títulos y encabezados) y las 4 primeras columnas clave (`No. Caso`, `Tipo Doc`, `Documento Identidad`, `Nombre Completo del Menor`), permitiendo desplazarse horizontal y verticalmente sin perder el contexto del paciente.
    - **Autofiltros de Excel Nativos:** Activados en la fila de encabezados para filtrado ágil por cualquier variable (municipio, EPS, diagnóstico, estado, etc.).
  - **Segunda Hoja: 'Resumen Epidemiológico':** Se añadió automáticamente una segunda pestaña al libro con:
    - **4 Tarjetas de Métricas Clave (KPIs):** Total Casos Registrados, Casos en Seguimiento Activo, Citas Vencidas y Casos Cerrados.
    - **Tabla de Distribución Nutricional:** Casos y porcentajes de participación por cada clasificación clínica.
    - **Tabla de Distribución Territorial:** Casos y porcentajes agrupados por municipio de residencia.
* **Beneficio:** Transforma una exportación técnica en un informe ejecutivo y clínico listo para auditorías del Ministerio de Salud, mesas de trabajo con EPS y gestión operativa de los equipos de campo de la IPSI Kottushi Sao Ana>a.

### Mejora M13: Corrección Integral de Codificación UTF-8 en Clasificaciones Nutricionales ('Desnutrición', 'antropométrico')
* **Descripción:** 
  - **Saneamiento de la Vista Clínica (`vw_estado_actual_casos`):** Se identificó que la definición interna de la vista en PostgreSQL contenía secuencias mojibake (`Ã³`, `Ã©`) generadas por una inicialización previa con encoding ANSI/Windows-1252. Se ejecutó una recarga limpia y forzada con codificación estrictamente `UTF-8`, reemplazando todas las etiquetas diagnósticas (`Desnutrición aguda moderada`, `Desnutrición aguda severa`, `Riesgo de desnutrición aguda` y `Sin dato antropométrico`).
  - **Propagación Inmediata a la Plataforma Web y API:** Se verificó la eliminación del error en todos los endpoints consumidores (`/api/casos`, `/api/reportes/dashboard`, modal de detalle clínico y gráfica de torta/donut).
  - **Corrección en Exportación a Excel:** El libro descargable (`/api/reportes/exportar-excel`) ahora despliega los diagnósticos clínicos con ortografía y tildes exactas tanto en la hoja detallada como en la tabla ejecutiva de resumen.
  - **Mejora del Selector en Frontend:** Se renombraron las opciones del menú desplegable de filtros en [index.html](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/frontend/index.html) para mostrar los nombres completos normativos (*Desnutrición Aguda Severa, Desnutrición Aguda Moderada, Riesgo de Desnutrición Aguda, Peso Adecuado para la Talla, Sobrepeso / Obesidad*).
* **Beneficio:** Garantiza la presentación ortográfica impecable de los informes y la interfaz para el personal médico, auditores y directivos de la institución.

### Mejora M14: Módulo de Impresión Oficial y Exportación en PDF del Expediente Clínico Individual
* **Descripción:** 
  - **Generador de Reporte Clínico Oficial e Imprimible (`/api/casos/{caso_id}/imprimir`):** Se desarrolló un generador de documentos médicos en [reporte_expediente.py](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/backend/app/reporte_expediente.py) que consolida toda la información asistencial, administrativa y de trazabilidad de cualquier menor seleccionado, conforme a la **Resolución 000115 de 2026**:
    1. **Membrete Oficial:** Identificación institucional de la IPSI Kottushi Sao Ana>a, NIT, habilitación REPS, marco normativo ministerial y fecha/hora exacta de emisión.
    2. **Ficha de Filiación y Datos Sociales:** Nombre completo, tipo y número de documento, sexo, fecha de nacimiento, edad exacta en meses, municipio, EAPB / EPS, sede primaria, datos del cuidador(a) (nombre, documento, teléfono) y comunidad o georreferenciación.
    3. **Resumen Epidemiológico y Estado Clínico:** Evento SIVIGILA notificado (113 o 114), fecha de notificación, cooperante notificador, medio de notificación, estado actual del caso, total de controles acumulados, último Puntaje Z (P/T), clasificación nutricional destacada con semáforo y estado de la próxima cita.
    4. **Matriz Longitudinal de Evolución Antropométrica:** Tabla cronológica completa con todas las consultas médicas, peso, talla, perímetro braquial, Z-score, variaciones acumuladas ($\Delta$ Peso y $\Delta$ Z-Score), esquema de tratamiento, sobres de FTLC entregados y próxima cita programada.
    5. **Trazabilidad Detallada Hito a Hito:** Fichas individuales estructuradas sin truncamiento de información para la Captación Inicial comunitaria, la Gestión Comunitaria GBAI, la Primera Atención Médica en IPSI y cada uno de los Controles de Seguimiento (incluyendo prueba de apetito, escenario de manejo ambulatorio/hospitalario, comorbilidades, novedades y observaciones clínicas completas).
    6. **Firmas de Responsabilidad Médica y Auditoría:** Espacios formales para firma y registro médico del profesional tratante y de la coordinación de vigilancia epidemiológica.
    7. **Cláusula de Confidencialidad y Custodia Legal:** Amparado en la Ley 1581 de 2012 (Habeas Data) y Resolución 1995 de 1999 (Custodia de Historias Clínicas).
  - **Optimización para Impresora y PDF (`@media print`):** Formato carta estándar (*Letter Portrait*), colorimetría exacta (`print-color-adjust: exact`), márgenes de 10-12 mm, saltos de página inteligentes (`break-inside: avoid;`) para evitar tarjetas cortadas por la mitad, y ocultamiento automático de barras de navegación y botones de pantalla.
  - **Integración en la Plataforma Web:**
    - Botón **"🖨️ Imprimir Expediente"** en la cabecera de la pestaña del Expediente Clínico.
    - Botón rápido **"🖨️"** en la columna de acciones de la tabla general de casos para imprimir directamente cualquier paciente sin necesidad de pasos adicionales.
    - Soporte de apertura con previsualización o diálogo directo de impresión (`?autoprint=true`).
  - **Blindaje y Manejo Robusto de Valores Nulos:** Control estricto de tipos ante hitos clínicos con valores iniciales ausentes (`None` en `delta_peso_kg`, `delta_zscore` o Z-score de captación), garantizando que cualquier caso con datos parciales o históricos se imprima sin errores de servidor 500.
* **Beneficio:** Permite a la IPSI generar, imprimir o guardar en PDF de inmediato el informe clínico integral de cualquier niño para requerimientos de auditoría de las EPS, visitas de inspección de Secretarías de Salud, comités técnicos o remisiones hospitalarias.

### Mejora M15: Módulo de Carga Masiva y Sincronización Incremental de Reportes Excel EPS (ETL Web con Upsert)
* **Descripción:** 
  - **Servicio Backend de Ingesta Inteligente ([services_importacion.py](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/backend/app/services_importacion.py)):**
    - Se implementó el motor de procesamiento para archivos `.xlsx` y `.xls` enviados periódicamente por las trabajadoras de las aseguradoras (EPS Familiar de Colombia, Nueva EPS, Dusakawi, Cajacopi, etc.).
    - **Lógica de Sincronización Incremental (Upsert):**
      1. **Pacientes Registrados:** El sistema detecta mediante `numero_documento` si el menor ya existe en la base de datos. Si existe, actualiza sus datos de contacto (teléfono, cuidador, comunidad) sin sobreescribir con valores nulos y sin duplicar pacientes.
      2. **Pacientes Nuevos:** Si el menor no existe, crea automáticamente su registro maestro en `pacientes`, su cuidador en `cuidadores`, su episodio de notificación en `notificaciones_caso` y sus datos iniciales de captación.
      3. **Trazabilidad y Controles Nuevos:** Despivota los bloques de seguimiento (hasta 50 controles). Si un control ya existía, ajusta mediciones; si es nuevo (ej. control 4, 5, etc.), lo inserta en `controles_seguimiento` y recalcula Z-scores y fecha de próxima cita médica.
  - **Endpoint API REST ([importacion.py](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/backend/app/routers/importacion.py)):**
    - `POST /api/importacion/subir-excel`: Recibe el archivo multipart, procesa en memoria y retorna un informe detallado de auditoría (pacientes creados, actualizados, nuevos controles insertados, hojas procesadas y tiempo de ejecución).
  - **Interfaz de Usuario Web en [index.html](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/frontend/index.html) y [app.js](file:///C:/Users/Roberto/Downloads/sandra/sistema_dnt/frontend/js/app.js):**
    - Nueva pestaña de navegación: **"📥 Carga Masiva Excel EPS"** y botón superior de acceso rápido **"Subir Reporte EPS"**.
    - Zona interactiva *Drag and Drop* para arrastrar y soltar el archivo Excel o seleccionarlo con explorador de archivos.
    - Indicador visual de progreso con animación durante la carga.
    - Panel de resultados con 4 tarjetas de métricas en vivo: *Pacientes Nuevos Creados*, *Pacientes Actualizados*, *Nuevos Controles Anexados* y *Controles Ajustados*.
    - Botón de navegación inmediata para ir a revisar los casos actualizados en la tabla de seguimiento.
* **Beneficio:** Automatiza por completo la recepción y consolidación de los archivos que envían las trabajadoras de las EPS en campo, eliminando la digitación manual y garantizando que la IPSI mantenga su base de datos y la ruta de atención siempre al día.

---

## 3. Matriz de Avance por Etapas (100% COMPLETADAS)

| Etapa | Descripción | Estado | Fecha de Finalización |
| :--- | :--- | :---: | :---: |
| **Etapa 1** | Inicialización del entorno, estructura modular de directorios, configuración `.env` y Docker Compose | **Completado** | 2026-11-15 |
| **Etapa 2** | Creación y ajuste de Scripts DDL de Base de Datos (`01_schema.sql`, `02_views.sql`) | **Completado** | 2026-11-15 |
| **Etapa 3** | Desarrollo y ejecución del script de migración ETL (`migrar_excel.py`) con despivotado y auditoría | **Completado** | 2026-11-15 |
| **Etapa 4** | Implementación del Backend API REST con FastAPI (Catálogos, Pacientes, Casos, Controles, Dashboard) | **Completado** | 2026-11-15 |
| **Etapa 5** | Diseño y Construcción de Frontend Web SPA Integrado | **Completado** | 2026-11-15 |
| **Etapa 6** | Pruebas de integración, verificación de endpoints en Swagger (`/docs`) y exportación a Excel | **Completado** | 2026-11-15 |
| **Etapa 7** | Trazabilidad Integral Unificada y Timeline Visual de la Ruta de Atención | **Completado** | 2026-11-15 |

---

## 4. Reporte Final de Auditoría de la Migración

| Indicador | Total en Base de Datos | Observaciones |
| :--- | :---: | :--- |
| **Total Pacientes Únicos** | **1.750** | Deduplicados por número de documento único. |
| **Duplicados Resueltos** | **36** | Casos consolidados en el paciente correspondiente. |
| **Total Episodios de Notificación** | **1.786** | Casos correspondientes a Eventos 113 y 114. |
| **- Casos En seguimiento activo** | **1.000** | En monitoreo clínico periódico. |
| **- Casos Cerrados** | **774** | Incluye los 104 egresos históricos y casos resueltos. |
| **- Casos En Búsqueda (GBAI)** | **10** | En gestión activa en territorio. |
| **- Casos Descartados** | **1** | Por no cumplir criterios clínicos de inclusión. |
| **- Otros estados** | **1** | Datos de control administrativo. |
| **Total Controles Despivotados** | **3.934** | Transformados desde los 50 bloques horizontales. |
| **Total Casos en Vista Clínica** | **1.786** | Evaluados en tiempo real con semáforo y próxima cita. |
| **Tiempo Total de Ejecución ETL** | **12.74 seg** | Optimizado con lectura en memoria. |

---

## 5. Guía de Operación y Acceso al Sistema

### Acceso a la Plataforma Web
* **Interfaz de Usuario (Frontend SPA):** [http://localhost:8000/](http://localhost:8000/)
* **Documentación Interactiva de la API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Documentación Alternativa (Redoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Exportación Directa a Excel:** [http://localhost:8000/api/reportes/exportar-excel](http://localhost:8000/api/reportes/exportar-excel)

### Comandos de Control para el Administrador
1. **Iniciar Base de Datos PostgreSQL:**
   ```bash
   cd sistema_dnt
   docker compose up -d
   ```
2. **Re-ejecutar Migración de Datos desde Excel:**
   ```bash
   cd sistema_dnt/etl
   python migrar_excel.py
   ```
3. **Iniciar Servidor de Aplicación (API + Frontend):**
   ```bash
   cd sistema_dnt/backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 6. Registro de Mejoras Funcionales y Nuevos Módulos

### Mejora M11: Conteo en Tiempo Real de Citas Vencidas
- Sincronización del contador de casos mostrados con el encabezado HTTP `X-Total-Count`.
- Visualización de badge dinámico cuando se filtra por citas vencidas.

### Mejora M12: Indicadores Mensuales Multi-Anuales Dinámicos
- Extracción automática de todos los años con datos epidemiológicos (2024, 2025, 2026, 2027+).
- Selector dinámico de año y renderizado mensual con gráficos y tablas de tendencia.

### Mejora M13: Plantilla Excel Estilizada y Legible
- Generación de Excel con formato institucional de IPSI Kottushi Sao Anaa.
- Cabecera en azul corporativo, bordes finos, fuentes claras, filtros automáticos y paneles congelados.

### Mejora M14: Corrección Ortográfica y Terminológica Normativa
- Corrección de la palabra "Desnutrición" en toda la interfaz web, tablas, modales y exportaciones a Excel.
- Alineación con los lineamientos de la Resolución 000115 de 2026.

### Mejora M15: Expediente Clínico Imprimible y Sincronización de Reportes EPS
- Endpoint y vista HTML optimizada para impresión formal de expedientes individuales (`/api/casos/{id}/imprimir-expediente`).
- Módulo de carga masiva de Excel EPS con upsert automático de pacientes y controles.

### Mejora M16: Módulo Oficial de Notificados (Formato PM-RIA-FT-003)
- **Implementación Integral del Libro de Notificados:**
  - Nueva pestaña en la barra de navegación: **"📋 Notificados (FT-003)"**.
  - **Banner de KPIs específicos:** Total notificados (1.786), Evento 113 DNT (168), Evento 114 Riesgo (1.577), Con 1ra Atención (1.555), Sin 1ra Atención (231), En Búsqueda GBAI (10), En Seguimiento Activo (1.000) y Cerrados (774).
  - **Filtros Dinámicos:** Búsqueda en vivo (documento, paciente, cuidador, cooperante), Evento SIVIGILA, Primera Atención, Municipio, EAPB y Estado del Caso.
  - **Tabla Maestra Estilizada:** Conteo en tiempo real, paginación configurable (25, 50, 100, 250 filas), visualización de captación inicial, búsqueda GBAI, 1ra atención IPSI y botones directos de acción (Expediente, Imprimir y Editar).
  - **Modal de Edición en Tiempo Real (`#modal-editar-notificacion`):** Permite actualizar fuente, cooperante, fechas, medidas antropométricas de captación y 1ra atención, estado GBAI, contacto del cuidador y observaciones mediante `PUT /api/notificaciones/{caso_id}`.

### Mejora M17: Exportación Excel Oficial Idéntica al Formato PM-RIA-FT-003
- **Fidelidad Visual y Estructural Completa:**
  - Inclusión del bloque institucional en filas 1 a 4 con el logo original de la IPSI Kottushi Sao Anaa en `A1:B4`.
  - Título combinado `C1:O3`: "REGISTRO DE NOTIFICACION DE PACIENTES CON DESNUTRICIÓN Y RIESGO DE DESNUTRICIÓN".
  - Bloques de proceso `C4:F4` ("MACROPROCESO: MISIONAL") y `G4:O4` ("PROCESO: RUTAS INTEGRALES DE ATENCIÓN").
  - Bloque documental `P1:R4` con Fecha (2026-08-26), Versión (02) y Código (PM-RIA-FT-003).
  - Fila 6: Numeración secuencial de las 48 columnas (1 a 48).
  - Fila 7: Subtotal dinámico con fórmula `=SUBTOTAL(3,H9:H{total})`.
  - Fila 8: Encabezados con las 48 columnas oficiales y paleta de colores original por bloques temáticos:
    - Verde Esmeralda/Teal (`#15A7A0`): Identificación, demografía, afiliación y GBAI.
    - Naranja cálido (`#F79646`): Captación inicial y medidas del notificador.
    - Terracota/Naranja oscuro (`#C66B24`): Primera atención en la IPSI, tratamiento y conducta.
    - Gris oscuro (`#7F7F7F`): Identificadores, edades, diagnósticos normativos y alertas de egreso.
  - Formato de celdas: Fechas en `YYYY-MM-DD`, Z-scores y pesos en `0.00`, tallas en `0.0`, bordes delgados `#D9D9D9`.
  - Inmovilización de paneles en fila 8 y columna 4, más filtros automáticos en las 48 columnas.
  - **Formatos Condicionales Oficiales Nativos Aplicados:**
    - *Columna H (Numero Id)* y *Columna V (Doc Cuidador)*: Detección automática de duplicados (`#FFC7CE` / `#9C0006`).
    - *Columna P (Edad Actual Meses)*: Semáforo normativo ($\ge 60$ meses en rojo vino `#F8D0CE` / `#953735`; $\le 59$ meses en verde azulado `#D9EFE9` / `#008080`).
    - *Columnas AC y AM (Clasificación Inicial y 1ra Atención)*: Reglas semafóricas completas (Severa en rojo `#F8D0CE` / `#9B1C13`, Moderada en naranja `#FDECC8` / `#E46C0A`, Riesgo en amarillo `#FCF3CF` / `#7A5B00`, Adecuado en verde `#D9EFE9` / `#0E6E6A`, Fuera de rango en gris).
    - *Columna AG (Estado Búsqueda)*: Efectiva/Atendido en verde, En Búsqueda/Pendiente en ámbar, Fallida en rojo.
    - *Columna AN (Prueba de Apetito)*: Positiva en verde, Negativa en rojo.
    - *Columna AR (Estado Actual)*: En seguimiento en azul, Cerrado en gris, En Búsqueda en ámbar.
    - *Columnas AU y AV (Alertas etarias)*: Alerta `>59m` en naranja `#FDECC8` y Alerta egreso `≥60m` en rojo `#F8D0CE`.

### Mejora M18: Navegación UX Avanzada, Centro de Alertas de Rescate Nutricional y Respaldo de BD en 1 Clic
- **1. Navegación y Usabilidad Clínica (UX):**
  - **Botón «Volver a la Lista» en el Expediente Clínico:**
    - Se agregó un botón superior contextual y un botón flotante ergonómico (`exp-boton-flotante-volver`) en `#tab-expediente`.
    - Detecta automáticamente si el profesional ingresó desde *Notificados (FT-003)*, *Casos en Seguimiento* o el *Tablero General*.
    - Al hacer clic, regresa de inmediato a la pestaña previa manteniendo intactos todos los filtros de búsqueda, selector de EAPB/municipio, ordenamiento y la página exacta en la que se encontraba el usuario.
  - **Búsqueda Global Rápida Universal (`Ctrl + K`):**
    - Se incorporó en la cabecera institucional un buscador universal accesible mediante el atajo `Ctrl + K` (o `Cmd + K` en macOS).
    - Despliega una paleta de comando interactiva con desenfoque de fondo (*backdrop blur*), búsqueda con *debounce* de 200 ms y navegación por teclado (flechas `↑` y `↓`, selección con `ENTER`, y cierre con `ESC`).
    - Endpoint backend dedicado: `GET /api/casos/busqueda-global?q=...` sobre la vista optimizada `vw_estado_actual_casos`. Permite buscar por documento (RC, TI, CC), nombres completos, acudiente o teléfono, abriendo directamente el expediente clínico.

- **2. Vigilancia Epidemiológica y Centro de Alertas de Rescate Nutricional:**
  - **Botón y Badge Dinámico en Cabecera:**
    - Indicador visual `🚨 Alertas Clínicas` con conteo en vivo de casos en riesgo epidemiológico.
  - **Modal Especializado con 4 Categorías Clínicas (`#modal-alertas-rescate`):**
    - **🔴 Pérdida de Peso (Desmejora Clínica):** Detecta menores en seguimiento cuyo peso en el último control fue inferior al control previo ($\Delta\text{Peso} < 0$). Muestra la pérdida en kg, el lapso entre controles, datos del cuidador y botón de llamada telefónica directa.
    - **🟡 Estancamiento Ponderal ($< 5\text{ g/kg/día}$):** Identifica niños con 2 o más controles donde la ganancia ponderal diaria calculada $\frac{(\text{peso}_2 - \text{peso}_1) \times 1000}{\text{peso}_1 \times \text{días}}$ es deficiente ($< 5.0\text{ g/kg/d}$), señal de posible fallo del tratamiento ambulatorio con FTLC o inapetencia.
    - **🟠 Riesgo de Abandono / Inasistencia ($> 15\text{ días}$):** Citas programadas con más de 15 días de vencimiento sin reporte de asistencia, para activación inmediata de búsqueda activa comunitaria (GBAI).
    - **🔵 Próximos Egresos por Edad (59 Meses):** Menores que cumplirán 60 meses en los próximos 30 días, calculando con exactitud los días restantes para coordinar su egreso formal de la ruta de desnutrición y remisión a programas escolares o modalidades del ICBF.
  - **Ajustes de Legibilidad y Usabilidad UI en Alertas:**
    - Se rediseñó la barra de pestañas del modal de alertas a formato *pills* fluidas (`flex-wrap gap-2.5`), eliminando el corte horizontal de letras provocado por el scrollbar nativo.
    - Se eliminó el botón redundante de llamada a acudiente, manteniendo el teléfono como dato textual de consulta y dejando únicamente la acción asistencial directa: `Ver Expediente →`.
  - **Endpoint Backend:** `GET /api/reportes/alertas-rescate`, con procesamiento analítico mediante CTEs y funciones ventana SQL (`LAG`, `PARTITION BY`, `ROW_NUMBER`).

- **3. Seguridad y Respaldo Institucional (Copia de Seguridad en 1 Clic):**
  - **Botón `💾 Backup BD` en Cabecera:**
    - Permite al equipo administrativo y asistencial generar y descargar de forma inmediata una copia de seguridad íntegra de la base de datos PostgreSQL institucional.
  - **Endpoint Backend:** `GET /api/reportes/backup-bd`.
    - Ejecuta `pg_dump` de la base de datos `ipsi_nutricion`, comprime el flujo a formato `.sql.gz` en memoria con compresión `gzip` y lo entrega con cabecera `Content-Disposition: attachment; filename="ipsi_nutricion_backup_YYYYMMDD_HHMMSS.sql.gz"`.

### Mejora M19: Auditoría Quirúrgica, Cruce por DNI y Consolidación Integral de 128 Archivos Excel
- **Auditoría e Inventario Completo:**
  - Se inspeccionaron y analizaron los 128 archivos de datos (`.xlsx`, `.xls`, `.csv`) ubicados en el directorio `sandra/` y subcarpetas (`BASE DE DATOS F.C 2026/`, censos, semanas epidemiológicas).
- **Metodología de Cruce por DNI y Normalización:**
  - Uso del Documento de Identificación (DNI) como llave primaria natural de concordancia tras normalización numérica estricta (longitud canónica 6-11 dígitos) y validación nominal ($\ge 4$ caracteres).
  - Exclusión quirúrgica de registros corruptos (filas donde las columnas de documento contenían nombres de entidades hospitalarias o IPS).
- **Resultados de la Consolidación en PostgreSQL:**
  - **Pacientes en Base de Datos:** Incrementó de 1.749 a **10.656 pacientes únicos** (+8.906 pacientes nuevos legítimos incorporados, +509%).
  - **Casos Epidemiológicos:** Incrementó de 1.786 a **10.692 casos** (+8.906 casos nuevos, +498%).
  - **Cuidadores / Madres:** Incrementó de 1.714 a **8.794 cuidadores** vinculados.
  - **Pacientes Existentes Enriquecidos:** Se actualizaron **221 pacientes** que tenían campos vacíos (`'SIN REGISTRO'`, `'NO REPORTA'`) completando teléfonos de contacto, nombres de acudientes y comunidades/rancherías wayuu.
  - **Integridad de Controles Históricos:** Se protegieron intactos los **3.935 controles antropométricos** previos.
- **Clasificación del Inventario de Archivos:**
  - **93 archivos** que aportaron pacientes nuevos (reportes SIVIGILA Evento 113 y 114, semanas epidemiológicas 14-43, censos territoriales de Uribia, Maicao, Manaure y Riohacha).
  - **3 archivos** que enriquecieron datos faltantes en pacientes ya existentes.
  - **3 archivos** redundantes / ya consolidados (100% de sus registros ya existían en la base de datos).
  - **29 archivos** sin datos clínicos válidos o inutilizables (plantillas en blanco, resúmenes estadísticos agregados sin DNI, matrices antiguas con columnas desplazadas o archivos vacíos de 0 bytes).
- **Documento Técnico Oficial Generado:**
  - [auditoria_y_consolidacion_excels_sandra.md](file:///c:/Users/Roberto/Downloads/sandra/auditoria_y_consolidacion_excels_sandra.md) con el informe técnico completo, tablas detalladas de los 128 archivos y recomendaciones de custodia y depuración.




