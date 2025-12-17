from pathlib import Path

from src.ingestion.dummy_ingest import run_dummy_ingestion


def main():
    out_file: Path = run_dummy_ingestion(n=3)
    print(f"Se ha creado el fichero: {out_file}")
    assert out_file.exists(), "El fichero JSON no se ha creado"
    assert out_file.suffix == ".json", "El fichero no es JSON"

    print("\n✅ Ingesta dummy OK. Revisa el contenido en:")
    print(f"   {out_file}")


if __name__ == "__main__":
    main()
