-- ============================================================================
-- BASE DE DATOS: Sistema de Vigilancia y Seguimiento Nutricional
-- IPSI Kottushi Sao Ana>a
-- Vista Clínica: Estado Actual de Casos y Semáforo de Citas
-- Conforme a Resolución 000115 de 2026
-- ============================================================================

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
