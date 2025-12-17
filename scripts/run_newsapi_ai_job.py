#!/usr/bin/env python
"""
scripts/run_newsapi_ai_job.py - Runner for multi-query ingestion

Usage:
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru_2026.yaml
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru_2026.yaml --date-start 2025-12-16 --date-end 2025-12-17
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru_2026.yaml --priority 1 2  # Only priority 1 and 2 groups
    python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru_2026.yaml --max-per-group 20 --max-total 100

Features:
- Multi-query strategy (one query per concept group)
- Automatic deduplication across queries
- Priority-based group filtering
- Integrates with existing normalization and loading pipeline
"""
from __future__ import annotations

import argparse
import subprocess
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


def run_quality_checks(run_id: str, row_count: int) -> list:
    """Run quality checks on ingested data."""
    checks = []
    
    # Check 1: Minimum rows
    min_rows = 1
    checks.append({
        "check": "min_rows",
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
    
    return checks


def main():
    parser = argparse.ArgumentParser(
        description="NewsAPI.ai Multi-Query Ingestion Job (v2)"
    )
    parser.add_argument(
        "--scope",
        required=True,
        help="Path to scope YAML file (e.g., config/newsapi_scope_peru_2026.yaml)"
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
    logger.info(f"[JOB] Starting multi-query ingestion v2")
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
            load_result = run_dw_load(interim_path)
            logger.info(f"[JOB] DW Load OK")
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
    # STEP 5: QUALITY CHECKS
    # =========================================================================
    final_rows = result.unique_articles
    if dedupe_result and "dedup_run" in dedupe_result:
        final_rows = dedupe_result["dedup_run"].get("dst_rows", final_rows)
    
    checks = run_quality_checks(run_id, final_rows)
    all_ok = all(c["ok"] for c in checks)
    
    if all_ok:
        logger.success(
            f"[JOB] OK: "
            f"RAW_GROUPS={result.groups_queried} "
            f"RAW_TOTAL={result.total_articles} "
            f"RAW_UNIQUE={result.unique_articles} "
            f"DEDUP_RUN={dedupe_result.get('dedup_run', {}) if dedupe_result else 'skipped'} "
            f"checks={checks}"
        )
    else:
        failed_checks = [c for c in checks if not c["ok"]]
        logger.error(f"[JOB] FAILED checks: {failed_checks}")
        sys.exit(1)


if __name__ == "__main__":
    main()
