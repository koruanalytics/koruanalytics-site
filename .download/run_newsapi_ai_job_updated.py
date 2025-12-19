#!/usr/bin/env python
"""
scripts/run_newsapi_ai_job.py - Runner for multi-query ingestion

Usage:
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --date-start 2025-12-16 --date-end 2025-12-17
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --priority 1 2  # Only priority 1 and 2 groups
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --max-per-group 20 --max-total 100
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --skip-extract  # Skip incident extraction

Features:
- Multi-query strategy (one query per concept group)
- Automatic deduplication across queries
- Priority-based group filtering
- Incident extraction with ACLED classification
- API enrichment fields (source_title, category, concepts, etc.)
- Integrates with existing normalization and loading pipeline
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from loguru import logger

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.newsapi_ai_ingest import IngestParams, MultiQueryIngestor


def run_normalization(raw_path: Path) -> Path:
    """Run normalization on raw JSON file."""
    from src.processing.normalize_newsapi_ai import run_newsapi_ai_normalization, NormalizeParams
    params = NormalizeParams(
        raw_path=raw_path,
        out_dir=Path("data/interim/newsapi_ai"),
    )
    return run_newsapi_ai_normalization(params)


def run_dw_load(interim_path: Path) -> dict:
    """Load normalized data into DuckDB."""
    from src.processing.load_newsapi_ai_to_dw import load_newsapi_ai_into_duckdb
    load_newsapi_ai_into_duckdb(interim_path)
    return {"status": "ok"}


def run_dedupe(run_id: str) -> dict:
    """Run deduplication in DuckDB."""
    from src.processing.dedupe_newsapi_ai_in_duckdb import dedupe_newsapi_ai_in_duckdb
    return dedupe_newsapi_ai_in_duckdb(ingest_run_id=run_id)


def run_incident_extraction(run_id: str) -> dict:
    """
    Extract incidents from deduplicated articles.
    
    Uses ACLED classification and extracts API enrichment fields.
    """
    import duckdb
    import pandas as pd
    from src.utils.config import load_config
    from src.incidents.extract_baseline import extract_from_article
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    # Query articles with API enrichment fields
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
            -- API Enrichment fields
            source_title,
            is_duplicate,
            category_labels,
            location_label,
            concept_labels,
            -- GEO fields from API
            lat,
            lon,
            adm1,
            adm2,
            adm3
        FROM stg_news_newsapi_ai_dedup_run
        WHERE ingest_run_id = ?
        """,
        [run_id],
    ).df()
    
    if articles.empty:
        con.close()
        return {
            "status": "warning",
            "message": f"No articles found for run_id={run_id}",
            "extracted": 0,
        }
    
    extraction_version = cfg.get("incidents", {}).get("model_version", "acled_v2")
    
    # Extract incidents
    rows = []
    for _, r in articles.iterrows():
        rows.append(
            extract_from_article(
                r.to_dict(),
                ingest_run_id=run_id,
                extraction_version=extraction_version,
            )
        )
    
    df = pd.DataFrame(rows)
    
    # Idempotency: delete previous extraction for this run
    con.execute(
        "DELETE FROM stg_incidents_extracted WHERE ingest_run_id = ?",
        [run_id]
    )
    
    # Get table columns for robust insert
    table_cols = [
        r[0] for r in con.execute(
            "SELECT name FROM pragma_table_info('stg_incidents_extracted') ORDER BY cid"
        ).fetchall()
    ]
    
    # Only insert columns that exist in table
    common_cols = [c for c in table_cols if c in df.columns]
    
    if not common_cols:
        con.close()
        raise RuntimeError(
            f"No common columns between extraction and table.\n"
            f"df_cols={list(df.columns)}\n"
            f"table_cols={table_cols}"
        )
    
    # Register DataFrame and insert
    con.register("df_inc", df)
    cols_sql = ", ".join([f'"{c}"' for c in common_cols])
    con.execute(
        f"""
        INSERT INTO stg_incidents_extracted ({cols_sql})
        SELECT {cols_sql}
        FROM df_inc
        """
    )
    
    # Get stats
    inserted = con.execute(
        "SELECT COUNT(*) FROM stg_incidents_extracted WHERE ingest_run_id = ?",
        [run_id],
    ).fetchone()[0]
    
    # Enrichment stats
    enrichment = con.execute(
        """
        SELECT
            COUNT(*) as total,
            COUNT(source_title) as with_source,
            COUNT(api_category) as with_category,
            COUNT(api_location) as with_location,
            COUNT(concept_labels) as with_concepts
        FROM stg_incidents_extracted
        WHERE ingest_run_id = ?
        """,
        [run_id]
    ).fetchone()
    
    con.close()
    
    return {
        "status": "ok",
        "extracted": inserted,
        "version": extraction_version,
        "enrichment": {
            "total": enrichment[0],
            "with_source_title": enrichment[1],
            "with_category": enrichment[2],
            "with_location": enrichment[3],
            "with_concepts": enrichment[4],
        }
    }


