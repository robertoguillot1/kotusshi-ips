from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgrespassword@localhost:5432/ipsi_nutricion')
with engine.connect() as conn:
    for tname in ['pacientes', 'notificaciones_caso', 'vw_estado_actual_casos']:
        cols = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{tname}'
        """)).fetchall()
        print(f"Columnas de {tname}: {[c[0] for c in cols]}")
