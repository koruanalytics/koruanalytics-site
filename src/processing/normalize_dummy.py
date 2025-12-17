from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime
from typing import Any, Dict, List

from src.utils.config import load_config


def load_raw_dummy_file(path: Path) -> List[Dict[str, Any]]:
    """Carga un fichero JSON de la carpeta raw/dummy y devuelve la lista de artículos."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero raw: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Se esperaba una lista de artículos en {path}, pero se encontró: {type(data)}")

    return data


def normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza un artículo 'raw' a un formato estándar.
    """
    return {
        "incident_id": f"{article.get('source', 'unknown')}__{article.get('external_id', '')}",
        "source": article.get("source"),
        "external_id": article.get("external_id"),
        "title": article.get("title"),
        "published_at": article.get("published_at"),
        "url": article.get("url"),
        "content": article.get("content"),
        "language": article.get("language", "unknown"),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def save_interim_dummy(articles: List[Dict[str, Any]], raw_file: Path) -> Path:
    """Guarda los artículos normalizados en data/interim/dummy/ con el mismo nombre que el raw."""
    cfg = load_config()
    interim_root = Path(cfg["data_paths"]["interim"])
    out_dir = interim_root / "dummy"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / raw_file.name
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    return out_file


def normalize_dummy_file(raw_file: Path) -> Path:
    """
    Punto de entrada: dado un fichero RAW de dummy,
    genera su versión normalizada en data/interim/dummy/.
    """
    raw_articles = load_raw_dummy_file(raw_file)
    normalized = [normalize_article(a) for a in raw_articles]
    out_file = save_interim_dummy(normalized, raw_file)
    return out_file
