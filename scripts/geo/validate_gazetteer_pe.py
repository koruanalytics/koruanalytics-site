from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from loguru import logger

from src.utils.config import load_config

REQUIRED_COLS = [
    "place_id", "ubigeo_reniec",
    "adm1_code", "adm2_code", "adm3_code",
    "adm1_name", "adm2_name", "adm3_name",
    "display_name", "search_name",
    "region", "macroregion_inei", "macroregion_minsa",
    "iso_3166_2", "fips",
    "superficie", "altitud", "lat", "lon",
    "frontera"
]

def main():
    cfg = load_config()
    p = Path(cfg["geo"]["gazetteer_path"])

    if not p.exists():
        raise SystemExit(f"[GEO] ERROR: gazetteer not found: {p.as_posix()}")

    df = pd.read_csv(p)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"[GEO] ERROR: missing columns: {missing}")

    # checks básicos de calidad
    if df["place_id"].isna().any():
        raise SystemExit("[GEO] ERROR: place_id contains nulls")

    dup = df["place_id"].duplicated().sum()
    if dup > 0:
        raise SystemExit(f"[GEO] ERROR: duplicated place_id: {dup}")

    logger.success(f"[GEO] OK: {p.as_posix()} rows={len(df)} cols={len(df.columns)}")
    print(df.head(3).to_string(index=False))

if __name__ == "__main__":
    main()
