# scripts/utils/reset_medallion_tables.py
# Reset Medallion tables for fresh re-ingestion
# Last updated: 2026-01-09

import duckdb
from pathlib import Path
from loguru import logger

DB_PATH = Path("data/osint_dw.duckdb")

def reset_medallion_tables():
    """
    Truncate Medallion tables in correct order (Gold -> Silver -> Bronze).
    Shows before/after counts.
    """
    tables = [
        "gold_daily_stats",
        "gold_incidents", 
        "silver_news_enriched",
        "bronze_news"
    ]
    
    con = duckdb.connect(str(DB_PATH))
    
    # Show current state
    logger.info("=== ESTADO ACTUAL ===")
    for table in reversed(tables):
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count:,} rows")
        except Exception as e:
            logger.warning(f"  {table}: NO EXISTE - {e}")
    
    # Confirm
    print("\n" + "="*50)
    response = input("Vaciar todas las tablas Medallion? (yes/no): ")
    if response.lower() != "yes":
        logger.info("Operacion cancelada")
        con.close()
        return False
    
    # Truncate in order (Gold -> Silver -> Bronze)
    logger.info("\n=== VACIANDO TABLAS ===")
    for table in tables:
        try:
            con.execute(f"DELETE FROM {table}")
            logger.success(f"  OK {table} vaciada")
        except Exception as e:
            logger.error(f"  ERROR {table}: {e}")
    
    # Verify
    logger.info("\n=== ESTADO FINAL ===")
    for table in reversed(tables):
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count:,} rows")
        except Exception as e:
            logger.warning(f"  {table}: {e}")
    
    con.close()
    logger.success("\nReset completado. Listo para re-ingesta.")
    return True

if __name__ == "__main__":
    reset_medallion_tables()
