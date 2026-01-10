"""
scripts/core/daily_pipeline.py - Pipeline diario completo OSINT Perú 2026

Ejecuta el pipeline completo:
1. Ingesta de NewsAPI.ai → bronze_news (con dedupe)
2. Enriquecimiento LLM → silver_news_enriched
3. Construcción → gold_incidents + gold_daily_stats
4. Generación de alertas (opcional)
5. Generación de informe diario (opcional)

Uso:
    # Pipeline completo (ingesta + enriquecimiento)
    python -m scripts.core.daily_pipeline --full
    
    # Solo ingesta (sin LLM)
    python -m scripts.core.daily_pipeline --ingest-only
    
    # Solo enriquecimiento (procesar pendientes)
    python -m scripts.core.daily_pipeline --enrich-only
    
    # Con rango de fechas específico (aumenta límite automáticamente)
    python -m scripts.core.daily_pipeline --full --date-start 2025-12-15 --date-end 2026-01-05
    
    # Ingesta masiva histórica
    python -m scripts.core.daily_pipeline --full --date-start 2025-12-15 --date-end 2026-01-05 --max-articles 5000

Programación recomendada (Task Scheduler / cron):
    - Cada 6 horas: python -m scripts.core.daily_pipeline --full
    - O diario a las 6am: python -m scripts.core.daily_pipeline --full
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Añadir root al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import duckdb
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DB_PATH = "data/osint_dw.duckdb"
SCOPE_PATH = "config/newsapi_scope_peru_v6.yaml"  # v6: source + keywords BY GROUP
RAW_DIR = "data/raw/newsapi_ai"
INTERIM_DIR = "data/interim/newsapi_ai"

# Límites por defecto
DEFAULT_MAX_ARTICLES = 500  # Para ingesta diaria
DEFAULT_ENRICH_BATCH = 100  # Artículos por batch de LLM
ARTICLES_PER_DAY_ESTIMATE = 150  # Estimado para calcular límite automático


# =============================================================================
# PASO 1: INGESTA
# =============================================================================

def calculate_max_articles(date_start: date, date_end: date, user_max: Optional[int] = None) -> int:
    """
    Calcula el límite de artículos basado en el rango de fechas.
    Para ingestas históricas, aumenta automáticamente el límite.
    """
    days = (date_end - date_start).days + 1
    
    if user_max is not None:
        return user_max
    
    # Si es más de 3 días, calcular límite dinámico
    if days > 3:
        calculated = days * ARTICLES_PER_DAY_ESTIMATE
        logger.info(f"[INGESTA] Rango de {days} días - límite automático: {calculated} artículos")
        return calculated
    
    return DEFAULT_MAX_ARTICLES


def run_ingestion(
    date_start: date,
    date_end: date,
    max_articles: Optional[int] = None
) -> Dict[str, Any]:
    """
    Ejecuta ingesta de NewsAPI.ai con dedupe integrado.
    """
    # Calcular límite dinámico si no se especifica
    actual_max = calculate_max_articles(date_start, date_end, max_articles)
    
    logger.info(f"[INGESTA] {date_start} a {date_end}, max={actual_max}")
    
    from src.ingestion.newsapi_ai_ingest import IngestParams, MultiQueryIngestor
    from src.processing.normalize_newsapi_ai import run_newsapi_ai_normalization, NormalizeParams
    
    # 1. Ingestar desde API
    params = IngestParams(
        scope_yaml=Path(SCOPE_PATH),
        out_dir=Path(RAW_DIR),
        date_start=date_start,
        date_end=date_end,
        max_total=actual_max,
    )
    
    ingestor = MultiQueryIngestor(params)
    result = ingestor.run()
    
    logger.info(f"[INGESTA] Raw: {result.unique_articles} artículos")
    
    # 2. Normalizar a parquet (FIX: usar NormalizeParams)
    normalize_params = NormalizeParams(
        raw_path=result.output_path,
        out_dir=Path(INTERIM_DIR)
    )
    parquet_path = run_newsapi_ai_normalization(normalize_params)
    logger.info(f"[INGESTA] Normalizado: {parquet_path}")
    
    # 3. Cargar a bronze con dedupe
    new_articles = load_to_bronze_with_dedupe(parquet_path, result.run_id)
    
    return {
        "run_id": result.run_id,
        "raw_articles": result.unique_articles,
        "new_articles": new_articles,
        "date_start": date_start.isoformat(),
        "date_end": date_end.isoformat(),
    }


def load_to_bronze_with_dedupe(parquet_path: Path, run_id: str) -> int:
    """
    Carga artículos a bronze_news con dedupe por título.
    Solo inserta artículos que no existen ya.
    """
    con = duckdb.connect(DB_PATH)
    
    # Contar antes
    before = con.execute("SELECT COUNT(*) FROM bronze_news").fetchone()[0]
    
    # Insertar solo nuevos (dedupe por primeros 100 chars del título)
    con.execute(f"""
        INSERT INTO bronze_news
        SELECT p.*
        FROM read_parquet('{parquet_path}') p
        WHERE NOT EXISTS (
            SELECT 1 FROM bronze_news b
            WHERE LOWER(TRIM(LEFT(b.title, 100))) = LOWER(TRIM(LEFT(p.title, 100)))
        )
    """)
    
    # Contar después
    after = con.execute("SELECT COUNT(*) FROM bronze_news").fetchone()[0]
    new_count = after - before
    
    con.close()
    
    logger.success(f"[BRONZE] +{new_count} artículos nuevos (total: {after})")
    return new_count


# =============================================================================
# PASO 2: ENRIQUECIMIENTO
# =============================================================================

def run_enrichment(limit: int = DEFAULT_ENRICH_BATCH, process_all: bool = False) -> Dict[str, Any]:
    """
    Ejecuta enriquecimiento LLM de artículos pendientes.
    
    Args:
        limit: Máximo de artículos a procesar por batch
        process_all: Si True, procesa todos los pendientes en batches
    """
    from src.enrichment.llm_enrichment_pipeline import EnrichmentPipeline
    
    pipeline = EnrichmentPipeline(DB_PATH)
    
    # Verificar pendientes
    con = pipeline.get_connection()
    pending = con.execute("""
        SELECT COUNT(*) FROM bronze_news b
        LEFT JOIN silver_news_enriched s ON b.incident_id = s.bronze_id
        WHERE s.bronze_id IS NULL
    """).fetchone()[0]
    con.close()
    
    if pending == 0:
        logger.info("[ENRICH] No hay artículos pendientes")
        return {"processed": 0, "pending": 0}
    
    total_processed = 0
    total_relevantes = 0
    total_cost = 0.0
    
    if process_all:
        # Procesar todos en batches
        logger.info(f"[ENRICH] Procesando TODOS los {pending} artículos pendientes...")
        
        while pending > 0:
            actual_limit = min(limit, pending)
            logger.info(f"[ENRICH] Batch: {actual_limit} artículos (quedan {pending})...")
            
            result = pipeline.process_to_silver(limit=actual_limit)
            
            total_processed += result["processed"]
            total_relevantes += result["relevantes"]
            total_cost += result["stats"]["cost_usd"]
            
            # Actualizar pendientes
            con = pipeline.get_connection()
            pending = con.execute("""
                SELECT COUNT(*) FROM bronze_news b
                LEFT JOIN silver_news_enriched s ON b.incident_id = s.bronze_id
                WHERE s.bronze_id IS NULL
            """).fetchone()[0]
            con.close()
        
        # Construir gold al final
        logger.info("[ENRICH] Construyendo tablas Gold...")
        gold_result = pipeline.build_gold_incidents()
        stats_result = pipeline.build_gold_daily_stats()
        
        return {
            "processed": total_processed,
            "relevantes": total_relevantes,
            "gold_incidents": gold_result["count"],
            "gold_days": stats_result["days"],
            "cost_usd": round(total_cost, 4),
            "pending_remaining": 0,
        }
    else:
        # Procesar solo un batch
        actual_limit = min(limit, pending)
        logger.info(f"[ENRICH] Procesando {actual_limit} de {pending} pendientes...")
        
        result = pipeline.run_full_pipeline(limit=actual_limit)
        
        return {
            "processed": result["silver"]["processed"],
            "relevantes": result["silver"]["relevantes"],
            "gold_incidents": result["gold"]["count"],
            "gold_days": result["stats"]["days"],
            "cost_usd": result["silver"]["stats"]["cost_usd"],
            "pending_remaining": pending - actual_limit,
        }


# =============================================================================
# PASO 3: ALERTAS
# =============================================================================

def check_and_generate_alerts() -> Dict[str, Any]:
    """
    Genera alertas para incidentes de alta prioridad.
    """
    con = duckdb.connect(DB_PATH)
    
    # Buscar incidentes de alta prioridad de hoy
    today = date.today().isoformat()
    
    high_priority = con.execute(f"""
        SELECT 
            incident_id,
            tipo_evento,
            departamento,
            muertos,
            heridos,
            titulo
        FROM gold_incidents
        WHERE fecha_incidente = '{today}'
          AND (
              muertos > 0 
              OR heridos >= 5
              OR tipo_evento IN ('terrorismo', 'violencia_politica', 'violencia_armada')
          )
        ORDER BY muertos DESC, heridos DESC
    """).fetchdf()
    
    alerts_count = len(high_priority)
    
    if alerts_count > 0:
        logger.warning(f"[ALERTAS] {alerts_count} incidentes de alta prioridad hoy")
        
        # Insertar en ops_alerts (si existe la tabla)
        try:
            for _, row in high_priority.iterrows():
                con.execute("""
                    INSERT INTO ops_alerts (alert_type, severity, message, incident_id, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, [
                    row['tipo_evento'],
                    'HIGH' if row['muertos'] > 0 else 'MEDIUM',
                    f"{row['tipo_evento']}: {row['titulo'][:100]}",
                    row['incident_id']
                ])
        except Exception as e:
            logger.debug(f"No se pudieron insertar alertas: {e}")
    else:
        logger.info("[ALERTAS] Sin alertas de alta prioridad hoy")
    
    con.close()
    
    return {
        "alerts_generated": alerts_count,
        "high_priority_incidents": high_priority.to_dict('records') if alerts_count > 0 else []
    }


