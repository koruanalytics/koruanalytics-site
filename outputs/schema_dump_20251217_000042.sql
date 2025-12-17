-- ============================================================
-- DuckDB Schema Dump
-- Generated: 20251217_000042
-- Database: C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru\data\osint_dw.duckdb
-- Tables: 18, Views: 1
-- ============================================================

-- Table: curation_incident_overrides (0 rows, 18 columns)
CREATE TABLE curation_incident_overrides (
    "created_by" VARCHAR,
    "override_adm2" VARCHAR,
    "override_location_text" VARCHAR,
    "override_lon" DOUBLE,
    "review_status" VARCHAR,
    "override_body" VARCHAR,
    "override_adm3" VARCHAR,
    "override_adm1" VARCHAR,
    "updated_by" VARCHAR,
    "incident_id" VARCHAR,
    "override_incident_type" VARCHAR,
    "override_place_id" VARCHAR,
    "override_lat" DOUBLE,
    "updated_at" TIMESTAMP,
    "review_notes" VARCHAR,
    "override_confidence" DOUBLE,
    "created_at" TIMESTAMP,
    "override_title" VARCHAR
);

-- Table: curation_incident_overrides_backup (0 rows, 28 columns)
CREATE TABLE curation_incident_overrides_backup (
    "incident_id" VARCHAR,
    "incident_type_override" VARCHAR,
    "actors_json_override" VARCHAR,
    "victims_json_override" VARCHAR,
    "location_text_override" VARCHAR,
    "place_id_override" VARCHAR,
    "lat_override" DOUBLE,
    "lon_override" DOUBLE,
    "adm1_override" VARCHAR,
    "adm2_override" VARCHAR,
    "adm3_override" VARCHAR,
    "review_notes" VARCHAR,
    "updated_at" TIMESTAMP,
    "updated_by" VARCHAR,
    "review_status" VARCHAR,
    "created_at" TIMESTAMP,
    "created_by" VARCHAR,
    "override_incident_type" VARCHAR,
    "override_confidence" DOUBLE,
    "override_location_text" VARCHAR,
    "override_place_id" VARCHAR,
    "override_adm1" VARCHAR,
    "override_adm2" VARCHAR,
    "override_adm3" VARCHAR,
    "override_lat" DOUBLE,
    "override_lon" DOUBLE,
    "override_title" VARCHAR,
    "override_body" VARCHAR
);

-- Table: dim_places_pe (1893 rows, 20 columns)
CREATE TABLE dim_places_pe (
    "place_id" VARCHAR,
    "ubigeo_reniec" VARCHAR,
    "adm1_code" VARCHAR,
    "adm2_code" VARCHAR,
    "adm3_code" VARCHAR,
    "adm1_name" VARCHAR,
    "adm2_name" VARCHAR,
    "adm3_name" VARCHAR,
    "display_name" VARCHAR,
    "search_name" VARCHAR,
    "region" VARCHAR,
    "macroregion_inei" VARCHAR,
    "macroregion_minsa" VARCHAR,
    "iso_3166_2" VARCHAR,
    "fips" VARCHAR,
    "superficie" DOUBLE,
    "altitud" DOUBLE,
    "lat" DOUBLE,
    "lon" DOUBLE,
    "frontera" VARCHAR
);

-- Table: dq_run_metrics (16 rows, 5 columns)
CREATE TABLE dq_run_metrics (
    "ingest_run_id" VARCHAR NOT NULL,
    "metric_name" VARCHAR NOT NULL,
    "metric_value" DOUBLE,
    "metric_text" VARCHAR,
    "created_at" TIMESTAMP DEFAULT now(),
    PRIMARY KEY ("ingest_run_id", "metric_name")
);

-- Table: fct_incident_places (18 rows, 7 columns)
CREATE TABLE fct_incident_places (
    "ingest_run_id" VARCHAR,
    "incident_id" VARCHAR,
    "place_id" VARCHAR,
    "score" DOUBLE,
    "method" VARCHAR,
    "is_primary" BOOLEAN,
    "created_at" TIMESTAMP DEFAULT now()
);

-- Table: fct_incidents (9 rows, 22 columns)
CREATE TABLE fct_incidents (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "original_uri" VARCHAR,
    "url" VARCHAR,
    "published_at" TIMESTAMP,
    "ingest_run_id" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "incident_type" VARCHAR,
    "actors_json" VARCHAR,
    "victims_json" VARCHAR,
    "location_text" VARCHAR,
    "lat" DOUBLE,
    "lon" DOUBLE,
    "adm1" VARCHAR,
    "adm2" VARCHAR,
    "adm3" VARCHAR,
    "confidence" DOUBLE,
    "extraction_version" VARCHAR,
    "review_status" VARCHAR,
    "review_notes" VARCHAR,
    "updated_at" TIMESTAMP
);

