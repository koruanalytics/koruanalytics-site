from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


def get_table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> list[str]:
    rows = con.execute(
        f"SELECT name FROM pragma_table_info('{table_name}') ORDER BY cid"
    ).fetchall()
    return [r[0] for r in rows]


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    try:
        con.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
        return True
    except Exception:
        return False


def pick_source_col(stg_cols: list[str]) -> str:
    for c in ["source_uri", "source", "original_uri", "url"]:
        if c in stg_cols:
            return c
    raise RuntimeError(f"[FACT] No source column found in stg_incidents_extracted. cols={stg_cols}")


def pick_published_col(stg_cols: list[str]) -> str | None:
    for c in ["published_at", "published", "date", "datetime"]:
        if c in stg_cols:
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])

    stg = "stg_incidents_extracted"
    fct = "fct_incidents"
    overrides_tbl = "curation_incident_overrides"

    stg_cols = get_table_columns(con, stg)
    fct_cols = get_table_columns(con, fct)

    source_col = pick_source_col(stg_cols)
    pub_col = pick_published_col(stg_cols)

    built_at = datetime.now(timezone.utc)

    # overrides: solo se usan si existe la tabla y tiene columnas override_*
    overrides_enabled = False
    o_cols: list[str] = []
    if table_exists(con, overrides_tbl):
        o_cols = get_table_columns(con, overrides_tbl)
        overrides_enabled = any(c.startswith("override_") for c in o_cols)

    # idempotencia por run
    con.execute(f"DELETE FROM {fct} WHERE ingest_run_id = ?", [args.run_id])

    # helpers para expresiones
    def s(col: str) -> str:
        return f"s.\"{col}\""

    def o(col: str) -> str:
        return f"o.\"{col}\""

    def coalesce_override(override_col: str, base_expr: str) -> str:
        if overrides_enabled and override_col in o_cols:
            return f"COALESCE({o(override_col)}, {base_expr})"
        return base_expr

    # mapa de expresiones “conocidas” (lo demás: NULL)
    expr_by_col: dict[str, str] = {}

    # claves / metadata típicas
    if "incident_id" in fct_cols and "incident_id" in stg_cols:
        expr_by_col["incident_id"] = s("incident_id")

    if "ingest_run_id" in fct_cols and "ingest_run_id" in stg_cols:
        expr_by_col["ingest_run_id"] = s("ingest_run_id")

    # source en el fact puede llamarse source_uri o source (o ambas)
    if "source_uri" in fct_cols:
        expr_by_col["source_uri"] = s(source_col)
    if "source" in fct_cols:
        expr_by_col["source"] = s(source_col)

    # published
    if "published_at" in fct_cols:
        expr_by_col["published_at"] = s(pub_col) if pub_col else "NULL::TIMESTAMP"

    # incident_type + confidence
    if "incident_type" in fct_cols:
        expr_by_col["incident_type"] = coalesce_override("override_incident_type", s("incident_type") if "incident_type" in stg_cols else "NULL")
    if "confidence" in fct_cols:
        expr_by_col["confidence"] = s("confidence") if "confidence" in stg_cols else "NULL::DOUBLE"

    # geo
    if "place_id" in fct_cols:
        expr_by_col["place_id"] = coalesce_override("override_place_id", s("place_id") if "place_id" in stg_cols else "NULL")
    if "adm1" in fct_cols:
        expr_by_col["adm1"] = coalesce_override("override_adm1", s("adm1") if "adm1" in stg_cols else "NULL")
    if "adm2" in fct_cols:
        expr_by_col["adm2"] = coalesce_override("override_adm2", s("adm2") if "adm2" in stg_cols else "NULL")
    if "adm3" in fct_cols:
        expr_by_col["adm3"] = coalesce_override("override_adm3", s("adm3") if "adm3" in stg_cols else "NULL")
    if "lat" in fct_cols:
        expr_by_col["lat"] = coalesce_override("override_lat", s("lat") if "lat" in stg_cols else "NULL::DOUBLE")
    if "lon" in fct_cols:
        expr_by_col["lon"] = coalesce_override("override_lon", s("lon") if "lon" in stg_cols else "NULL::DOUBLE")

    # texto (por si tu fct lo incluye)
    for c in ["title", "body"]:
        if c in fct_cols:
            expr_by_col[c] = s(c) if c in stg_cols else "NULL"

    # versioning/timestamps (nombres frecuentes)
    if "extraction_version" in fct_cols:
        expr_by_col["extraction_version"] = s("extraction_version") if "extraction_version" in stg_cols else "NULL"
    for ts_col in ["built_at", "created_at", "loaded_at"]:
        if ts_col in fct_cols:
            # usamos el mismo built_at para cualquiera de estos campos si existen
            expr_by_col[ts_col] = "?"  # parámetro built_at

    # fallback: si el fact tiene columnas extra que también existen en staging, las pasamos
    for col in fct_cols:
        if col not in expr_by_col and col in stg_cols:
            expr_by_col[col] = s(col)

    # resto: NULL
    select_exprs = []
    for col in fct_cols:
        select_exprs.append(expr_by_col.get(col, "NULL"))

    insert_cols_sql = ", ".join([f"\"{c}\"" for c in fct_cols])
    select_exprs_sql = ", ".join(select_exprs)

    join_sql = ""
    if overrides_enabled:
        join_sql = f"LEFT JOIN {overrides_tbl} o ON s.incident_id = o.incident_id"
        logger.info("[FACT] Building with overrides (override_* columns detected).")
    else:
        logger.info("[FACT] Building WITHOUT overrides (no override_* columns present).")

    sql = f"""
    INSERT INTO {fct} ({insert_cols_sql})
    SELECT {select_exprs_sql}
    FROM {stg} s
    {join_sql}
    WHERE s.ingest_run_id = ?
    """

    # parámetros: built_at (puede usarse 0,1 o varias veces) + run_id
    # Como hemos puesto "?" para timestamps, necesitamos pasar built_at tantas veces como "?" haya
    num_ts_params = sum(1 for e in select_exprs if e.strip() == "?")
    params = [built_at] * num_ts_params + [args.run_id]

    con.execute(sql, params)

    n = con.execute(f"SELECT COUNT(*) FROM {fct} WHERE ingest_run_id = ?", [args.run_id]).fetchone()[0]
    con.close()

    logger.success(
        f"[FACT] Built {fct} rows={n} run={args.run_id} "
        f"(fct_cols={len(fct_cols)}, stg_cols={len(stg_cols)}, overrides={overrides_enabled})"
    )


if __name__ == "__main__":
    main()
