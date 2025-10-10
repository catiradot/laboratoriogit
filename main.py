import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "dwlab")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")

engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Crear tabla si no existe
ddl = """
CREATE TABLE IF NOT EXISTS ventas (
    ventaid INT PRIMARY KEY,
    cliente VARCHAR(100),
    producto VARCHAR(100),
    categoria VARCHAR(100),
    preciounitario DECIMAL(12,2),
    unidades INT,
    fecha DATE
)
"""
with engine.begin() as conn:
    conn.execute(text(ddl))
print("Conectado y tabla ventas lista.")

df = pd.read_csv("ventas.csv")
df["preciounitario"] = pd.to_numeric(df["preciounitario"], errors="coerce")
df["unidades"] = pd.to_numeric(df["unidades"], errors="coerce")
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE ventas"))
    df.to_sql("ventas", con=engine, if_exists="append", index=False, method="multi", chunksize=1000)
print(f"Carga inicial completada. Registros: {len(df)}")

dfinc = pd.read_csv("ventasincrementales.csv")
dfinc["preciounitario"] = pd.to_numeric(dfinc["preciounitario"], errors="coerce")
dfinc["unidades"] = pd.to_numeric(dfinc["unidades"], errors="coerce")
dfinc["fecha"] = pd.to_datetime(dfinc["fecha"], errors="coerce").dt.date

records = dfinc.to_dict(orient="records")
upsert_sql = text("""
INSERT INTO ventas (ventaid, cliente, producto, categoria, preciounitario, unidades, fecha)
VALUES (:ventaid, :cliente, :producto, :categoria, :preciounitario, :unidades, :fecha)
ON DUPLICATE KEY UPDATE
    cliente=VALUES(cliente),
    producto=VALUES(producto),
    categoria=VALUES(categoria),
    preciounitario=VALUES(preciounitario),
    unidades=VALUES(unidades),
    fecha=VALUES(fecha)
""")
batch = 1000
with engine.begin() as conn:
    for i in range(0, len(records), batch):
        conn.execute(upsert_sql, records[i:i+batch])
print(f"UPSERT aplicado. Filas procesadas: {len(dfinc)}")
