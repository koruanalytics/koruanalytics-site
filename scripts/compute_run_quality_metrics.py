from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd
from loguru import logger


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return repo_root() / "data" / "osint_dw.duckdb"


def outputs_dir() -> Path:
    p = repo_root() / "outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


DDL_METRICS = """
CREATE TABLE IF NOT EXISTS dq_run_metrics (
  ingest_run_id   VARCHAR,
  metric_name     VARCHAR,
  metric_value    DOUBLE,
  metric_text     VARCHAR,
  created_at      TIMESTAMP DEFAULT now(),
  PRIMARY KEY (ingest_run_id, metric_name)
);
"""


UPSERT_METRIC = """
INSERT INTO dq_run_metrics (ingest_run_id, metric_name, metric_value, metric_text, created_at)
VALUES (?, ?, ?, ?, now())
ON CONFLICT (ingest_run_id, metric_name) DO UPDATE SET
  metric_value = excluded.metric_value,
  metric_text  = excluded.metric_text,
  created_at   = now()
;
"""


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db", default=str(default_db_path()))
    parser.add_argument("--amb-gap", type=float, default=0.05, help="Umbral de ambigüedad: gap <= amb-gap (cuando hay s2)")
    parser.add_argument("--top-k", type=int, default=2, help="Top candidatos a exportar por incidente ambiguo")
    args = parser.parse_args()

    run_id = args.run_id
    out_md = outputs_dir() / f"run_report_{run_id}.md"
    out_csv = outputs_dir() / f"ambiguous_{run_id}.csv"

    con = duckdb.connect(args.db)
    try:
        con.execute(DDL_METRICS)

        # ---- 1) Base counts
        incidents = con.execute(
            "SELECT COUNT(*) FROM stg_incidents_extracted WHERE ingest_run_id = ?",
            [run_id],
        ).fetchone()[0]

        loc_empty = con.execute(
            """
            SELECT SUM(CASE WHEN location_text IS NULL OR TRIM(location_text) = '' THEN 1 ELSE 0 END)
            FROM stg_incidents_extracted
            WHERE ingest_run_id = ?
            """,
            [run_id],
        ).fetchone()[0] or 0

        stg_with_place = con.execute(
            """
            SELECT SUM(CASE WHEN place_id IS NOT NULL THEN 1 ELSE 0 END)
            FROM stg_incidents_extracted
            WHERE ingest_run_id = ?
            """,
            [run_id],
        ).fetchone()[0] or 0

        # ---- 2) GEO candidates / mappings
        cand_rows = con.execute(
            "SELECT COUNT(*) FROM stg_incident_place_candidates WHERE ingest_run_id = ?",
            [run_id],
        ).fetchone()[0]

        map_rows = con.execute(
            "SELECT COUNT(*) FROM map_incident_place WHERE ingest_run_id = ?",
            [run_id],
        ).fetchone()[0]

        primary_cnt = con.execute(
            """
            SELECT COUNT(*) FROM map_incident_place
            WHERE ingest_run_id = ? AND is_primary = TRUE
            """,
            [run_id],
        ).fetchone()[0]

        # incidents with any candidates
        cand_incidents = con.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT incident_id
              FROM stg_incident_place_candidates
              WHERE ingest_run_id = ?
              GROUP BY incident_id
            )
            """,
            [run_id],
        ).fetchone()[0]

        # ---- 3) Ambiguity (gap top1-top2)
        gap_df = con.execute(
            """
            WITH r AS (
              SELECT incident_id, score,
                     row_number() OVER (PARTITION BY incident_id ORDER BY score DESC) AS rn
              FROM map_incident_place
              WHERE ingest_run_id = ?
            ),
            p AS (
              SELECT incident_id,
                     max(CASE WHEN rn=1 THEN score END) AS s1,
                     max(CASE WHEN rn=2 THEN score END) AS s2
              FROM r
              GROUP BY incident_id
            )
            SELECT incident_id, s1, s2, (s1 - coalesce(s2, 0)) AS gap
            FROM p
            """,
            [run_id],
        ).df()

        if len(gap_df) == 0:
            ambiguous_cnt = 0
        else:
            ambiguous_cnt = int(((~gap_df["s2"].isna()) & (gap_df["gap"] <= args.amb_gap)).sum())

        # ---- 4) Curated consistency + overrides applied
        base_rows = con.execute(
            "SELECT COUNT(*) FROM fct_incidents WHERE ingest_run_id = ?",
            [run_id],
        ).fetchone()[0]

        curated_rows = con.execute(
            "SELECT COUNT(*) FROM fct_incidents_curated WHERE ingest_run_id = ?",
            [run_id],
        ).fetchone()[0]

        # overrides applied % (usa check_curation_run lógica indirecta: incidentes con alguna override no-null)
        o_cols = [r[1] for r in con.execute("PRAGMA table_info('curation_incident_overrides')").fetchall()]
        override_cols = [c for c in o_cols if c.startswith("override_")]
        if override_cols:
            cond = " OR ".join([f"o.{c} IS NOT NULL" for c in override_cols])
            overrides_applied = con.execute(
                f"""
                SELECT COUNT(*)
                FROM fct_incidents f
                JOIN curation_incident_overrides o ON o.incident_id = f.incident_id
                WHERE f.ingest_run_id = ?
                  AND ({cond})
                """,
                [run_id],
            ).fetchone()[0]
        else:
            overrides_applied = 0

        # ---- Save metrics (upsert)
        metrics = {
            "incidents": float(incidents),
            "location_text_empty_cnt": float(loc_empty),
            "location_text_empty_pct": round(100.0 * safe_div(loc_empty, incidents), 2),
            "stg_with_place_cnt": float(stg_with_place),
            "stg_with_place_pct": round(100.0 * safe_div(stg_with_place, incidents), 2),

            "geo_candidates_rows": float(cand_rows),
            "geo_map_rows": float(map_rows),
            "geo_primary_cnt": float(primary_cnt),
            "geo_incidents_with_candidates_cnt": float(cand_incidents),
            "geo_incidents_with_candidates_pct": round(100.0 * safe_div(cand_incidents, incidents), 2),

            "geo_ambiguous_cnt": float(ambiguous_cnt),
            "geo_ambiguous_pct": round(100.0 * safe_div(ambiguous_cnt, incidents), 2),

            "fact_base_rows": float(base_rows),
            "fact_curated_rows": float(curated_rows),

            "overrides_applied_cnt": float(overrides_applied),
            "overrides_applied_pct": round(100.0 * safe_div(overrides_applied, incidents), 2),
        }

        for k, v in metrics.items():
            con.execute(UPSERT_METRIC, [run_id, k, float(v), None])

        # ---- 5) Export ambiguous incidents (top-k candidates)
        amb_df = gap_df.copy()
        amb_df = amb_df[(~amb_df["s2"].isna()) & (amb_df["gap"] <= args.amb_gap)].copy()

        if len(amb_df) > 0:
            amb_ids = amb_df["incident_id"].tolist()

            # pull top-k candidates per incident
            placeholders = ",".join(["?"] * len(amb_ids))
            cand_df = con.execute(
                f"""
                WITH ranked AS (
                  SELECT
                    ingest_run_id,
                    incident_id,
                    place_id,
                    adm1, adm2, adm3,
                    score,
                    method,
                    matched_text_norm,
                    matched_tokens,
                    row_number() OVER (PARTITION BY incident_id ORDER BY score DESC, matched_tokens DESC, place_id ASC) AS rn
                  FROM map_incident_place
                  WHERE ingest_run_id = ?
                    AND incident_id IN ({placeholders})
                )
                SELECT * FROM ranked WHERE rn <= ?
                ORDER BY incident_id, rn
                """,
                [run_id, *amb_ids, args.top_k],
            ).df()

            # join with title for readability
            titles_df = con.execute(
                f"""
                SELECT incident_id, title, url
                FROM stg_incidents_extracted
                WHERE ingest_run_id = ?
                  AND incident_id IN ({placeholders})
                """,
                [run_id, *amb_ids],
            ).df()

            cand_df = cand_df.merge(titles_df, on="incident_id", how="left")
            cand_df.to_csv(out_csv, index=False, encoding="utf-8")
        else:
            # write empty csv with headers
            pd.DataFrame(columns=[
                "ingest_run_id","incident_id","place_id","adm1","adm2","adm3",
                "score","method","matched_text_norm","matched_tokens","rn","title","url"
            ]).to_csv(out_csv, index=False, encoding="utf-8")

        # ---- 6) Write Markdown report
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        lines.append(f"# OSINT Run Quality Report")
        lines.append(f"- run_id: **{run_id}**")
        lines.append(f"- generated_at: `{now}`")
        lines.append("")
        lines.append("## Summary")
        lines.append(f"- incidents: **{incidents}**")
        lines.append(f"- location_text empty: **{loc_empty}** ({metrics['location_text_empty_pct']}%)")
        lines.append(f"- staging with place_id (after GEO v2): **{stg_with_place}** ({metrics['stg_with_place_pct']}%)")
        lines.append("")
        lines.append("## GEO v2")
        lines.append(f"- candidates rows: **{cand_rows}**")
        lines.append(f"- map rows: **{map_rows}**")
        lines.append(f"- primary marks: **{primary_cnt}** (expected ~= incidents with candidates)")
        lines.append(f"- incidents with candidates: **{cand_incidents}** ({metrics['geo_incidents_with_candidates_pct']}%)")
        lines.append(f"- ambiguous incidents (gap <= {args.amb_gap} with 2+ candidates): **{ambiguous_cnt}** ({metrics['geo_ambiguous_pct']}%)")
        lines.append(f"- ambiguous details CSV: `{out_csv.name}`")
        lines.append("")
        lines.append("## Curation")
        lines.append(f"- overrides applied: **{overrides_applied}** ({metrics['overrides_applied_pct']}%)")
        lines.append("")
        lines.append("## Fact tables")
        lines.append(f"- fct_incidents rows: **{base_rows}**")
        lines.append(f"- fct_incidents_curated rows: **{curated_rows}**")
        lines.append("")
        out_md.write_text("\n".join(lines), encoding="utf-8")

        logger.success(f"Quality report written: {out_md}")
        logger.success(f"Ambiguous candidates CSV: {out_csv}")
        logger.success(f"Metrics upserted into dq_run_metrics: {len(metrics)} metrics")
        return 0

    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
