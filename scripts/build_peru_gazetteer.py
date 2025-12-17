from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import requests
from loguru import logger

from src.utils.config import load_config

# URL "landing" (puede redirigir a otros dominios)
DEFAULT_URL = "https://www.datosabiertos.gob.pe/node/8295/download"

OUT_COLS = [
    "place_id",
    "ubigeo_reniec",
    "adm1_code",
    "adm2_code",
    "adm3_code",
    "adm1_name",
    "adm2_name",
    "adm3_name",
    "display_name",
    "search_name",
    "region",
    "macroregion_inei",
    "macroregion_minsa",
    "iso_3166_2",
    "fips",
    "superficie",
    "altitud",
    "lat",
    "lon",
    "frontera",
]

def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = " ".join(s.split())
    return s

def pick(df: pd.DataFrame, *names: str) -> str:
    for n in names:
        if n in df.columns:
            return n
    raise KeyError(f"Missing column. Tried: {names}. Found: {list(df.columns)}")

def download_csv(url: str, out_path: Path) -> None:
    """
    Descarga robusta:
    - añade User-Agent
    - sigue redirects
    - si el destino hace 403, levanta error y te explica modo offline
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/csv,application/octet-stream,application/vnd.ms-excel,*/*",
    }

    logger.info(f"[GEO] Downloading: {url}")
    with requests.Session() as s:
        r = s.get(url, headers=headers, timeout=60, allow_redirects=True)
        # logging extra útil
        logger.info(f"[GEO] HTTP status={r.status_code} final_url={r.url}")

        if r.status_code == 403:
            raise RuntimeError(
                "403 Forbidden al descargar el gazetteer.\n"
                f"URL final: {r.url}\n\n"
                "Solución: descarga manualmente el CSV en el navegador y guárdalo en:\n"
                "  data/raw/geo/peru_ubigeo_official_raw.csv\n"
                "Luego vuelve a ejecutar este script (ya no descargará)."
            )

        r.raise_for_status()
        out_path.write_bytes(r.content)

    logger.success(f"[GEO] Downloaded to: {out_path.as_posix()} ({out_path.stat().st_size} bytes)")

def main():
    cfg = load_config()

    raw_dir = Path(cfg["data_paths"]["raw"]) / "geo"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "peru_ubigeo_official_raw.csv"

    out_path = Path(cfg["geo"]["gazetteer_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Descargar si no existe (si existe, modo offline automático)
    if not raw_path.exists():
        download_csv(DEFAULT_URL, raw_path)
    else:
        logger.info(f"[GEO] Using existing raw file: {raw_path.as_posix()}")

    # 2) Leer CSV oficial
    #    Si viene con ';' lo leemos así. Si no, fallback a ','
    try:
        df = pd.read_csv(raw_path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        if df.shape[1] <= 1:
            raise ValueError("Parsed as 1 column with ';' delimiter")
    except Exception:
        df = pd.read_csv(raw_path, sep=",", encoding="utf-8-sig", dtype=str, keep_default_na=False)

    df.rename(columns={c: c.strip() for c in df.columns}, inplace=True)

    # 3) Mapear columnas
    c_inei = pick(df, "ubigeo_inei", "UBIGEO_INEI", "Ubigeo_inei")
    c_ren  = pick(df, "ubigeo_reniec", "UBIGEO_RENIEC", "Ubigeo_reniec")
    c_dep  = pick(df, "departamento", "DEPARTAMENTO", "Departamento")
    c_prov = pick(df, "provincia", "PROVINCIA", "Provincia")
    c_dist = pick(df, "distrito", "DISTRITO", "Distrito")
    c_reg  = pick(df, "region", "REGION", "Region")
    c_mi   = pick(df, "macroregion_inei", "MACROREGION_INEI", "Macroregion_inei")
    c_mm   = pick(df, "macroregion_minsa", "MACROREGION_MINSA", "Macroregion_minsa")
    c_iso  = pick(df, "iso_3166_2", "ISO_3166_2")
    c_fips = pick(df, "fips", "FIPS")
    c_sup  = pick(df, "superficie", "SUPERFICIE", "Superficie")
    c_alt  = pick(df, "altitud", "ALTITUD", "Altitud")
    c_lat  = pick(df, "latitud", "LATITUD", "Latitud")
    c_lon  = pick(df, "longitud", "LONGITUD", "Longitud")
    c_fron = pick(df, "frontera", "FRONTERA", "Frontera")

    # 4) Construir output
    place_id = df[c_inei].str.zfill(6)
    out = pd.DataFrame({
        "place_id": place_id,
        "ubigeo_reniec": df[c_ren].str.zfill(6),
        "adm1_code": place_id.str.slice(0, 2),
        "adm2_code": place_id.str.slice(0, 4),
        "adm3_code": place_id,

        "adm1_name": df[c_dep].str.strip(),
        "adm2_name": df[c_prov].str.strip(),
        "adm3_name": df[c_dist].str.strip(),

        "region": df[c_reg].str.strip(),
        "macroregion_inei": df[c_mi].str.strip(),
        "macroregion_minsa": df[c_mm].str.strip(),
        "iso_3166_2": df[c_iso].str.strip(),
        "fips": df[c_fips].str.strip(),
        "superficie": df[c_sup].str.strip(),
        "altitud": df[c_alt].str.strip(),

        # decimales con coma -> punto
        "lat": df[c_lat].str.replace(",", ".", regex=False).str.strip(),
        "lon": df[c_lon].str.replace(",", ".", regex=False).str.strip(),

        "frontera": df[c_fron].str.strip(),
    })

    out["display_name"] = out["adm3_name"] + ", " + out["adm2_name"] + ", " + out["adm1_name"]
    out["search_name"] = out["display_name"].map(norm_text)

    for c in ["superficie", "altitud", "lat", "lon"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out[OUT_COLS]

    # 5) Guardar CSV limpio + Parquet opcional
    out.to_csv(out_path, index=False, encoding="utf-8")
    logger.success(f"[GEO] Wrote gazetteer CSV: {out_path.as_posix()} rows={len(out)} cols={len(out.columns)}")

    parquet_path = out_path.with_suffix(".parquet")
    try:
        out.to_parquet(parquet_path, index=False)
        logger.success(f"[GEO] Wrote gazetteer Parquet: {parquet_path.as_posix()}")
    except Exception as e:
        logger.warning(f"[GEO] Parquet not written (optional): {e}")

    print(out.head(3).to_string(index=False))

if __name__ == "__main__":
    main()
