libs = [
    # Core
    "pandas", "requests", "dotenv",
    # BBDD
    "duckdb", "sqlalchemy", "psycopg2",
    # NLP
    "spacy", "spacy_transformers", "transformers", "torch",
    # GEO
    "geopandas", "shapely", "pyproj", "rtree", "geopy",
    # Infra
    "prefect", "fastapi", "uvicorn", "streamlit",
    # Calidad
    "pytest", "pydantic", "loguru", "great_expectations",
]

print("=== Test de imports avanzados OSINT ===")
errores = []

for lib in libs:
    try:
        __import__(lib)
        print(f"[OK] {lib}")
    except Exception as e:
        print(f"[ERROR] {lib} -> {e}")
        errores.append((lib, e))

print("\nResumen:")
if errores:
    print("❌ Hay librerías con problemas:")
    for lib, e in errores:
        print(f" - {lib}: {e}")
else:
    print("✅ Todas las librerías se han importado correctamente.")