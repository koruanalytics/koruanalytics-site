# scripts/utils/validate_reingestion.py
# Validate data quality after re-ingestion
# Last updated: 2026-01-09

import duckdb
from pathlib import Path
from loguru import logger

DB_PATH = Path("data/osint_dw.duckdb")

def validate_reingestion():
    """
    Validate Medallion tables after re-ingestion.
    """
    con = duckdb.connect(str(DB_PATH))
    
    logger.info("=== VALIDACION POST RE-INGESTA ===\n")
    
    # 1. Row counts
    logger.info("1. CONTEO DE REGISTROS")
    tables_counts = {}
    for table in ["bronze_news", "silver_news_enriched", "gold_incidents", "gold_daily_stats"]:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            tables_counts[table] = count
            logger.info(f"   {table}: {count:,} rows")
        except Exception as e:
            logger.error(f"   {table}: ERROR - {e}")
            tables_counts[table] = 0
    
    # 2. Date ranges
    logger.info("\n2. RANGOS DE FECHAS")
    try:
        result = con.execute("""
            SELECT 
                MIN(DATE(published_at)) as min_date,
                MAX(DATE(published_at)) as max_date,
                COUNT(DISTINCT DATE(published_at)) as num_days
            FROM bronze_news
        """).fetchone()
        logger.info(f"   Bronze: {result[0]} -> {result[1]} ({result[2]} dias)")
    except Exception as e:
        logger.error(f"   Bronze dates: {e}")
    
    try:
        result = con.execute("""
            SELECT 
                MIN(fecha_incidente) as min_date,
                MAX(fecha_incidente) as max_date,
                COUNT(DISTINCT fecha_incidente) as num_days
            FROM gold_incidents
        """).fetchone()
        logger.info(f"   Gold incidents: {result[0]} -> {result[1]} ({result[2]} dias)")
    except Exception as e:
        logger.error(f"   Gold dates: {e}")
    
    # 3. Conversion rates
    logger.info("\n3. TASAS DE CONVERSION")
    if tables_counts.get("bronze_news", 0) > 0:
        silver_rate = tables_counts.get("silver_news_enriched", 0) / tables_counts["bronze_news"] * 100
        gold_rate = tables_counts.get("gold_incidents", 0) / tables_counts["bronze_news"] * 100
        logger.info(f"   Bronze -> Silver: {silver_rate:.1f}%")
        logger.info(f"   Bronze -> Gold: {gold_rate:.1f}% (incidentes relevantes)")
    
    # 4. Event type distribution
    logger.info("\n4. DISTRIBUCION POR TIPO DE EVENTO")
    try:
        results = con.execute("""
            SELECT tipo_evento, COUNT(*) as count
            FROM gold_incidents
            GROUP BY tipo_evento
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        for row in results:
            logger.info(f"   {row[0]}: {row[1]:,}")
    except Exception as e:
        logger.error(f"   Event types: {e}")
    
    # 5. Geographic coverage
    logger.info("\n5. COBERTURA GEOGRAFICA")
    try:
        results = con.execute("""
            SELECT departamento, COUNT(*) as count
            FROM gold_incidents
            WHERE departamento IS NOT NULL AND departamento != ''
            GROUP BY departamento
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        for row in results:
            logger.info(f"   {row[0]}: {row[1]:,}")
    except Exception as e:
        logger.error(f"   Geography: {e}")
    
    # 6. Quality checks
    logger.info("\n6. VERIFICACIONES DE CALIDAD")
    
    try:
        no_rel = con.execute("""
            SELECT COUNT(*) FROM gold_incidents 
            WHERE tipo_evento = 'no_relevante'
        """).fetchone()[0]
        if no_rel == 0:
            logger.success(f"   OK 0 registros 'no_relevante' en gold")
        else:
            logger.warning(f"   WARN {no_rel} registros 'no_relevante' en gold")
    except Exception as e:
        logger.error(f"   no_relevante check: {e}")
    
    try:
        nulls = con.execute("""
            SELECT 
                SUM(CASE WHEN tipo_evento IS NULL THEN 1 ELSE 0 END) as null_tipo,
                SUM(CASE WHEN titulo IS NULL OR titulo = '' THEN 1 ELSE 0 END) as null_titulo
            FROM gold_incidents
        """).fetchone()
        if nulls[0] == 0 and nulls[1] == 0:
            logger.success(f"   OK Sin nulls en campos criticos")
        else:
            logger.warning(f"   WARN Nulls: tipo_evento={nulls[0]}, titulo={nulls[1]}")
    except Exception as e:
        logger.error(f"   Null check: {e}")
    
    # 7. Impact stats
    logger.info("\n7. ESTADISTICAS DE IMPACTO")
    try:
        result = con.execute("""
            SELECT 
                SUM(muertos) as total_muertos,
                SUM(heridos) as total_heridos
            FROM gold_incidents
        """).fetchone()
        logger.info(f"   Total muertos registrados: {result[0] or 0:,}")
        logger.info(f"   Total heridos registrados: {result[1] or 0:,}")
    except Exception as e:
        logger.error(f"   Impact stats: {e}")
    
    con.close()
    
    # Final assessment
    logger.info("\n" + "="*50)
    bronze = tables_counts.get("bronze_news", 0)
    gold = tables_counts.get("gold_incidents", 0)
    
    if bronze > 0 and gold > 0:
        logger.success("RE-INGESTA VALIDADA EXITOSAMENTE")
        logger.info(f"  {bronze:,} articulos ingestados -> {gold:,} incidentes relevantes")
    else:
        logger.error("VALIDACION FALLIDA - revisar logs")
    
    return bronze > 0 and gold > 0

if __name__ == "__main__":
    validate_reingestion()
