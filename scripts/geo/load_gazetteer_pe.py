from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config

DIM_PLACES_DDL = """
CREATE TABLE IF NOT EXISTS dim_places_pe (
  place_id VARCHAR,          -- UBIGEO INEI (6)
  ubigeo_reniec VARCHAR,     -- UBIGEO RENIEC (6)

  departamento VARCHAR,
  provincia VARCHAR,
  distrito VARCHAR,

  region VARCHAR,
  macroregion_inei VARCHAR,
  macroregion_minsa VARCHAR,

  iso_3166_2 VARCHAR,
  fips VARCHAR,

  superficie DOUBLE,
  altitud DOUBLE,
  lat DOUBLE,
  lon DOUBLE,

  frontera VARCHAR
);
"""

def main():
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    con.execute(DIM_PLACES_DDL)

    gaz_path = cfg["geo"]["gazetteer_path"]

    # Reload completo (determinista y simple)
    con.execute("DELETE FROM dim_places_pe")
    con.execute(
        "INSERT INTO dim_places_pe SELECT * FROM read_csv_auto(?, HEADER=TRUE)",
        [gaz_path],
    )

    n = con.execute("SELECT COUNT(*) FROM dim_places_pe").fetchone()[0]
    con.close()

    logger.success(f"[GEO] Loaded dim_places_pe rows={n} from {gaz_path}")

if __name__ == "__main__":
    main()
