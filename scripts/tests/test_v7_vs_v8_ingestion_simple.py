# scripts/tests/test_v7_vs_v8_ingestion_simple.py
"""
Test simplificado de ingesta v7 vs v8.2 (11 grupos optimizados).
Alineado con la arquitectura real del proyecto OSINT Perú 2026.

v8.2 changes:
- 11 optimized keyword groups (anti-duplication strategy)
- Consolidated related themes to minimize inter-group duplication
- Mutually exclusive keywords (each keyword in exactly 1 group)
- Target: 340-370 articles/day (vs v7: 321)
"""
import sys
from pathlib import Path
from datetime import date
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# =============================================================================
# CONFIGURACIÓN (igual que daily_pipeline.py)
# =============================================================================

DB_PATH = "data/osint_dw.duckdb"
V7_SCOPE = "config/newsapi_scope_peru_v7.yaml"
V8_SCOPE = "config/newsapi_scope_peru_v8_2.yaml"  # Using v8.2 - 11 optimized groups
RAW_DIR_V7 = "data/raw/newsapi_ai_test_v7"
RAW_DIR_V8 = "data/raw/newsapi_ai_test_v8_2"  # Separate dir for v8.2

def test_version_ingestion(version: str, test_date: date, scope_path: str, raw_dir: str) -> Dict:
    """
    Ejecuta ingesta de prueba para una versión específica.
    No toca la BD, solo retorna artículos obtenidos del API.
    """
    from src.ingestion.newsapi_ai_ingest import IngestParams, MultiQueryIngestor
    
    logger.info(f"{'='*70}")
    logger.info(f"TESTING INGESTION - {version.upper()}")
    logger.info(f"{'='*70}")
    logger.info(f"Date: {test_date}")
    logger.info(f"Config: {scope_path}")
    logger.info(f"Output: {raw_dir}")
    
    # Crear parámetros de ingesta
    params = IngestParams(
        scope_yaml=Path(scope_path),
        out_dir=Path(raw_dir),
        date_start=test_date,
        date_end=test_date,
        max_total=500,  # Límite razonable para test
    )
    
    # Ejecutar ingesta
    ingestor = MultiQueryIngestor(params)
    result = ingestor.run()
    
    logger.info(f"✅ {version}: {result.unique_articles} artículos únicos")
    logger.info(f"   Output: {result.output_path}")
    logger.info(f"   Run ID: {result.run_id}")
    
    return {
        'version': version,
        'articles_count': result.unique_articles,
        'output_path': str(result.output_path),
        'run_id': result.run_id
    }


def compare_results(v7_result: Dict, v8_result: Dict):
    """Compara resultados de v7 vs v8."""
    logger.info(f"\n{'='*70}")
    logger.info("COMPARISON: v7 vs v8")
    logger.info(f"{'='*70}\n")
    
    v7_count = v7_result['articles_count']
    v8_count = v8_result['articles_count']
    
    logger.info(f"📊 Article Counts:")
    logger.info(f"  v7: {v7_count} articles")
    logger.info(f"  v8: {v8_count} articles")
    
    if v7_count > 0:
        diff_pct = ((v8_count - v7_count) / v7_count) * 100
        logger.info(f"  Difference: {diff_pct:+.1f}%")
    else:
        logger.warning(f"  v7 returned 0 articles - cannot calculate percentage")
        diff_pct = None
    
    # Recomendación
    logger.info(f"\n{'='*70}")
    logger.info("RECOMMENDATION")
    logger.info(f"{'='*70}\n")
    
    if v7_count == 0:
        logger.warning("⚠️  CANNOT RECOMMEND - v7 returned 0 articles")
        logger.warning("Check API key, date, or network connection")
        return
    
    if diff_pct is None:
        return
    
    if abs(diff_pct) <= 15:
        logger.info("✅ RECOMMEND DEPLOYMENT")
        logger.info("Reasons:")
        logger.info(f"  • Article counts similar ({diff_pct:+.1f}%)")
        logger.info(f"  • v8.2 optimized groups maintain v7 baseline")
        logger.info(f"  • Anti-duplication strategy working")
    elif 15 < diff_pct <= 35:
        logger.info("✅ RECOMMEND DEPLOYMENT (with monitoring)")
        logger.info("Reasons:")
        logger.info(f"  • Article count increased {diff_pct:.1f}%")
        logger.info(f"  • Improved coverage from optimized groups")
        logger.info(f"  • Monitor quality during first week")
    elif -20 <= diff_pct < -15:
        logger.warning("⚠️  REVIEW REQUIRED")
        logger.warning("Reasons:")
        logger.warning(f"  • Article count dropped {diff_pct:.1f}%")
        logger.warning(f"  • Review keyword changes")
        logger.warning(f"  • Check if lost articles are low-value")
    else:
        logger.error("❌ DO NOT DEPLOY")
        logger.error("Reasons:")
        logger.error(f"  • Extreme count change: {diff_pct:+.1f}%")
        logger.error(f"  • Investigate configuration or API issues")
    
    logger.info(f"\n📁 Output files:")
    logger.info(f"  v7: {v7_result['output_path']}")
    logger.info(f"  v8: {v8_result['output_path']}")
    logger.info(f"\n💡 You can inspect these JSON files to see actual articles")


def main():
    """Main test execution."""
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description="Simple v7 vs v8.1 (18 grupos) ingestion comparison")
    parser.add_argument(
        '--date',
        type=str,
        default=(date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
        help='Test date (YYYY-MM-DD), default: yesterday'
    )
    
    args = parser.parse_args()
    test_date = date.fromisoformat(args.date)
    
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    logger.info(f"{'='*70}")
    logger.info("SIMPLE v7 vs v8.2 INGESTION TEST (11 GRUPOS OPTIMIZADOS)")
    logger.info(f"{'='*70}")
    logger.info(f"Test date: {test_date}")
    logger.info(f"v8.2: 11 grupos anti-duplicación optimizados")
    logger.info(f"{'='*70}\n")
    
    # Verificar que configs existen
    if not Path(V7_SCOPE).exists():
        logger.error(f"❌ Config not found: {V7_SCOPE}")
        return
    
    if not Path(V8_SCOPE).exists():
        logger.error(f"❌ Config not found: {V8_SCOPE}")
        return
    
    # Test v7
    try:
        v7_result = test_version_ingestion("v7", test_date, V7_SCOPE, RAW_DIR_V7)
    except Exception as e:
        logger.error(f"❌ v7 test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test v8
    try:
        v8_result = test_version_ingestion("v8", test_date, V8_SCOPE, RAW_DIR_V8)
    except Exception as e:
        logger.error(f"❌ v8 test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Compare
    compare_results(v7_result, v8_result)
    
    logger.info(f"\n{'='*70}")
    logger.info("TEST COMPLETE")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    main()
