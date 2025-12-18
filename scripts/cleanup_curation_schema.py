"""
scripts/cleanup_curation_schema.py - One-time cleanup of duplicate columns

The curation_incident_overrides table has duplicate columns with inconsistent naming:
- incident_type_override vs override_incident_type
- place_id_override vs override_place_id
etc.

This script:
1. Creates a clean backup of the table
2. Migrates data to the correct columns (override_* prefix)
3. Drops the old columns (*_override suffix)

Run once: python scripts/cleanup_curation_schema.py
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


# Mapping: old_column -> new_column (both should exist, we keep new and drop old)
COLUMN_MIGRATIONS = {
    "incident_type_override": "override_incident_type",
    "actors_json_override": None,  # Drop, no equivalent
    "victims_json_override": None,  # Drop, no equivalent
    "location_text_override": "override_location_text",
    "place_id_override": "override_place_id",
    "lat_override": "override_lat",
    "lon_override": "override_lon",
    "adm1_override": "override_adm1",
    "adm2_override": "override_adm2",
    "adm3_override": "override_adm3",
}


def get_columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    cols = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {r[1] for r in cols}


def main() -> int:
    cfg = load_config()
    db_path = cfg["db"]["duckdb_path"]
    
    logger.info(f"Opening DB: {db_path}")
    con = duckdb.connect(db_path)
    
    try:
        table = "curation_incident_overrides"
        cols = get_columns(con, table)
        
        logger.info(f"Current columns in {table}: {len(cols)}")
        
        # Check if cleanup is needed
        old_cols = [c for c in COLUMN_MIGRATIONS.keys() if c in cols]
        if not old_cols:
            logger.success("No cleanup needed - old columns don't exist")
            return 0
        
        logger.info(f"Found old columns to migrate/drop: {old_cols}")
        
        # Step 1: Migrate data from old to new columns (if both exist and old has data)
        for old_col, new_col in COLUMN_MIGRATIONS.items():
            if old_col not in cols:
                continue
                
            if new_col and new_col in cols:
                # Copy data from old to new where new is NULL
                logger.info(f"Migrating data: {old_col} -> {new_col}")
                con.execute(f"""
                    UPDATE {table}
                    SET {new_col} = {old_col}
                    WHERE {new_col} IS NULL AND {old_col} IS NOT NULL
                """)
        
        # Step 2: Create clean table without old columns
        # DuckDB doesn't support DROP COLUMN, so we recreate the table
        
        # Get columns to keep (exclude old naming convention)
        keep_cols = [c for c in cols if c not in COLUMN_MIGRATIONS.keys()]
        
        logger.info(f"Columns to keep: {keep_cols}")
        
        # Backup
        con.execute(f"CREATE TABLE IF NOT EXISTS {table}_backup AS SELECT * FROM {table}")
        backup_count = con.execute(f"SELECT COUNT(*) FROM {table}_backup").fetchone()[0]
        logger.info(f"Backup created: {table}_backup ({backup_count} rows)")
        
        # Recreate table
        cols_sql = ", ".join([f'"{c}"' for c in keep_cols])
        
        con.execute(f"CREATE TABLE {table}_clean AS SELECT {cols_sql} FROM {table}")
        con.execute(f"SELECT COUNT(*) FROM {table}_clean").fetchone()[0]
        
        # Swap tables
        con.execute(f"DROP TABLE {table}")
        con.execute(f"ALTER TABLE {table}_clean RENAME TO {table}")
        
        # Verify
        final_cols = get_columns(con, table)
        logger.success(f"Cleanup complete. {table} now has {len(final_cols)} columns (was {len(cols)})")
        logger.info(f"Final columns: {sorted(final_cols)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        logger.info("If needed, restore from backup: ALTER TABLE curation_incident_overrides_backup RENAME TO curation_incident_overrides")
        return 1
        
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())