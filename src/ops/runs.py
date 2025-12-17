from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import duckdb

OPS_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS ops_ingest_runs (
    run_id VARCHAR,
    job_name VARCHAR,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR,
    params_json VARCHAR,
    raw_rows BIGINT,
    interim_rows BIGINT,
    stg_rows BIGINT,
    dedup_run_rows BIGINT,
    dedup_total_rows BIGINT,
    incidents_extracted_rows BIGINT,
    incidents_fact_rows BIGINT,
    exit_code INTEGER,
    log_path VARCHAR
);
"""

def utcnow_naive() -> datetime:
    # DuckDB guarda TIMESTAMP naive: usamos UTC sin tzinfo
    return datetime.now(timezone.utc).replace(tzinfo=None)

def ensure_ops_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(OPS_RUNS_DDL)

def start_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    job_name: str,
    params: Optional[Dict[str, Any]] = None,
    log_path: Optional[str] = None,
) -> None:
    ensure_ops_tables(con)
    con.execute(
        """
        INSERT INTO ops_ingest_runs (
          run_id, job_name, started_at, status, params_json, log_path
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            job_name,
            utcnow_naive(),
            "RUNNING",
            json.dumps(params or {}, ensure_ascii=False),
            log_path,
        ],
    )

def end_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    status: str,
    exit_code: int,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    metrics = metrics or {}
    ensure_ops_tables(con)
    con.execute(
        """
        UPDATE ops_ingest_runs
        SET ended_at = ?,
            status = ?,
            exit_code = ?,
            raw_rows = COALESCE(?, raw_rows),
            interim_rows = COALESCE(?, interim_rows),
            stg_rows = COALESCE(?, stg_rows),
            dedup_run_rows = COALESCE(?, dedup_run_rows),
            dedup_total_rows = COALESCE(?, dedup_total_rows),
            incidents_extracted_rows = COALESCE(?, incidents_extracted_rows),
            incidents_fact_rows = COALESCE(?, incidents_fact_rows)
        WHERE run_id = ?
        """,
        [
            utcnow_naive(),
            status,
            int(exit_code),
            metrics.get("raw_rows"),
            metrics.get("interim_rows"),
            metrics.get("stg_rows"),
            metrics.get("dedup_run_rows"),
            metrics.get("dedup_total_rows"),
            metrics.get("incidents_extracted_rows"),
            metrics.get("incidents_fact_rows"),
            run_id,
        ],
    )
