import psycopg2

conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/ipsi_nutricion')
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'controles'")
print("CONTROLES:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'casos'")
print("CASOS:", [r[0] for r in cur.fetchall()])
conn.close()
