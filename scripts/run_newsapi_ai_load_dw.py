from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.load_newsapi_ai_to_dw import load_newsapi_ai_into_duckdb


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner: INTERIM parquet -> DuckDB staging table")
    parser.add_argument("--parquet", required=True, help="Parquet INTERIM (data/interim/newsapi_ai/xxxx.parquet)")
    parser.add_argument("--table", default="stg_news_newsapi_ai", help="Tabla staging destino en DuckDB")
    args = parser.parse_args()

    load_newsapi_ai_into_duckdb(Path(args.parquet), table_name=args.table)


if __name__ == "__main__":
    main()
