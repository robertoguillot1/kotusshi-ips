from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
sql = """
CREATE OR REPLACE VIEW vw_estado_actual_casos AS
WITH ultimo_control AS (
     SELECT DISTINCT ON (controles_seguimiento.caso_id) controles_seguimiento.caso_id,
        controles_seguimiento.numero_seguimiento,
        controles_seguimiento.fecha_control,
        controles_seguimiento.peso_kg,
        controles_seguimiento.talla_cm,
        controles_seguimiento.perimetro_braquial_cm,
        controles_seguimiento.z_score,
        controles_seguimiento.tratamiento,
        controles_seguimiento.sobres_ftlc_entregados,
        controles_seguimiento.novedad_id
       FROM controles_seguimiento
      ORDER BY controles_seguimiento.caso_id, controles_seguimiento.numero_seguimiento DESC, controles_seguimiento.fecha_control DESC
    )
SELECT c.caso_id,
p.paciente_id,
p.tipo_documento,
p.numero_documento,
concat_ws(' '::text, p.primer_nombre, p.segundo_nombre, p.primer_apellido, p.segundo_apellido) AS nombre_completo,
p.sexo,
p.fecha_nacimiento,
((EXTRACT(year FROM age((CURRENT_DATE)::timestamp with time zone, (p.fecha_nacimiento)::timestamp with time zone)) * (12)::numeric) + EXTRACT(month FROM age((CURRENT_DATE)::timestamp with time zone, (p.fecha_nacimiento)::timestamp with time zone))) AS edad_meses_actual,
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
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < '-3.0'::numeric) THEN 'Desnutrición aguda severa'::text
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < '-2.0'::numeric) THEN 'Desnutrición aguda moderada'::text
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < '-1.0'::numeric) THEN 'Riesgo de desnutrición aguda'::text
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) <= 1.0) THEN 'Peso adecuado para la talla'::text
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) > 1.0) THEN 'Sobrepeso / Obesidad'::text
        ELSE 'Sin dato antropométrico'::text
    END AS clasificacion_nutricional_actual,
(
    CASE
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < '-2.0'::numeric) THEN (COALESCE(uc.fecha_control, c.fecha_primera_atencion) + '7 days'::interval)
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) < '-1.0'::numeric) THEN (COALESCE(uc.fecha_control, c.fecha_primera_atencion) + '15 days'::interval)
        WHEN (COALESCE(uc.z_score, c.zscore_atencion, c.zscore_inicial) IS NOT NULL) THEN (COALESCE(uc.fecha_control, c.fecha_primera_atencion) + '1 mon'::interval)
        ELSE NULL::timestamp without time zone
    END)::date AS fecha_proxima_cita,
c.asignacion_interna AS nutricionista_asignado
FROM ((((((notificaciones_caso c
 JOIN pacientes p ON ((c.paciente_id = p.paciente_id)))
 LEFT JOIN cat_municipios m ON ((p.municipio_id = m.municipio_id)))
 LEFT JOIN cat_eapb e ON ((c.eapb_id = e.eapb_id)))
 LEFT JOIN cat_sedes_ipsi s ON ((c.ips_primaria_id = s.sede_id)))
 LEFT JOIN cuidadores cu ON ((p.cuidador_id = cu.cuidador_id)))
 LEFT JOIN ultimo_control uc ON ((c.caso_id = uc.caso_id)));
"""
db.execute(text(sql))
db.commit()
print("VIEW UPDATED SUCCESSFULLY!")
db.close()
