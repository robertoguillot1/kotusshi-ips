from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine('postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion')

with engine.connect() as conn:
    print("Probando Query 1: SIVIGILA...")
    sql_sivigila = """
    SELECT 
        '113' AS cod_eve,
        nc.fecha_notificacion AS fec_not,
        EXTRACT(WEEK FROM nc.fecha_notificacion)::INT AS semana,
        EXTRACT(YEAR FROM nc.fecha_notificacion)::INT AS anio,
        p.tipo_documento AS tip_ide_,
        p.numero_documento AS num_ide_,
        p.primer_nombre AS pri_nom_,
        COALESCE(p.segundo_nombre, '') AS seg_nom_,
        p.primer_apellido AS pri_ape_,
        COALESCE(p.segundo_apellido, '') AS seg_ape_,
        p.sexo AS sexo_,
        p.fecha_nacimiento AS fec_nac_,
        FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)))::INT AS edad_meses,
        m.nombre AS municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_vereda,
        e.nombre AS eapb,
        COALESCE(v.clasificacion_nutricional_actual, 'Desnutrición Aguda') AS diagnostico_inicial,
        nc.estado_caso AS estado_actual,
        nc.fuente_notificacion AS fuente_captacion
    FROM notificaciones_caso nc
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN vw_estado_actual_casos v ON nc.caso_id = v.caso_id
    LIMIT 5;
    """
    df1 = pd.read_sql_query(text(sql_sivigila), conn)
    print("SIVIGILA OK:", len(df1), "filas")

    print("\nProbando Query 2: T-302...")
    sql_t302 = """
    SELECT 
        nc.caso_id,
        m.nombre AS municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_rancheria,
        COALESCE(cuid.nombre_completo, 'Sin Cuidador') AS nombre_cuidador,
        COALESCE(cuid.telefono, 'Sin Teléfono') AS telefono_contacto,
        p.tipo_documento,
        p.numero_documento,
        TRIM(CONCAT_WS(' ', p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido)) AS nombre_menor,
        p.sexo,
        p.fecha_nacimiento,
        FLOOR(EXTRACT(YEAR FROM age(CURRENT_DATE, p.fecha_nacimiento)) * 12 + EXTRACT(MONTH FROM age(CURRENT_DATE, p.fecha_nacimiento)))::INT AS edad_meses,
        e.nombre AS eapb,
        nc.fecha_notificacion,
        nc.peso_inicial_kg,
        nc.talla_inicial_cm,
        nc.zscore_inicial,
        COALESCE(v.clasificacion_nutricional_actual, 'Desnutrición Aguda') AS clasificacion_nutricional_inicial,
        nc.fecha_primera_atencion,
        v.fecha_ultima_atencion,
        v.clasificacion_nutricional_actual,
        nc.sobres_ftlc_inicial AS formula_terapeutica_sobres,
        nc.estado_caso,
        COALESCE(nc.observaciones, 'Seguimiento por Equipo Extramural GBAI') AS conducta
    FROM notificaciones_caso nc
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cat_municipios m ON p.municipio_id = m.municipio_id
    LEFT JOIN cat_eapb e ON nc.eapb_id = e.eapb_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    LEFT JOIN vw_estado_actual_casos v ON nc.caso_id = v.caso_id
    LIMIT 5;
    """
    df2 = pd.read_sql_query(text(sql_t302), conn)
    print("T-302 OK:", len(df2), "filas")

    print("\nProbando Query 3: Búsqueda Activa...")
    sql_gbai = """
    SELECT 
        v.caso_id,
        v.municipio,
        COALESCE(p.georreferenciacion, 'Comunidad Indígena') AS comunidad_rancheria,
        COALESCE(p.georreferenciacion, 'Sin Dato') AS georreferenciacion,
        COALESCE(cuid.nombre_completo, 'Sin Cuidador') AS nombre_cuidador,
        COALESCE(cuid.telefono, 'Sin Teléfono') AS telefono_cuidador,
        v.tipo_documento,
        v.numero_documento,
        v.nombre_completo AS nombre_menor,
        v.edad_meses_actual,
        v.eapb,
        v.clasificacion_nutricional_actual,
        v.fecha_ultima_atencion,
        v.fecha_proxima_cita,
        (CURRENT_DATE - v.fecha_proxima_cita) AS dias_vencido,
        CASE 
            WHEN (CURRENT_DATE - v.fecha_proxima_cita) >= 30 THEN 'CRÍTICA (>30 días)'
            ELSE 'ALTA (15-29 días)'
        END AS prioridad_rescate
    FROM vw_estado_actual_casos v
    JOIN notificaciones_caso nc ON v.caso_id = nc.caso_id
    JOIN pacientes p ON nc.paciente_id = p.paciente_id
    LEFT JOIN cuidadores cuid ON p.cuidador_id = cuid.cuidador_id
    WHERE v.estado_caso = 'En seguimiento' AND v.fecha_proxima_cita IS NOT NULL AND v.fecha_proxima_cita < (CURRENT_DATE - INTERVAL '15 days')
    LIMIT 5;
    """
    df3 = pd.read_sql_query(text(sql_gbai), conn)
    print("GBAI OK:", len(df3), "filas")
