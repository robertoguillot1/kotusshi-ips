# Sistema de Vigilancia y Seguimiento Nutricional (IPSI Kottushi Sao Anaa)
## Digitalización de la Ruta de Atención Integral DNT — Resolución 000115 de 2026

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.x-FF6384?style=flat&logo=chart.js&logoColor=white)](https://www.chartjs.org/)

---

## 1. Descripción del Proyecto

El **Sistema de Vigilancia y Seguimiento Nutricional** es una plataforma integral desarrollada para la **IPSI Kottushi Sao Anaa** (La Guajira, Colombia). Su objetivo es reemplazar la gestión manual basada en hojas de cálculo por una arquitectura transaccional moderna, escalable y auditable.

El sistema digitaliza y automatiza los instrumentos normativos oficiales:
- **FT-003 (PM-RIA-FT-003):** Notificación de casos, caracterización demográfica, georreferenciación en comunidades/rancherías y primera atención clínica.
- **FT-004 (PM-RIA-FT-004):** Seguimiento longitudinal y evolución nutricional periódica (hasta 50 controles).

### Eventos Epidemiológicos SIVIGILA Cubiertos:
* **Evento 113:** Desnutrición Aguda Moderada y Severa en menores de 0 a 59 meses.
* **Evento 114:** Riesgo de Desnutrición Aguda en menores de 0 a 59 meses.

---

## 2. Marco Normativo y Reglas Clínicas

El motor de reglas clínicas del backend implementa los lineamientos de la **Resolución 000115 de 2026** (actualización técnica de la Resolución 2350 de 2020 del Ministerio de Salud y Protección Social de Colombia):

1. **Clasificación Nutricional Automatizada según Puntaje Z (P/T):**
   * **Desnutrición Aguda Severa:** $Z < -3.0$ o presencia de edema bilateral.
   * **Desnutrición Aguda Moderada:** $-3.0 \le Z < -2.0$.
   * **Riesgo de Desnutrición Aguda:** $-2.0 \le Z < -1.0$.
   * **Peso Adecuado para la Talla:** $-1.0 \le Z \le +1.0$.
   * **Sobrepeso / Obesidad:** $Z > +1.0$ (con alertas asociadas).

2. **Calendarización Inteligente de Citas y Controles:**
   * **Casos con DNT Severa o Moderada:** Control obligatorio cada **7 días**.
   * **Casos con Riesgo de DNT:** Control obligatorio cada **15 días**.
   * **Casos con Estado Adecuado:** Control de mantenimiento cada **30 días**.

3. **Control Estricto de Ventana Etaria:**
   * Admisión clínica de **0 a 59 meses**.
   * Alerta automática de **egreso obligatorio por edad** al cumplir $\ge 60$ meses.

---

## 3. Arquitectura y Stack Tecnológico

```mermaid
flowchart LR
    A["Frontend SPA (HTML5 + Tailwind CSS + Chart.js)"] -->|"API REST JSON"| B["Backend (FastAPI + SQLAlchemy)"]
    B --> C[("PostgreSQL 15 Local / Docker")]
    B -.->|"Migración Futura"| D[("Supabase Cloud DB")]
    E["ETL & Pipeline de Migración (Python + OpenPyXL)"] --> C
```

* **Motor de Base de Datos:** PostgreSQL 15 (desplegable en local o vía Docker Compose), con compatibilidad total para migración a Supabase.
* **Backend:** Python 3.11+ con **FastAPI**, **SQLAlchemy** y validación de esquemas con **Pydantic**.
* **Frontend:** Single Page Application (SPA) responsiva construida con HTML5 semántico, Tailwind CSS y Chart.js, servida de manera autónoma directamente por FastAPI.
* **ETL & Procesamiento:** Scripts optimizados en Python con `openpyxl` y lectura matricial en memoria RAM para carga masiva y despivotado vertical.

---

## 4. Consolidación y Auditoría Masiva de Datos

Como parte del desarrollo, se realizó un proceso exhaustivo de auditoría e integración sobre **128 archivos de datos** (libros de Excel y CSV) distribuidos en la operación de la IPSI:

| Métrica del Repositorio | Estado Previo | Estado Consolidado |
| :--- | :---: | :---: |
| **Pacientes únicos registrados** | 1.749 | **10.656 (+509%)** |
| **Casos epidemiológicos en seguimiento** | 1.786 | **10.692 (+498%)** |
| **Cuidadores / Madres registrados** | 1.714 | **8.794** |
| **Pacientes enriquecidos (teléfono/ranchería/acudiente)** | - | **221 pacientes** |
| **Controles antropométricos históricos protegidos** | 3.935 | **3.935** |

*El proceso utilizó el **DNI normalizado (6 a 11 dígitos)** como llave natural única para deduplicar, resolver solapamientos y enriquecer expedientes incompletos sin colisiones.*

---

## 5. Estructura del Repositorio

```text
├── sistema_dnt/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py                   # Punto de entrada FastAPI y montaje de rutas
│   │   │   ├── config.py                 # Variables de entorno y configuración
│   │   │   ├── database.py               # Motor de conexión SQLAlchemy
│   │   │   ├── models.py                 # Modelos ORM relacionales
│   │   │   ├── schemas.py                # Esquemas Pydantic de entrada/salida
│   │   │   ├── services.py               # Lógica de negocio clínico (Z-score, citas, semáforos)
│   │   │   ├── services_importacion.py   # Servicio de parseo e importación masiva
│   │   │   ├── reporte_expediente.py     # Generación de reportes y consolidados
│   │   │   └── routers/                  # Endpoints REST (casos, controles, catalogos, reportes)
│   │   └── scripts/                      # Herramientas de auditoría, cruce y extracción quirúrgica
│   ├── database/
│   │   ├── 01_schema.sql                 # Esquema relacional DDL (tablas, FK, índices)
│   │   └── 02_views.sql                  # Vistas analíticas y consolidados clínicos
│   ├── etl/
│   │   └── migrar_excel.py               # Pipeline ETL de alto rendimiento (Excel -> PostgreSQL)
│   ├── frontend/
│   │   ├── index.html                    # Interfaz gráfica SPA de usuario
│   │   ├── css/styles.css                # Estilos visuales personalizados
│   │   └── js/app.js                     # Controlador JavaScript reactivo y gráficos
│   └── docker-compose.yml                # Configuración de contenedor PostgreSQL
├── auditoria_y_consolidacion_excels_sandra.md # Informe técnico del cruce de 128 archivos
├── bitacora_mejoras_y_etapas.md          # Registro pormenorizado de mejoras y desarrollo
├── especificacion_tecnica_backend_y_bd_ipsi.md # Especificación arquitectónica original
├── .gitignore                            # Exclusión de hojas de cálculo y credenciales
└── README.md                             # Documentación general del proyecto
```

---

## 6. Guía de Instalación y Puesta en Marcha

### Prerrequisitos
* **Python 3.11+**
* **Docker** y **Docker Compose** (opcional, si se desea levantar PostgreSQL en contenedor) o una instancia local de **PostgreSQL 15+**.

### Paso 1: Configurar Variables de Entorno
En la raíz de `sistema_dnt/`, crea o ajusta tu archivo `.env` tomando como base `.env.example`:
```env
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True
```

### Paso 2: Levantar la Base de Datos
Si utilizas Docker:
```bash
cd sistema_dnt
docker-compose up -d
```
Luego aplica el esquema inicial y las vistas SQL:
```bash
psql -h localhost -U postgres -d ipsi_nutricion -f database/01_schema.sql
psql -h localhost -U postgres -d ipsi_nutricion -f database/02_views.sql
```

### Paso 3: Instalar Dependencias de Python
```bash
cd backend
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic openpyxl pandas python-dotenv
```

### Paso 4: Iniciar el Servidor de Aplicación
Desde `sistema_dnt/backend`:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Paso 5: Acceder a la Plataforma
* **Aplicación Web (Frontend SPA):** `http://localhost:8000/`
* **Documentación Interactiva Swagger / OpenAPI:** `http://localhost:8000/docs`
* **Especificación ReDoc:** `http://localhost:8000/redoc`

---

## 7. Módulos y Funcionalidades del Sistema

1. **Tablero de Control (Dashboard Epidemiológico):**
   * Indicadores clave (KPIs) en tiempo real: casos activos, niños recuperados, alertas de citas vencidas y egresos por edad.
   * Gráficos interactivos de distribución por estado nutricional, municipio y aseguradora (EAPB).

2. **Gestión de Casos en Vivo:**
   * Semáforo de alerta clínica normativo (rojo: desnutrición severa, naranja: desnutrición moderada, amarillo: riesgo, verde: adecuado).
   * Buscador dinámico por número de documento o nombres.
   * Filtros combinados por estado del caso, municipio y EPS.

3. **Expediente Clínico Longitudinal:**
   * Resumen demográfico del paciente, datos del acudiente y georreferenciación.
   * **Timeline cronológico interactivo:** Hitos de atención (`Captación -> Búsqueda Activa (GBAI) -> Primera Atención -> Controles 1..N -> Egreso`).
   * **Curva Antropométrica:** Gráfico en tiempo real de la evolución del Puntaje Z y Peso corporal a lo largo del tiempo.
   * **Ficha de Detalle de Hito:** Modal con antropometría, cálculo de variaciones ($\Delta$ peso y $\Delta$ Z-Score), prueba de apetito, fórmula terapéutica (FTLC) entregada y notas clínicas.

4. **Registro de Notificaciones (FT-003):**
   * Formulario guiado para el ingreso de nuevos menores al programa con validaciones de campos requeridos.

5. **Registro Rápido de Controles (FT-004):**
   * Modal de captura en un solo clic que clasifica automáticamente el estado nutricional y calcula la fecha de la próxima cita.

6. **Exportación e Interoperabilidad:**
   * Generación y descarga en vivo de reportes e indicadores consolidados en formato estructurado para auditorías y entes de control territorial.

---

## 8. Seguridad y Manejo de Datos

* **Protección de Datos Sensibles:** Los archivos Excel con información clínica de pacientes están estrictamente excluidos del repositorio mediante el archivo [`.gitignore`](.gitignore).
* **Auditoría e Integridad:** Todas las operaciones sobre casos y controles respetan integridad referencial con claves foráneas, borrado en cascada protegido e indexación sobre números de documento y fechas de atención.

---

## 9. Licencia y Créditos

Desarrollado para la **IPSI Kottushi Sao Anaa** en el marco del fortalecimiento institucional y la optimización de la Ruta de Atención Integral para la Nutrición Infantil en La Guajira, Colombia.