-- Table: fct_incidents_curated (6 rows, 22 columns)
CREATE TABLE fct_incidents_curated (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "original_uri" VARCHAR,
    "url" VARCHAR,
    "published_at" TIMESTAMP,
    "ingest_run_id" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "incident_type" VARCHAR,
    "actors_json" VARCHAR,
    "victims_json" VARCHAR,
    "location_text" VARCHAR,
    "lat" DOUBLE,
    "lon" DOUBLE,
    "adm1" VARCHAR,
    "adm2" VARCHAR,
    "adm3" VARCHAR,
    "confidence" DOUBLE,
    "extraction_version" VARCHAR,
    "review_status" VARCHAR,
    "review_notes" VARCHAR,
    "updated_at" TIMESTAMP
);

-- Table: incidents_test (1 rows, 3 columns)
CREATE TABLE incidents_test (
    "incident_id" INTEGER,
    "country" VARCHAR,
    "incident_type" VARCHAR
);

-- Table: map_incident_place (9 rows, 5 columns)
CREATE TABLE map_incident_place (
    "incident_id" VARCHAR,
    "place_id" VARCHAR,
    "score" DOUBLE,
    "method" VARCHAR,
    "ingest_run_id" VARCHAR
);

-- Table: map_incident_place_v2 (18 rows, 14 columns)
CREATE TABLE map_incident_place_v2 (
    "ingest_run_id" VARCHAR,
    "incident_id" VARCHAR,
    "place_id" VARCHAR,
    "adm1" VARCHAR,
    "adm2" VARCHAR,
    "adm3" VARCHAR,
    "lat" DOUBLE,
    "lon" DOUBLE,
    "matched_text_norm" VARCHAR,
    "matched_tokens" INTEGER,
    "method" VARCHAR,
    "score" DOUBLE,
    "is_primary" BOOLEAN,
    "created_at" TIMESTAMP DEFAULT now()
);

-- Table: ops_alerts (0 rows, 7 columns)
CREATE TABLE ops_alerts (
    "alert_id" VARCHAR,
    "run_id" VARCHAR,
    "severity" VARCHAR,
    "message" VARCHAR,
    "created_at" TIMESTAMP,
    "context_json" VARCHAR,
    "is_active" BOOLEAN
);

-- Table: ops_ingest_runs (0 rows, 15 columns)
CREATE TABLE ops_ingest_runs (
    "run_id" VARCHAR,
    "job_name" VARCHAR,
    "started_at" TIMESTAMP,
    "ended_at" TIMESTAMP,
    "status" VARCHAR,
    "params_json" VARCHAR,
    "raw_rows" BIGINT,
    "interim_rows" BIGINT,
    "stg_rows" BIGINT,
    "dedup_run_rows" BIGINT,
    "dedup_total_rows" BIGINT,
    "incidents_extracted_rows" BIGINT,
    "incidents_fact_rows" BIGINT,
    "exit_code" INTEGER,
    "log_path" VARCHAR
);

-- Table: stg_incident_place_candidates (18 rows, 13 columns)
CREATE TABLE stg_incident_place_candidates (
    "ingest_run_id" VARCHAR,
    "incident_id" VARCHAR,
    "matched_text_norm" VARCHAR,
    "matched_tokens" INTEGER,
    "candidate_place_id" VARCHAR,
    "candidate_adm1" VARCHAR,
    "candidate_adm2" VARCHAR,
    "candidate_adm3" VARCHAR,
    "candidate_lat" DOUBLE,
    "candidate_lon" DOUBLE,
    "method" VARCHAR,
    "score" DOUBLE,
    "created_at" TIMESTAMP DEFAULT now()
);

-- Table: stg_incidents_extracted (9 rows, 22 columns)
CREATE TABLE stg_incidents_extracted (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "original_uri" VARCHAR,
    "url" VARCHAR,
    "published_at" TIMESTAMP,
    "ingest_run_id" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "incident_type" VARCHAR,
    "actors_json" VARCHAR,
    "victims_json" VARCHAR,
    "location_text" VARCHAR,
    "lat" DOUBLE,
    "lon" DOUBLE,
    "adm1" VARCHAR,
    "adm2" VARCHAR,
    "adm3" VARCHAR,
    "confidence" DOUBLE,
    "extraction_version" VARCHAR,
    "review_status" VARCHAR,
    "review_notes" VARCHAR,
    "place_id" VARCHAR
);

-- Table: stg_news_dummy (8 rows, 9 columns)
CREATE TABLE stg_news_dummy (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "external_id" VARCHAR,
    "title" VARCHAR,
    "published_at" VARCHAR,
    "url" VARCHAR,
    "content" VARCHAR,
    "language" VARCHAR,
    "created_at" VARCHAR
);

