from __future__ import annotations

import duckdb
from pathlib import Path
from loguru import logger

from src.utils.config import load_config


def _as_posix(p: Path) -> str:
    return p.resolve().as_posix()


def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    return con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table],
    ).fetchone()[0] > 0


def _get_table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    # column_name in ordinal_position order
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    return [r[0] for r in rows]


def _get_parquet_columns(con: duckdb.DuckDBPyConnection, parquet_posix: str) -> list[str]:
    # DuckDB can introspect parquet schema
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{parquet_posix}')"
    ).fetchall()
    # DESCRIBE returns: (column_name, column_type, null, key, default, extra)
    return [r[0] for r in rows]


def load_newsapi_ai_into_duckdb(parquet_path: Path, table_name: str = "stg_news_newsapi_ai") -> None:
    """
    Carga un parquet INTERIM (normalizado) en DuckDB como tabla staging.

    Comportamiento:
      - Si la tabla no existe: la crea con el schema del parquet + columnas técnicas (ingest_run_id, ingest_file).
      - Si existe y el schema NO coincide: DROP + CREATE (staging), luego carga.
      - Idempotencia por ingest_run_id: borra ese run_id antes de insertar.

    Esto evita errores cuando evoluciona el schema del normalizador.
    """
    cfg = load_config()
    db_path = Path(cfg["db"]["duckdb_path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"No existe el parquet: {parquet_path}")

    ingest_run_id = parquet_path.stem  # p.ej. 20251213081340
    parquet_posix = _as_posix(parquet_path)
    db_posix = _as_posix(db_path)

    logger.info(f"Conectando DuckDB: {db_posix}")
    con = duckdb.connect(db_posix)

    parquet_cols = _get_parquet_columns(con, parquet_posix)

    # staging columns (siempre añadimos al final)
    tech_cols = ["ingest_run_id", "ingest_file"]

    if _table_exists(con, table_name):
        table_cols = _get_table_columns(con, table_name)

        # Comparamos columnas sin tech cols (porque pueden existir ya)
        # y también el orden: staging debe reflejar parquet
        table_data_cols = [c for c in table_cols if c not in tech_cols]

        if table_data_cols != parquet_cols:
            logger.warning(
                f"Schema mismatch en {table_name}. "
                f"Tabla tiene {len(table_data_cols)} cols, parquet tiene {len(parquet_cols)} cols. "
                "Recreo la tabla (staging)."
            )
            con.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Crear si no existe (o si la recreamos)
    if not _table_exists(con, table_name):
        con.execute(
            f"""
            CREATE TABLE {table_name} AS
            SELECT
                *,
                '{ingest_run_id}'::VARCHAR AS ingest_run_id,
                '{parquet_posix}'::VARCHAR AS ingest_file
            FROM read_parquet('{parquet_posix}')
            WHERE 1=0
            """
        )

    # Idempotencia por run_id
    con.execute(f"DELETE FROM {table_name} WHERE ingest_run_id = '{ingest_run_id}'")

    # Insert explícito por columnas para evitar “N values supplied”
    # (parquet cols + tech cols)
    insert_cols = parquet_cols + tech_cols
    insert_cols_sql = ", ".join(insert_cols)

    con.execute(
        f"""
        INSERT INTO {table_name} ({insert_cols_sql})
        SELECT
            *,
            '{ingest_run_id}'::VARCHAR AS ingest_run_id,
            '{parquet_posix}'::VARCHAR AS ingest_file
        FROM read_parquet('{parquet_posix}')
        """
    )

    rowcount = con.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE ingest_run_id = '{ingest_run_id}'"
    ).fetchone()[0]

    con.close()
    logger.success(f"[DW] Carga OK -> {table_name} (ingest_run_id={ingest_run_id}, rows={rowcount})")
