#!/usr/bin/env python3
"""
scripts/extract_sentiment.py

Extrae sentimiento de noticias usando pysentimiento (modelo RoBERTuito).

Campos añadidos:
- sentiment: 'POS', 'NEU', 'NEG'
- sentiment_score: float (probabilidad del sentimiento detectado)

Usage:
    python scripts/extract_sentiment.py --migrate    # Añadir columnas
    python scripts/extract_sentiment.py --backfill   # Analizar textos
    python scripts/extract_sentiment.py --all        # Todo
    python scripts/extract_sentiment.py --test       # Probar
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

# Lazy load del analyzer (tarda unos segundos)
_analyzer = None

def get_analyzer():
    """Carga el analizador de sentimiento (lazy)."""
    global _analyzer
    if _analyzer is None:
        logger.info("Cargando modelo de sentimiento (primera vez puede tardar)...")
        from pysentimiento import create_analyzer
        _analyzer = create_analyzer(task='sentiment', lang='es')
        logger.success("Modelo cargado")
    return _analyzer


def analyze_sentiment(text: str) -> dict:
    """
    Analiza el sentimiento de un texto.
    
    Args:
        text: Texto a analizar
    
    Returns:
        dict con 'sentiment' (POS/NEU/NEG) y 'score' (float)
    """
    if not text or len(text.strip()) < 10:
        return {"sentiment": None, "score": None}
    
    try:
        analyzer = get_analyzer()
        # Limitar texto a 512 tokens (límite del modelo)
        text = text[:1500]  # Aproximadamente 512 tokens
        
        result = analyzer.predict(text)
        
        return {
            "sentiment": result.output,  # POS, NEU, NEG
            "score": round(result.probas[result.output], 3),
        }
    except Exception as e:
        logger.warning(f"Error analizando sentimiento: {e}")
        return {"sentiment": None, "score": None}


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def migrate_add_sentiment_columns():
    """Añade columnas sentiment y sentiment_score a las tablas."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    tables = ["stg_incidents_extracted", "fct_incidents", "fct_daily_report"]
    columns = [
        ("sentiment", "VARCHAR"),
        ("sentiment_score", "DOUBLE"),
    ]
    
    for table in tables:
        for col_name, col_type in columns:
            try:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                logger.success(f"+ {table}.{col_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "Duplicate" in str(e):
                    logger.info(f"✓ {table}.{col_name} ya existe")
                else:
                    logger.warning(f"✗ {table}.{col_name}: {e}")
    
    con.close()
    print("\n✅ Migración completada")


def backfill_sentiment(limit: int = None):
    """
    Analiza sentimiento de incidentes existentes.
    
    Args:
        limit: Limitar número de incidentes (para pruebas)
    """
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    # Obtener incidentes sin sentimiento
    limit_sql = f"LIMIT {limit}" if limit else ""
    
    incidents = con.execute(f"""
        SELECT incident_id, title, body 
        FROM stg_incidents_extracted
        WHERE sentiment IS NULL
        {limit_sql}
    """).fetchdf()
    
    if len(incidents) == 0:
        logger.info("No hay incidentes pendientes de analizar")
        return
    
    logger.info(f"Analizando {len(incidents)} incidentes...")
    
    # Pre-cargar el modelo
    get_analyzer()
    
    updated = 0
    sentiment_counts = {"POS": 0, "NEU": 0, "NEG": 0}
    
    for i, row in incidents.iterrows():
        # Usar título + primeras líneas del body
        text = f"{row['title']}. {(row['body'] or '')[:500]}"
        
        result = analyze_sentiment(text)
        
        if result['sentiment']:
            con.execute("""
                UPDATE stg_incidents_extracted 
                SET sentiment = ?, sentiment_score = ?
                WHERE incident_id = ?
            """, [result['sentiment'], result['score'], row['incident_id']])
            
            updated += 1
            sentiment_counts[result['sentiment']] = sentiment_counts.get(result['sentiment'], 0) + 1
        
        # Progress
        if (i + 1) % 10 == 0:
            logger.info(f"  Procesados {i + 1}/{len(incidents)}...")
    
    # Propagar a fct_incidents
    con.execute("""
        UPDATE fct_incidents SET 
            sentiment = s.sentiment,
            sentiment_score = s.sentiment_score
        FROM stg_incidents_extracted s
        WHERE fct_incidents.incident_id = s.incident_id
    """)
    
    # Propagar a fct_daily_report
    con.execute("""
        UPDATE fct_daily_report SET 
            sentiment = s.sentiment,
            sentiment_score = s.sentiment_score
        FROM stg_incidents_extracted s
        WHERE fct_daily_report.incident_id = s.incident_id
    """)
    
    con.close()
    
    logger.success(f"Actualizados {updated} incidentes")
    logger.info(f"  POS: {sentiment_counts.get('POS', 0)}")
    logger.info(f"  NEU: {sentiment_counts.get('NEU', 0)}")
    logger.info(f"  NEG: {sentiment_counts.get('NEG', 0)}")


def test_sentiment():
    """Prueba el análisis de sentimiento."""
    
    test_cases = [
        ("Asesinan a payaso al acudir a dar un show", "NEG"),
        ("Miles marchan pacíficamente exigiendo reformas", "NEU"),
        ("Gobierno inaugura nueva escuela en zona rural", "POS"),
        ("Turba enfurecida lincha a presunto ladrón", "NEG"),
        ("Se firma acuerdo de paz entre las partes", "POS"),
        ("Detienen a sospechosos de narcotráfico", "NEG"),
    ]
    
    print("=== TEST DE SENTIMIENTO ===\n")
    
    analyzer = get_analyzer()
    
    for text, expected in test_cases:
        result = analyze_sentiment(text)
        match = result['sentiment'] == expected
        status = "✓" if match else "~"  # ~ porque el modelo puede variar
        
        print(f"{status} {result['sentiment']:4} ({result['score']:.2f}) -> {text[:50]}...")
        if not match:
            print(f"   (esperado: {expected})")
    
    print("\nNota: El modelo puede clasificar diferente según contexto.")


def show_results():
    """Muestra distribución de sentimientos."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    print("=== DISTRIBUCIÓN DE SENTIMIENTO ===\n")
    
    dist = con.execute("""
        SELECT 
            sentiment,
            COUNT(*) as count,
            ROUND(AVG(sentiment_score), 2) as avg_score
        FROM fct_daily_report
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ORDER BY count DESC
    """).fetchdf()
    
    print(dist.to_string(index=False))
    
    print("\n=== EJEMPLOS POR SENTIMIENTO ===\n")
    
    for sent in ['NEG', 'NEU', 'POS']:
        examples = con.execute(f"""
            SELECT sentiment_score, LEFT(title, 60) as title
            FROM fct_daily_report
            WHERE sentiment = '{sent}'
            ORDER BY sentiment_score DESC
            LIMIT 3
        """).fetchdf()
        
        if len(examples) > 0:
            print(f"\n{sent}:")
            for _, row in examples.iterrows():
                print(f"  ({row['sentiment_score']:.2f}) {row['title']}...")
    
    con.close()


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extraer sentimiento de noticias")
    parser.add_argument("--migrate", action="store_true", help="Añadir columnas")
    parser.add_argument("--backfill", action="store_true", help="Analizar textos")
    parser.add_argument("--limit", type=int, help="Limitar número de textos")
    parser.add_argument("--test", action="store_true", help="Probar análisis")
    parser.add_argument("--show", action="store_true", help="Mostrar resultados")
    parser.add_argument("--all", action="store_true", help="Ejecutar todo")
    
    args = parser.parse_args()
    
    if args.test:
        test_sentiment()
        return
    
    if args.all or args.migrate:
        print("=== Migración ===")
        migrate_add_sentiment_columns()
    
    if args.all or args.backfill:
        print("\n=== Backfill ===")
        backfill_sentiment(limit=args.limit)
    
    if args.all or args.show:
        print("\n")
        show_results()
    
    if not any([args.migrate, args.backfill, args.test, args.show, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
