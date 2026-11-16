from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
view_def = db.execute(text("SELECT definition FROM pg_views WHERE viewname = 'vw_estado_actual_casos'")).scalar()
print("VIEW DEF:\n", view_def)
db.close()
