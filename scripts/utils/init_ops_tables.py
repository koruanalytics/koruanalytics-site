# init_ops_tables.py
# Last updated: 2026-01-09
# Description: Initialize operational tables for pipeline monitoring and alerting
# Schema version: 2.1 - Aligned with actual production schema + migrations

"""
Operational Tables Schema for OSINT Peru 2026

This module defines and initializes tables used for:
- Pipeline execution tracking (ops_pipeline_runs)
- Alert management with incident traceability (ops_alerts)
- Operational metrics logging (ops_metrics)

Usage:
    python -m scripts.utils.init_ops_tables
    python -m scripts.utils.init_ops_tables --reset
    python -m scripts.utils.init_ops_tables --verify
"""

import argparse
import duckdb
from pathlib import Path
from loguru import logger
from datetime import datetime


# Database path - adjust if your project uses different location
DB_PATH = Path("data/osint_dw.duckdb")


def get_ops_tables_ddl() -> dict[str, str]:
    """
    Return DDL statements for all operational tables.
    
    Schema version 2.2 - Aligned with actual production schema.
    
    Tables:
    - ops_alerts: Alert management with incident traceability
    - ops_ingest_runs: Pipeline execution tracking with detailed metrics
    
    Returns:
        Dictionary mapping table_name -> CREATE TABLE statement
    """
    return {
        # Ingest run tracking - matches actual production schema
        "ops_ingest_runs": """
            CREATE TABLE IF NOT EXISTS ops_ingest_runs (
                run_id VARCHAR PRIMARY KEY,
                job_name VARCHAR,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status VARCHAR DEFAULT 'running',
                params_json VARCHAR,
                raw_rows BIGINT DEFAULT 0,
                interim_rows BIGINT DEFAULT 0,
                stg_rows BIGINT DEFAULT 0,
                dedup_run_rows BIGINT DEFAULT 0,
                dedup_total_rows BIGINT DEFAULT 0,
                incidents_extracted_rows BIGINT DEFAULT 0,
                incidents_fact_rows BIGINT DEFAULT 0,
                exit_code INTEGER,
                log_path VARCHAR
            )
        """,
        
        # Alert management - aligned with production + all migrations
        "ops_alerts": """
            CREATE TABLE IF NOT EXISTS ops_alerts (
                alert_id VARCHAR PRIMARY KEY,
                run_id VARCHAR,
                pipeline_name VARCHAR,
                alert_type VARCHAR,
                severity VARCHAR NOT NULL DEFAULT 'info',
                message VARCHAR NOT NULL,
                incident_id VARCHAR,
                context_json VARCHAR,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by VARCHAR
            )
        """
    }


def get_expected_columns() -> dict[str, list[str]]:
    """
    Return expected columns for each table (for validation).
    
    Returns:
        Dictionary mapping table_name -> list of column names
    """
    return {
        "ops_ingest_runs": [
            "run_id", "job_name", "started_at", "ended_at", "status",
            "params_json", "raw_rows", "interim_rows", "stg_rows",
            "dedup_run_rows", "dedup_total_rows", "incidents_extracted_rows",
            "incidents_fact_rows", "exit_code", "log_path"
        ],
        "ops_alerts": [
            "alert_id", "run_id", "pipeline_name", "alert_type", "severity",
            "message", "incident_id", "context_json", "is_active",
            "created_at", "resolved_at", "resolved_by"
        ]
    }


def init_ops_tables(db_path: Path = DB_PATH, reset: bool = False) -> dict[str, int]:
    """
    Initialize operational tables in DuckDB.
    
    Args:
        db_path: Path to DuckDB database file
        reset: If True, drop existing tables before creating
        
    Returns:
        Dictionary with table names and row counts after initialization
    """
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {db_path.parent}")
    
    con = duckdb.connect(str(db_path))
    tables_ddl = get_ops_tables_ddl()
    results = {}
    
    try:
        for table_name, ddl in tables_ddl.items():
            if reset:
                logger.warning(f"Dropping table: {table_name}")
                con.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            logger.info(f"Creating table: {table_name}")
            con.execute(ddl)
            
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            results[table_name] = count
            logger.info(f"  → {table_name}: {count} rows")
        
        con.commit()
        logger.success("Operational tables initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing tables: {e}")
        raise
    finally:
        con.close()
    
    return results


def verify_schema(db_path: Path = DB_PATH) -> dict[str, dict]:
    """
    Verify current schema of operational tables against expected.
    
    Args:
        db_path: Path to DuckDB database file
        
    Returns:
        Dictionary with verification results per table
    """
    con = duckdb.connect(str(db_path), read_only=True)
    expected = get_expected_columns()
    results = {}
    
    try:
        for table_name, expected_cols in expected.items():
            try:
                actual = con.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """).fetchall()
                actual_cols = [col[0] for col in actual]
                
                missing = set(expected_cols) - set(actual_cols)
                extra = set(actual_cols) - set(expected_cols)
                
                results[table_name] = {
                    'exists': True,
                    'actual_columns': actual_cols,
                    'expected_columns': expected_cols,
                    'missing': list(missing),
                    'extra': list(extra),
                    'aligned': len(missing) == 0
                }
            except Exception:
                results[table_name] = {
                    'exists': False,
                    'actual_columns': [],
                    'expected_columns': expected_cols,
                    'missing': expected_cols,
                    'extra': [],
                    'aligned': False
                }
                
    finally:
        con.close()
    
    return results


def print_verification(results: dict):
    """Print verification results."""
    print("\n" + "=" * 60)
    print("SCHEMA VERIFICATION REPORT")
    print("=" * 60)
    
    all_aligned = True
    
    for table_name, info in results.items():
        status = "✅" if info['aligned'] else "⚠️"
        exists = "EXISTS" if info['exists'] else "MISSING"
        print(f"\n{status} {table_name} ({exists})")
        
        if not info['exists']:
            print(f"   Table does not exist - run init_ops_tables.py")
            all_aligned = False
            continue
        
        if info['missing']:
            print(f"   Missing columns: {info['missing']}")
            all_aligned = False
        
        if info['extra']:
            print(f"   Extra columns (OK): {info['extra']}")
        
        if info['aligned']:
            print(f"   All {len(info['expected_columns'])} expected columns present")
    
    print("\n" + "=" * 60)
    if all_aligned:
        print("✅ All tables aligned with expected schema")
    else:
        print("⚠️  Schema misalignment detected - run migrations or --reset")
    print("=" * 60 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize operational tables for OSINT Peru 2026"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all operational tables (WARNING: data loss)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify schema alignment without modifying"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help=f"Path to DuckDB database (default: {DB_PATH})"
    )
    
    args = parser.parse_args()
    db_path = Path(args.db)
    
    if args.verify:
        results = verify_schema(db_path)
        print_verification(results)
        return
    
    if args.reset:
        confirm = input("WARNING: This will delete all data in ops tables. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
    
    print(f"\n=== Initializing Operational Tables ===")
    print(f"Database: {db_path}")
    print(f"Reset mode: {args.reset}\n")
    
    results = init_ops_tables(db_path, reset=args.reset)
    
    print("\n=== Results ===")
    for table, count in results.items():
        print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
