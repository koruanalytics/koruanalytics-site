from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, Optional

import pandas as pd


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class PlaceMatch:
    place_id: str
    adm1_name: Optional[str]
    adm2_name: Optional[str]
    adm3_name: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    score: float
    method: str
    display_name: Optional[str]


class GazetteerResolver:
    def __init__(self, gazetteer_df: pd.DataFrame, fuzzy_threshold: float = 0.84):
        self.df = gazetteer_df.copy()
        self.fuzzy_threshold = fuzzy_threshold

        self.name_map: Dict[str, int] = {}

        def add_name(n: str, idx: int):
            nn = norm_text(n)
            if nn and nn not in self.name_map:
                self.name_map[nn] = idx

        for idx, r in self.df.iterrows():
            add_name(r.get("display_name", ""), idx)
            add_name(r.get("search_name", ""), idx)
            add_name(r.get("adm3_name", ""), idx)
            add_name(r.get("adm2_name", ""), idx)
            add_name(r.get("adm1_name", ""), idx)

    def resolve(self, text: Optional[str]) -> Optional[PlaceMatch]:
        if not text:
            return None
        t = norm_text(text)

        # exact
        if t in self.name_map:
            r = self.df.loc[self.name_map[t]]
            return self._match_from_row(r, score=1.0, method="exact")

        # contains
        for nn, idx in self.name_map.items():
            if nn and nn in t:
                r = self.df.loc[idx]
                return self._match_from_row(r, score=0.95, method="contains")

        # fuzzy
        best_score = 0.0
        best_idx = None
        for nn, idx in self.name_map.items():
            s = SequenceMatcher(None, t, nn).ratio()
            if s > best_score:
                best_score = s
                best_idx = idx

        if best_idx is not None and best_score >= self.fuzzy_threshold:
            r = self.df.loc[best_idx]
            return self._match_from_row(r, score=float(best_score), method="fuzzy")

        return None

    def _match_from_row(self, r: pd.Series, score: float, method: str) -> PlaceMatch:
        def to_float(x):
            try:
                return float(x) if x is not None and x != "" else None
            except Exception:
                return None

        return PlaceMatch(
            place_id=str(r.get("place_id")),
            adm1_name=r.get("adm1_name"),
            adm2_name=r.get("adm2_name"),
            adm3_name=r.get("adm3_name"),
            lat=to_float(r.get("lat")),
            lon=to_float(r.get("lon")),
            score=score,
            method=method,
            display_name=r.get("display_name"),
        )
