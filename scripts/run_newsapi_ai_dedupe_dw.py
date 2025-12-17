from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.dedupe_newsapi_ai_in_duckdb import dedupe_newsapi_ai_in_duckdb


def main():
    parser = argparse.ArgumentParser(description="Dedupe NewsAPI.ai staging in DuckDB")
    parser.add_argument("--src", default="stg_news_newsapi_ai")
    parser.add_argument("--dst", default="stg_news_newsapi_ai_dedup")
    args = parser.parse_args()

    dedupe_newsapi_ai_in_duckdb(src_table=args.src, dst_table=args.dst)


if __name__ == "__main__":
    main()
