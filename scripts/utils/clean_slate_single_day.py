# scripts/utils/clean_slate_single_day.py
# Clean slate: vaciar todo y re-ingestar un solo día para pruebas
# Last updated: 2026-01-10

import duckdb
from pathlib import Path
from loguru import logger
import shutil

DB_PATH = Path("data/osint_dw.duckdb")
RAW_DIR = Path("data/raw/newsapi_ai")
INTERIM_DIR = Path("data/interim/newsapi_ai")

def clean_slate():
    """
    Limpia completamente las tablas Medallion y los archivos raw/interim.
    Prepara el sistema para una ingesta limpia de pruebas.
    """
    logger.info("=" * 60)
    logger.info("CLEAN SLATE - REINICIO COMPLETO")
    logger.info("=" * 60)
    
    # 1. Mostrar estado actual
    con = duckdb.connect(str(DB_PATH))
    
    logger.info("\n[1/4] ESTADO ACTUAL:")
    tables = ["bronze_news", "silver_news_enriched", "gold_incidents", "gold_daily_stats"]
    for table in tables:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count:,} rows")
        except Exception as e:
            logger.warning(f"  {table}: NO EXISTE - {e}")
    
    # 2. Confirmar
    print("\n" + "=" * 60)
    print("ADVERTENCIA: Esto eliminará TODOS los datos de:")
    print("  - bronze_news, silver_news_enriched, gold_incidents, gold_daily_stats")
    print("  - Archivos en data/raw/newsapi_ai/")
    print("  - Archivos en data/interim/newsapi_ai/")
    print("=" * 60)
    response = input("\n¿Continuar con clean slate? (yes/no): ")
    
    if response.lower() != "yes":
        logger.info("Operación cancelada")
        con.close()
        return False
    
    # 3. Vaciar tablas (orden: Gold -> Silver -> Bronze)
    logger.info("\n[2/4] VACIANDO TABLAS...")
    for table in ["gold_daily_stats", "gold_incidents", "silver_news_enriched", "bronze_news"]:
        try:
            con.execute(f"DELETE FROM {table}")
            logger.success(f"  ✓ {table} vaciada")
        except Exception as e:
            logger.error(f"  ✗ {table}: {e}")
    
    con.close()
    
    # 4. Limpiar archivos raw e interim
    logger.info("\n[3/4] LIMPIANDO ARCHIVOS...")
    
    # Raw
    if RAW_DIR.exists():
        files = list(RAW_DIR.glob("*.json"))
        for f in files:
            f.unlink()
        logger.success(f"  ✓ {len(files)} archivos JSON eliminados de {RAW_DIR}")
    
    # Interim
    if INTERIM_DIR.exists():
        files = list(INTERIM_DIR.glob("*.parquet"))
        for f in files:
            f.unlink()
        logger.success(f"  ✓ {len(files)} archivos Parquet eliminados de {INTERIM_DIR}")
    
    # 5. Verificar estado final
    logger.info("\n[4/4] ESTADO FINAL:")
    con = duckdb.connect(str(DB_PATH))
    for table in tables:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"  {table}: {count} rows")
        except:
            pass
    con.close()
    
    logger.success("\n✓ CLEAN SLATE COMPLETADO")
    logger.info("\nPróximo paso - Ingestar un día de prueba:")
    logger.info("  python -m scripts.core.daily_pipeline --full --date-start 2026-01-01 --date-end 2026-01-01")
    
    return True

if __name__ == "__main__":
    clean_slate()
