# scripts/export_review_queue.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def outputs_dir() -> Path:
    p = repo_root() / "outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


SQL = r"""
SELECT
  ingest_run_id,
  incident_id,
  published_at,
  source,
  title,
  url,

  incident_type,
  confidence,
  location_text,
  place_id,
  adm1, adm2, adm3, lat, lon,

  override_review_status,
  override_review_notes,

  override_incident_type,
  override_confidence,
  override_location_text,
  override_place_id,
  override_adm1,
  override_adm2,
  override_adm3,
  override_lat,
  override_lon,

  effective_incident_type,
  effective_confidence,
  effective_location_text,
  effective_place_id,
  effective_adm1,
  effective_adm2,
  effective_adm3,
  effective_lat,
  effective_lon

FROM v_incidents_review_queue
WHERE ingest_run_id = ?
ORDER BY published_at DESC
;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(db_path()))
    args = parser.parse_args()

    out = outputs_dir() / f"review_queue_{args.run_id}.csv"

    logger.info(f"Exporting review queue for run_id={args.run_id} -> {out}")
    con = duckdb.connect(args.db)
    try:
        df = con.execute(SQL, [args.run_id]).df()
        df.to_csv(out, index=False, encoding="utf-8")
        logger.success(f"Wrote {len(df)} rows: {out}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
