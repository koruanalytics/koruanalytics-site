# scripts/run_newsapi_ai_ingest.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import date

# --- Asegura imports del proyecto (src/...) ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # raíz del repo
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ---------------------------------------------

from src.ingestion.newsapi_ai_ingest import IngestParams, run_newsapi_ai_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner ingesta NewsAPI.ai -> RAW JSON.")
    parser.add_argument("--scope", required=True, help="YAML scope (ej: config/newsapi_scope_peru_2025-11.yaml)")
    parser.add_argument("--out-dir", default="data/raw/newsapi_ai", help="Directorio RAW salida")
    parser.add_argument("--date-start", default="2025-11-01", help="YYYY-MM-DD")
    parser.add_argument("--date-end", default="2025-11-30", help="YYYY-MM-DD")
    parser.add_argument("--max-items", type=int, default=20, help="Nº artículos a traer")
    parser.add_argument("--sort-by", default="date", choices=["date", "rel"], help="Orden")
    parser.add_argument("--allow-archive", action="store_true", help="Permite archive (si plan lo soporta)")
    parser.add_argument("--langs", nargs="+", default=None, help="Override langs (ej: --langs spa eng)")
    args = parser.parse_args()

    params = IngestParams(
        scope_yaml=Path(args.scope),
        out_dir=Path(args.out_dir),
        date_start=date.fromisoformat(args.date_start),
        date_end=date.fromisoformat(args.date_end),
        max_items=args.max_items,
        sort_by=args.sort_by,
        allow_archive=args.allow_archive,
        langs=args.langs,
    )

    run_newsapi_ai_ingestion(params)


if __name__ == "__main__":
    main()
