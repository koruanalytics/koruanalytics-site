#!/usr/bin/env python3
"""
scripts/build_fct_daily_report.py

Construye fct_daily_report desde stg_incidents_extracted o fct_incidents.
Genera resúmenes extractivos usando sumy (si está disponible).

La tabla fct_daily_report está diseñada para generar informes diarios
de incidentes con un formato listo para consumir.

Usage:
    # Construir desde un run específico
    python scripts/build_fct_daily_report.py --run-id 20251219...
    
    # Construir desde una fecha específica
    python scripts/build_fct_daily_report.py --date 2025-12-19
    
    # Construir desde los últimos N días
    python scripts/build_fct_daily_report.py --days 7
    
    # Reconstruir todo (desde stg_incidents_extracted)
    python scripts/build_fct_daily_report.py --rebuild-all
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
from loguru import logger

from src.utils.config import load_config

# Try to import sumy for summarization
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False
    logger.warning("sumy not installed. Using fallback summarization. Install with: pip install sumy")


# =============================================================================
# DDL
# =============================================================================

FCT_DAILY_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS fct_daily_report (
    -- Keys
    report_id VARCHAR PRIMARY KEY,
    incident_id VARCHAR,
    ingest_run_id VARCHAR,
    
    -- Temporal
    incident_date DATE,
    report_date DATE DEFAULT CURRENT_DATE,
    
    -- Source
    source_name VARCHAR,
    source_title VARCHAR,
    url VARCHAR,
    
    -- Location
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    location_display VARCHAR,
    
    -- Classification
    event_type VARCHAR,
    sub_event_type VARCHAR,
    disorder_type VARCHAR,
    api_category VARCHAR,
    confidence DOUBLE,
    
    -- Content
    title VARCHAR,
    summary_es VARCHAR,
    summary_en VARCHAR,
    
    -- Entities
    persons_mentioned VARCHAR,
    organizations_mentioned VARCHAR,
    concept_labels VARCHAR,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# =============================================================================
# SUMMARIZATION
# =============================================================================

def summarize_text(text: str, language: str = "spanish", sentences: int = 2) -> Optional[str]:
    """
    Generate extractive summary using sumy LSA algorithm.
    Falls back to first N sentences if sumy not available.
    
    Args:
        text: Input text to summarize
        language: Language for tokenization (spanish, english)
        sentences: Number of sentences in summary
    
    Returns:
        Summary string or None if text is empty
    """
    if not text or len(text.strip()) < 50:
        return text if text else None
    
    if SUMY_AVAILABLE:
        try:
            parser = PlaintextParser.from_string(text, Tokenizer(language))
            summarizer = LsaSummarizer()
            summary_sentences = summarizer(parser.document, sentences)
            result = " ".join(str(s) for s in summary_sentences)
            if result.strip():
                return result
        except Exception as e:
            logger.debug(f"Sumy failed, using fallback: {e}")
    
    # Fallback: extract first N sentences
    return _fallback_summary(text, sentences)


def _fallback_summary(text: str, sentences: int = 2) -> str:
    """Extract first N sentences as summary."""
    if not text:
        return ""
    
    # Split by sentence endings
    import re
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) <= sentences:
        return text[:500]  # Limit length
    
    summary = " ".join(parts[:sentences])
    return summary[:500]  # Limit length


# =============================================================================
# HELPERS
# =============================================================================

def build_location_display(adm3: str, adm2: str, adm1: str) -> str:
    """Build human-readable location string."""
    parts = [p for p in [adm3, adm2, adm1] if p and str(p).strip()]
    return ", ".join(parts) if parts else "Perú"


def generate_report_id(incident_id: str) -> str:
    """Generate unique report ID from incident ID."""
    if not incident_id:
        return f"RPT_{hashlib.md5(str(date.today()).encode()).hexdigest()[:12]}"
    return f"RPT_{incident_id[:16]}"


# =============================================================================
# MAIN BUILD FUNCTION
# =============================================================================

def build_daily_report(
    con: duckdb.DuckDBPyConnection,
    run_id: str = None,
    target_date: date = None,
    days: int = None,
    rebuild_all: bool = False,
) -> dict:
    """
    Build fct_daily_report from incidents.
    
    Args:
        con: DuckDB connection
        run_id: Filter by specific run ID
        target_date: Filter by incident date
        days: Filter by last N days
        rebuild_all: Rebuild entire table from all incidents
    
    Returns:
        dict with build statistics
    """
    # Ensure table exists
    con.execute(FCT_DAILY_REPORT_DDL)
    
    # Build WHERE clause
    where_clauses = []
    params = []
    
    if run_id:
        where_clauses.append("ingest_run_id = ?")
        params.append(run_id)
    
    if target_date:
        where_clauses.append("DATE(published_at) = ?")
        params.append(target_date)
    
    if days:
        start_date = date.today() - timedelta(days=days)
        where_clauses.append("DATE(published_at) >= ?")
        params.append(start_date)
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Query incidents (use DISTINCT to avoid duplicates)
    query = f"""
        SELECT DISTINCT ON (incident_id)
            incident_id,
            ingest_run_id,
            published_at,
            source,
            source_title,
            url,
            adm1,
            adm2,
            adm3,
            lat,
            lon,
            incident_type,
            sub_event_type,
            disorder_type,
            api_category,
            confidence,
            title,
            body,
            concept_labels
        FROM stg_incidents_extracted
        {where_sql}
        ORDER BY incident_id, published_at DESC
    """
    
    incidents = con.execute(query, params).fetchdf()
    
    if incidents.empty:
        logger.warning("No incidents found matching criteria")
        return {"status": "warning", "message": "No incidents found", "rows": 0}
    
    logger.info(f"Processing {len(incidents)} incidents...")
    
    # Build report rows
    rows = []
    for _, inc in incidents.iterrows():
        # Generate summary
        body = inc.get("body") or ""
        summary_es = summarize_text(body, "spanish", 2)
        
        # Detect language and generate English summary if needed
        summary_en = None
        lang = "es"
        if body and any(word in body.lower() for word in ["the ", " is ", " are ", " was "]):
            lang = "en"
            summary_en = summarize_text(body, "english", 2)
            if not summary_es or summary_es == summary_en:
                summary_es = summary_en  # Use English as Spanish too
        
        # Parse date
        published_at = inc.get("published_at")
        if pd.notna(published_at):
            if hasattr(published_at, 'date'):
                incident_date = published_at.date()
            else:
                try:
                    incident_date = pd.to_datetime(published_at).date()
                except:
                    incident_date = None
        else:
            incident_date = None
        
        rows.append({
            "report_id": generate_report_id(inc.get("incident_id")),
            "incident_id": inc.get("incident_id"),
            "ingest_run_id": inc.get("ingest_run_id"),
            "incident_date": incident_date,
            "report_date": date.today(),
            "source_name": inc.get("source"),
            "source_title": inc.get("source_title"),
            "url": inc.get("url"),
            "adm1": inc.get("adm1"),
            "adm2": inc.get("adm2"),
            "adm3": inc.get("adm3"),
            "lat": inc.get("lat"),
            "lon": inc.get("lon"),
            "location_display": build_location_display(
                inc.get("adm3"), inc.get("adm2"), inc.get("adm1")
            ),
            "event_type": inc.get("incident_type"),
            "sub_event_type": inc.get("sub_event_type"),
            "disorder_type": inc.get("disorder_type"),
            "api_category": inc.get("api_category"),
            "confidence": inc.get("confidence"),
            "title": inc.get("title"),
            "summary_es": summary_es,
            "summary_en": summary_en,
            "persons_mentioned": None,  # TODO: Extract from concept_labels
            "organizations_mentioned": None,  # TODO: Extract from concept_labels
            "concept_labels": inc.get("concept_labels"),
        })
    
    df = pd.DataFrame(rows)
    
    # Delete existing rows for idempotency
    if run_id:
        con.execute("DELETE FROM fct_daily_report WHERE ingest_run_id = ?", [run_id])
    elif target_date:
        con.execute("DELETE FROM fct_daily_report WHERE incident_date = ?", [target_date])
    elif days:
        start_date = date.today() - timedelta(days=days)
        con.execute("DELETE FROM fct_daily_report WHERE incident_date >= ?", [start_date])
    elif rebuild_all:
        con.execute("DELETE FROM fct_daily_report")
    
    # Insert new rows
    con.register("df_report", df)
    
    # Get columns that exist in both DataFrame and table
    table_cols = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'fct_daily_report'"
    ).fetchall()]
    
    common_cols = [c for c in df.columns if c in table_cols]
    cols_sql = ", ".join([f'"{c}"' for c in common_cols])
    
    con.execute(f"""
        INSERT INTO fct_daily_report ({cols_sql})
        SELECT {cols_sql} FROM df_report
    """)
    
    inserted = con.execute("SELECT COUNT(*) FROM fct_daily_report").fetchone()[0]
    
    logger.success(f"Built fct_daily_report: {len(rows)} rows inserted, {inserted} total")
    
    return {
        "status": "ok",
        "rows_processed": len(incidents),
        "rows_inserted": len(rows),
        "total_rows": inserted,
        "sumy_available": SUMY_AVAILABLE,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Build fct_daily_report")
    parser.add_argument("--run-id", help="Filter by ingest run ID")
    parser.add_argument("--date", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Filter by last N days")
    parser.add_argument("--rebuild-all", action="store_true", help="Rebuild entire table")
    parser.add_argument("--db", help="Path to DuckDB (default: from config)")
    
    args = parser.parse_args()
    
    # Load config
    cfg = load_config()
    db_path = args.db or cfg["db"]["duckdb_path"]
    
    logger.info(f"Database: {db_path}")
    
    con = duckdb.connect(db_path)
    
    try:
        target_date = None
        if args.date:
            target_date = date.fromisoformat(args.date)
        
        result = build_daily_report(
            con=con,
            run_id=args.run_id,
            target_date=target_date,
            days=args.days,
            rebuild_all=args.rebuild_all,
        )
        
        logger.info(f"Result: {result}")
        
        # Show sample
        if result.get("rows_inserted", 0) > 0:
            sample = con.execute("""
                SELECT incident_date, source_title, location_display, 
                       event_type, LEFT(title, 50) as title_short
                FROM fct_daily_report
                ORDER BY incident_date DESC
                LIMIT 5
            """).fetchdf()
            logger.info(f"\nSample:\n{sample.to_string()}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
