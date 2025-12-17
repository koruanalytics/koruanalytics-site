# scripts/create_curation_schema.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    q = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_name = ?
    """
    return con.execute(q, [table]).fetchone()[0] > 0


def get_columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    cols = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
    return {r[1] for r in cols}


def ensure_column(con: duckdb.DuckDBPyConnection, table: str, col: str, col_type: str, default_sql: str | None = None):
    cols = get_columns(con, table)
    if col in cols:
        return
    logger.info(f"[MIGRATION] Adding column {table}.{col} {col_type}")
    con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
    if default_sql:
        con.execute(f"UPDATE {table} SET {col} = {default_sql} WHERE {col} IS NULL")


def build_review_queue_view_sql(con: duckdb.DuckDBPyConnection) -> str:
    """
    Construye la view v_incidents_review_queue sin asumir que override columns ya existan.
    Como nosotros las garantizamos con ensure_column, la view puede ser estática.
    """
    return r"""
CREATE OR REPLACE VIEW v_incidents_review_queue AS
SELECT
  e.ingest_run_id,
  e.incident_id,
  e.published_at,
  e.source,
  e.title,
  e.url,
  e.body,

  -- baseline extraído
  e.incident_type,
  e.confidence,
  e.extraction_version,
  e.location_text,
  e.place_id,
  e.adm1,
  e.adm2,
  e.adm3,
  e.lat,
  e.lon,

  -- estado revisión de staging (si existe)
  e.review_status AS staging_review_status,
  e.review_notes  AS staging_review_notes,

  -- overrides (si existen)
  o.review_status AS override_review_status,
  o.review_notes  AS override_review_notes,

  o.override_incident_type,
  o.override_confidence,
  o.override_location_text,
  o.override_place_id,
  o.override_adm1,
  o.override_adm2,
  o.override_adm3,
  o.override_lat,
  o.override_lon,
  o.override_title,
  o.override_body,

  -- effective
  COALESCE(o.override_incident_type, e.incident_type) AS effective_incident_type,
  COALESCE(o.override_confidence,    e.confidence)    AS effective_confidence,
  COALESCE(o.override_location_text, e.location_text) AS effective_location_text,

  COALESCE(o.override_place_id, e.place_id) AS effective_place_id,
  COALESCE(o.override_adm1,     e.adm1)     AS effective_adm1,
  COALESCE(o.override_adm2,     e.adm2)     AS effective_adm2,
  COALESCE(o.override_adm3,     e.adm3)     AS effective_adm3,
  COALESCE(o.override_lat,      e.lat)      AS effective_lat,
  COALESCE(o.override_lon,      e.lon)      AS effective_lon

FROM stg_incidents_extracted e
LEFT JOIN curation_incident_overrides o
  ON o.incident_id = e.incident_id
;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(default_db_path()), help="Ruta a osint_dw.duckdb")
    args = parser.parse_args()

    logger.info(f"Opening DB: {args.db}")
    con = duckdb.connect(args.db)
    try:
        # 1) create table if not exists (mínimo)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS curation_incident_overrides (
              incident_id           VARCHAR PRIMARY KEY,
              review_notes          VARCHAR,
              updated_at            TIMESTAMP,
              updated_by            VARCHAR
            );
            """
        )

        # 2) aseguramos columnas esperadas para F8 (migración forward)
        ensure_column(con, "curation_incident_overrides", "review_status", "VARCHAR", default_sql="'PENDING'")
        ensure_column(con, "curation_incident_overrides", "created_at", "TIMESTAMP", default_sql="now()")
        ensure_column(con, "curation_incident_overrides", "created_by", "VARCHAR")

        ensure_column(con, "curation_incident_overrides", "override_incident_type", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_confidence", "DOUBLE")
        ensure_column(con, "curation_incident_overrides", "override_location_text", "VARCHAR")

        ensure_column(con, "curation_incident_overrides", "override_place_id", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_adm1", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_adm2", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_adm3", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_lat", "DOUBLE")
        ensure_column(con, "curation_incident_overrides", "override_lon", "DOUBLE")

        ensure_column(con, "curation_incident_overrides", "override_title", "VARCHAR")
        ensure_column(con, "curation_incident_overrides", "override_body", "VARCHAR")

        # 3) view de cola revisión
        con.execute(build_review_queue_view_sql(con))

        logger.success("Curation schema OK (table migrated + view refreshed).")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
