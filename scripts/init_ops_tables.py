from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


DDL = """
CREATE TABLE IF NOT EXISTS ops_ingest_runs (
  ingest_run_id VARCHAR,
  pipeline_name VARCHAR,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  status VARCHAR,
  notes VARCHAR
);

CREATE TABLE IF NOT EXISTS ops_alerts (
  alert_id VARCHAR,
  ingest_run_id VARCHAR,
  pipeline_name VARCHAR,
  alert_type VARCHAR,
  severity VARCHAR,
  message VARCHAR,
  created_at TIMESTAMP
);
"""


def main():
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    con.execute(DDL)
    con.close()
    logger.success("[OPS] Tables ready: ops_ingest_runs, ops_alerts")


if __name__ == "__main__":
    main()