# =============================================================================
# PASO 4: RESUMEN DIARIO
# =============================================================================

def generate_daily_summary() -> Dict[str, Any]:
    """
    Genera resumen diario para reporting.
    """
    con = duckdb.connect(DB_PATH)
    today = date.today().isoformat()
    
    # Stats del día
    stats = con.execute(f"""
        SELECT 
            COUNT(*) as total_incidentes,
            COALESCE(SUM(muertos), 0) as total_muertos,
            COALESCE(SUM(heridos), 0) as total_heridos
        FROM gold_incidents
        WHERE fecha_incidente = '{today}'
    """).fetchone()
    
    # Por tipo
    by_type = con.execute(f"""
        SELECT tipo_evento, COUNT(*) as n
        FROM gold_incidents
        WHERE fecha_incidente = '{today}'
        GROUP BY 1 ORDER BY 2 DESC
    """).fetchdf()
    
    # Por departamento
    by_depto = con.execute(f"""
        SELECT COALESCE(departamento, 'Sin ubicación') as depto, COUNT(*) as n
        FROM gold_incidents
        WHERE fecha_incidente = '{today}'
        GROUP BY 1 ORDER BY 2 DESC
    """).fetchdf()
    
    con.close()
    
    summary = {
        "fecha": today,
        "total_incidentes": stats[0],
        "total_muertos": stats[1],
        "total_heridos": stats[2],
        "por_tipo": dict(zip(by_type['tipo_evento'], by_type['n'])) if len(by_type) > 0 else {},
        "por_departamento": dict(zip(by_depto['depto'], by_depto['n'])) if len(by_depto) > 0 else {},
    }
    
    logger.info(f"[RESUMEN] {today}: {stats[0]} incidentes, {stats[1]} muertos, {stats[2]} heridos")
    
    return summary


