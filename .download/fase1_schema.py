"""
src/db/schema.py - Unified DDL definitions

This is the SINGLE SOURCE OF TRUTH for all table schemas.
All init/migration scripts should import from here.

Naming conventions:
- Tables: snake_case (stg_, fct_, dim_, map_, ops_)
- Override columns: override_<field_name> (NOT <field_name>_override)
- Timestamps: created_at, updated_at, built_at
- Run tracking: ingest_run_id
"""
from __future__ import annotations

# =============================================================================
# STAGING TABLES
# =============================================================================

STG_NEWS_NEWSAPI_AI_DDL = """
CREATE TABLE IF NOT EXISTS stg_news_newsapi_ai (
    incident_id VARCHAR,
    source VARCHAR,
    source_article_id VARCHAR,
    original_uri VARCHAR,
    is_duplicate BOOLEAN,
    url VARCHAR,
    title VARCHAR,
    body VARCHAR,
    published_at TIMESTAMP,
    language VARCHAR,
    source_title VARCHAR,
    source_uri VARCHAR,
    country_location_uri VARCHAR,
    retrieved_at TIMESTAMP,
    concept_uris VARCHAR[],
    concept_labels VARCHAR[],
    category_uris VARCHAR[],
    category_labels VARCHAR[],
    location_uri VARCHAR,
    location_label VARCHAR,
    location_text VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    ingest_run_id VARCHAR,
    ingest_file VARCHAR
);
"""

STG_INCIDENTS_EXTRACTED_DDL = """
CREATE TABLE IF NOT EXISTS stg_incidents_extracted (
    -- Keys
    incident_id VARCHAR,
    ingest_run_id VARCHAR,
    
    -- Source info
    source VARCHAR,
    original_uri VARCHAR,
    url VARCHAR,
    
    -- Content
    title VARCHAR,
    body VARCHAR,
    published_at TIMESTAMP,
    
    -- ACLED Classification
    incident_type VARCHAR,
    sub_event_type VARCHAR,
    disorder_type VARCHAR,
    confidence DOUBLE,
    extraction_version VARCHAR,
    
    -- NLP placeholders
    actors_json VARCHAR,
    victims_json VARCHAR,
    
    -- GEO
    location_text VARCHAR,
    place_id VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    
    -- Review
    review_status VARCHAR,
    review_notes VARCHAR,
    
    -- API Enrichment (from NewsAPI.ai)
    source_title VARCHAR,
    is_duplicate BOOLEAN,
    api_category VARCHAR,
    api_location VARCHAR,
    concept_labels VARCHAR
);
"""

