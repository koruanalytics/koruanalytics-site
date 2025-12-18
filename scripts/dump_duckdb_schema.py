"""
scripts/dump_duckdb_schema.py - Export DuckDB schema to SQL file

Exports all tables and views with their column definitions.
Note: DuckDB doesn't support SHOW CREATE TABLE, so we generate DDL from metadata.

Usage:
    python scripts/dump_duckdb_schema.py
    python scripts/dump_duckdb_schema.py --stdout
    python scripts/dump_duckdb_schema.py --db path/to/db.duckdb
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger


def repo_root() -> Path:
    return PROJECT_ROOT


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def outputs_dir() -> Path:
    p = repo_root() / "outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Get all table names."""
    q = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    return [r[0] for r in con.execute(q).fetchall()]


def get_views(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Get all view names."""
    q = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
      AND table_type = 'VIEW'
    ORDER BY table_name
    """
    return [r[0] for r in con.execute(q).fetchall()]


def get_column_info(con: duckdb.DuckDBPyConnection, table: str) -> list[dict]:
    """Get column definitions for a table."""
    rows = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
    columns = []
    for row in rows:
        columns.append({
            "name": row[1],
            "type": row[2],
            "notnull": bool(row[3]),
            "default": row[4],
            "pk": bool(row[5]),
        })
    return columns


def get_row_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    """Get row count for a table."""
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return -1


def generate_create_table(table: str, columns: list[dict]) -> str:
    """Generate CREATE TABLE statement from column info."""
    lines = [f"CREATE TABLE {table} ("]
    
    col_defs = []
    pk_cols = []
    
    for col in columns:
        parts = [f'    "{col["name"]}"', col["type"]]
        
        if col["notnull"]:
            parts.append("NOT NULL")
        
        if col["default"] is not None:
            parts.append(f"DEFAULT {col['default']}")
        
        if col["pk"]:
            pk_cols.append(col["name"])
        
        col_defs.append(" ".join(parts))
    
    # Add primary key constraint if any
    if pk_cols:
        pk_str = ", ".join([f'"{c}"' for c in pk_cols])
        col_defs.append(f"    PRIMARY KEY ({pk_str})")
    
    lines.append(",\n".join(col_defs))
    lines.append(");")
    
    return "\n".join(lines)


def get_view_definition(con: duckdb.DuckDBPyConnection, view: str) -> str:
    """Try to get view definition."""
    try:
        # DuckDB stores view definitions in duckdb_views()
        result = con.execute(f"""
            SELECT sql FROM duckdb_views() WHERE view_name = '{view}'
        """).fetchone()
        if result:
            return result[0]
    except Exception:
        pass
    
    return f"-- View definition not available for {view}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Export DuckDB schema to SQL")
    ap.add_argument("--db", default=str(default_db_path()), help="Path to DuckDB file")
    ap.add_argument("--stdout", action="store_true", help="Also print to console")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return 1

    con = duckdb.connect(str(db_path), read_only=True)
    
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_sql = outputs_dir() / f"schema_dump_{ts}.sql"
        out_txt = outputs_dir() / f"schema_summary_{ts}.txt"

        tables = get_tables(con)
        views = get_views(con)

        logger.info(f"Found {len(tables)} tables, {len(views)} views in schema 'main'")

        # Generate SQL dump
        sql_lines = []
        sql_lines.append("-- " + "=" * 60)
        sql_lines.append("-- DuckDB Schema Dump")
        sql_lines.append(f"-- Generated: {ts}")
        sql_lines.append(f"-- Database: {args.db}")
        sql_lines.append(f"-- Tables: {len(tables)}, Views: {len(views)}")
        sql_lines.append("-- " + "=" * 60)
        sql_lines.append("")

        # Tables
        for table in tables:
            columns = get_column_info(con, table)
            row_count = get_row_count(con, table)
            
            sql_lines.append(f"-- Table: {table} ({row_count} rows, {len(columns)} columns)")
            sql_lines.append(generate_create_table(table, columns))
            sql_lines.append("")

        # Views
        for view in views:
            sql_lines.append(f"-- View: {view}")
            view_def = get_view_definition(con, view)
            sql_lines.append(view_def)
            sql_lines.append("")

        sql_content = "\n".join(sql_lines)
        out_sql.write_text(sql_content, encoding="utf-8")
        logger.success(f"SQL dump written: {out_sql}")

        # Generate summary
        summary_lines = []
        summary_lines.append(f"Schema Summary - {ts}")
        summary_lines.append("=" * 50)
        summary_lines.append("")
        summary_lines.append("TABLES:")
        for table in tables:
            row_count = get_row_count(con, table)
            col_count = len(get_column_info(con, table))
            summary_lines.append(f"  {table}: {row_count} rows, {col_count} columns")
        
        summary_lines.append("")
        summary_lines.append("VIEWS:")
        for view in views:
            summary_lines.append(f"  {view}")

        summary_content = "\n".join(summary_lines)
        out_txt.write_text(summary_content, encoding="utf-8")
        logger.success(f"Summary written: {out_txt}")

        if args.stdout:
            print(sql_content)

        return 0

    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())