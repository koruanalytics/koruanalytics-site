"""
src/processing/dedupe_newsapi_ai_in_duckdb.py

Deduplicación de artículos en DuckDB.

Crea dos tablas:
- stg_news_newsapi_ai_dedup: Dedupe GLOBAL (todos los runs, últimas versiones)
- stg_news_newsapi_ai_dedup_run: Dedupe del RUN actual (solo artículos del run especificado)

Usa canonical_uri = COALESCE(original_uri, source_article_id) como clave de dedup.
"""
from __future__ import annotations

import duckdb
from pathlib import Path
from loguru import logger

from src.utils.config import load_config


def _as_posix(p: Path) -> str:
    return p.resolve().as_posix()


def dedupe_newsapi_ai_in_duckdb(
    src_table: str = "stg_news_newsapi_ai",
    dst_table: str = "stg_news_newsapi_ai_dedup",
    dst_table_run: str = "stg_news_newsapi_ai_dedup_run",
    ingest_run_id: str | None = None,
) -> dict:
    """
    Deduplica artículos de NewsAPI.ai en DuckDB.
    
    Crea DOS tablas:
    1. {dst_table}: Dedupe GLOBAL sobre todos los runs
       - Mantiene la versión más reciente de cada artículo
       - Útil para análisis histórico
       
    2. {dst_table_run}: Dedupe del RUN actual
       - Solo artículos del ingest_run_id especificado
       - Deduplicados contra el histórico global
       - Útil para procesamiento del pipeline (extracción de incidentes)
    
    Args:
        src_table: Tabla fuente con artículos crudos
        dst_table: Tabla destino para dedupe global
        dst_table_run: Tabla destino para dedupe del run actual
        ingest_run_id: ID del run actual (requerido para crear _dedup_run)
    
    Returns:
        dict con estadísticas de dedup:
        - dedup_global: {src_rows, dst_rows, removed}
        - dedup_run: {src_rows, dst_rows, removed}
    """
    cfg = load_config()
    db_path = Path(cfg["db"]["duckdb_path"])
    con = duckdb.connect(_as_posix(db_path))
    
    result = {
        "dedup_global": {},
        "dedup_run": {},
    }
    
    # =========================================================================
    # PASO 1: Dedupe GLOBAL (todos los runs)
    # =========================================================================
    con.execute(f"DROP TABLE IF EXISTS {dst_table}")
    
    con.execute(
        f"""
        CREATE TABLE {dst_table} AS
        WITH base AS (
            SELECT
                *,
                COALESCE(original_uri, source_article_id) AS canonical_uri
            FROM {src_table}
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY canonical_uri
                    ORDER BY published_at DESC NULLS LAST, ingest_run_id DESC
                ) AS rn
            FROM base
        )
        SELECT * EXCLUDE(rn, canonical_uri)
        FROM ranked
        WHERE rn = 1
        """
    )
    
    total_src_global = con.execute(f"SELECT COUNT(*) FROM {src_table}").fetchone()[0]
    total_dst_global = con.execute(f"SELECT COUNT(*) FROM {dst_table}").fetchone()[0]
    removed_global = total_src_global - total_dst_global
    
    result["dedup_global"] = {
        "src_rows": total_src_global,
        "dst_rows": total_dst_global,
        "removed": removed_global,
    }
    
    # =========================================================================
    # PASO 2: Dedupe del RUN actual (si se especifica ingest_run_id)
    # =========================================================================
    if ingest_run_id:
        con.execute(f"DROP TABLE IF EXISTS {dst_table_run}")
        
        # Artículos del run actual que NO son duplicados de runs anteriores
        con.execute(
            f"""
            CREATE TABLE {dst_table_run} AS
            WITH run_articles AS (
                SELECT
                    *,
                    COALESCE(original_uri, source_article_id) AS canonical_uri
                FROM {src_table}
                WHERE ingest_run_id = '{ingest_run_id}'
            ),
            -- Artículos de runs ANTERIORES (para detectar duplicados históricos)
            historical AS (
                SELECT DISTINCT
                    COALESCE(original_uri, source_article_id) AS canonical_uri
                FROM {src_table}
                WHERE ingest_run_id < '{ingest_run_id}'
            ),
            -- Dedupe dentro del run actual
            run_deduped AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY canonical_uri
                        ORDER BY published_at DESC NULLS LAST
                    ) AS rn
                FROM run_articles
            )
            SELECT r.* EXCLUDE(rn, canonical_uri)
            FROM run_deduped r
            LEFT JOIN historical h ON r.canonical_uri = h.canonical_uri
            WHERE r.rn = 1
              AND h.canonical_uri IS NULL  -- Excluir duplicados históricos
            """
        )
        
        total_src_run = con.execute(
            f"SELECT COUNT(*) FROM {src_table} WHERE ingest_run_id = '{ingest_run_id}'"
        ).fetchone()[0]
        total_dst_run = con.execute(f"SELECT COUNT(*) FROM {dst_table_run}").fetchone()[0]
        removed_run = total_src_run - total_dst_run
        
        result["dedup_run"] = {
            "src_rows": total_src_run,
            "dst_rows": total_dst_run,
            "removed": removed_run,
            "ingest_run_id": ingest_run_id,
        }
        
        logger.success(
            f"[DW] Dedupe OK -> {dst_table} ({total_src_global} -> {total_dst_global}, "
            f"removed={removed_global})"
        )
        logger.success(
            f"[DW] Dedupe RUN -> {dst_table_run} ({total_src_run} -> {total_dst_run}, "
            f"removed={removed_run}, run={ingest_run_id})"
        )
    else:
        logger.success(
            f"[DW] Dedupe OK -> {dst_table} ({total_src_global} -> {total_dst_global}, "
            f"removed={removed_global})"
        )
    
    con.close()
    return result
