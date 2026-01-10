# scripts/utils/run_historical_reingestion.py
# Historical re-ingestion for OSINT Peru 2026
# Last updated: 2026-01-09 (FIXED: added --full flag)

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

def run_historical_reingestion(
    start_date: str = "2025-12-31",
    end_date: str = "2026-01-09"
):
    """
    Run daily_pipeline.py for each date in range.
    
    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format (inclusive)
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    total_days = (end - start).days + 1
    logger.info(f"=== RE-INGESTA HISTORICA ===")
    logger.info(f"Rango: {start_date} -> {end_date} ({total_days} dias)")
    
    current = start
    day_num = 0
    errors = []
    
    while current <= end:
        day_num += 1
        date_str = current.strftime("%Y-%m-%d")
        logger.info(f"\n[{day_num}/{total_days}] Procesando: {date_str}")
        
        try:
            # Run daily_pipeline for this date
            # IMPORTANT: --full flag is REQUIRED for the pipeline to execute
            result = subprocess.run(
                [
                    sys.executable, "-m", "scripts.core.daily_pipeline",
                    "--full",  # <-- THIS IS REQUIRED!
                    "--date-start", date_str,
                    "--date-end", date_str
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout per day
            )
            
            if result.returncode == 0:
                logger.success(f"  OK {date_str} completado")
                # Show relevant output lines
                for line in result.stdout.split('\n'):
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in ['bronze', 'gold', 'silver', 'ingesta', 'enrich', 'articulos', 'articles', 'nuevos', 'completado']):
                        logger.info(f"    {line.strip()}")
            else:
                logger.error(f"  ERROR {date_str} fallo (returncode={result.returncode})")
                if result.stderr:
                    logger.error(f"    stderr: {result.stderr[:500]}")
                if result.stdout:
                    logger.error(f"    stdout: {result.stdout[:500]}")
                errors.append(date_str)
                
        except subprocess.TimeoutExpired:
            logger.error(f"  ERROR {date_str} timeout (>10 min)")
            errors.append(date_str)
        except Exception as e:
            logger.error(f"  ERROR {date_str}: {e}")
            errors.append(date_str)
        
        current += timedelta(days=1)
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("=== RESUMEN RE-INGESTA ===")
    logger.info(f"Dias procesados: {day_num}")
    logger.info(f"Exitosos: {day_num - len(errors)}")
    logger.info(f"Fallidos: {len(errors)}")
    
    if errors:
        logger.warning(f"Fechas con error: {errors}")
    
    return len(errors) == 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Historical re-ingestion")
    parser.add_argument("--start", default="2025-12-31", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-01-09", help="End date YYYY-MM-DD")
    
    args = parser.parse_args()
    
    success = run_historical_reingestion(args.start, args.end)
    sys.exit(0 if success else 1)
