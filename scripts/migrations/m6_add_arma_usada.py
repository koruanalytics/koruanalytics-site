"""
scripts/migrations/m6_add_arma_usada.py

Migration M6: Add arma_usada column to silver_news_enriched and gold_incidents.

This migration adds the arma_usada field for weapon type analysis in violent incidents.
Safe to run multiple times (idempotent).

Valid values: arma_fuego, arma_blanca, objeto_contundente, explosivo, 
              vehiculo, fuego, veneno, ninguna, desconocida, no_aplica

Usage:
    python -m scripts.migrations.m6_add_arma_usada --check
    python -m scripts.migrations.m6_add_arma_usada --apply
    python -m scripts.migrations.m6_add_arma_usada --rollback

Last updated: 2026-01-18
"""
from __future__ import annotations

import os
import argparse
from datetime import datetime

import duckdb
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/osint_dw.duckdb")

MIGRATION_NAME = "M6_arma_usada"
MIGRATION_VERSION = "2026-01-18"


def check_column_exists(con: duckdb.DuckDBPyConnection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    try:
        result = con.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = '{column}'
        """).fetchone()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking column {table}.{column}: {e}")
        return False


def check_migration_status(db_path: str = DB_PATH) -> dict:
    """
    Check current migration status.
    Returns dict with status for each table.
    """
    con = duckdb.connect(db_path)
    
    status = {
        "migration": MIGRATION_NAME,
        "version": MIGRATION_VERSION,
        "tables": {}
    }
    
    # Check silver_news_enriched
    silver_exists = check_column_exists(con, "silver_news_enriched", "arma_usada")
    status["tables"]["silver_news_enriched"] = {
        "column_exists": silver_exists,
        "needs_migration": not silver_exists
    }
    
    # Check gold_incidents
    gold_exists = check_column_exists(con, "gold_incidents", "arma_usada")
    status["tables"]["gold_incidents"] = {
        "column_exists": gold_exists,
        "needs_migration": not gold_exists
    }
    
    # Get row counts
    try:
        silver_count = con.execute("SELECT COUNT(*) FROM silver_news_enriched").fetchone()[0]
        status["tables"]["silver_news_enriched"]["row_count"] = silver_count
    except:
        status["tables"]["silver_news_enriched"]["row_count"] = 0
    
    try:
        gold_count = con.execute("SELECT COUNT(*) FROM gold_incidents").fetchone()[0]
        status["tables"]["gold_incidents"]["row_count"] = gold_count
    except:
        status["tables"]["gold_incidents"]["row_count"] = 0
    
    status["needs_migration"] = any(
        t["needs_migration"] for t in status["tables"].values()
    )
    
    con.close()
    return status


def apply_migration(db_path: str = DB_PATH, dry_run: bool = False) -> dict:
    """
    Apply the M6 migration to add arma_usada column.
    
    Args:
        db_path: Path to DuckDB database
        dry_run: If True, only show what would be done
        
    Returns:
        Dict with migration results
    """
    con = duckdb.connect(db_path)
    
    results = {
        "migration": MIGRATION_NAME,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "changes": []
    }
    
    # Migration for silver_news_enriched
    if not check_column_exists(con, "silver_news_enriched", "arma_usada"):
        sql = """
            ALTER TABLE silver_news_enriched 
            ADD COLUMN arma_usada VARCHAR
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {sql}")
            results["changes"].append({
                "table": "silver_news_enriched",
                "action": "ADD COLUMN arma_usada",
                "status": "pending"
            })
        else:
            try:
                con.execute(sql)
                logger.success("Added arma_usada to silver_news_enriched")
                results["changes"].append({
                    "table": "silver_news_enriched",
                    "action": "ADD COLUMN arma_usada",
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error adding column to silver: {e}")
                results["changes"].append({
                    "table": "silver_news_enriched",
                    "action": "ADD COLUMN arma_usada",
                    "status": "error",
                    "error": str(e)
                })
    else:
        logger.info("silver_news_enriched.arma_usada already exists")
        results["changes"].append({
            "table": "silver_news_enriched",
            "action": "ADD COLUMN arma_usada",
            "status": "already_exists"
        })
    
    # Migration for gold_incidents
    if not check_column_exists(con, "gold_incidents", "arma_usada"):
        sql = """
            ALTER TABLE gold_incidents 
            ADD COLUMN arma_usada VARCHAR
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {sql}")
            results["changes"].append({
                "table": "gold_incidents",
                "action": "ADD COLUMN arma_usada",
                "status": "pending"
            })
        else:
            try:
                con.execute(sql)
                logger.success("Added arma_usada to gold_incidents")
                results["changes"].append({
                    "table": "gold_incidents",
                    "action": "ADD COLUMN arma_usada",
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error adding column to gold: {e}")
                results["changes"].append({
                    "table": "gold_incidents",
                    "action": "ADD COLUMN arma_usada",
                    "status": "error",
                    "error": str(e)
                })
    else:
        logger.info("gold_incidents.arma_usada already exists")
        results["changes"].append({
            "table": "gold_incidents",
            "action": "ADD COLUMN arma_usada",
            "status": "already_exists"
        })
    
    con.close()
    
    # Summary
    success_count = sum(1 for c in results["changes"] if c["status"] in ("success", "already_exists"))
    results["success"] = success_count == len(results["changes"])
    
    return results


def rollback_migration(db_path: str = DB_PATH, dry_run: bool = False) -> dict:
    """
    Rollback the M6 migration by removing arma_usada column.
    WARNING: This will delete all arma_usada data!
    
    Args:
        db_path: Path to DuckDB database
        dry_run: If True, only show what would be done
        
    Returns:
        Dict with rollback results
    """
    con = duckdb.connect(db_path)
    
    results = {
        "migration": MIGRATION_NAME,
        "action": "ROLLBACK",
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "changes": []
    }
    
    # Rollback for silver_news_enriched
    if check_column_exists(con, "silver_news_enriched", "arma_usada"):
        sql = "ALTER TABLE silver_news_enriched DROP COLUMN arma_usada"
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {sql}")
            results["changes"].append({
                "table": "silver_news_enriched",
                "action": "DROP COLUMN arma_usada",
                "status": "pending"
            })
        else:
            try:
                con.execute(sql)
                logger.warning("Dropped arma_usada from silver_news_enriched")
                results["changes"].append({
                    "table": "silver_news_enriched",
                    "action": "DROP COLUMN arma_usada",
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error dropping column from silver: {e}")
                results["changes"].append({
                    "table": "silver_news_enriched",
                    "action": "DROP COLUMN arma_usada",
                    "status": "error",
                    "error": str(e)
                })
    else:
        logger.info("silver_news_enriched.arma_usada does not exist")
        results["changes"].append({
            "table": "silver_news_enriched",
            "action": "DROP COLUMN arma_usada",
            "status": "not_exists"
        })
    
    # Rollback for gold_incidents
    if check_column_exists(con, "gold_incidents", "arma_usada"):
        sql = "ALTER TABLE gold_incidents DROP COLUMN arma_usada"
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {sql}")
            results["changes"].append({
                "table": "gold_incidents",
                "action": "DROP COLUMN arma_usada",
                "status": "pending"
            })
        else:
            try:
                con.execute(sql)
                logger.warning("Dropped arma_usada from gold_incidents")
                results["changes"].append({
                    "table": "gold_incidents",
                    "action": "DROP COLUMN arma_usada",
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error dropping column from gold: {e}")
                results["changes"].append({
                    "table": "gold_incidents",
                    "action": "DROP COLUMN arma_usada",
                    "status": "error",
                    "error": str(e)
                })
    else:
        logger.info("gold_incidents.arma_usada does not exist")
        results["changes"].append({
            "table": "gold_incidents",
            "action": "DROP COLUMN arma_usada",
            "status": "not_exists"
        })
    
    con.close()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="M6 Migration: Add arma_usada column"
    )
    parser.add_argument("--check", action="store_true",
                        help="Check migration status without making changes")
    parser.add_argument("--apply", action="store_true",
                        help="Apply the migration")
    parser.add_argument("--rollback", action="store_true",
                        help="Rollback the migration (WARNING: deletes data)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--db", type=str, default=DB_PATH,
                        help=f"Path to database (default: {DB_PATH})")
    
    args = parser.parse_args()
    
    if args.check:
        print("\n" + "=" * 50)
        print(f"MIGRATION CHECK: {MIGRATION_NAME}")
        print("=" * 50)
        
        status = check_migration_status(args.db)
        
        print(f"\nMigration: {status['migration']} (v{status['version']})")
        print(f"Needs migration: {status['needs_migration']}")
        print("\nTable Status:")
        
        for table, info in status["tables"].items():
            icon = "✓" if info["column_exists"] else "✗"
            print(f"  {icon} {table}")
            print(f"      Column exists: {info['column_exists']}")
            print(f"      Row count: {info['row_count']}")
            print(f"      Needs migration: {info['needs_migration']}")
    
    elif args.apply:
        print("\n" + "=" * 50)
        print(f"APPLYING MIGRATION: {MIGRATION_NAME}")
        print("=" * 50)
        
        if args.dry_run:
            print("\n[DRY RUN MODE - No changes will be made]\n")
        
        results = apply_migration(args.db, dry_run=args.dry_run)
        
        print(f"\nResults:")
        print(f"  Success: {results['success']}")
        print(f"  Changes:")
        for change in results["changes"]:
            print(f"    - {change['table']}: {change['action']} → {change['status']}")
    
    elif args.rollback:
        print("\n" + "=" * 50)
        print(f"ROLLBACK MIGRATION: {MIGRATION_NAME}")
        print("=" * 50)
        print("\n⚠️  WARNING: This will DELETE all arma_usada data!")
        
        if args.dry_run:
            print("\n[DRY RUN MODE - No changes will be made]\n")
            results = rollback_migration(args.db, dry_run=True)
        else:
            confirm = input("\nType 'ROLLBACK' to confirm: ")
            if confirm == "ROLLBACK":
                results = rollback_migration(args.db, dry_run=False)
            else:
                print("Rollback cancelled.")
                exit(0)
        
        print(f"\nResults:")
        for change in results["changes"]:
            print(f"  - {change['table']}: {change['action']} → {change['status']}")
    
    else:
        parser.print_help()
