import duckdb

con = duckdb.connect("data/osint_dw.duckdb")

# intenta primero en la tabla dedup_run (la que usamos como fuente en F2.2)
try:
    row = con.execute("""
        select ingest_run_id
        from stg_news_newsapi_ai_dedup_run
        order by ingest_run_id desc
        limit 1
    """).fetchone()
except Exception:
    row = None

# fallback: staging raw normalizada si dedup_run está vacía o no existe
if not row:
    row = con.execute("""
        select ingest_run_id
        from stg_news_newsapi_ai
        order by ingest_run_id desc
        limit 1
    """).fetchone()

con.close()
print(row[0] if row else "")
