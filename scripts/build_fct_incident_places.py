# scripts/build_fct_incident_places.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS fct_incident_places (
              ingest_run_id VARCHAR,
              incident_id   VARCHAR,
              place_id      VARCHAR,
              score         DOUBLE,
              method        VARCHAR,
              is_primary    BOOLEAN,
              created_at    TIMESTAMP DEFAULT now()
            );
            """
        )

        con.execute("DELETE FROM fct_incident_places WHERE ingest_run_id = ?", [args.run_id])

        con.execute(
            """
            INSERT INTO fct_incident_places (ingest_run_id, incident_id, place_id, score, method, is_primary)
            SELECT ingest_run_id, incident_id, place_id, score, method, is_primary
            FROM map_incident_place
            WHERE ingest_run_id = ?;
            """,
            [args.run_id],
        )

        n = con.execute(
            "SELECT COUNT(*) FROM fct_incident_places WHERE ingest_run_id = ?",
            [args.run_id],
        ).fetchone()[0]
        logger.success(f"fct_incident_places built for run_id={args.run_id}: {n} rows")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
