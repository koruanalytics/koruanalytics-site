# scripts/run_geo_resolve_incidents.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


DDL = r"""
CREATE TABLE IF NOT EXISTS map_incident_place (
  ingest_run_id     VARCHAR,
  incident_id       VARCHAR,

  place_id          VARCHAR,
  adm1              VARCHAR,
  adm2              VARCHAR,
  adm3              VARCHAR,
  lat               DOUBLE,
  lon               DOUBLE,

  matched_text_norm VARCHAR,
  matched_tokens    INTEGER,
  method            VARCHAR,
  score             DOUBLE,

  is_primary        BOOLEAN,

  created_at        TIMESTAMP DEFAULT now()
);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    try:
        con.execute(DDL)
        con.execute("DELETE FROM map_incident_place WHERE ingest_run_id = ?", [args.run_id])

        # Insert con columnas explícitas (sin created_at)
        con.execute(
            r"""
            INSERT INTO map_incident_place (
              ingest_run_id, incident_id,
              place_id, adm1, adm2, adm3, lat, lon,
              matched_text_norm, matched_tokens,
              method, score,
              is_primary
            )
            SELECT
              c.ingest_run_id,
              c.incident_id,

              c.candidate_place_id AS place_id,
              c.candidate_adm1     AS adm1,
              c.candidate_adm2     AS adm2,
              c.candidate_adm3     AS adm3,
              c.candidate_lat      AS lat,
              c.candidate_lon      AS lon,

              c.matched_text_norm,
              c.matched_tokens,
              c.method,
              c.score,

              (ROW_NUMBER() OVER (
                 PARTITION BY c.ingest_run_id, c.incident_id
                 ORDER BY c.score DESC, c.matched_tokens DESC, c.candidate_place_id ASC
               ) = 1) AS is_primary

            FROM stg_incident_place_candidates c
            WHERE c.ingest_run_id = ?
            """,
            [args.run_id],
        )

        # Update staging con primary
        con.execute(
            r"""
            UPDATE stg_incidents_extracted e
            SET
              place_id = p.place_id,
              adm1 = p.adm1,
              adm2 = p.adm2,
              adm3 = p.adm3,
              lat  = p.lat,
              lon  = p.lon
            FROM map_incident_place p
            WHERE e.ingest_run_id = p.ingest_run_id
              AND e.incident_id   = p.incident_id
              AND p.is_primary = TRUE
              AND e.ingest_run_id = ?
            """,
            [args.run_id],
        )

        n_map = con.execute(
            "SELECT COUNT(*) FROM map_incident_place WHERE ingest_run_id = ?",
            [args.run_id],
        ).fetchone()[0]
        n_primary = con.execute(
            """
            SELECT COUNT(*)
            FROM map_incident_place
            WHERE ingest_run_id = ?
              AND is_primary = TRUE
            """,
            [args.run_id],
        ).fetchone()[0]

        logger.success(f"GEO resolve v2 OK. map rows={n_map}, primary rows={n_primary}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