def run_quality_checks(run_id: str, row_count: int, new_articles: int = None) -> list:
    """
    Run quality checks on ingested data.
    
    Args:
        run_id: Ingest run ID
        row_count: Total articles in dedup table
        new_articles: Articles new to this run (after historical dedup). 
                      If None, uses row_count.
    """
    checks = []
    
    # Check 1: Minimum rows ingested (before historical dedup)
    min_rows = 1
    checks.append({
        "check": "min_rows_ingested",
        "min_rows": min_rows,
        "value": row_count,
        "ok": row_count >= min_rows,
    })
    
    # Check 2: Maximum rows (sanity check)
    max_rows = 5000
    checks.append({
        "check": "max_rows",
        "max_rows": max_rows,
        "value": row_count,
        "ok": row_count <= max_rows,
    })
    
    # Check 3: New articles (informational, not a failure)
    # It's OK to have 0 new articles if we're re-ingesting the same date range
    if new_articles is not None:
        checks.append({
            "check": "new_articles",
            "value": new_articles,
            "ok": True,  # Always OK, just informational
            "info": "0 new = all articles already existed in previous runs"
        })
    
    return checks


def main():
    parser = argparse.ArgumentParser(
        description="NewsAPI.ai Multi-Query Ingestion Job (v2)"
    )
    parser.add_argument(
        "--scope",
        required=True,
        help="Path to scope YAML file (e.g., config/newsapi_scope_peru.yaml)"
    )
    parser.add_argument(
        "--date-start",
        help="Start date (YYYY-MM-DD). Default: yesterday"
    )
    parser.add_argument(
        "--date-end",
        help="End date (YYYY-MM-DD). Default: today"
    )
    parser.add_argument(
        "--max-per-group",
        type=int,
        default=50,
        help="Max articles per concept group (default: 50)"
    )
    parser.add_argument(
        "--max-total",
        type=int,
        default=200,
        help="Max total articles across all groups (default: 200)"
    )
    parser.add_argument(
        "--priority",
        type=int,
        nargs="+",
        help="Priority levels to query (e.g., --priority 1 2). Default: all"
    )
    parser.add_argument(
        "--skip-normalize",
        action="store_true",
        help="Skip normalization step"
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Skip DuckDB load step"
    )
    parser.add_argument(
        "--skip-dedupe",
        action="store_true",
        help="Skip deduplication step"
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip incident extraction step"
    )
    parser.add_argument(
        "--out-dir",
        default="data/raw/newsapi_ai",
        help="Output directory for raw JSON (default: data/raw/newsapi_ai)"
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Parse dates
    if args.date_end:
        end_date = date.fromisoformat(args.date_end)
    else:
        end_date = date.today()
    
    if args.date_start:
        start_date = date.fromisoformat(args.date_start)
    else:
        start_date = end_date - timedelta(days=1)
    
    # Validate scope file exists
    scope_path = Path(args.scope)
    if not scope_path.exists():
        logger.error(f"Scope file not found: {scope_path}")
        sys.exit(1)
    
    # =========================================================================
    # STEP 1: INGESTION (Multi-Query)
    # =========================================================================
    logger.info("[JOB] Starting multi-query ingestion v2")
    logger.info(f"[JOB] Scope: {scope_path}")
    logger.info(f"[JOB] Date range: {start_date} to {end_date}")
    logger.info(f"[JOB] Max per group: {args.max_per_group}, Max total: {args.max_total}")
    if args.priority:
        logger.info(f"[JOB] Priority filter: {args.priority}")
    
    params = IngestParams(
        scope_yaml=scope_path,
        out_dir=Path(args.out_dir),
        date_start=start_date,
        date_end=end_date,
        max_per_group=args.max_per_group,
        max_total=args.max_total,
        priority_filter=args.priority,
    )
    
    try:
        ingestor = MultiQueryIngestor(params)
        result = ingestor.run()
    except Exception as ex:
        logger.error(f"[JOB] Ingestion failed: {ex}")
        sys.exit(1)
    
    raw_path = result.output_path
    run_id = result.run_id
    
    logger.info(
        f"[JOB] Ingest OK: raw={raw_path} "
        f"groups={result.groups_queried} "
        f"total={result.total_articles} "
        f"unique={result.unique_articles} "
        f"run_id={run_id}"
    )
    
    # Log per-group results
    for gr in result.group_results:
        status = "✓" if not gr.error else "✗"
        logger.info(
            f"  {status} {gr.group_id}: found={gr.articles_found}, new={gr.articles_new}"
        )
    
    if result.errors:
        for err in result.errors:
            logger.warning(f"  Error: {err}")
    
    # =========================================================================
    # STEP 2: NORMALIZATION
    # =========================================================================
    if not args.skip_normalize:
        try:
            interim_path = run_normalization(raw_path)
            logger.info(f"[JOB] Normalize OK: {interim_path}")
        except Exception as ex:
            logger.error(f"[JOB] Normalization failed: {ex}")
            sys.exit(1)
    else:
        logger.info("[JOB] Skipping normalization")
        interim_path = None
    
    # =========================================================================
    # STEP 3: DW LOAD
    # =========================================================================
    if not args.skip_load and interim_path:
        try:
            run_dw_load(interim_path)
            logger.info("[JOB] DW Load OK")
        except Exception as ex:
            logger.error(f"[JOB] DW Load failed: {ex}")
            sys.exit(1)
    else:
        logger.info("[JOB] Skipping DW load")
    
    # =========================================================================
    # STEP 4: DEDUPLICATION
    # =========================================================================
    dedupe_result = None
    if not args.skip_dedupe:
        try:
            dedupe_result = run_dedupe(run_id)
            logger.info(
                f"[JOB] Dedupe OK: "
                f"run={dedupe_result.get('dedup_run', {})} "
                f"global={dedupe_result.get('dedup_global', {})}"
            )
        except Exception as ex:
            logger.error(f"[JOB] Dedupe failed: {ex}")
            sys.exit(1)
    else:
        logger.info("[JOB] Skipping deduplication")
    
    # =========================================================================
    # STEP 5: INCIDENT EXTRACTION (NEW)
    # =========================================================================
    extract_result = None
    if not args.skip_extract:
        try:
            extract_result = run_incident_extraction(run_id)
            if extract_result["status"] == "ok":
                enrichment = extract_result.get("enrichment", {})
                logger.success(
                    f"[JOB] Extract OK: "
                    f"incidents={extract_result['extracted']} "
                    f"version={extract_result['version']}"
                )
                logger.info(
                    f"[JOB] Enrichment: "
                    f"source_title={enrichment.get('with_source_title', 0)}/{enrichment.get('total', 0)}, "
                    f"category={enrichment.get('with_category', 0)}/{enrichment.get('total', 0)}, "
                    f"location={enrichment.get('with_location', 0)}/{enrichment.get('total', 0)}, "
                    f"concepts={enrichment.get('with_concepts', 0)}/{enrichment.get('total', 0)}"
                )
            else:
                logger.warning(f"[JOB] Extract warning: {extract_result.get('message')}")
        except Exception as ex:
            logger.error(f"[JOB] Extraction failed: {ex}")
            import traceback
            traceback.print_exc()
            # Don't exit - extraction failure shouldn't stop the job
    else:
        logger.info("[JOB] Skipping incident extraction")
    
    # =========================================================================
    # STEP 6: QUALITY CHECKS
    # =========================================================================
    # Use unique articles from ingestion (before historical dedup)
    ingested_rows = result.unique_articles
    
    # New articles after historical dedup
    new_articles = 0
    if dedupe_result and "dedup_run" in dedupe_result:
        new_articles = dedupe_result["dedup_run"].get("dst_rows", 0)
    
    checks = run_quality_checks(run_id, ingested_rows, new_articles)
    all_ok = all(c["ok"] for c in checks)
    
    if all_ok:
        incidents_extracted = extract_result["extracted"] if extract_result else 0
        logger.success(
            f"[JOB] COMPLETE: "
            f"run_id={run_id} "
            f"ingested={ingested_rows} "
            f"new={new_articles} "
            f"incidents={incidents_extracted}"
        )
        if new_articles == 0:
            logger.info("[JOB] Note: 0 new articles = all were already in previous runs (expected for repeated date ranges)")
    else:
        failed_checks = [c for c in checks if not c["ok"]]
        logger.error(f"[JOB] FAILED checks: {failed_checks}")
        sys.exit(1)


if __name__ == "__main__":
    main()
