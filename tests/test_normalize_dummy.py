from pathlib import Path

# ❌ AHORA MISMO tienes algo así:
# from src.ingestion.dummy_ingest import run_dummy_ingest

# ✅ CÁMBIALO POR:
from src.ingestion.dummy_ingest import run_dummy_ingestion

from src.processing.normalize_dummy import normalize_dummy_file


def main():
    # 1) Generar RAW dummy
    raw_file: Path = run_dummy_ingestion(n=3)
    print(f"[RAW] Fichero generado: {raw_file}")

    # 2) Normalizar a INTERIM
    interim_file: Path = normalize_dummy_file(raw_file)
    print(f"[INTERIM] Fichero generado: {interim_file}")

    # 3) Validaciones básicas
    assert raw_file.exists(), "El fichero RAW no existe"
    assert interim_file.exists(), "El fichero INTERIM no se ha creado"
    assert interim_file.suffix == ".json", "El fichero INTERIM no es JSON"

    print("\n✅ Normalización dummy OK.")
    print(f"   RAW:     {raw_file}")
    print(f"   INTERIM: {interim_file}")


if __name__ == "__main__":
    main()