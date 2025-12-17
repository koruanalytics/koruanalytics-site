# scripts/check_curation_run.py
from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
from loguru import logger


ALLOWED = {"PENDING", "IN_REVIEW", "APPROVED", "REJECTED"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def cols(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    return {r[1] for r in con.execute(f"PRAGMA table_info('{table}')").fetchall()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    try:
        # sanity: columnas
        c_cols = cols(con, "curation_incident_overrides")
        if "review_status" not in c_cols:
            logger.error("curation_incident_overrides.review_status missing. Run create_curation_schema.py first.")
            return 2

        # 1) dominio review_status
        bad = con.execute(
            """
            SELECT DISTINCT review_status
            FROM curation_incident_overrides
            WHERE review_status IS NOT NULL
            """
        ).fetchall()
        bad_vals = {r[0] for r in bad if r[0] not in ALLOWED}
        if bad_vals:
            logger.error(f"Invalid review_status values: {sorted(bad_vals)}")
            return 2

        # 2) override_place_id existe en dim_places_pe si la columna existe
        if "override_place_id" in c_cols:
            missing_place = con.execute(
                """
                SELECT COUNT(*)
                FROM curation_incident_overrides o
                LEFT JOIN dim_places_pe p
                  ON p.place_id = o.override_place_id
                WHERE o.override_place_id IS NOT NULL
                  AND p.place_id IS NULL
                """
            ).fetchone()[0]
            if missing_place:
                logger.error(f"Overrides with override_place_id not found in dim_places_pe: {missing_place}")
                return 2

        # 3) telemetría: % incidentes del run con overrides (solo columnas que existan)
        override_cols = [
            "override_incident_type",
            "override_confidence",
            "override_location_text",
            "override_place_id",
            "override_adm1",
            "override_adm2",
            "override_adm3",
            "override_lat",
            "override_lon",
            "override_title",
            "override_body",
        ]
        present = [c for c in override_cols if c in c_cols]
        cond = " OR ".join([f"o.{c} IS NOT NULL" for c in present]) if present else "FALSE"

        tot = con.execute(
            "SELECT COUNT(*) FROM fct_incidents WHERE ingest_run_id = ?",
            [args.run_id],
        ).fetchone()[0]

        ov = con.execute(
            f"""
            SELECT COUNT(*)
            FROM fct_incidents f
            JOIN curation_incident_overrides o
              ON o.incident_id = f.incident_id
            WHERE f.ingest_run_id = ?
              AND ({cond})
            """,
            [args.run_id],
        ).fetchone()[0]

        pct = (ov / tot * 100.0) if tot else 0.0
        logger.success(f"Curation checks OK. Overrides applied: {ov}/{tot} ({pct:.1f}%)")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
