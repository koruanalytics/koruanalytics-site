#!/usr/bin/env python
"""
scripts/migrations/m4_add_motivo_aparente.py

M4 Migration: Add motivo_aparente column to silver_news_enriched and gold_incidents.

This migration adds a new field to track the apparent motive/cause of incidents,
enabling pattern analysis of violence motivations.

Valid values for motivo_aparente:
- robo: Theft, assault, robbery
- ajuste_cuentas: Criminal settling of scores, revenge
- violencia_familiar: Domestic violence
- riña: Fight, brawl, altercation
- resistencia_autoridad: Resisting arrest, confrontation with police
- extorsion: Refusal to pay extortion
- pasional: Crime of passion, jealousy
- politico: Political, electoral motivation
- desconocido: Unknown or unclear motive
- accidental: Accidental, no criminal intent

Usage:
    python -m scripts.migrations.m4_add_motivo_aparente --dry-run
    python -m scripts.migrations.m4_add_motivo_aparente --apply

Last updated: 2026-01-18
"""
from __future__ import annotations

import argparse
import os
import sys

import duckdb
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DB_PATH = os.getenv("DB_PATH", "data/osint_dw.duckdb")


def check_column_exists(con: duckdb.DuckDBPyConnection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    result = con.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}'
    """).fetchone()
    return result is not None


def run_migration(dry_run: bool = True):
    """
    Run M4 migration to add motivo_aparente column.
    
    Args:
        dry_run: If True, only show what would be done without making changes.
    """
    logger.info("=" * 60)
    logger.info("M4 MIGRATION: Add motivo_aparente column")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    logger.info("=" * 60)
    
    con = duckdb.connect(DB_PATH)
    
    migrations = [
        {
            'table': 'silver_news_enriched',
            'column': 'motivo_aparente',
            'ddl': "ALTER TABLE silver_news_enriched ADD COLUMN motivo_aparente VARCHAR DEFAULT 'desconocido'"
        },
        {
            'table': 'gold_incidents',
            'column': 'motivo_aparente',
            'ddl': "ALTER TABLE gold_incidents ADD COLUMN motivo_aparente VARCHAR DEFAULT 'desconocido'"
        }
    ]
    
    changes_needed = []
    
    for mig in migrations:
        exists = check_column_exists(con, mig['table'], mig['column'])
        if exists:
            logger.info(f"✓ {mig['table']}.{mig['column']} already exists - skipping")
        else:
            logger.info(f"○ {mig['table']}.{mig['column']} MISSING - will add")
            changes_needed.append(mig)
    
    if not changes_needed:
        logger.success("No changes needed - migration already applied")
        con.close()
        return {"status": "already_applied", "changes": 0}
    
    logger.info(f"\n{len(changes_needed)} change(s) needed:")
    for mig in changes_needed:
        logger.info(f"  - {mig['ddl']}")
    
    if dry_run:
        logger.warning("\nDRY RUN - no changes applied")
        logger.info("Run with --apply to execute migration")
        con.close()
        return {"status": "dry_run", "changes": len(changes_needed)}
    
    # Apply changes
    logger.info("\nApplying changes...")
    applied = 0
    
    for mig in changes_needed:
        try:
            con.execute(mig['ddl'])
            logger.success(f"  ✓ Added {mig['table']}.{mig['column']}")
            applied += 1
        except Exception as e:
            logger.error(f"  ✗ Failed to add {mig['table']}.{mig['column']}: {e}")
    
    # Verify
    logger.info("\nVerifying migration...")
    for mig in migrations:
        exists = check_column_exists(con, mig['table'], mig['column'])
        status = "✓" if exists else "✗"
        logger.info(f"  {status} {mig['table']}.{mig['column']}")
    
    # Show current row counts
    logger.info("\nCurrent table counts:")
    for table in ['silver_news_enriched', 'gold_incidents']:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count} rows")
        except Exception as e:
            logger.warning(f"  {table}: ERROR - {e}")
    
    con.close()
    
    logger.success(f"\nMigration complete: {applied}/{len(changes_needed)} changes applied")
    return {"status": "applied", "changes": applied}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="M4 Migration: Add motivo_aparente column"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        default=True,
        help="Show what would be done without making changes (default)"
    )
    parser.add_argument(
        "--apply", 
        action="store_true",
        help="Actually apply the migration"
    )
    
    args = parser.parse_args()
    
    # --apply overrides default --dry-run
    dry_run = not args.apply
    
    result = run_migration(dry_run=dry_run)
    
    # Exit code based on result
    if result["status"] == "applied" and result["changes"] > 0:
        sys.exit(0)
    elif result["status"] == "already_applied":
        sys.exit(0)
    elif result["status"] == "dry_run":
        sys.exit(0)
    else:
        sys.exit(1)
