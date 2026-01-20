"""
scripts/utils/export_gold_to_csv.py
Last updated: 2026-01-16
Description: Export gold_incidents to CSV with UTF-8-sig encoding for Power BI.

M9: This script ensures proper encoding for Spanish characters in Power BI/Excel.
Uses UTF-8-sig (with BOM) which Excel and Power BI recognize automatically.

USAGE:
    python scripts/utils/export_gold_to_csv.py
    python scripts/utils/export_gold_to_csv.py --output data/exports/incidents.csv
    python scripts/utils/export_gold_to_csv.py --validate
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import duckdb
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.text_utils import normalize_unicode, has_unicode_escapes


def export_gold_to_csv(
    db_path: str,
    output_path: str,
    validate: bool = True
) -> dict:
    """
    Export gold_incidents to CSV with proper UTF-8 encoding.
    
    Args:
        db_path: Path to DuckDB database
        output_path: Path for output CSV file
        validate: If True, check for remaining Unicode escapes
        
    Returns:
        Dictionary with export statistics
    """
    con = duckdb.connect(db_path, read_only=True)
    
    # Get all records from gold_incidents
    df = con.execute("""
        SELECT 
            incident_id,
            tipo_evento,
            subtipo,
            fecha_incidente,
            fecha_publicacion,
            muertos,
            heridos,
            departamento,
            provincia,
            distrito,
            adm4_name,
            ubicacion_display,
            lat,
            lon,
            tiene_geo,
            nivel_geo,
            actores,
            organizaciones,
            titulo,
            resumen,
            url,
            source_name,
            sentiment,
            relevancia_score
        FROM gold_incidents
        ORDER BY fecha_incidente DESC, fecha_publicacion DESC
    """).fetchdf()
    
    con.close()
    
    if len(df) == 0:
        logger.warning("No records found in gold_incidents")
        return {"exported": 0, "errors": 0, "file": None}
    
    # M9: Apply final normalization to ensure no escapes remain
    text_columns = [
        'titulo', 'resumen', 'actores', 'organizaciones',
        'departamento', 'provincia', 'distrito', 'adm4_name',
        'ubicacion_display', 'source_name', 'subtipo'
    ]
    
    escapes_found = 0
    for col in text_columns:
        if col in df.columns:
            for idx, val in df[col].items():
                if isinstance(val, str) and has_unicode_escapes(val):
                    escapes_found += 1
                    df.at[idx, col] = normalize_unicode(val)
    
    if escapes_found > 0:
        logger.warning(f"Found and fixed {escapes_found} Unicode escape sequences")
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Export with UTF-8-sig (includes BOM for Excel/Power BI)
    df.to_csv(
        output_file,
        index=False,
        encoding='utf-8-sig',  # BOM for Windows compatibility
        date_format='%Y-%m-%d'
    )
    
    logger.success(f"Exported {len(df)} records to {output_file}")
    
    # Validation step
    errors = 0
    if validate:
        logger.info("Validating exported file...")
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            if '\\u00' in content:
                errors += 1
                logger.error("VALIDATION FAILED: Unicode escapes still present in output")
                # Find examples
                import re
                matches = re.findall(r'\\u[0-9a-fA-F]{4}', content)[:5]
                logger.error(f"Examples: {matches}")
            else:
                logger.success("VALIDATION PASSED: No Unicode escapes in output")
    
    return {
        "exported": len(df),
        "escapes_fixed": escapes_found,
        "errors": errors,
        "file": str(output_file)
    }


def validate_database_encoding(db_path: str) -> dict:
    """
    Check for Unicode escape sequences across all Medallion tables.
    
    Returns statistics on encoding issues found.
    """
    con = duckdb.connect(db_path, read_only=True)
    results = {}
    
    checks = [
        ("bronze_news", ["title", "body", "source_title"]),
        ("silver_news_enriched", ["title", "resumen_es", "resumen_en", "departamento", "actores_json", "organizaciones_json"]),
        ("gold_incidents", ["titulo", "resumen", "actores", "organizaciones", "ubicacion_display"]),
    ]
    
    for table, columns in checks:
        table_issues = {}
        try:
            for col in columns:
                # Check for \u escapes in column
                count = con.execute(f"""
                    SELECT COUNT(*) FROM {table}
                    WHERE {col} LIKE '%\\u00%'
                """).fetchone()[0]
                
                if count > 0:
                    table_issues[col] = count
                    
        except Exception as e:
            table_issues["_error"] = str(e)
        
        results[table] = table_issues
    
    con.close()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export gold_incidents to CSV with UTF-8-sig encoding"
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("DB_PATH", "data/osint_dw.duckdb"),
        help="Path to DuckDB database"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: data/exports/gold_incidents_YYYYMMDD.csv)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate exported file for encoding issues"
    )
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Check database tables for encoding issues"
    )
    
    args = parser.parse_args()
    
    if args.check_db:
        print("\n=== DATABASE ENCODING CHECK ===\n")
        results = validate_database_encoding(args.db_path)
        
        total_issues = 0
        for table, issues in results.items():
            if issues:
                print(f"{table}:")
                for col, count in issues.items():
                    if col != "_error":
                        print(f"  - {col}: {count} records with escapes")
                        total_issues += count
                    else:
                        print(f"  - ERROR: {count}")
            else:
                print(f"{table}: ✓ Clean")
        
        print(f"\nTotal encoding issues: {total_issues}")
        exit(0)
    
    # Default output path with timestamp
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        args.output = f"data/exports/gold_incidents_{timestamp}.csv"
    
    result = export_gold_to_csv(
        db_path=args.db_path,
        output_path=args.output,
        validate=args.validate or True  # Always validate
    )
    
    print(f"\n=== EXPORT SUMMARY ===")
    print(f"Records exported: {result['exported']}")
    print(f"Escapes fixed:    {result['escapes_fixed']}")
    print(f"Validation errors: {result['errors']}")
    print(f"Output file:      {result['file']}")
