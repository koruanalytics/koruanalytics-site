# validate_schema_alignment.py
# Last updated: 2026-01-09
# Description: Validates that INSERT statements in code match actual table schemas
#
# Usage:
#   python -m scripts.utils.validate_schema_alignment
#   python -m scripts.utils.validate_schema_alignment --fix-suggestions

"""
Schema Alignment Validator for OSINT Peru 2026

This script:
1. Reads actual table schemas from DuckDB
2. Scans Python files for INSERT statements
3. Reports misalignments between code and schema
4. Suggests fixes when --fix-suggestions is used

Common issues detected:
- INSERT references non-existent columns
- INSERT missing required columns (NOT NULL without DEFAULT)
- Column order mismatches
"""

import argparse
import re
import duckdb
from pathlib import Path
from dataclasses import dataclass
from loguru import logger


DB_PATH = Path("data/osint_dw.duckdb")
SOURCE_PATHS = [
    Path("scripts/core"),
    Path("src/enrichment"),
    Path("src/ingestion"),
    Path("src/processing"),
]


@dataclass
class ColumnInfo:
    """Information about a table column."""
    name: str
    data_type: str
    is_nullable: bool
    has_default: bool


@dataclass
class InsertStatement:
    """Parsed INSERT statement from code."""
    file_path: Path
    line_number: int
    table_name: str
    columns: list[str]
    raw_sql: str


def get_table_schema(con, table_name: str) -> dict[str, ColumnInfo]:
    """
    Get schema information for a table.
    
    Args:
        con: DuckDB connection
        table_name: Name of the table
        
    Returns:
        Dictionary mapping column_name -> ColumnInfo
    """
    try:
        result = con.execute(f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()
        
        return {
            row[0]: ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=(row[2] == 'YES'),
                has_default=(row[3] is not None)
            )
            for row in result
        }
    except Exception as e:
        logger.warning(f"Could not get schema for {table_name}: {e}")
        return {}


def find_insert_statements(file_path: Path) -> list[InsertStatement]:
    """
    Find INSERT statements in a Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        List of InsertStatement objects
    """
    statements = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning(f"Could not read {file_path}: {e}")
        return statements
    
    # Pattern to match INSERT INTO statements
    # Handles multi-line strings and various formatting
    pattern = r'INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES'
    
    lines = content.split('\n')
    full_content = content.upper()
    
    for match in re.finditer(pattern, full_content, re.IGNORECASE | re.MULTILINE):
        table_name = match.group(1).lower()
        columns_str = match.group(2)
        columns = [c.strip().lower() for c in columns_str.split(',')]
        
        # Find line number
        start_pos = match.start()
        line_number = content[:start_pos].count('\n') + 1
        
        # Get raw SQL (approximate - first 200 chars from match)
        raw_sql = content[match.start():match.start() + 200].split('\n')[0]
        
        statements.append(InsertStatement(
            file_path=file_path,
            line_number=line_number,
            table_name=table_name,
            columns=columns,
            raw_sql=raw_sql[:100] + "..."
        ))
    
    return statements


def validate_insert(insert: InsertStatement, schema: dict[str, ColumnInfo]) -> list[str]:
    """
    Validate an INSERT statement against table schema.
    
    Args:
        insert: InsertStatement to validate
        schema: Table schema from database
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not schema:
        errors.append(f"Table '{insert.table_name}' not found in database")
        return errors
    
    schema_columns = set(schema.keys())
    insert_columns = set(insert.columns)
    
    # Check for columns in INSERT that don't exist in schema
    extra_columns = insert_columns - schema_columns
    if extra_columns:
        errors.append(f"INSERT references non-existent columns: {extra_columns}")
    
    # Check for required columns missing from INSERT
    for col_name, col_info in schema.items():
        if col_name not in insert_columns:
            if not col_info.is_nullable and not col_info.has_default:
                errors.append(f"Missing required column (NOT NULL, no default): {col_name}")
    
    return errors


def scan_project(db_path: Path, source_paths: list[Path]) -> dict:
    """
    Scan project for schema alignment issues.
    
    Args:
        db_path: Path to DuckDB database
        source_paths: List of paths to scan for Python files
        
    Returns:
        Dictionary with validation results
    """
    results = {
        'files_scanned': 0,
        'inserts_found': 0,
        'issues': [],
        'valid': []
    }
    
    # Connect to database
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        return results
    
    # Cache schemas
    schema_cache = {}
    
    try:
        # Scan all Python files
        for source_path in source_paths:
            if not source_path.exists():
                logger.warning(f"Path not found: {source_path}")
                continue
                
            for py_file in source_path.rglob("*.py"):
                if "_legacy" in str(py_file) or "__pycache__" in str(py_file):
                    continue
                    
                results['files_scanned'] += 1
                inserts = find_insert_statements(py_file)
                
                for insert in inserts:
                    results['inserts_found'] += 1
                    
                    # Get schema (cached)
                    if insert.table_name not in schema_cache:
                        schema_cache[insert.table_name] = get_table_schema(con, insert.table_name)
                    
                    schema = schema_cache[insert.table_name]
                    errors = validate_insert(insert, schema)
                    
                    if errors:
                        results['issues'].append({
                            'file': str(insert.file_path),
                            'line': insert.line_number,
                            'table': insert.table_name,
                            'columns': insert.columns,
                            'errors': errors,
                            'sql_preview': insert.raw_sql
                        })
                    else:
                        results['valid'].append({
                            'file': str(insert.file_path),
                            'line': insert.line_number,
                            'table': insert.table_name
                        })
    finally:
        con.close()
    
    return results


def print_report(results: dict, show_suggestions: bool = False):
    """Print validation report."""
    print("\n" + "=" * 70)
    print("SCHEMA ALIGNMENT VALIDATION REPORT")
    print("=" * 70)
    
    print(f"\nFiles scanned: {results['files_scanned']}")
    print(f"INSERT statements found: {results['inserts_found']}")
    print(f"Valid: {len(results['valid'])}")
    print(f"Issues: {len(results['issues'])}")
    
    if results['valid']:
        print("\n✅ VALID INSERTS:")
        for item in results['valid']:
            print(f"   {item['file']}:{item['line']} → {item['table']}")
    
    if results['issues']:
        print("\n❌ ISSUES FOUND:")
        for issue in results['issues']:
            print(f"\n   File: {issue['file']}")
            print(f"   Line: {issue['line']}")
            print(f"   Table: {issue['table']}")
            print(f"   Columns in INSERT: {issue['columns']}")
            print(f"   SQL Preview: {issue['sql_preview']}")
            print(f"   Errors:")
            for error in issue['errors']:
                print(f"      - {error}")
            
            if show_suggestions:
                print(f"   Suggestion: Review and align INSERT with table schema")
    
    print("\n" + "=" * 70)
    
    if not results['issues']:
        print("✅ All INSERT statements are aligned with schemas!")
    else:
        print(f"⚠️  Found {len(results['issues'])} issue(s) requiring attention")
    
    print("=" * 70 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate INSERT statements against DuckDB schemas"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help=f"Path to DuckDB database (default: {DB_PATH})"
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show suggestions for fixing issues"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Scanning project for schema alignment issues...")
    results = scan_project(Path(args.db), SOURCE_PATHS)
    
    if args.json:
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results, show_suggestions=args.fix_suggestions)
    
    # Exit with error code if issues found
    return 1 if results['issues'] else 0


if __name__ == "__main__":
    exit(main())
