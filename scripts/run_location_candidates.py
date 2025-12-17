# scripts/run_location_candidates.py
from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def normalize(s: str) -> str:
    s = s or ""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokenize(s: str) -> List[str]:
    s = normalize(s)
    return s.split(" ") if s else []


def ngrams(tokens: List[str], n: int) -> Iterable[str]:
    for i in range(0, len(tokens) - n + 1):
        yield " ".join(tokens[i : i + n])


def table_cols(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    return {r[1] for r in con.execute(f"PRAGMA table_info('{table}')").fetchall()}


@dataclass(frozen=True)
class PlaceRow:
    place_id: str
    name_norm: str
    adm_level: int
    adm1: str | None
    adm2: str | None
    adm3: str | None
    lat: float | None
    lon: float | None


def score_candidate(matched_ngram: str, adm_level: int, in_location_text: bool) -> float:
    """
    Scoring interpretable:
      - match length (más tokens = mejor)
      - granularidad (adm3 > adm2 > adm1)
      - boost si aparece en location_text (más fiable que body/title)
    """
    n_tokens = len(matched_ngram.split())
    base = {1: 0.20, 2: 0.35, 3: 0.50}.get(adm_level, 0.20)
    length_bonus = {1: 0.10, 2: 0.20, 3: 0.30}.get(n_tokens, 0.10)
    loc_boost = 0.15 if in_location_text else 0.0
    return round(min(1.0, base + length_bonus + loc_boost), 4)


def build_place_index(con: duckdb.DuckDBPyConnection) -> Dict[str, List[PlaceRow]]:
    """
    dim_places_pe real (según tu error):
      place_id, display_name, search_name, adm1_name, adm2_name (y opcional adm3_name), lat, lon

    Fix clave: indexar:
      - nombre completo (search/display)
      - alias corto (antes de coma)
      - alias por separadores comunes (" - ", " / ", " | ")
    """
    cols = table_cols(con, "dim_places_pe")
    has_adm3 = "adm3_name" in cols
    has_lat = "lat" in cols
    has_lon = "lon" in cols

    adm3_expr = "adm3_name AS adm3" if has_adm3 else "NULL AS adm3"
    lat_expr = "lat" if has_lat else "NULL::DOUBLE AS lat"
    lon_expr = "lon" if has_lon else "NULL::DOUBLE AS lon"

    sql = f"""
      SELECT
        place_id,
        COALESCE(search_name, display_name) AS place_name,
        adm1_name AS adm1,
        adm2_name AS adm2,
        {adm3_expr},
        {lat_expr} AS lat,
        {lon_expr} AS lon
      FROM dim_places_pe
      WHERE COALESCE(search_name, display_name) IS NOT NULL
    """
    rows = con.execute(sql).fetchall()

    index: Dict[str, List[PlaceRow]] = {}

    def add_key(key: str, pr: PlaceRow):
        k = normalize(key)
        if not k:
            return
        index.setdefault(k, []).append(pr)

    for place_id, place_name, adm1, adm2, adm3, lat, lon in rows:
        full = (place_name or "").strip()
        if not full:
            continue

        if adm3:
            level = 3
        elif adm2:
            level = 2
        else:
            level = 1

        pr = PlaceRow(
            place_id=str(place_id),
            name_norm=normalize(full),
            adm_level=level,
            adm1=adm1,
            adm2=adm2,
            adm3=adm3,
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
        )

        # nombre completo
        add_key(full, pr)

        # alias corto (muy común: "Huancayo, Junín, Perú")
        short = full.split(",")[0].strip()
        if short and short.lower() != full.lower():
            add_key(short, pr)

        # alias adicional por separadores
        for sep in [" - ", " / ", " | "]:
            if sep in full:
                add_key(full.split(sep)[0].strip(), pr)

    logger.info(f"Place index built: {len(index)} unique normalized names (with short aliases)")
    return index


DDL = r"""
CREATE TABLE IF NOT EXISTS stg_incident_place_candidates (
  ingest_run_id   VARCHAR,
  incident_id     VARCHAR,

  matched_text_norm VARCHAR,
  matched_tokens    INTEGER,

  candidate_place_id VARCHAR,
  candidate_adm1     VARCHAR,
  candidate_adm2     VARCHAR,
  candidate_adm3     VARCHAR,
  candidate_lat      DOUBLE,
  candidate_lon      DOUBLE,

  method           VARCHAR,
  score            DOUBLE,

  created_at       TIMESTAMP DEFAULT now()
);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--use-body", action="store_true", help="Buscar n-grams también en body (más recall, más ruido)")
    args = parser.parse_args()

    con = duckdb.connect(args.db)
    try:
        con.execute(DDL)
        con.execute("DELETE FROM stg_incident_place_candidates WHERE ingest_run_id = ?", [args.run_id])

        place_index = build_place_index(con)

        inc_rows = con.execute(
            """
            SELECT incident_id, title, body, location_text
            FROM stg_incidents_extracted
            WHERE ingest_run_id = ?
            """,
            [args.run_id],
        ).fetchall()

        total = len(inc_rows)
        empty_loc = sum(1 for _, _, _, lt in inc_rows if not (lt or "").strip())
        logger.info(f"Incidents in run: {total}; location_text empty: {empty_loc} ({(empty_loc/total*100.0 if total else 0):.1f}%)")
        if total and empty_loc == total:
            logger.warning("All incidents have empty location_text. Candidates depend on title/body toponyms.")

        total_ins = 0
        incidents_with_any_match = 0

        for incident_id, title, body, location_text in inc_rows:
            incident_id = str(incident_id)

            tokens_title = tokenize(title or "")
            tokens_loc = tokenize(location_text or "")
            tokens_body = tokenize(body or "") if args.use_body else []

            candidates: List[Tuple[float, str, PlaceRow, str]] = []

            for n in (3, 2, 1):
                # location_text
                for ng in ngrams(tokens_loc, n):
                    if ng in place_index:
                        for pr in place_index[ng]:
                            candidates.append((score_candidate(ng, pr.adm_level, True), ng, pr, f"ngram_{n}_loc"))
                # title
                for ng in ngrams(tokens_title, n):
                    if ng in place_index:
                        for pr in place_index[ng]:
                            candidates.append((score_candidate(ng, pr.adm_level, False), ng, pr, f"ngram_{n}_title"))
                # body (opcional)
                if args.use_body:
                    for ng in ngrams(tokens_body, n):
                        if ng in place_index:
                            for pr in place_index[ng]:
                                candidates.append((score_candidate(ng, pr.adm_level, False), ng, pr, f"ngram_{n}_body"))

            candidates.sort(key=lambda x: x[0], reverse=True)

            # dedupe por place_id manteniendo mejor score
            best_by_place: Dict[str, Tuple[float, str, PlaceRow, str]] = {}
            for sc, ng, pr, method in candidates:
                if pr.place_id not in best_by_place or sc > best_by_place[pr.place_id][0]:
                    best_by_place[pr.place_id] = (sc, ng, pr, method)

            final = sorted(best_by_place.values(), key=lambda x: x[0], reverse=True)[: args.top_k]
            if final:
                incidents_with_any_match += 1

            for sc, ng, pr, method in final:
                con.execute(
                    """
                    INSERT INTO stg_incident_place_candidates (
                      ingest_run_id, incident_id,
                      matched_text_norm, matched_tokens,
                      candidate_place_id, candidate_adm1, candidate_adm2, candidate_adm3,
                      candidate_lat, candidate_lon,
                      method, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        args.run_id,
                        incident_id,
                        ng,
                        len(ng.split()),
                        pr.place_id,
                        pr.adm1,
                        pr.adm2,
                        pr.adm3,
                        pr.lat,
                        pr.lon,
                        method,
                        sc,
                    ],
                )
                total_ins += 1

        logger.success(f"Candidate extraction v2 OK. Inserted rows: {total_ins}. Incidents with >=1 match: {incidents_with_any_match}/{total}")
        if total_ins == 0:
            logger.warning("0 candidates inserted. Next: try --use-body or improve location_text extraction/aliases.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
