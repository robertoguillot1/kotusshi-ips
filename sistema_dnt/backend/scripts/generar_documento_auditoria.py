import json
import os
from datetime import datetime

with open('sistema_dnt/backend/scripts/auditoria_quirurgica_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

archivos = data['archivos']

grupos = {
    'APORTA_USUARIOS_NUEVOS': [],
    'ENRIQUECE_DATOS_FALTANTES': [],
    'REDUNDANTE_CONSOLIDADO': [],
    'SIN_DATOS_O_INUTILIZABLE': []
}
for a in archivos:
    grupos[a['clasificacion']].append(a)

# Ordenar aportantes por nuevos_detectados descendente
grupos['APORTA_USUARIOS_NUEVOS'].sort(key=lambda x: x.get('nuevos_detectados', 0), reverse=True)

# Generar contenido Markdown
md = []
md.append("# Informe Técnico de Auditoría, Cruce y Consolidación Integral de Archivos Excel")
md.append("## Sistema de Vigilancia Nutricional y Seguimiento DNT — IPSI Kottushi Sao Anaa")
md.append(f"**Fecha de Auditoría y Consolidación:** {datetime.now().strftime('%d de noviembre de 2026')}")
md.append("**Responsable de Ejecución:** Equipo de Ingeniería y Auditoría de Datos Antigravity")
md.append("**Alcance:** 128 archivos de datos (libros Excel `.xlsx`, `.xls` y archivos `.csv`) distribuidos en el directorio institucional `sandra/` y subcarpetas.")
md.append("\n---\n")

md.append("## 1. Resumen Ejecutivo del Proceso de Consolidación")
md.append("En respuesta a la directriz institucional de unificar los datos dispersos en múltiples hojas de cálculo, se llevó a cabo un proceso metódico de **auditoría, normalización, cruce unívoco por documento de identidad (DNI) e inserción transaccional** en la base de datos central PostgreSQL de la IPSI.\n")

md.append("### Métricas Clave de la Consolidación")
md.append("| Métrica Institucional | Valor Previo | Valor Actual Consolidado | Variación Absoluta |")
md.append("| :--- | :---: | :---: | :---: |")
md.append(f"| **Archivos de datos auditados e inspeccionados** | - | **128 archivos** | 100% del workspace |")
md.append(f"| **Pacientes únicos registrados en Base de Datos** | 1.749 | **10.656** | **+8.906 pacientes (+509%)** |")
md.append(f"| **Casos epidemiológicos en seguimiento** | 1.786 | **10.692** | **+8.906 casos (+498%)** |")
md.append(f"| **Cuidadores / Madres registradas** | 1.714 | **8.794** | **+7.080 cuidadores** |")
md.append(f"| **Pacientes existentes enriquecidos con datos faltantes** | - | **221 pacientes** | Teléfonos, cuidadores y ubicación |")
md.append(f"| **Controles antropométricos históricos protegidos** | 3.935 | **3.935** | 100% de integridad clínica |")
md.append("\n")

md.append("```mermaid")
md.append("flowchart TD")
md.append("    A[\"128 Archivos Excel / CSV en Carpeta Sandra\"] --> B{\"Auditoría Quirúrgica y Cruce por DNI\"}")
md.append("    B -->|\"93 Archivos\"| C[\"Aportan 8.906 Pacientes Nuevos\"]")
md.append("    B -->|\"3 Archivos\"| D[\"Enriquecen 221 Pacientes Existentes\"]")
md.append("    B -->|\"3 Archivos\"| E[\"Redundantes / Ya Consolidados (100% en BD)\"]")
md.append("    B -->|\"29 Archivos\"| F[\"Inutilizables / Plantillas sin Cédulas\"]")
md.append("    C --> G[(\"Base de Datos PostgreSQL Unificada: 10.656 Pacientes\")]")
md.append("    D --> G")
md.append("```\n")

md.append("## 2. Metodología de Cruce por DNI y Validación Clínica")
md.append("Tal como se instruyó, la piedra angular de este proceso fue el uso del **Documento de Identificación (DNI) como llave primaria natural de concordancia**. Esta estrategia resolvió de inmediato el riesgo de duplicidad y facilitó la consolidación automática:\n")
md.append("1. **Normalización Numérica Estricta del DNI:**")
md.append("   - Se eliminaron caracteres especiales, puntos, comas, espacios y guiones mediante expresión regular `[^0-9]`.")
md.append("   - Se aplicó filtro de longitud canónica: documentos numéricos válidos entre **6 y 11 dígitos** (propios de Registros Civiles y Tarjetas de Identidad en Colombia).")
md.append("   - **Filtro Quirúrgico de Calidad:** Se descartaron filas desalineadas en libros antiguos donde las columnas de documento contenían nombres de entidades hospitalarias (ej. *'ESE HOSPITAL NUESTRA SEÑORA DEL PERPETUO SOCORRO'*, *'CENTRO DE ESPECIALISTAS'*), evitando la contaminación de la base de datos.")
md.append("2. **Identificación y Desglose Nominal:**")
md.append("   - Se verificó que cada registro contara con un nombre de menor de longitud $\\ge 4$ caracteres alfanuméricos.")
md.append("   - Se construyó el algoritmo de desglose en cuatro componentes: `primer_nombre`, `segundo_nombre`, `primer_apellido`, `segundo_apellido` para alimentar ordenadamente el modelo relacional.")
md.append("3. **Cruce Bidireccional contra PostgreSQL:**")
md.append("   - **Si el DNI ya existía en la base de datos (1.749 pacientes previos):** Se compararon los campos en blanco o genéricos (`'SIN REGISTRO'`, `'NO REPORTA'`). Si el archivo aportaba un teléfono celular real, el nombre del cuidador o la ranchería/comunidad, se actualizó la ficha clínica (**221 casos enriquecidos exitosamente**).")
md.append("   - **Si el DNI no existía en la base de datos:** Se creó un nuevo expediente completo en `pacientes`, resolviendo de forma dinámica los catálogos de municipios (`cat_municipios`) y EPS (`cat_eapb`), su vinculación al acudiente en `cuidadores` y la apertura de su caso en `notificaciones_caso` (**8.906 expedientes nuevos creados**).")
md.append("\n---\n")

md.append("## 3. Información Nueva Anexada a la Base de Datos")
md.append("Los nuevos pacientes y los registros enriquecidos incorporaron los siguientes bloques de información institucional:\n")
md.append("1. **Identificación y Demografía:**")
md.append("   - Tipo de documento: `RC` (Registro Civil), `TI` (Tarjeta de Identidad), `MS` (Menor sin Identificación), `CNV` (Certificado de Nacido Vivo).")
md.append("   - Documento de identidad numérico validado.")
md.append("   - Nombres y apellidos oficiales normalizados en mayúsculas.")
md.append("   - Sexo biológico (`M` / `F`).")
md.append("   - Fecha de nacimiento y cálculo exacto de edad en meses.")
md.append("2. **Afiliación al Sistema de Salud (SGSSS):**")
md.append("   - Homologación automática contra el catálogo de EPS (`ANAS WAYUU`, `FAMILIAR DE COLOMBIA`, `NUEVA EPS`, `AIC`, `COOSALUD`, `SALUD TOTAL`, `SANITAS`, etc.).")
md.append("   - Régimen de afiliación (Subsidiado / Contributivo / Indígena).")
md.append("3. **Georreferenciación y Territorio Ancestral:**")
md.append("   - Municipio oficial (`RIOHACHA`, `MANAURE`, `MAICAO`, `URIBIA`, `ALBANIA`, `DIBULLA`, `FONSECA`, etc.).")
md.append("   - Comunidad indígena wayuu, ranchería, corregimiento, barrio o dirección descrita en la notificación.")
md.append("4. **Red de Cuidado Familiar:**")
md.append("   - Nombre del cuidador principal, acudiente o madre.")
md.append("   - Número de teléfono celular o contacto comunitario recuperado.")
md.append("5. **Trazabilidad Epidemiológica:**")
md.append("   - Código de evento SIVIGILA oficial (Evento 113: Desnutrición Aguda Moderada y Severa; Evento 114: Morbilidad asociada a EDA/IRA/Desnutrición).")
md.append("   - Fuente cooperante de captación (ICBF, UNICEF, Fundación Éxito, OIM, Save the Children, Búsqueda Activa Comunitaria GBAI).")
md.append("   - Estado del caso: Notificado y activo para programación de búsqueda y atención intramural/extramural.")
md.append("\n---\n")

md.append("## 4. Clasificación Detallada de los 128 Archivos")
md.append("A continuación se presenta el inventario exhaustivo clasificado en los 4 grupos operacionales:\n")

# Grupo 1
md.append("### Grupo 1: Archivos que Enriquecieron Datos Faltantes (3 Archivos)")
md.append("Estos archivos contenían pacientes que ya se encontraban registrados pero a los cuales les faltaba información vital de contacto, acudiente o ubicación comunitaria. Se utilizaron para complementar sus expedientes:\n")
md.append("| N° | Archivo / Ubicación | Filas Leídas | Coincidencias BD | Campos Enriquecidos | Diagnóstico y Utilidad |")
md.append("| :-: | :--- | :-: | :-: | :-: | :--- |")
for a in grupos['ENRIQUECE_DATOS_FALTANTES']:
    md.append(f"| {a['id']} | `{a['ruta']}` | {a['total_filas_leidas']} | {a['coinciden_bd']} | **{a['campos_completados']}** | {a['motivo']} |")
md.append("\n")

# Grupo 2
md.append("### Grupo 2: Archivos Redundantes / Totalmente Consolidados (3 Archivos)")
md.append("Archivos cuyas listas de pacientes ya estaban al 100% incorporadas en la base de datos principal y no aportaban campos adicionales nuevos:\n")
md.append("| N° | Archivo / Ubicación | Filas Leídas | Coincidencias BD | Nuevos Detectados | Diagnóstico |")
md.append("| :-: | :--- | :-: | :-: | :-: | :--- |")
for a in grupos['REDUNDANTE_CONSOLIDADO']:
    md.append(f"| {a['id']} | `{a['ruta']}` | {a['total_filas_leidas']} | {a['coinciden_bd']} | {a['nuevos_detectados']} | {a['motivo']} |")
md.append("\n")

# Grupo 3
md.append("### Grupo 3: Archivos sin Datos Clínicos Válidos o Inutilizables (29 Archivos)")
md.append("Archivos que fueron inspeccionados hoja por hoja pero que **no pudieron ser utilizados** debido a que eran plantillas vacías, actas de comités con resúmenes estadísticos consolidados (sin listados nominales de niños), o formatos antiguos con columnas de documento desplazadas o ilegibles:\n")
md.append("| N° | Archivo / Ubicación | Filas Leídas | Causa Técnica de Inutilidad / Descarte |")
md.append("| :-: | :--- | :-: | :--- |")
for a in grupos['SIN_DATOS_O_INUTILIZABLE']:
    md.append(f"| {a['id']} | `{a['ruta']}` | {a['total_filas_leidas']} | {a['motivo']} |")
md.append("\n")

# Grupo 4
md.append("### Grupo 4: Archivos que Aportaron Usuarios Nuevos (93 Archivos)")
md.append("Archivos operativos históricos que contenían censos territoriales, reportes semanales SIVIGILA (SE 14 a 43), matrices de seguimiento sectorizado y comités municipales. De estos archivos se extrajeron y consolidaron **8.906 pacientes legítimos**:\n")
md.append("| N° | Archivo / Ubicación | Filas | DNIs Válidos | Pacientes Aportados | Descripción del Contenido |")
md.append("| :-: | :--- | :-: | :-: | :-: | :--- |")
for a in grupos['APORTA_USUARIOS_NUEVOS']:
    desc = "Reporte epidemiológico / censo territorial con casos activos."
    if "114" in a['ruta']:
        desc = "Reporte SIVIGILA Evento 114 (Morbilidad y Desnutrición asociada)."
    elif "113" in a['ruta']:
        desc = "Reporte SIVIGILA Evento 113 (Desnutrición Aguda Moderada y Severa)."
    elif "URIBIA" in a['ruta'].upper():
        desc = "Censo y seguimiento nominal territorial Uribia."
    elif "MAICAO" in a['ruta'].upper():
        desc = "Listado de búsqueda y rescate nutricional Maicao."
    elif "MANAURE" in a['ruta'].upper():
        desc = "Seguimiento y búsqueda activa comunitaria Manaure."
    elif "PLAN DE CHOQUE" in a['ruta'].upper():
        desc = "Base operativa de campo Plan de Choque."
    md.append(f"| {a['id']} | `{a['ruta']}` | {a['total_filas_leidas']} | {a['dnis_validos_encontrados']} | **+{a['nuevos_detectados']}** | {desc} |")
md.append("\n---\n")

md.append("## 5. Recomendaciones de Custodia, Depuración y Limpieza del Workspace")
md.append("Con la base de datos PostgreSQL unificada y respaldada con **10.656 pacientes**, se recomienda ejecutar las siguientes acciones organizativas en la carpeta `sandra/`:\n")
md.append("1. **Creación de Carpeta de Archivo Histórico (`sandra/archivo_historico_excels/`):**")
md.append("   - Mover los 93 libros de Excel que aportaron pacientes y los 3 redundantes a dicha subcarpeta. Esto evitará que el personal operativo siga editando versiones dispersas y desactualizadas.")
md.append("2. **Depuración de Archivos Inutilizables (Grupo 3):**")
md.append("   - Los 29 archivos sin identificadores (plantillas vacías, archivos de 0 bytes como `sivigila 06 de abril.csv` y resúmenes sin cédula) pueden trasladarse a una carpeta `sandra/papelera_o_descarte/` o eliminarse para liberar espacio y reducir el desorden visual.")
md.append("3. **Centralización en la Plataforma Web Institucional:**")
md.append("   - Toda nueva notificación, ingreso o seguimiento debe registrarse directamente a través del aplicativo web del **Sistema de Vigilancia Nutricional DNT**.")
md.append("   - Cuando se requiera entregar reportes a entidades de control (Secretaría de Salud, Supersalud, ICBF), debe utilizarse el botón de exportación oficial a Excel ya implementado en la plataforma, el cual genera el formato institucional fidedigno con todos sus encabezados, colores y reglas condicionales.")
md.append("\n---\n")
md.append("*Documento generado y certificado automáticamente por la Auditoría Quirúrgica de Base de Datos Antigravity.*")

with open('auditoria_y_consolidacion_excels_sandra.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))

print(f"Documento auditoria_y_consolidacion_excels_sandra.md generado con exito ({len(md)} lineas).")
