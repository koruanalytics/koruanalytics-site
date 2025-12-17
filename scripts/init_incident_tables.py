from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


DDL = """
CREATE TABLE IF NOT EXISTS stg_incidents_extracted (
  incident_id VARCHAR,
  ingest_run_id VARCHAR,

  source_uri VARCHAR,           -- original_uri / canonical
  title VARCHAR,
  body VARCHAR,
  published_at TIMESTAMP,

  incident_type VARCHAR,        -- baseline (rules)
  confidence DOUBLE,

  -- GEO placeholders / enrichment
  place_id VARCHAR,
  adm1 VARCHAR,
  adm2 VARCHAR,
  adm3 VARCHAR,
  lat DOUBLE,
  lon DOUBLE,

  extraction_version VARCHAR,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS curation_incident_overrides (
  incident_id VARCHAR,
  override_incident_type VARCHAR,
  override_place_id VARCHAR,
  override_adm1 VARCHAR,
  override_adm2 VARCHAR,
  override_adm3 VARCHAR,
  override_lat DOUBLE,
  override_lon DOUBLE,
  analyst VARCHAR,
  reason VARCHAR,
  created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fct_incidents (
  incident_id VARCHAR,
  ingest_run_id VARCHAR,
  source_uri VARCHAR,
  published_at TIMESTAMP,
  incident_type VARCHAR,
  confidence DOUBLE,

  place_id VARCHAR,
  adm1 VARCHAR,
  adm2 VARCHAR,
  adm3 VARCHAR,
  lat DOUBLE,
  lon DOUBLE,

  extraction_version VARCHAR,
  built_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS map_incident_place (
  incident_id VARCHAR,
  place_id VARCHAR,
  score DOUBLE,
  method VARCHAR,
  ingest_run_id VARCHAR
);
"""


def main():
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    con.execute(DDL)
    con.close()
    logger.success("[INC] Tables ready: stg_incidents_extracted, overrides, fct_incidents, map_incident_place")


if __name__ == "__main__":
    main()