# =============================================================================
# PIPELINE COMPLETO
# =============================================================================

def run_full_pipeline(
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    max_articles: Optional[int] = None,
    enrich_limit: int = DEFAULT_ENRICH_BATCH,
    skip_ingest: bool = False,
    skip_enrich: bool = False,
    process_all_pending: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta pipeline diario completo.
    
    Args:
        process_all_pending: Si True, procesa TODOS los artículos pendientes (no solo un batch)
    """
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("PIPELINE DIARIO OSINT PERÚ 2026")
    logger.info(f"Inicio: {start_time.isoformat()}")
    logger.info("=" * 60)
    
    results = {}
    
    # 1. Ingesta
    if not skip_ingest:
        if date_end is None:
            date_end = date.today()
        if date_start is None:
            date_start = date_end - timedelta(days=1)
        
        logger.info("\n[1/4] INGESTA")
        results["ingestion"] = run_ingestion(date_start, date_end, max_articles)
    else:
        logger.info("\n[1/4] INGESTA - Saltada")
        results["ingestion"] = {"skipped": True}
    
    # 2. Enriquecimiento
    if not skip_enrich:
        logger.info("\n[2/4] ENRIQUECIMIENTO LLM")
        results["enrichment"] = run_enrichment(
            limit=enrich_limit, 
            process_all=process_all_pending
        )
    else:
        logger.info("\n[2/4] ENRIQUECIMIENTO - Saltado")
        results["enrichment"] = {"skipped": True}
    
    # 3. Alertas
    logger.info("\n[3/4] ALERTAS")
    results["alerts"] = check_and_generate_alerts()
    
    # 4. Resumen
    logger.info("\n[4/4] RESUMEN DIARIO")
    results["summary"] = generate_daily_summary()
    
    # Fin
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 60)
    logger.success("PIPELINE COMPLETADO")
    logger.info(f"Duración: {duration:.1f} segundos")
    if "enrichment" in results and "cost_usd" in results["enrichment"]:
        logger.info(f"Costo LLM: ${results['enrichment']['cost_usd']}")
    logger.info("=" * 60)
    
    results["duration_seconds"] = duration
    
    return results


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline Diario OSINT Perú 2026")
    
    # Modos
    parser.add_argument("--full", action="store_true", help="Pipeline completo")
    parser.add_argument("--ingest-only", action="store_true", help="Solo ingesta")
    parser.add_argument("--enrich-only", action="store_true", help="Solo enriquecimiento")
    parser.add_argument("--status", action="store_true", help="Mostrar estado")
    
    # Parámetros
    parser.add_argument("--date-start", type=str, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--date-end", type=str, help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--max-articles", type=int, default=None, 
                        help="Límite máximo de artículos (auto-calculado si no se especifica)")
    parser.add_argument("--enrich-limit", type=int, default=DEFAULT_ENRICH_BATCH,
                        help=f"Artículos por batch de LLM (default: {DEFAULT_ENRICH_BATCH})")
    parser.add_argument("--single-batch", action="store_true",
                        help="Solo procesar un batch de enriquecimiento (no todos los pendientes)")
    
    args = parser.parse_args()
    
    # Parsear fechas
    date_start = date.fromisoformat(args.date_start) if args.date_start else None
    date_end = date.fromisoformat(args.date_end) if args.date_end else None
    
    if args.status:
        con = duckdb.connect(DB_PATH)
        print("\n=== ESTADO DEL SISTEMA ===")
        for t in ['bronze_news', 'silver_news_enriched', 'gold_incidents', 'gold_daily_stats']:
            count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:25} {count:>6} rows")
        
        pending = con.execute("""
            SELECT COUNT(*) FROM bronze_news b
            LEFT JOIN silver_news_enriched s ON b.incident_id = s.bronze_id
            WHERE s.bronze_id IS NULL
        """).fetchone()[0]
        print(f"\n  Pendientes de enriquecer: {pending}")
        
        # Mostrar rango de fechas
        date_range = con.execute("""
            SELECT MIN(CAST(published_at AS DATE)), MAX(CAST(published_at AS DATE))
            FROM bronze_news
        """).fetchone()
        if date_range[0]:
            print(f"  Rango de fechas: {date_range[0]} a {date_range[1]}")
        
        con.close()
    
    elif args.full:
        run_full_pipeline(
            date_start=date_start,
            date_end=date_end,
            max_articles=args.max_articles,
            enrich_limit=args.enrich_limit,
            process_all_pending=not args.single_batch,
        )
    
    elif args.ingest_only:
        if date_end is None:
            date_end = date.today()
        if date_start is None:
            date_start = date_end - timedelta(days=1)
        run_ingestion(date_start, date_end, args.max_articles)
    
    elif args.enrich_only:
        run_enrichment(limit=args.enrich_limit, process_all=not args.single_batch)
    
    else:
        parser.print_help()
