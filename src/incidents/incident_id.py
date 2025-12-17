from __future__ import annotations

import hashlib
from typing import Optional


def make_incident_id(original_uri: Optional[str], url: Optional[str], published_at: Optional[str]) -> str:
    """
    ID estable (hash): prioriza original_uri (canónica).
    Si no existe, usa url|published_at.
    """
    base = (original_uri or "").strip()
    if not base:
        base = f"{(url or '').strip()}|{(published_at or '').strip()}"
    if not base:
        base = "unknown"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()
