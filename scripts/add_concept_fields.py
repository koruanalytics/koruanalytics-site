#!/usr/bin/env python3
"""
scripts/add_concept_fields.py

Agrega campos separados para personas y organizaciones extraídas del API:
- persons_mentioned: Lista de personas (type='person')
- orgs_mentioned: Lista de organizaciones (type='org')

También crea un script de alertas automáticas.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger


def migrate_add_concept_columns():
    """Añade columnas para personas y organizaciones."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    tables = ["stg_incidents_extracted", "fct_incidents", "fct_daily_report"]
    columns = [
        ("persons_mentioned", "VARCHAR"),
        ("orgs_mentioned", "VARCHAR"),
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


def update_normalize_script():
    """Muestra el código a añadir en normalize_newsapi_ai.py"""
    
    code = '''
# === AÑADIR EN normalize_newsapi_ai.py, en la función de normalización ===

def extract_concepts_by_type(concepts: list) -> dict:
    """Extrae concepts separados por tipo."""
    result = {
        'persons': [],
        'orgs': [],
        'locations': [],
        'wiki': [],
    }
    
    for c in (concepts or []):
        ctype = c.get('type', '')
        label = c.get('label', {})
        
        # El label puede ser dict {'eng': 'Name'} o string
        if isinstance(label, dict):
            name = label.get('eng') or label.get('spa') or list(label.values())[0] if label else ''
        else:
            name = str(label)
        
        if not name:
            continue
            
        if ctype == 'person':
            result['persons'].append(name)
        elif ctype == 'org':
            result['orgs'].append(name)
        elif ctype == 'loc':
            result['locations'].append(name)
        else:
            result['wiki'].append(name)
    
    return result

# En el loop de normalización, después de extraer concept_labels:
# concepts_by_type = extract_concepts_by_type(article.get('concepts', []))
# row['persons_mentioned'] = '; '.join(concepts_by_type['persons'][:5]) or None
# row['orgs_mentioned'] = '; '.join(concepts_by_type['orgs'][:5]) or None
'''
    print(code)


def backfill_from_raw():
    """Rellena persons/orgs desde los archivos raw existentes."""
    import json
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    raw_dir = Path("data/raw/newsapi_ai")
    if not raw_dir.exists():
        logger.error("No existe data/raw/newsapi_ai")
        return
    
    # Procesar cada archivo raw
    updates = []
    for raw_file in sorted(raw_dir.glob("*.json")):
        try:
            with open(raw_file, encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Error leyendo {raw_file}: {e}")
            continue
        
        for art in data.get('articles', []):
            uri = art.get('uri') or art.get('url', '')
            
            persons = []
            orgs = []
            
            for c in art.get('concepts', []):
                ctype = c.get('type', '')
                label = c.get('label', {})
                
                if isinstance(label, dict):
                    name = label.get('eng') or label.get('spa') or ''
                else:
                    name = str(label) if label else ''
                
                if not name:
                    continue
                
                if ctype == 'person':
                    persons.append(name)
                elif ctype == 'org':
                    orgs.append(name)
            
            if persons or orgs:
                updates.append({
                    'uri': uri,
                    'persons': '; '.join(persons[:5]) if persons else None,
                    'orgs': '; '.join(orgs[:5]) if orgs else None,
                })
    
    logger.info(f"Procesados {len(updates)} artículos con persons/orgs")
    
    # Actualizar en la BD
    updated = 0
    for upd in updates:
        if upd['persons'] or upd['orgs']:
            try:
                con.execute("""
                    UPDATE stg_incidents_extracted 
                    SET persons_mentioned = ?, orgs_mentioned = ?
                    WHERE original_uri = ? OR url = ?
                """, [upd['persons'], upd['orgs'], upd['uri'], upd['uri']])
                updated += 1
            except:
                pass
    
    # También actualizar fct_daily_report
    con.execute("""
        UPDATE fct_daily_report SET 
            persons_mentioned = s.persons_mentioned,
            orgs_mentioned = s.orgs_mentioned
        FROM stg_incidents_extracted s
        WHERE fct_daily_report.incident_id = s.incident_id
    """)
    
    con.close()
    logger.success(f"Actualizados {updated} registros con persons/orgs")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true", help="Añadir columnas a tablas")
    parser.add_argument("--backfill", action="store_true", help="Rellenar desde raw JSON")
    parser.add_argument("--show-code", action="store_true", help="Mostrar código para normalize")
    parser.add_argument("--all", action="store_true", help="Ejecutar todo")
    
    args = parser.parse_args()
    
    if args.all or args.migrate:
        print("=== Migración ===")
        migrate_add_concept_columns()
    
    if args.all or args.backfill:
        print("\n=== Backfill desde raw ===")
        backfill_from_raw()
    
    if args.show_code:
        print("\n=== Código para normalize ===")
        update_normalize_script()
    
    if not any([args.migrate, args.backfill, args.show_code, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
