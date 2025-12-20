#!/usr/bin/env python3
"""
scripts/generate_alerts.py

Genera alertas automáticas para incidentes críticos.

Criterios de alerta:
- violence_against_civilians con confianza >= 0.6
- battles con confianza >= 0.5
- explosions_remote_violence con confianza >= 0.5
- Incidentes con palabras clave críticas (asesinato, secuestro, bomba)

Usage:
    python scripts/generate_alerts.py
    python scripts/generate_alerts.py --days 1
    python scripts/generate_alerts.py --output alerts.json
    python scripts/generate_alerts.py --email  # Futuro: enviar por email
"""
import sys
import json
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger


# Configuración de alertas
ALERT_CONFIG = {
    "high_priority_types": {
        "violence_against_civilians": 0.6,
        "battles": 0.5,
        "explosions_remote_violence": 0.5,
    },
    "critical_keywords": [
        "asesinato", "asesinado", "asesinada", "asesinan",
        "secuestro", "secuestrado", "secuestrada",
        "bomba", "explosion", "atentado",
        "linchamiento", "linchado",
        "candidato", "candidata", "politico", "alcalde",
    ],
    "max_alerts": 20,
}


def generate_alerts(con: duckdb.DuckDBPyConnection, days: int = 7) -> list:
    """Genera lista de alertas basada en criterios."""
    
    alerts = []
    start_date = date.today() - timedelta(days=days)
    
    # Alerta 1: Por tipo de incidente y confianza
    for incident_type, min_conf in ALERT_CONFIG["high_priority_types"].items():
        results = con.execute(f"""
            SELECT 
                incident_id,
                incident_date,
                source_title,
                location_display,
                event_type,
                confidence,
                title,
                url,
                persons_mentioned,
                orgs_mentioned
            FROM fct_daily_report
            WHERE event_type = '{incident_type}'
              AND confidence >= {min_conf}
              AND incident_date >= '{start_date}'
            ORDER BY confidence DESC, incident_date DESC
            LIMIT 10
        """).fetchdf()
        
        for _, row in results.iterrows():
            alerts.append({
                "type": "high_confidence",
                "severity": "HIGH" if row["confidence"] >= 0.7 else "MEDIUM",
                "incident_type": row["event_type"],
                "confidence": row["confidence"],
                "date": str(row["incident_date"]),
                "title": row["title"],
                "location": row["location_display"],
                "source": row["source_title"],
                "url": row["url"],
                "persons": row["persons_mentioned"],
                "orgs": row["orgs_mentioned"],
                "incident_id": row["incident_id"],
            })
    
    # Alerta 2: Por palabras clave críticas (sin importar tipo)
    keywords_pattern = "|".join(ALERT_CONFIG["critical_keywords"])
    
    keyword_results = con.execute(f"""
        SELECT 
            incident_id,
            incident_date,
            source_title,
            location_display,
            event_type,
            confidence,
            title,
            url
        FROM fct_daily_report
        WHERE incident_date >= '{start_date}'
          AND (
            LOWER(title) SIMILAR TO '.*({keywords_pattern}).*'
          )
          AND incident_id NOT IN (
            SELECT incident_id FROM fct_daily_report
            WHERE event_type IN ('violence_against_civilians', 'battles', 'explosions_remote_violence')
              AND confidence >= 0.5
          )
        ORDER BY incident_date DESC
        LIMIT 10
    """).fetchdf()
    
    for _, row in keyword_results.iterrows():
        alerts.append({
            "type": "keyword_match",
            "severity": "MEDIUM",
            "incident_type": row["event_type"],
            "confidence": row["confidence"],
            "date": str(row["incident_date"]),
            "title": row["title"],
            "location": row["location_display"],
            "source": row["source_title"],
            "url": row["url"],
            "incident_id": row["incident_id"],
        })
    
    # Deduplicar por incident_id
    seen = set()
    unique_alerts = []
    for alert in alerts:
        if alert["incident_id"] not in seen:
            seen.add(alert["incident_id"])
            unique_alerts.append(alert)
    
    # Ordenar por severidad y fecha
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    unique_alerts.sort(key=lambda x: (severity_order.get(x["severity"], 2), x["date"]), reverse=True)
    
    return unique_alerts[:ALERT_CONFIG["max_alerts"]]


def print_alerts(alerts: list):
    """Imprime alertas en formato legible."""
    
    if not alerts:
        print("✅ No hay alertas críticas")
        return
    
    print(f"🚨 {len(alerts)} ALERTAS DETECTADAS")
    print("=" * 70)
    
    for i, alert in enumerate(alerts, 1):
        severity_icon = "🔴" if alert["severity"] == "HIGH" else "🟡"
        
        print(f"\n{severity_icon} [{i}] {alert['severity']} - {alert['incident_type']}")
        print(f"   📅 {alert['date']} | 📍 {alert.get('location', 'N/A')}")
        print(f"   📰 {alert['title'][:70]}...")
        print(f"   🔗 {alert.get('url', 'N/A')[:60]}...")
        
        if alert.get('persons'):
            print(f"   👤 Personas: {alert['persons']}")
        if alert.get('orgs'):
            print(f"   🏢 Orgs: {alert['orgs']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generar alertas de incidentes críticos")
    parser.add_argument("--days", type=int, default=7, help="Días hacia atrás (default: 7)")
    parser.add_argument("--output", help="Guardar alertas en archivo JSON")
    parser.add_argument("--quiet", action="store_true", help="Solo mostrar conteo")
    
    args = parser.parse_args()
    
    from src.utils.config import load_config
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    try:
        alerts = generate_alerts(con, args.days)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(alerts, f, indent=2, ensure_ascii=False)
            print(f"✅ {len(alerts)} alertas guardadas en {args.output}")
        elif args.quiet:
            print(f"Alertas: {len(alerts)}")
        else:
            print_alerts(alerts)
        
        # Resumen por severidad
        high = sum(1 for a in alerts if a["severity"] == "HIGH")
        medium = sum(1 for a in alerts if a["severity"] == "MEDIUM")
        
        if not args.quiet:
            print(f"\n📊 Resumen: {high} HIGH, {medium} MEDIUM")
        
    finally:
        con.close()


if __name__ == "__main__":
    main()
