#!/usr/bin/env python3
"""
scripts/migrate_add_api_fields.py

Migración para añadir campos de enriquecimiento del API a las tablas de incidentes.

Campos nuevos:
- sub_event_type: Subtipo ACLED (25 tipos)
- disorder_type: Tipo de desorden ACLED (3 tipos)
- source_title: Nombre del medio (El Comercio, RPP, etc.)
- is_duplicate: Flag de duplicado del API
- api_category: Categoría principal del API (Politics, Crime)
- api_location: Ubicación detectada por el API
- concept_labels: Entidades extraídas (personas, orgs, lugares)

Usage:
    python scripts/migrate_add_api_fields.py
    python scripts/migrate_add_api_fields.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger

from src.utils.config import load_config


# Columnas a añadir (nombre, tipo, valor por defecto)
COLUMNS_TO_ADD = [
    ("sub_event_type", "VARCHAR", None),
    ("disorder_type", "VARCHAR", None),
    ("source_title", "VARCHAR", None),
    ("is_duplicate", "BOOLEAN", None),
    ("api_category", "VARCHAR", None),
    ("api_location", "VARCHAR", None),
    ("concept_labels", "VARCHAR", None),
]

# Tablas a migrar
TABLES_TO_MIGRATE = [
    "stg_incidents_extracted",
    "fct_incidents",
    "fct_incidents_curated",
]


def get_table_columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    """Obtiene las columnas de una tabla."""
    try:
        result = con.execute(f"PRAGMA table_info('{table}')").fetchall()
        return {row[1] for row in result}
    except Exception:
        return set()


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    """Verifica si una tabla existe."""
    try:
        con.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def add_column(
    con: duckdb.DuckDBPyConnection,
    table: str,
    column: str,
    col_type: str,
    default: str | None = None,
    dry_run: bool = False
) -> bool:
    """Añade una columna a una tabla si no existe."""
    existing_cols = get_table_columns(con, table)
    
    if column in existing_cols:
        logger.info(f"  ✓ {table}.{column} ya existe")
        return False
    
    sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
    if default is not None:
        sql += f" DEFAULT {default}"
    
    if dry_run:
        logger.info(f"  [DRY-RUN] {sql}")
    else:
        con.execute(sql)
        logger.success(f"  + {table}.{column} ({col_type}) añadida")
    
    return True


def migrate_table(
    con: duckdb.DuckDBPyConnection,
    table: str,
    dry_run: bool = False
) -> dict:
    """Migra una tabla añadiendo las columnas faltantes."""
    result = {
        "table": table,
        "exists": False,
        "columns_added": [],
        "columns_skipped": [],
    }
    
    if not table_exists(con, table):
        logger.warning(f"  ⚠ Tabla {table} no existe - saltando")
        return result
    
    result["exists"] = True
    logger.info(f"Migrando: {table}")
    
    for col_name, col_type, col_default in COLUMNS_TO_ADD:
        added = add_column(con, table, col_name, col_type, col_default, dry_run)
        if added:
            result["columns_added"].append(col_name)
        else:
            result["columns_skipped"].append(col_name)
    
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Migración: añadir campos del API")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar cambios, no ejecutar")
    parser.add_argument("--db", default=None, help="Ruta a DuckDB (default: desde config)")
    args = parser.parse_args()
    
    # Cargar configuración
    cfg = load_config()
    db_path = args.db or cfg["db"]["duckdb_path"]
    
    logger.info(f"Database: {db_path}")
    if args.dry_run:
        logger.warning("=== MODO DRY-RUN: No se harán cambios ===")
    
    con = duckdb.connect(db_path)
    
    try:
        logger.info("=" * 60)
        logger.info("Migración: Añadir campos de enriquecimiento del API")
        logger.info("=" * 60)
        
        results = []
        for table in TABLES_TO_MIGRATE:
            result = migrate_table(con, table, args.dry_run)
            results.append(result)
        
        # También migrar curation_incident_overrides para override_sub_event_type y override_disorder_type
        logger.info("\nMigrando tabla de curación...")
        curation_cols = [
            ("override_sub_event_type", "VARCHAR", None),
            ("override_disorder_type", "VARCHAR", None),
        ]
        
        if table_exists(con, "curation_incident_overrides"):
            for col_name, col_type, col_default in curation_cols:
                add_column(con, "curation_incident_overrides", col_name, col_type, col_default, args.dry_run)
        
        # Resumen
        logger.info("\n" + "=" * 60)
        logger.info("RESUMEN DE MIGRACIÓN")
        logger.info("=" * 60)
        
        total_added = 0
        for r in results:
            if r["exists"]:
                added = len(r["columns_added"])
                total_added += added
                status = "✓" if added > 0 else "="
                logger.info(f"  {status} {r['table']}: +{added} columnas")
                if r["columns_added"]:
                    logger.info(f"      Añadidas: {', '.join(r['columns_added'])}")
        
        if args.dry_run:
            logger.warning(f"\n[DRY-RUN] Se habrían añadido {total_added} columnas")
        else:
            logger.success(f"\nMigración completada: {total_added} columnas añadidas")
        
        # Verificación final
        if not args.dry_run:
            logger.info("\nVerificación:")
            for table in TABLES_TO_MIGRATE:
                if table_exists(con, table):
                    cols = get_table_columns(con, table)
                    new_cols = [c for c, _, _ in COLUMNS_TO_ADD if c in cols]
                    logger.info(f"  {table}: {len(new_cols)}/{len(COLUMNS_TO_ADD)} campos API presentes")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
