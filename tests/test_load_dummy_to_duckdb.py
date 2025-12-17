from pathlib import Path

from src.ingestion.dummy_ingest import run_dummy_ingestion
from src.processing.normalize_dummy import normalize_dummy_file
from src.processing.load_dummy_to_duckdb import load_dummy_interim_to_duckdb


def main():
    print("=== Test carga INTERIM dummy -> DuckDB ===")

    # 1) Generar RAW
    raw_file: Path = run_dummy_ingestion(n=5)
    print(f"[RAW] Fichero generado: {raw_file}")

    # 2) Normalizar a INTERIM
    interim_file: Path = normalize_dummy_file(raw_file)
    print(f"[INTERIM] Fichero generado: {interim_file}")

    # 3) Cargar en DuckDB
    n_rows = load_dummy_interim_to_duckdb()
    print(f"[DW] Filas cargadas en stg_news_dummy: {n_rows}")

    assert n_rows > 0, "No se han cargado filas en stg_news_dummy"

    print("\n✅ Carga dummy en DuckDB OK.")


if __name__ == "__main__":
    main()