-- Table: stg_news_newsapi_ai (84 rows, 28 columns)
CREATE TABLE stg_news_newsapi_ai (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "source_article_id" VARCHAR,
    "original_uri" VARCHAR,
    "is_duplicate" BOOLEAN,
    "url" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "published_at" VARCHAR,
    "language" VARCHAR,
    "source_title" VARCHAR,
    "source_uri" VARCHAR,
    "country_location_uri" VARCHAR,
    "retrieved_at" VARCHAR,
    "concept_uris" VARCHAR[],
    "concept_labels" VARCHAR[],
    "category_uris" VARCHAR[],
    "category_labels" VARCHAR[],
    "location_uri" INTEGER,
    "location_label" VARCHAR,
    "location_text" INTEGER,
    "lat" INTEGER,
    "lon" INTEGER,
    "adm1" INTEGER,
    "adm2" INTEGER,
    "adm3" INTEGER,
    "ingest_run_id" VARCHAR,
    "ingest_file" VARCHAR
);

-- Table: stg_news_newsapi_ai_dedup (19 rows, 29 columns)
CREATE TABLE stg_news_newsapi_ai_dedup (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "source_article_id" VARCHAR,
    "original_uri" VARCHAR,
    "is_duplicate" BOOLEAN,
    "url" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "published_at" VARCHAR,
    "language" VARCHAR,
    "source_title" VARCHAR,
    "source_uri" VARCHAR,
    "country_location_uri" VARCHAR,
    "retrieved_at" VARCHAR,
    "concept_uris" VARCHAR[],
    "concept_labels" VARCHAR[],
    "category_uris" VARCHAR[],
    "category_labels" VARCHAR[],
    "location_uri" INTEGER,
    "location_label" VARCHAR,
    "location_text" INTEGER,
    "lat" INTEGER,
    "lon" INTEGER,
    "adm1" INTEGER,
    "adm2" INTEGER,
    "adm3" INTEGER,
    "ingest_run_id" VARCHAR,
    "ingest_file" VARCHAR,
    "canonical_uri" VARCHAR
);

-- Table: stg_news_newsapi_ai_dedup_run (3 rows, 29 columns)
CREATE TABLE stg_news_newsapi_ai_dedup_run (
    "incident_id" VARCHAR,
    "source" VARCHAR,
    "source_article_id" VARCHAR,
    "original_uri" VARCHAR,
    "is_duplicate" BOOLEAN,
    "url" VARCHAR,
    "title" VARCHAR,
    "body" VARCHAR,
    "published_at" VARCHAR,
    "language" VARCHAR,
    "source_title" VARCHAR,
    "source_uri" VARCHAR,
    "country_location_uri" VARCHAR,
    "retrieved_at" VARCHAR,
    "concept_uris" VARCHAR[],
    "concept_labels" VARCHAR[],
    "category_uris" VARCHAR[],
    "category_labels" VARCHAR[],
    "location_uri" INTEGER,
    "location_label" VARCHAR,
    "location_text" INTEGER,
    "lat" INTEGER,
    "lon" INTEGER,
    "adm1" INTEGER,
    "adm2" INTEGER,
    "adm3" INTEGER,
    "ingest_run_id" VARCHAR,
    "ingest_file" VARCHAR,
    "canonical_uri" VARCHAR
);

-- View: v_incidents_review_queue
CREATE VIEW v_incidents_review_queue AS SELECT e.ingest_run_id, e.incident_id, e.published_at, e."source", e.title, e.url, e.body, e.incident_type, e.confidence, e.extraction_version, e.location_text, e.place_id, e.adm1, e.adm2, e.adm3, e.lat, e.lon, e.review_status AS staging_review_status, e.review_notes AS staging_review_notes, o.review_status AS override_review_status, o.review_notes AS override_review_notes, o.override_incident_type, o.override_confidence, o.override_location_text, o.override_place_id, o.override_adm1, o.override_adm2, o.override_adm3, o.override_lat, o.override_lon, o.override_title, o.override_body, COALESCE(o.override_incident_type, e.incident_type) AS effective_incident_type, COALESCE(o.override_confidence, e.confidence) AS effective_confidence, COALESCE(o.override_location_text, e.location_text) AS effective_location_text, COALESCE(o.override_place_id, e.place_id) AS effective_place_id, COALESCE(o.override_adm1, e.adm1) AS effective_adm1, COALESCE(o.override_adm2, e.adm2) AS effective_adm2, COALESCE(o.override_adm3, e.adm3) AS effective_adm3, COALESCE(o.override_lat, e.lat) AS effective_lat, COALESCE(o.override_lon, e.lon) AS effective_lon FROM stg_incidents_extracted AS e LEFT JOIN curation_incident_overrides AS o ON ((o.incident_id = e.incident_id));
