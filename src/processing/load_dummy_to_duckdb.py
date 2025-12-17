from pathlib import Path
import json
import duckdb
import pandas as pd

from src.utils.config import load_config


def load_dummy_interim_to_duckdb() -> int:
    """
    Lee los ficheros de data/interim/dummy,
    los combina en un DataFrame y los carga en la tabla stg_news_dummy en DuckDB.

    Devuelve el número de filas cargadas.
    """
    cfg = load_config()

    interim_base = Path(cfg["data_paths"]["interim"])
    interim_dir = interim_base / "dummy"
    db_path = Path(cfg["db"]["duckdb_path"])

    if not interim_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de interim dummy: {interim_dir}")

    # Buscar todos los JSON normalizados en data/interim/dummy
    files = sorted(interim_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No hay ficheros JSON en {interim_dir}. Ejecuta antes la normalización.")

    rows = []
    for f in files:
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                rows.extend(data)
            else:
                rows.append(data)

    if not rows:
        raise ValueError(f"No se han leído registros desde {interim_dir}")

    df = pd.DataFrame(rows)

    # Asegurarnos de que la carpeta de la BBDD existe
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))

    # Crear tabla si no existe, basándonos en las columnas del DataFrame
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS stg_news_dummy AS
        SELECT * FROM df LIMIT 0
        """
    )

    # Para este MVP: vaciar y recargar
    con.execute("DELETE FROM stg_news_dummy")
    con.execute("INSERT INTO stg_news_dummy SELECT * FROM df")

    con.close()

    print(f"[load_dummy_to_duckdb] Cargadas {len(df)} filas en stg_news_dummy ({db_path})")
    return len(df)
