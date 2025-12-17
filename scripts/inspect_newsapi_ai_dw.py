from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import yaml


def main():
    parser = argparse.ArgumentParser(description="Inspect NewsAPI.ai tables in DuckDB")
    parser.add_argument("--stg", default="stg_news_newsapi_ai")
    parser.add_argument("--dedup", default="stg_news_newsapi_ai_dedup")
    parser.add_argument("--run-id", default=None, help="Filter by ingest_run_id (optional)")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    cfg = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
    db = Path(cfg["db"]["duckdb_path"]).resolve().as_posix()
    con = duckdb.connect(db)

    print(f"DB: {db}\n")

    stg_count = con.execute(f"SELECT COUNT(*) FROM {args.stg}").fetchone()[0]
    dedup_count = con.execute(f"SELECT COUNT(*) FROM {args.dedup}").fetchone()[0]
    print(f"STG   {args.stg}:   {stg_count}")
    print(f"DEDUP {args.dedup}: {dedup_count}\n")

    print("=== STG SCHEMA ===")
    print(con.execute(f"DESCRIBE {args.stg}").fetchdf().to_string(index=False))
    print()

    where = ""
    if args.run_id:
        where = f"WHERE ingest_run_id = '{args.run_id}'"

    print("=== LATEST STG ===")
    q1 = f"""
    SELECT
        ingest_run_id,
        published_at,
        language,
        is_duplicate,
        COALESCE(original_uri, source_article_id) AS canonical_uri,
        substr(title, 1, 140) AS title
    FROM {args.stg}
    {where}
    ORDER BY ingest_run_id DESC, published_at DESC
    LIMIT {args.limit}
    """
    print(con.execute(q1).fetchdf().to_string(index=False))
    print()

    print("=== LATEST DEDUP ===")
    q2 = f"""
    SELECT
        published_at,
        language,
        COALESCE(original_uri, source_article_id) AS canonical_uri,
        substr(title, 1, 140) AS title
    FROM {args.dedup}
    ORDER BY published_at DESC
    LIMIT {args.limit}
    """
    print(con.execute(q2).fetchdf().to_string(index=False))
    print()

    print("=== DUPLICATES IN STG (by canonical_uri) ===")
    q3 = f"""
    WITH x AS (
      SELECT
        COALESCE(original_uri, source_article_id) AS canonical_uri,
        COUNT(*) AS n
      FROM {args.stg}
      {where}
      GROUP BY 1
    )
    SELECT * FROM x
    WHERE n > 1
    ORDER BY n DESC
    LIMIT 30
    """
    print(con.execute(q3).fetchdf().to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
