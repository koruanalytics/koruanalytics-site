# scripts/build_fct_incidents_curated.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def table_cols(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info('{table}')").fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    try:
        logger.info("Building fct_incidents_curated snapshot (schema-aware)...")

        # 1) crear tabla curada con el esquema del baseline
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS fct_incidents_curated AS
            SELECT * FROM fct_incidents WHERE 1=0;
            """
        )

        # 2) idempotencia por run
        con.execute("DELETE FROM fct_incidents_curated WHERE ingest_run_id = ?", [args.run_id])

        f_cols = set(table_cols(con, "fct_incidents"))
        o_cols = set(table_cols(con, "curation_incident_overrides"))

        # 3) mapping override -> fact (solo se aplica si ambas columnas existen)
        mappings = [
            ("override_incident_type", "incident_type"),
            ("override_confidence", "confidence"),
            ("override_location_text", "location_text"),
            ("override_title", "title"),
            ("override_body", "body"),

            ("override_place_id", "place_id"),
            ("override_adm1", "adm1"),
            ("override_adm2", "adm2"),
            ("override_adm3", "adm3"),
            ("override_lat", "lat"),
            ("override_lon", "lon"),
        ]

        replace_exprs: list[str] = []
        applied: list[tuple[str, str]] = []

        for o_col, f_col in mappings:
            if o_col in o_cols and f_col in f_cols:
                replace_exprs.append(f"COALESCE(o.{o_col}, f.{f_col}) AS {f_col}")
                applied.append((o_col, f_col))

        if not replace_exprs:
            logger.warning("No override mappings apply (schema mismatch). Copying baseline rows as-is.")
            con.execute(
                """
                INSERT INTO fct_incidents_curated
                SELECT *
                FROM fct_incidents
                WHERE ingest_run_id = ?;
                """,
                [args.run_id],
            )
        else:
            replace_sql = ",\n                ".join(replace_exprs)
            sql = f"""
            INSERT INTO fct_incidents_curated
            SELECT
              f.* REPLACE (
                {replace_sql}
              )
            FROM fct_incidents f
            LEFT JOIN curation_incident_overrides o
              ON o.incident_id = f.incident_id
            WHERE f.ingest_run_id = ?;
            """
            con.execute(sql, [args.run_id])

        cnt = con.execute(
            "SELECT COUNT(*) FROM fct_incidents_curated WHERE ingest_run_id = ?",
            [args.run_id],
        ).fetchone()[0]

        logger.success(f"fct_incidents_curated built for run_id={args.run_id}: {cnt} rows")
        logger.info(f"Applied override mappings: {applied}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
