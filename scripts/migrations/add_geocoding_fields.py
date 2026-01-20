"""
scripts/migrations/add_geocoding_fields.py

Migration script to add geocoding fields (adm4_name, nivel_geo) to existing tables.

Usage:
    python -m scripts.migrations.add_geocoding_fields

Last updated: 2026-01-11
"""
from __future__ import annotations

import os
from loguru import logger
import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/osint_dw.duckdb")


def check_column_exists(con, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = con.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = ?
    """, [table_name]).fetchdf()
    
    return column_name in result['column_name'].tolist()


def migrate():
    """
    Add geocoding fields to silver_news_enriched and gold_incidents.
    
    Fields to add:
    - adm4_name VARCHAR: Name of sub-district location (poblado, centro poblado)
    - nivel_geo VARCHAR: Geocoding precision level
    """
    con = duckdb.connect(DB_PATH)
    
    logger.info("=" * 60)
    logger.info("MIGRATION: Adding geocoding fields")
    logger.info("=" * 60)
    
    # Check if tables exist
    tables = con.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'main'
    """).fetchdf()['table_name'].tolist()
    
    if 'silver_news_enriched' not in tables:
        logger.warning("Table silver_news_enriched does not exist. Skipping.")
        con.close()
        return
    
    if 'gold_incidents' not in tables:
        logger.warning("Table gold_incidents does not exist. Skipping.")
        con.close()
        return
    
    # =========================================================================
    # SILVER_NEWS_ENRICHED
    # =========================================================================
    
    logger.info("\n[1/2] Migrating silver_news_enriched...")
    
    # Add adm4_name
    if not check_column_exists(con, 'silver_news_enriched', 'adm4_name'):
        logger.info("  Adding column: adm4_name")
        con.execute("ALTER TABLE silver_news_enriched ADD COLUMN adm4_name VARCHAR")
        logger.success("  ✓ Added adm4_name")
    else:
        logger.info("  ✓ adm4_name already exists")
    
    # Add nivel_geo
    if not check_column_exists(con, 'silver_news_enriched', 'nivel_geo'):
        logger.info("  Adding column: nivel_geo")
        con.execute("ALTER TABLE silver_news_enriched ADD COLUMN nivel_geo VARCHAR")
        logger.success("  ✓ Added nivel_geo")
    else:
        logger.info("  ✓ nivel_geo already exists")
    
    # =========================================================================
    # GOLD_INCIDENTS
    # =========================================================================
    
    logger.info("\n[2/2] Migrating gold_incidents...")
    
    # Add adm4_name
    if not check_column_exists(con, 'gold_incidents', 'adm4_name'):
        logger.info("  Adding column: adm4_name")
        con.execute("ALTER TABLE gold_incidents ADD COLUMN adm4_name VARCHAR")
        logger.success("  ✓ Added adm4_name")
    else:
        logger.info("  ✓ adm4_name already exists")
    
    # Add nivel_geo
    if not check_column_exists(con, 'gold_incidents', 'nivel_geo'):
        logger.info("  Adding column: nivel_geo")
        con.execute("ALTER TABLE gold_incidents ADD COLUMN nivel_geo VARCHAR")
        logger.success("  ✓ Added nivel_geo")
    else:
        logger.info("  ✓ nivel_geo already exists")
    
    # =========================================================================
    # VERIFICATION
    # =========================================================================
    
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)
    
    # Verify silver
    silver_count = con.execute("SELECT COUNT(*) FROM silver_news_enriched").fetchone()[0]
    silver_cols = con.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'silver_news_enriched'
        ORDER BY ordinal_position
    """).fetchdf()['column_name'].tolist()
    
    logger.info(f"\nsilver_news_enriched: {silver_count} rows")
    logger.info(f"  New columns present: adm4_name={('adm4_name' in silver_cols)}, "
                f"nivel_geo={('nivel_geo' in silver_cols)}")
    
    # Verify gold
    gold_count = con.execute("SELECT COUNT(*) FROM gold_incidents").fetchone()[0]
    gold_cols = con.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'gold_incidents'
        ORDER BY ordinal_position
    """).fetchdf()['column_name'].tolist()
    
    logger.info(f"\ngold_incidents: {gold_count} rows")
    logger.info(f"  New columns present: adm4_name={('adm4_name' in gold_cols)}, "
                f"nivel_geo={('nivel_geo' in gold_cols)}")
    
    con.close()
    
    logger.success("\n✓ Migration completed successfully")
    logger.info("\nNext steps:")
    logger.info("  1. Run geocoding to populate nivel_geo and coordinates")
    logger.info("  2. Rebuild gold_incidents: python -m src.enrichment.llm_enrichment_pipeline --build-gold")


if __name__ == "__main__":
    migrate()
