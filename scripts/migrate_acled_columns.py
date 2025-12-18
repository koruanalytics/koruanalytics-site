"""
scripts/migrate_acled_columns.py - Add ACLED classification columns

Adds new columns to support ACLED methodology:
- sub_event_type: ACLED sub-event type (25 types)
- disorder_type: ACLED disorder category (political_violence, demonstrations, strategic_developments)

Run once: python scripts/migrate_acled_columns.py

Tables affected:
- stg_incidents_extracted
- fct_incidents
- fct_incidents_curated (if exists)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


def get_columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    """Get existing column names for a table."""
    try:
        cols = con.execute(f"PRAGMA table_info('{table}')").fetchall()
        return {r[1] for r in cols}
    except Exception:
        return set()


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    """Check if table exists."""
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table]
    ).fetchone()
    return result[0] > 0


def add_column_if_missing(
    con: duckdb.DuckDBPyConnection, 
    table: str, 
    column: str, 
    col_type: str,
    default_value: str | None = None
) -> bool:
    """Add column to table if it doesn't exist."""
    cols = get_columns(con, table)
    
    if column in cols:
        logger.info(f"  Column {table}.{column} already exists - skipping")
        return False
    
    logger.info(f"  Adding column {table}.{column} ({col_type})")
    con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    
    if default_value is not None:
        con.execute(f"UPDATE {table} SET {column} = {default_value} WHERE {column} IS NULL")
    
    return True


def migrate_table(con: duckdb.DuckDBPyConnection, table: str) -> dict:
    """Add ACLED columns to a single table."""
    results = {
        "table": table,
        "sub_event_type_added": False,
        "disorder_type_added": False,
    }
    
    if not table_exists(con, table):
        logger.warning(f"  Table {table} does not exist - skipping")
        return results
    
    logger.info(f"Migrating table: {table}")
    
    # Add sub_event_type column
    results["sub_event_type_added"] = add_column_if_missing(
        con, table, "sub_event_type", "VARCHAR", default_value="NULL"
    )
    
    # Add disorder_type column
    results["disorder_type_added"] = add_column_if_missing(
        con, table, "disorder_type", "VARCHAR", default_value="NULL"
    )
    
    return results


def update_incident_type_mapping(con: duckdb.DuckDBPyConnection, table: str) -> int:
    """
    Update existing incident_type values to ACLED format.
    Maps old types to new ACLED event types.
    """
    if not table_exists(con, table):
        return 0
    
    # Mapping from old types to new ACLED types
    mappings = {
        "violence": "violence_against_civilians",
        "intimidation": "violence_against_civilians",
        "infrastructure_attack": "explosions_remote_violence",
        "protest_unrest": "riots",
        "protest": "protests",
        "electoral": "strategic_developments",
        "corruption": "strategic_developments",
        "other": "strategic_developments",
    }
    
    updated = 0
    for old_type, new_type in mappings.items():
        con.execute(f"""
            UPDATE {table}
            SET incident_type = '{new_type}'
            WHERE incident_type = '{old_type}'
        """)
        # DuckDB doesn't return rowcount easily, so we count manually
        count = con.execute(f"""
            SELECT COUNT(*) FROM {table} WHERE incident_type = '{new_type}'
        """).fetchone()[0]
        if count > 0:
            updated += 1
    
    return updated


def set_default_disorder_type(con: duckdb.DuckDBPyConnection, table: str) -> int:
    """Set disorder_type based on incident_type for existing rows."""
    if not table_exists(con, table):
        return 0
    
    cols = get_columns(con, table)
    if "disorder_type" not in cols:
        return 0
    
    # Update disorder_type based on incident_type
    con.execute(f"""
        UPDATE {table}
        SET disorder_type = CASE
            WHEN incident_type IN ('battles', 'explosions_remote_violence', 'violence_against_civilians') 
                THEN 'political_violence'
            WHEN incident_type IN ('protests', 'riots') 
                THEN 'demonstrations'
            ELSE 'strategic_developments'
        END
        WHERE disorder_type IS NULL
    """)
    
    count = con.execute(f"""
        SELECT COUNT(*) FROM {table} WHERE disorder_type IS NOT NULL
    """).fetchone()[0]
    
    return count


def main() -> int:
    cfg = load_config()
    db_path = cfg["db"]["duckdb_path"]
    
    logger.info(f"Opening DB: {db_path}")
    con = duckdb.connect(db_path)
    
    try:
        # Tables to migrate
        tables = [
            "stg_incidents_extracted",
            "fct_incidents",
            "fct_incidents_curated",
        ]
        
        logger.info("=" * 60)
        logger.info("ACLED Column Migration")
        logger.info("=" * 60)
        
        # Step 1: Add new columns
        logger.info("\nStep 1: Adding new columns...")
        migration_results = []
        for table in tables:
            result = migrate_table(con, table)
            migration_results.append(result)
        
        # Step 2: Update incident_type values to ACLED format
        logger.info("\nStep 2: Updating incident_type to ACLED format...")
        for table in tables:
            if table_exists(con, table):
                updated = update_incident_type_mapping(con, table)
                logger.info(f"  {table}: {updated} type mappings applied")
        
        # Step 3: Set disorder_type for existing rows
        logger.info("\nStep 3: Setting disorder_type for existing rows...")
        for table in tables:
            if table_exists(con, table):
                count = set_default_disorder_type(con, table)
                logger.info(f"  {table}: {count} rows with disorder_type set")
        
        # Step 4: Add columns to curation_incident_overrides
        logger.info("\nStep 4: Adding override columns for new fields...")
        if table_exists(con, "curation_incident_overrides"):
            add_column_if_missing(
                con, "curation_incident_overrides", 
                "override_sub_event_type", "VARCHAR"
            )
            add_column_if_missing(
                con, "curation_incident_overrides", 
                "override_disorder_type", "VARCHAR"
            )
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        
        for result in migration_results:
            table = result["table"]
            if table_exists(con, table):
                cols = get_columns(con, table)
                has_sub = "sub_event_type" in cols
                has_dis = "disorder_type" in cols
                logger.success(f"  {table}: sub_event_type={has_sub}, disorder_type={has_dis}")
        
        # Verify with sample data
        logger.info("\nSample data from stg_incidents_extracted:")
        if table_exists(con, "stg_incidents_extracted"):
            sample = con.execute("""
                SELECT incident_type, sub_event_type, disorder_type, COUNT(*) as cnt
                FROM stg_incidents_extracted
                GROUP BY incident_type, sub_event_type, disorder_type
                ORDER BY cnt DESC
                LIMIT 5
            """).fetchall()
            for row in sample:
                logger.info(f"  {row}")
        
        logger.success("\nMigration completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())