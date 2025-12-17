# scripts/import_overrides_from_csv.py
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import duckdb
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


UPSERT_SQL = r"""
INSERT INTO curation_incident_overrides (
  incident_id,
  override_incident_type,
  override_confidence,
  override_location_text,
  override_place_id,
  override_adm1,
  override_adm2,
  override_adm3,
  override_lat,
  override_lon,
  override_title,
  override_body,
  review_status,
  review_notes,
  updated_at,
  updated_by,
  created_by
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now(), ?, ?)
ON CONFLICT (incident_id) DO UPDATE SET
  override_incident_type = excluded.override_incident_type,
  override_confidence    = excluded.override_confidence,
  override_location_text = excluded.override_location_text,
  override_place_id      = excluded.override_place_id,
  override_adm1          = excluded.override_adm1,
  override_adm2          = excluded.override_adm2,
  override_adm3          = excluded.override_adm3,
  override_lat           = excluded.override_lat,
  override_lon           = excluded.override_lon,
  override_title         = excluded.override_title,
  override_body          = excluded.override_body,
  review_status          = excluded.review_status,
  review_notes           = excluded.review_notes,
  updated_at             = now(),
  updated_by             = excluded.updated_by
;
"""


def _norm_empty(x):
    if pd.isna(x):
        return None
    if isinstance(x, str) and x.strip() == "":
        return None
    return x


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="CSV editado con columnas override_*")
    parser.add_argument("--user", default="manual")
    parser.add_argument("--db", default=str(db_path()))
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    if "incident_id" not in df.columns:
        raise ValueError("CSV must contain incident_id")

    # columnas esperadas (si faltan, las creamos como None)
    cols = [
        "incident_id",
        "override_incident_type",
        "override_confidence",
        "override_location_text",
        "override_place_id",
        "override_adm1",
        "override_adm2",
        "override_adm3",
        "override_lat",
        "override_lon",
        "override_title",
        "override_body",
        "override_review_status",   # del export
        "override_review_notes"     # del export
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    # mapeo: export usa override_review_status/notes, tabla usa review_status/notes
    df["review_status"] = df["override_review_status"].replace("", "PENDING")
    df["review_notes"]  = df["override_review_notes"]

    # casting numérico seguro
    def to_float(v):
        v = _norm_empty(v)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    rows = []
    for _, r in df.iterrows():
        rows.append([
            _norm_empty(r["incident_id"]),
            _norm_empty(r["override_incident_type"]),
            to_float(r["override_confidence"]),
            _norm_empty(r["override_location_text"]),
            _norm_empty(r["override_place_id"]),
            _norm_empty(r["override_adm1"]),
            _norm_empty(r["override_adm2"]),
            _norm_empty(r["override_adm3"]),
            to_float(r["override_lat"]),
            to_float(r["override_lon"]),
            _norm_empty(r["override_title"]),
            _norm_empty(r["override_body"]),
            _norm_empty(r["review_status"]) or "PENDING",
            _norm_empty(r["review_notes"]),
            args.user,  # updated_by
            args.user,  # created_by (solo aplica en insert)
        ])

    con = duckdb.connect(args.db)
    try:
        n = 0
        for row in rows:
            if not row[0]:
                continue
            con.execute(UPSERT_SQL, row)
            n += 1
        logger.success(f"Upserted {n} overrides from CSV: {csv_path}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
