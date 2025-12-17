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
    ingest_run_id: str | None = None,
) -> dict:
    """
    Dedupe usando:
      canonical_uri = COALESCE(original_uri, source_article_id)

    Si ingest_run_id != None:
      dedupe solo sobre filas de ese run (útil para QA).
    Si ingest_run_id == None:
      dedupe global sobre toda la tabla (útil para análisis).
    """
    cfg = load_config()
    db_path = Path(cfg["db"]["duckdb_path"])
    con = duckdb.connect(_as_posix(db_path))

    con.execute(f"DROP TABLE IF EXISTS {dst_table}")

    where_clause = ""
    if ingest_run_id:
        where_clause = f"WHERE ingest_run_id = '{ingest_run_id}'"

    con.execute(
        f"""
        CREATE TABLE {dst_table} AS
        WITH base AS (
            SELECT
                *,
                COALESCE(original_uri, source_article_id) AS canonical_uri
            FROM {src_table}
            {where_clause}
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
        SELECT * EXCLUDE(rn)
        FROM ranked
        WHERE rn = 1
        """
    )

    total_src = con.execute(
        f"SELECT COUNT(*) FROM {src_table} {where_clause}"
    ).fetchone()[0]
    total_dst = con.execute(f"SELECT COUNT(*) FROM {dst_table}").fetchone()[0]
    removed = total_src - total_dst

    con.close()

    logger.success(f"[DW] Dedupe OK -> {dst_table} ({total_src} -> {total_dst}, removed={removed})")
    return {"src_rows": total_src, "dst_rows": total_dst, "removed": removed}