STG_INCIDENT_PLACE_CANDIDATES_DDL = """
CREATE TABLE IF NOT EXISTS stg_incident_place_candidates (
    ingest_run_id VARCHAR,
    incident_id VARCHAR,
    
    candidate_place_id VARCHAR,
    candidate_adm1 VARCHAR,
    candidate_adm2 VARCHAR,
    candidate_adm3 VARCHAR,
    candidate_lat DOUBLE,
    candidate_lon DOUBLE,
    
    matched_text_norm VARCHAR,
    matched_tokens INTEGER,
    method VARCHAR,
    score DOUBLE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# DIMENSION TABLES
# =============================================================================

DIM_PLACES_PE_DDL = """
CREATE TABLE IF NOT EXISTS dim_places_pe (
    place_id VARCHAR,
    ubigeo_reniec VARCHAR,
    
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    
    region VARCHAR,
    macroregion_inei VARCHAR,
    macroregion_minsa VARCHAR,
    
    iso_3166_2 VARCHAR,
    fips VARCHAR,
    
    superficie DOUBLE,
    altitud DOUBLE,
    lat DOUBLE,
    lon DOUBLE,
    
    frontera VARCHAR
);
"""

# =============================================================================
# FACT TABLES
# =============================================================================

FCT_INCIDENTS_DDL = """
CREATE TABLE IF NOT EXISTS fct_incidents (
    -- Keys
    incident_id VARCHAR,
    ingest_run_id VARCHAR,
    
    -- Source info
    source VARCHAR,
    original_uri VARCHAR,
    url VARCHAR,
    
    -- Content
    title VARCHAR,
    body VARCHAR,
    published_at TIMESTAMP,
    
    -- ACLED Classification
    incident_type VARCHAR,
    sub_event_type VARCHAR,
    disorder_type VARCHAR,
    confidence DOUBLE,
    extraction_version VARCHAR,
    
    -- NLP
    actors_json VARCHAR,
    victims_json VARCHAR,
    
    -- GEO
    location_text VARCHAR,
    place_id VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    
    -- Review
    review_status VARCHAR,
    review_notes VARCHAR,
    
    -- API Enrichment (from NewsAPI.ai)
    source_title VARCHAR,
    is_duplicate BOOLEAN,
    api_category VARCHAR,
    api_location VARCHAR,
    concept_labels VARCHAR,
    
    -- Metadata
    built_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

FCT_INCIDENTS_CURATED_DDL = """
CREATE TABLE IF NOT EXISTS fct_incidents_curated (
    -- Same schema as fct_incidents, created dynamically
    -- See build_fct_incidents_curated.py
);
"""

FCT_INCIDENT_PLACES_DDL = """
CREATE TABLE IF NOT EXISTS fct_incident_places (
    ingest_run_id VARCHAR,
    incident_id VARCHAR,
    
    place_id VARCHAR,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    
    matched_text_norm VARCHAR,
    matched_tokens INTEGER,
    method VARCHAR,
    score DOUBLE,
    
    is_primary BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# MAPPING TABLES
# =============================================================================

MAP_INCIDENT_PLACE_DDL = """
CREATE TABLE IF NOT EXISTS map_incident_place (
    incident_id VARCHAR,
    place_id VARCHAR,
    score DOUBLE,
    method VARCHAR,
    ingest_run_id VARCHAR
);
"""

map_incident_place_DDL = """
CREATE TABLE IF NOT EXISTS map_incident_place (
    ingest_run_id VARCHAR,
    incident_id VARCHAR,
    
    place_id VARCHAR,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    
    matched_text_norm VARCHAR,
    matched_tokens INTEGER,
    method VARCHAR,
    score DOUBLE,
    
    is_primary BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# CURATION TABLES
# =============================================================================

CURATION_INCIDENT_OVERRIDES_DDL = """
CREATE TABLE IF NOT EXISTS curation_incident_overrides (
    -- Key
    incident_id VARCHAR PRIMARY KEY,
    
    -- Override fields (use override_ prefix consistently)
    override_incident_type VARCHAR,
    override_sub_event_type VARCHAR,
    override_disorder_type VARCHAR,
    override_confidence DOUBLE,
    override_location_text VARCHAR,
    override_place_id VARCHAR,
    override_lat DOUBLE,
    override_lon DOUBLE,
    override_adm1 VARCHAR,
    override_adm2 VARCHAR,
    override_adm3 VARCHAR,
    override_title VARCHAR,
    override_body VARCHAR,
    
    -- Review workflow
    review_status VARCHAR DEFAULT 'PENDING',
    review_notes VARCHAR,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR,
    updated_at TIMESTAMP,
    updated_by VARCHAR
);
"""

# =============================================================================
# OPS TABLES
# =============================================================================

OPS_INGEST_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS ops_ingest_runs (
    run_id VARCHAR PRIMARY KEY,
    job_name VARCHAR,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR,
    params_json VARCHAR,
    raw_rows BIGINT,
    interim_rows BIGINT,
    stg_rows BIGINT,
    dedup_run_rows BIGINT,
    dedup_total_rows BIGINT,
    incidents_extracted_rows BIGINT,
    incidents_fact_rows BIGINT,
    exit_code INTEGER,
    log_path VARCHAR
);
"""

OPS_ALERTS_DDL = """
CREATE TABLE IF NOT EXISTS ops_alerts (
    alert_id VARCHAR PRIMARY KEY,
    ingest_run_id VARCHAR,
    pipeline_name VARCHAR,
    alert_type VARCHAR,
    severity VARCHAR,
    message VARCHAR,
    context_json VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DQ_RUN_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS dq_run_metrics (
    ingest_run_id VARCHAR,
    metric_name VARCHAR,
    metric_value DOUBLE,
    metric_text VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ingest_run_id, metric_name)
);
"""

# =============================================================================
# VIEWS
# =============================================================================

V_INCIDENTS_REVIEW_QUEUE_DDL = """
CREATE OR REPLACE VIEW v_incidents_review_queue AS
SELECT
    e.ingest_run_id,
    e.incident_id,
    e.published_at,
    e.source,
    e.source_title,
    e.title,
    e.url,
    e.body,
    
    -- ACLED Classification
    e.incident_type,
    e.sub_event_type,
    e.disorder_type,
    e.confidence,
    e.extraction_version,
    
    -- GEO
    e.location_text,
    e.api_location,
    e.place_id,
    e.adm1,
    e.adm2,
    e.adm3,
    e.lat,
    e.lon,
    
    -- API Enrichment
    e.api_category,
    e.concept_labels,
    e.is_duplicate,
    
    -- Staging review status
    e.review_status AS staging_review_status,
    e.review_notes AS staging_review_notes,
    
    -- Overrides
    o.review_status AS override_review_status,
    o.review_notes AS override_review_notes,
    o.override_incident_type,
    o.override_sub_event_type,
    o.override_disorder_type,
    o.override_confidence,
    o.override_location_text,
    o.override_place_id,
    o.override_adm1,
    o.override_adm2,
    o.override_adm3,
    o.override_lat,
    o.override_lon,
    o.override_title,
    o.override_body,
    
    -- Effective values (override wins)
    COALESCE(o.override_incident_type, e.incident_type) AS effective_incident_type,
    COALESCE(o.override_sub_event_type, e.sub_event_type) AS effective_sub_event_type,
    COALESCE(o.override_disorder_type, e.disorder_type) AS effective_disorder_type,
    COALESCE(o.override_confidence, e.confidence) AS effective_confidence,
    COALESCE(o.override_location_text, e.location_text) AS effective_location_text,
    COALESCE(o.override_place_id, e.place_id) AS effective_place_id,
    COALESCE(o.override_adm1, e.adm1) AS effective_adm1,
    COALESCE(o.override_adm2, e.adm2) AS effective_adm2,
    COALESCE(o.override_adm3, e.adm3) AS effective_adm3,
    COALESCE(o.override_lat, e.lat) AS effective_lat,
    COALESCE(o.override_lon, e.lon) AS effective_lon

FROM stg_incidents_extracted e
LEFT JOIN curation_incident_overrides o
    ON o.incident_id = e.incident_id;
"""

# =============================================================================
# ALL DDLs (for init scripts)
# =============================================================================

ALL_CORE_DDLS = [
    STG_INCIDENTS_EXTRACTED_DDL,
    FCT_INCIDENTS_DDL,
    MAP_INCIDENT_PLACE_DDL,
    DIM_PLACES_PE_DDL,
    OPS_INGEST_RUNS_DDL,
    OPS_ALERTS_DDL,
]

ALL_CURATION_DDLS = [
    CURATION_INCIDENT_OVERRIDES_DDL,
    STG_INCIDENT_PLACE_CANDIDATES_DDL,
    map_incident_place_DDL,
    FCT_INCIDENT_PLACES_DDL,
    DQ_RUN_METRICS_DDL,
    V_INCIDENTS_REVIEW_QUEUE_DDL,
]

ALL_DDLS = ALL_CORE_DDLS + ALL_CURATION_DDLS
