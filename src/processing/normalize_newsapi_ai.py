from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from loguru import logger


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def normalize_one_article(a: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    uri = a.get("uri")
    url = a.get("url")
    title = a.get("title")
    body = a.get("body")

    published_at = a.get("dateTimePub") or a.get("dateTime") or a.get("date")
    lang = a.get("lang")

    # fuente
    source_title = safe_get(a, ["source", "title"])
    source_uri = safe_get(a, ["source", "uri"])

    # dedupe helpers desde RAW
    is_duplicate = a.get("isDuplicate")
    original_uri = safe_get(a, ["originalArticle", "uri"])

    # conceptos
    concepts = a.get("concepts") or []
    concept_uris, concept_labels = [], []
    if isinstance(concepts, list):
        for c in concepts:
            if isinstance(c, dict):
                if c.get("uri"):
                    concept_uris.append(c.get("uri"))
                lbl = c.get("label")
                if isinstance(lbl, dict):
                    concept_labels.append(lbl.get("spa") or lbl.get("eng"))
                elif isinstance(lbl, str):
                    concept_labels.append(lbl)

    # categorías
    categories = a.get("categories") or []
    category_uris, category_labels = [], []
    if isinstance(categories, list):
        for c in categories:
            if isinstance(c, dict):
                if c.get("uri"):
                    category_uris.append(c.get("uri"))
                lbl = c.get("label")
                if isinstance(lbl, dict):
                    category_labels.append(lbl.get("spa") or lbl.get("eng"))
                elif isinstance(lbl, str):
                    category_labels.append(lbl)

    # location
    location = a.get("location") if isinstance(a.get("location"), dict) else {}
    location_uri = location.get("uri")
    location_label = None
    lbl = location.get("label")
    if isinstance(lbl, dict):
        location_label = lbl.get("spa") or lbl.get("eng")
    elif isinstance(lbl, str):
        location_label = lbl

    lat = location.get("lat") or location.get("latitude")
    lon = location.get("lon") or location.get("longitude")

    record = {
        "incident_id": uri,  # provisional (luego puedes generar id propio)
        "source": "newsapi_ai",
        "source_article_id": uri,
        "original_uri": original_uri,
        "is_duplicate": is_duplicate,
        "url": url,
        "title": title,
        "body": body,
        "published_at": published_at,
        "language": lang,
        "source_title": source_title,
        "source_uri": source_uri,
        "country_location_uri": meta.get("location_uri"),
        "retrieved_at": meta.get("generated_at_utc") or utc_now_iso_z(),
        "concept_uris": concept_uris,
        "concept_labels": concept_labels,
        "category_uris": category_uris,
        "category_labels": category_labels,
        "location_uri": location_uri,
        "location_label": location_label,
        "location_text": None,  # futuro: geoparsing desde title/body
        "lat": lat,
        "lon": lon,
        "adm1": None,
        "adm2": None,
        "adm3": None,
    }
    return record


@dataclass
class NormalizeParams:
    raw_path: Path
    out_dir: Path


def run_newsapi_ai_normalization(params: NormalizeParams) -> Path:
    payload = json.loads(params.raw_path.read_text(encoding="utf-8"))
    meta = payload.get("meta", {})
    articles = payload.get("articles", [])

    rows = [normalize_one_article(a, meta) for a in articles]
    df = pd.DataFrame(rows)

    params.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = params.out_dir / (params.raw_path.stem + ".parquet")
    df.to_parquet(out_path, index=False)

    logger.success(f"[INTERIM] Fichero generado: {out_path.as_posix()} (rows={len(df)})")
    return out_path
