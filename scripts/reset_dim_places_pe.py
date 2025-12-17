from __future__ import annotations

import sys
from pathlib import Path

# Asegura imports desde la raíz del repo
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


DIM_PLACES_DDL = """
CREATE TABLE dim_places_pe (
  place_id VARCHAR,
  ubigeo_reniec VARCHAR,
  adm1_code VARCHAR,
  adm2_code VARCHAR,
  adm3_code VARCHAR,
  adm1_name VARCHAR,
  adm2_name VARCHAR,
  adm3_name VARCHAR,
  display_name VARCHAR,
  search_name VARCHAR,
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


def main() -> None:
    cfg = load_config()
    db_path = cfg["db"]["duckdb_path"]

    con = duckdb.connect(db_path)

    # Drop + create con schema FULL (20 columnas)
    con.execute("DROP TABLE IF EXISTS dim_places_pe")
    con.execute(DIM_PLACES_DDL)

    con.close()
    logger.success("[GEO] OK: dim_places_pe recreada con schema FULL (20 columnas)")


if __name__ == "__main__":
    main()
