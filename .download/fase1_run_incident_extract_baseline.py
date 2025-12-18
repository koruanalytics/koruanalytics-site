"""
scripts/run_incident_extract_baseline.py

Extrae incidentes desde stg_news_newsapi_ai_dedup_run usando clasificación ACLED.
Incluye campos de enriquecimiento del API (source_title, category, concepts, etc.)

Usage:
    python scripts/run_incident_extract_baseline.py --run-id 20251218...
"""
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

    # ==========================================================================
    # Query ACTUALIZADA: incluir campos del API para enriquecimiento
    # ==========================================================================
    articles = con.execute(
        """
        SELECT
            ingest_run_id,
            original_uri,
            url,
            title,
            body,
            published_at,
            source,
            -- API Enrichment fields (NEW)
            source_title,
            is_duplicate,
            category_labels,
            location_label,
            concept_labels,
            -- GEO fields from API (if available)
            lat,
            lon,
            adm1,
            adm2,
            adm3
        FROM stg_news_newsapi_ai_dedup_run
        WHERE ingest_run_id = ?
        """,
        [args.run_id],
    ).df()

    if articles.empty:
        logger.warning(
            f"[INC] No articles found for run_id={args.run_id} "
            "in stg_news_newsapi_ai_dedup_run"
        )
        con.close()
        return

    extraction_version = cfg.get("incidents", {}).get("model_version", "acled_v2")

    # Log de campos disponibles
    api_fields = ["source_title", "category_labels", "location_label", "concept_labels"]
    available_api_fields = [f for f in api_fields if f in articles.columns]
    logger.info(
        f"[INC] Processing {len(articles)} articles. "
        f"API fields available: {available_api_fields}"
    )

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
    con.execute(
        "DELETE FROM stg_incidents_extracted WHERE ingest_run_id = ?",
        [args.run_id]
    )

    # ---- INSERT POR COLUMNAS COMUNES ----
    table_name = "stg_incidents_extracted"
    table_cols = get_table_columns(con, table_name)

    # Mapeos típicos por si el DW usa otros nombres
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

    # Log de columnas que se van a insertar vs las nuevas del API
    new_api_cols = ["source_title", "is_duplicate", "api_category", "api_location", "concept_labels"]
    inserted_api_cols = [c for c in new_api_cols if c in common_cols]
    missing_api_cols = [c for c in new_api_cols if c not in common_cols]

    if missing_api_cols:
        logger.warning(
            f"[INC] API columns missing in table (run migration): {missing_api_cols}"
        )
    if inserted_api_cols:
        logger.info(f"[INC] API enrichment columns to insert: {inserted_api_cols}")

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

    # Métricas de enriquecimiento
    if inserted_api_cols:
        enrichment_stats = con.execute(
            f"""
            SELECT
                COUNT(*) as total,
                COUNT(source_title) as with_source_title,
                COUNT(api_category) as with_category,
                COUNT(api_location) as with_api_location,
                COUNT(concept_labels) as with_concepts
            FROM stg_incidents_extracted
            WHERE ingest_run_id = ?
            """,
            [args.run_id]
        ).fetchone()

        if enrichment_stats:
            total = enrichment_stats[0]
            logger.info(
                f"[INC] Enrichment coverage: "
                f"source_title={enrichment_stats[1]}/{total}, "
                f"category={enrichment_stats[2]}/{total}, "
                f"api_location={enrichment_stats[3]}/{total}, "
                f"concepts={enrichment_stats[4]}/{total}"
            )

    con.close()
    logger.success(
        f"[INC] Extracted incidents rows={inserted} "
        f"run={args.run_id} version={extraction_version}"
    )


if __name__ == "__main__":
    main()
