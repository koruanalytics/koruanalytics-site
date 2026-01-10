# migrate_ops_alerts_v2b.py
# Last updated: 2026-01-09
# Description: Migration to add alert_type and pipeline_name to ops_alerts
#
# Usage:
#   python -m scripts.utils.migrate_ops_alerts_v2b --dry-run
#   python -m scripts.utils.migrate_ops_alerts_v2b

"""
Migration: ops_alerts - Add alert_type and pipeline_name

This completes the schema alignment after discovering the actual schema
differs from documentation.

Current schema (post v2 migration):
- alert_id, run_id, severity, message, created_at
- is_active, context_json
- incident_id, resolved_at, resolved_by (added in v2)

Adding:
- alert_type VARCHAR (for categorizing alerts: 'api_error', 'classification_error', etc.)
- pipeline_name VARCHAR (to identify which pipeline generated the alert)

This migration is idempotent - safe to run multiple times.
"""

import argparse
import duckdb
from pathlib import Path
from datetime import datetime
from loguru import logger


DB_PATH = Path("data/osint_dw.duckdb")

MIGRATIONS = [
    {
        'column': 'alert_type',
        'type': 'VARCHAR',
        'description': 'Type/category of alert (api_error, classification_error, etc.)'
    },
    {
        'column': 'pipeline_name',
        'type': 'VARCHAR',
        'description': 'Name of pipeline that generated this alert'
    }
]


def get_existing_columns(con, table_name: str) -> set[str]:
    """Get set of existing column names for a table."""
    try:
        result = con.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """).fetchall()
        return {row[0] for row in result}
    except Exception:
        return set()


def run_migration(db_path: Path, dry_run: bool = False) -> dict:
    """
    Run the migration to add alert_type and pipeline_name.
    
    Args:
        db_path: Path to DuckDB database
        dry_run: If True, only report what would be done
        
    Returns:
        Migration results dictionary
    """
    results = {
        'migration': 'ops_alerts_v2b',
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'columns_added': [],
        'columns_skipped': [],
        'errors': []
    }
    
    con = duckdb.connect(str(db_path))
    
    try:
        existing = get_existing_columns(con, 'ops_alerts')
        
        if not existing:
            results['errors'].append("Table 'ops_alerts' does not exist")
            return results
        
        logger.info(f"Existing columns: {sorted(existing)}")
        
        row_count = con.execute("SELECT COUNT(*) FROM ops_alerts").fetchone()[0]
        logger.info(f"Current row count: {row_count}")
        results['rows_before'] = row_count
        
        for migration in MIGRATIONS:
            col_name = migration['column']
            col_type = migration['type']
            
            if col_name in existing:
                logger.info(f"Column '{col_name}' already exists - skipping")
                results['columns_skipped'].append(col_name)
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] Would add: {col_name} {col_type}")
                results['columns_added'].append(f"{col_name} (dry run)")
            else:
                logger.info(f"Adding column: {col_name} {col_type}")
                try:
                    con.execute(f"ALTER TABLE ops_alerts ADD COLUMN {col_name} {col_type}")
                    results['columns_added'].append(col_name)
                    logger.success(f"  ✓ Added {col_name}")
                except Exception as e:
                    error_msg = f"Failed to add {col_name}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
        
        if not dry_run and results['columns_added']:
            con.commit()
        
        final_columns = get_existing_columns(con, 'ops_alerts')
        results['final_columns'] = sorted(final_columns)
        
        row_count_after = con.execute("SELECT COUNT(*) FROM ops_alerts").fetchone()[0]
        results['rows_after'] = row_count_after
        
    except Exception as e:
        results['errors'].append(f"Migration failed: {e}")
        logger.error(f"Migration failed: {e}")
    finally:
        con.close()
    
    return results


def print_results(results: dict):
    """Print migration results."""
    print("\n" + "=" * 60)
    print("MIGRATION RESULTS: ops_alerts v2b (alert_type + pipeline_name)")
    print("=" * 60)
    
    print(f"\nTimestamp: {results['timestamp']}")
    print(f"Dry run: {results['dry_run']}")
    
    if results.get('rows_before') is not None:
        print(f"\nRows before: {results['rows_before']}")
        print(f"Rows after: {results.get('rows_after', 'N/A')}")
    
    if results['columns_added']:
        print(f"\n✅ Columns added: {results['columns_added']}")
    
    if results['columns_skipped']:
        print(f"\n⏭️  Columns skipped (already exist): {results['columns_skipped']}")
    
    if results.get('final_columns'):
        print(f"\nFinal schema ({len(results['final_columns'])} columns):")
        for col in results['final_columns']:
            print(f"   - {col}")
    
    if results['errors']:
        print(f"\n❌ Errors:")
        for error in results['errors']:
            print(f"   - {error}")
    else:
        print(f"\n✅ Migration completed successfully!")
    
    print("=" * 60 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Add alert_type and pipeline_name to ops_alerts"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help=f"Path to DuckDB database (default: {DB_PATH})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    db_path = Path(args.db)
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1
    
    if not args.dry_run:
        print(f"\nThis will modify: {db_path}")
        confirm = input("Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return 0
    
    results = run_migration(db_path, dry_run=args.dry_run)
    print_results(results)
    
    return 1 if results['errors'] else 0


if __name__ == "__main__":
    exit(main())
