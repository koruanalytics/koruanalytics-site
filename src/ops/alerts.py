from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import duckdb

OPS_ALERTS_DDL = """
CREATE TABLE IF NOT EXISTS ops_alerts (
    alert_id VARCHAR,
    run_id VARCHAR,
    severity VARCHAR,
    message VARCHAR,
    created_at TIMESTAMP,
    context_json VARCHAR,
    is_active BOOLEAN
);
"""

def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def ensure_alerts_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(OPS_ALERTS_DDL)

def create_alert(
    con: duckdb.DuckDBPyConnection,
    alert_id: str,
    run_id: str,
    severity: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    ensure_alerts_table(con)
    con.execute(
        """
        INSERT INTO ops_alerts (
          alert_id, run_id, severity, message, created_at, context_json, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            alert_id,
            run_id,
            severity,
            message,
            utcnow_naive(),
            json.dumps(context or {}, ensure_ascii=False),
            True,
        ],
    )

def close_alerts_for_run(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    ensure_alerts_table(con)
    con.execute("UPDATE ops_alerts SET is_active = FALSE WHERE run_id = ?", [run_id])
