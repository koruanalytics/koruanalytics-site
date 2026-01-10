"""
scripts/utils/init_medallion_tables.py

Initializes Medallion architecture tables (bronze, silver, gold).
Uses DDL definitions from src/db/schema.py as single source of truth.

Usage:
    python -m scripts.utils.init_medallion_tables
    python -m scripts.utils.init_medallion_tables --check-only
    python -m scripts.utils.init_medallion_tables --drop-recreate

Last updated: 2026-01-09
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
from loguru import logger

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db.schema import (
    BRONZE_NEWS_DDL,
    SILVER_NEWS_ENRICHED_DDL,
    GOLD_INCIDENTS_DDL,
    GOLD_DAILY_STATS_DDL,
    MEDALLION_DDLS,
    init_medallion_tables,
)

DB_PATH = "data/osint_dw.duckdb"


def get_table_info(con, table_name: str) -> dict:
    """Get information about a table."""
    try:
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        cols = con.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """).fetchdf()
        return {
            "exists": True,
            "row_count": count,
            "column_count": len(cols),
            "columns": cols['column_name'].tolist()
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}


def check_tables(con) -> dict:
    """Check status of all Medallion tables."""
    tables = ['bronze_news', 'silver_news_enriched', 'gold_incidents', 'gold_daily_stats']
    results = {}
    
    for table in tables:
        results[table] = get_table_info(con, table)
    
    return results


def drop_tables(con, tables: list):
    """Drop specified tables."""
    for table in tables:
        try:
            con.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"Dropped table: {table}")
        except Exception as e:
            logger.error(f"Error dropping {table}: {e}")


def create_tables(con) -> dict:
    """Create Medallion tables using DDLs from schema.py."""
    results = init_medallion_tables(con)
    return results


def main():
    parser = argparse.ArgumentParser(description="Initialize Medallion tables")
    parser.add_argument("--check-only", action="store_true",
                        help="Only check table status, don't create")
    parser.add_argument("--drop-recreate", action="store_true",
                        help="Drop and recreate tables (WARNING: data loss!)")
    parser.add_argument("--db-path", default=DB_PATH,
                        help=f"Path to DuckDB database (default: {DB_PATH})")
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    Path(args.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    con = duckdb.connect(args.db_path)
    
    print("\n" + "=" * 60)
    print("MEDALLION TABLES INITIALIZATION")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    
    # Check current status
    print("\n--- Current Status ---")
    status = check_tables(con)
    
    all_exist = True
    for table, info in status.items():
        if info['exists']:
            print(f"  ✅ {table:25} {info['row_count']:>6} rows, {info['column_count']} columns")
        else:
            print(f"  ❌ {table:25} MISSING")
            all_exist = False
    
    if args.check_only:
        con.close()
        print("\n--- Check Complete ---")
        return 0 if all_exist else 1
    
    # Drop and recreate if requested
    if args.drop_recreate:
        print("\n--- Dropping Tables ---")
        print("⚠️  WARNING: This will delete all data!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("Aborted.")
            con.close()
            return 1
        
        drop_tables(con, ['gold_daily_stats', 'gold_incidents', 'silver_news_enriched', 'bronze_news'])
    
    # Create tables
    print("\n--- Creating Tables ---")
    results = create_tables(con)
    
    for table, result in results.items():
        if result == "created":
            print(f"  ✅ {table}: created")
        else:
            print(f"  ❌ {table}: {result}")
    
    # Verify
    print("\n--- Verification ---")
    final_status = check_tables(con)
    
    for table, info in final_status.items():
        if info['exists']:
            print(f"  ✅ {table:25} ready ({info['column_count']} columns)")
        else:
            print(f"  ❌ {table:25} FAILED: {info.get('error', 'unknown')}")
    
    con.close()
    
    print("\n" + "=" * 60)
    print("INITIALIZATION COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
