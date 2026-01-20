"""
scripts/migrations/m9_fix_unicode_encoding.py
Last updated: 2026-01-16
Description: Migration script to fix Unicode escape sequences in existing data.

M9 FIX: Normalizes \\uXXXX escapes to actual characters in silver and gold tables.

USAGE:
    python scripts/migrations/m9_fix_unicode_encoding.py --dry-run   # Preview changes
    python scripts/migrations/m9_fix_unicode_encoding.py --apply     # Apply changes

AFFECTED TABLES:
    - silver_news_enriched: actores_json, organizaciones_json
    - gold_incidents: actores, organizaciones
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.text_utils import normalize_unicode, has_unicode_escapes


def fix_silver_encoding(con: duckdb.DuckDBPyConnection, dry_run: bool = True) -> dict:
    """
    Fix Unicode escapes in silver_news_enriched.
    
    Fields: actores_json, organizaciones_json
    """
    stats = {"actores_json": 0, "organizaciones_json": 0}
    
    # Get records with escapes in actores_json
    actores_records = con.execute("""
        SELECT incident_id, actores_json 
        FROM silver_news_enriched 
        WHERE actores_json LIKE '%\\u00%'
    """).fetchall()
    
    logger.info(f"[silver] Found {len(actores_records)} records with escapes in actores_json")
    
    if not dry_run and actores_records:
        for incident_id, actores_json in actores_records:
            fixed = normalize_unicode(actores_json)
            con.execute("""
                UPDATE silver_news_enriched 
                SET actores_json = ? 
                WHERE incident_id = ?
            """, [fixed, incident_id])
            stats["actores_json"] += 1
    else:
        stats["actores_json"] = len(actores_records)
    
    # Get records with escapes in organizaciones_json
    orgs_records = con.execute("""
        SELECT incident_id, organizaciones_json 
        FROM silver_news_enriched 
        WHERE organizaciones_json LIKE '%\\u00%'
    """).fetchall()
    
    logger.info(f"[silver] Found {len(orgs_records)} records with escapes in organizaciones_json")
    
    if not dry_run and orgs_records:
        for incident_id, organizaciones_json in orgs_records:
            fixed = normalize_unicode(organizaciones_json)
            con.execute("""
                UPDATE silver_news_enriched 
                SET organizaciones_json = ? 
                WHERE incident_id = ?
            """, [fixed, incident_id])
            stats["organizaciones_json"] += 1
    else:
        stats["organizaciones_json"] = len(orgs_records)
    
    return stats


def fix_gold_encoding(con: duckdb.DuckDBPyConnection, dry_run: bool = True) -> dict:
    """
    Fix Unicode escapes in gold_incidents.
    
    Fields: actores, organizaciones, titulo, resumen, ubicacion_display
    """
    stats = {"actores": 0, "organizaciones": 0, "other": 0}
    
    # Get records with escapes in actores
    actores_records = con.execute("""
        SELECT incident_id, actores 
        FROM gold_incidents 
        WHERE actores LIKE '%\\u00%'
    """).fetchall()
    
    logger.info(f"[gold] Found {len(actores_records)} records with escapes in actores")
    
    if not dry_run and actores_records:
        for incident_id, actores in actores_records:
            fixed = normalize_unicode(actores)
            con.execute("""
                UPDATE gold_incidents 
                SET actores = ? 
                WHERE incident_id = ?
            """, [fixed, incident_id])
            stats["actores"] += 1
    else:
        stats["actores"] = len(actores_records)
    
    # Get records with escapes in organizaciones
    orgs_records = con.execute("""
        SELECT incident_id, organizaciones 
        FROM gold_incidents 
        WHERE organizaciones LIKE '%\\u00%'
    """).fetchall()
    
    logger.info(f"[gold] Found {len(orgs_records)} records with escapes in organizaciones")
    
    if not dry_run and orgs_records:
        for incident_id, organizaciones in orgs_records:
            fixed = normalize_unicode(organizaciones)
            con.execute("""
                UPDATE gold_incidents 
                SET organizaciones = ? 
                WHERE incident_id = ?
            """, [fixed, incident_id])
            stats["organizaciones"] += 1
    else:
        stats["organizaciones"] = len(orgs_records)
    
    # Check other text fields (titulo, resumen, ubicacion_display)
    other_fields = ['titulo', 'resumen', 'ubicacion_display']
    for field in other_fields:
        count = con.execute(f"""
            SELECT COUNT(*) FROM gold_incidents 
            WHERE {field} LIKE '%\\u00%'
        """).fetchone()[0]
        
        if count > 0:
            logger.info(f"[gold] Found {count} records with escapes in {field}")
            
            if not dry_run:
                records = con.execute(f"""
                    SELECT incident_id, {field} 
                    FROM gold_incidents 
                    WHERE {field} LIKE '%\\u00%'
                """).fetchall()
                
                for incident_id, value in records:
                    fixed = normalize_unicode(value)
                    con.execute(f"""
                        UPDATE gold_incidents 
                        SET {field} = ? 
                        WHERE incident_id = ?
                    """, [fixed, incident_id])
                    stats["other"] += 1
    
    return stats


def run_migration(db_path: str, dry_run: bool = True) -> dict:
    """
    Run the M9 encoding migration.
    
    Args:
        db_path: Path to DuckDB database
        dry_run: If True, only report what would be changed
        
    Returns:
        Migration statistics
    """
    mode = "DRY RUN" if dry_run else "APPLYING CHANGES"
    logger.info(f"=" * 60)
    logger.info(f"M9 ENCODING MIGRATION - {mode}")
    logger.info(f"=" * 60)
    logger.info(f"Database: {db_path}")
    
    con = duckdb.connect(db_path, read_only=dry_run)
    
    try:
        # Fix silver
        logger.info("\n[1/2] Processing silver_news_enriched...")
        silver_stats = fix_silver_encoding(con, dry_run)
        
        # Fix gold
        logger.info("\n[2/2] Processing gold_incidents...")
        gold_stats = fix_gold_encoding(con, dry_run)
        
        if not dry_run:
            # Commit changes (DuckDB auto-commits, but explicit is clearer)
            logger.info("\nChanges committed to database.")
        
    finally:
        con.close()
    
    # Summary
    total_silver = sum(silver_stats.values())
    total_gold = sum(gold_stats.values())
    total = total_silver + total_gold
    
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Silver records {'to fix' if dry_run else 'fixed'}: {total_silver}")
    for k, v in silver_stats.items():
        logger.info(f"  - {k}: {v}")
    logger.info(f"Gold records {'to fix' if dry_run else 'fixed'}: {total_gold}")
    for k, v in gold_stats.items():
        logger.info(f"  - {k}: {v}")
    logger.info(f"Total: {total}")
    
    if dry_run:
        logger.warning("\nThis was a DRY RUN. No changes were made.")
        logger.info("Run with --apply to apply changes.")
    else:
        logger.success("\nMigration completed successfully!")
    
    return {
        "silver": silver_stats,
        "gold": gold_stats,
        "total": total,
        "dry_run": dry_run
    }


def verify_migration(db_path: str) -> bool:
    """
    Verify that no Unicode escapes remain in the database.
    """
    con = duckdb.connect(db_path, read_only=True)
    
    checks = [
        ("silver_news_enriched", "actores_json"),
        ("silver_news_enriched", "organizaciones_json"),
        ("gold_incidents", "actores"),
        ("gold_incidents", "organizaciones"),
        ("gold_incidents", "titulo"),
        ("gold_incidents", "resumen"),
        ("gold_incidents", "ubicacion_display"),
    ]
    
    issues = []
    for table, column in checks:
        count = con.execute(f"""
            SELECT COUNT(*) FROM {table} 
            WHERE {column} LIKE '%\\u00%'
        """).fetchone()[0]
        
        if count > 0:
            issues.append(f"{table}.{column}: {count} records")
    
    con.close()
    
    if issues:
        logger.error("VERIFICATION FAILED - Escapes still found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    else:
        logger.success("VERIFICATION PASSED - No Unicode escapes found!")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="M9 Migration: Fix Unicode encoding in existing data"
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("DB_PATH", "data/osint_dw.duckdb"),
        help="Path to DuckDB database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify that migration was successful"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_migration(args.db_path)
        exit(0 if success else 1)
    
    if not args.dry_run and not args.apply:
        print("ERROR: Must specify either --dry-run or --apply")
        print("\nUsage:")
        print("  python scripts/migrations/m9_fix_unicode_encoding.py --dry-run")
        print("  python scripts/migrations/m9_fix_unicode_encoding.py --apply")
        print("  python scripts/migrations/m9_fix_unicode_encoding.py --verify")
        exit(1)
    
    result = run_migration(
        db_path=args.db_path,
        dry_run=not args.apply
    )
    
    exit(0 if result["total"] >= 0 else 1)
