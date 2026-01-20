"""
src/processing/normalize_newsapi_ai.py
Last updated: 2026-01-16
Description: Normalizes raw NewsAPI.ai articles to parquet for bronze_news.

M9 FIX: Added Unicode normalization to fix encoding issues
- Converts \\uXXXX escapes to actual characters (á, é, ñ, etc.)
- Applied to: title, body, source_title, location_label, concept_labels
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from loguru import logger

# M9: Import text normalization utilities
from src.utils.text_utils import normalize_unicode, normalize_list_unicode


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def normalize_one_article(a: Dict[str, Any], meta: Dict[str, Any], run_id: str, file_name: str) -> Dict[str, Any]:
    """
    Normalize a single article to bronze_news schema.
    
    M9: Applies Unicode normalization to all text fields to ensure
    proper encoding of Spanish characters (á, é, í, ó, ú, ñ, etc.)
    """
    uri = a.get("uri")
    url = a.get("url")
    
    # M9: Normalize title and body
    title = normalize_unicode(a.get("title"))
    body = normalize_unicode(a.get("body"))

    published_at = a.get("dateTimePub") or a.get("dateTime") or a.get("date")
    lang = a.get("lang")

    # M9: Normalize source title
    source_title = normalize_unicode(safe_get(a, ["source", "title"]))
    source_uri = safe_get(a, ["source", "uri"])

    # dedupe helpers from RAW
    is_duplicate = a.get("isDuplicate")
    original_uri = safe_get(a, ["originalArticle", "uri"])

    # concepts - M9: normalize labels
    concepts = a.get("concepts") or []
    concept_uris, concept_labels = [], []
    if isinstance(concepts, list):
        for c in concepts:
            if isinstance(c, dict):
                if c.get("uri"):
                    concept_uris.append(c.get("uri"))
                lbl = c.get("label")
                if isinstance(lbl, dict):
                    label_text = lbl.get("spa") or lbl.get("eng")
                    concept_labels.append(normalize_unicode(label_text))
                elif isinstance(lbl, str):
                    concept_labels.append(normalize_unicode(lbl))

    # categories - M9: normalize labels
    categories = a.get("categories") or []
    category_uris, category_labels = [], []
    if isinstance(categories, list):
        for c in categories:
            if isinstance(c, dict):
                if c.get("uri"):
                    category_uris.append(c.get("uri"))
                lbl = c.get("label")
                if isinstance(lbl, dict):
                    label_text = lbl.get("spa") or lbl.get("eng")
                    category_labels.append(normalize_unicode(label_text))
                elif isinstance(lbl, str):
                    category_labels.append(normalize_unicode(lbl))

    # location - M9: normalize location label
    location = a.get("location") if isinstance(a.get("location"), dict) else {}
    location_uri = location.get("uri")
    location_label = None
    lbl = location.get("label")
    if isinstance(lbl, dict):
        location_label = normalize_unicode(lbl.get("spa") or lbl.get("eng"))
    elif isinstance(lbl, str):
        location_label = normalize_unicode(lbl)

    lat = location.get("lat") or location.get("latitude")
    lon = location.get("lon") or location.get("longitude")

    record = {
        "incident_id": uri,
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
        "location_text": None,
        "lat": lat,
        "lon": lon,
        "adm1": None,
        "adm2": None,
        "adm3": None,
        # Ingest tracking columns
        "ingest_run_id": run_id,
        "ingest_file": file_name,
    }
    return record


@dataclass
class NormalizeParams:
    raw_path: Path
    out_dir: Path


def run_newsapi_ai_normalization(params: NormalizeParams) -> Path:
    """
    Normalize a raw NewsAPI.ai JSON file to parquet.
    
    M9: Now includes Unicode normalization for all text fields.
    
    Args:
        params: NormalizeParams with raw_path and out_dir
        
    Returns:
        Path to generated parquet file
    """
    payload = json.loads(params.raw_path.read_text(encoding="utf-8"))
    meta = payload.get("meta", {})
    articles = payload.get("articles", [])
    
    # Extract run_id and file_name from path
    run_id = params.raw_path.stem  # e.g., "20260105010617"
    file_name = params.raw_path.name  # e.g., "20260105010617.json"

    rows = [normalize_one_article(a, meta, run_id, file_name) for a in articles]
    df = pd.DataFrame(rows)

    params.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = params.out_dir / (params.raw_path.stem + ".parquet")
    df.to_parquet(out_path, index=False)

    logger.success(f"[INTERIM] File generated: {out_path.as_posix()} (rows={len(df)})")
    return out_path
