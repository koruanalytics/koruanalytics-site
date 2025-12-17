from pathlib import Path
import duckdb

DB_PATH = Path("data/osint_dw.duckdb")
DB_PATH.parent.mkdir(exist_ok=True)  # crea carpeta data/ si no existe

print("=== Test DuckDB OSINT ===")
print(f"Ruta de la base de datos: {DB_PATH}")

# Conectamos (si no existe, la crea)
con = duckdb.connect(DB_PATH)

# Creamos una tabla de prueba
con.execute("""
    CREATE TABLE IF NOT EXISTS incidents_test AS
    SELECT 1 AS incident_id, 'Peru' AS country, 'test' AS incident_type
""")

# Leemos la tabla
result = con.execute("SELECT * FROM incidents_test").fetchdf()
con.close()

print("\nContenido de incidents_test:")
print(result)

print("\n✅ DuckDB está funcionando y guardando datos en data/osint_dw.duckdb")