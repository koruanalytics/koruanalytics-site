from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--pipeline", default="incidents")
    args = ap.parse_args()

    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])

    min_rows = int(cfg.get("ops", {}).get("alerts_min_dedup_run_rows", 1))

    n = con.execute(
        "SELECT COUNT(*) FROM fct_incidents WHERE ingest_run_id = ?",
        [args.run_id],
    ).fetchone()[0]

    if n < min_rows:
        alert_id = str(uuid.uuid4())
        msg = f"Low incidents rows for run {args.run_id}: {n} (<{min_rows})"
        con.execute(
            """
            INSERT INTO ops_alerts VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [alert_id, args.run_id, args.pipeline, "LOW_ROWS", "WARN", msg, datetime.now(timezone.utc)],
        )
        logger.warning(f"[OPS] Alert created: {msg}")
    else:
        logger.success(f"[OPS] OK: incidents rows={n} run={args.run_id}")

    con.close()


if __name__ == "__main__":
    main()
