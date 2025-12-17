from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
from loguru import logger

from src.utils.config import load_config
from src.incidents.extract_baseline import extract_from_article


def get_table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> list[str]:
    """
    Devuelve las columnas reales de una tabla DuckDB en orden.
    """
    rows = con.execute(
        f"SELECT name FROM pragma_table_info('{table_name}') ORDER BY cid"
    ).fetchall()
    return [r[0] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])

    # Fuente: dedup_run del run actual
    articles = con.execute(
        """
     SELECT
         ingest_run_id,
        original_uri,
        url,
        title,
        body,
        published_at
    FROM stg_news_newsapi_ai_dedup_run
    WHERE ingest_run_id = ?
        """,
        [args.run_id],
    ).df()

    if articles.empty:
        logger.warning(f"[INC] No articles found for run_id={args.run_id} in stg_news_newsapi_ai_dedup_run")
        con.close()
        return

    extraction_version = cfg.get("incidents", {}).get("model_version", "baseline_rules_v1")

    rows = []
    for _, r in articles.iterrows():
        rows.append(
            extract_from_article(
                r.to_dict(),
                ingest_run_id=args.run_id,
                extraction_version=extraction_version,
            )
        )

    df = pd.DataFrame(rows)

    # Idempotencia por run (borra staging previo de este run)
    con.execute("DELETE FROM stg_incidents_extracted WHERE ingest_run_id = ?", [args.run_id])

    # ---- FIX ROBUSTO: INSERT POR COLUMNAS COMUNES ----
    table_name = "stg_incidents_extracted"
    table_cols = get_table_columns(con, table_name)

    # Mapeos típicos por si el DW usa otros nombres (ajusta si lo necesitas)
    # (en tu caso, stg_incidents_extracted usa source_uri en el DDL que te pasé)
    if "source_uri" in df.columns and "source_uri" not in table_cols and "original_uri" in table_cols:
        df = df.rename(columns={"source_uri": "original_uri"})
    if "original_uri" in df.columns and "original_uri" not in table_cols and "source_uri" in table_cols:
        df = df.rename(columns={"original_uri": "source_uri"})

    # Quedarnos solo con columnas que existen en la tabla
    common_cols = [c for c in df.columns if c in table_cols]
    if not common_cols:
        con.close()
        raise RuntimeError(
            "No common columns between df_inc and stg_incidents_extracted.\n"
            f"df_cols={list(df.columns)}\n"
            f"table_cols={table_cols}"
        )

    # Ordenar columnas como en tabla (más predecible)
    common_cols = [c for c in table_cols if c in common_cols]

    # Registrar DF en DuckDB
    con.register("df_inc", df)

    cols_sql = ", ".join([f'"{c}"' for c in common_cols])

    # Insert solo de columnas comunes; el resto queda NULL
    con.execute(
        f"""
        INSERT INTO {table_name} ({cols_sql})
        SELECT {cols_sql}
        FROM df_inc
        """
    )

    # Métrica final
    inserted = con.execute(
        "SELECT COUNT(*) FROM stg_incidents_extracted WHERE ingest_run_id = ?",
        [args.run_id],
    ).fetchone()[0]

    con.close()
    logger.success(f"[INC] Extracted incidents rows={inserted} run={args.run_id} version={extraction_version}")


if __name__ == "__main__":
    main()
