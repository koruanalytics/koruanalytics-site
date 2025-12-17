from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.normalize_newsapi_ai import NormalizeParams, run_newsapi_ai_normalization


def main():
    parser = argparse.ArgumentParser(description="Runner normalización NewsAPI.ai RAW -> INTERIM parquet")
    parser.add_argument("--raw", required=True, help="RAW JSON (data/raw/newsapi_ai/xxxx.json)")
    parser.add_argument("--out-dir", default="data/interim/newsapi_ai", help="Dir salida INTERIM")
    args = parser.parse_args()

    run_newsapi_ai_normalization(
        NormalizeParams(raw_path=Path(args.raw), out_dir=Path(args.out_dir))
    )


if __name__ == "__main__":
    main()
