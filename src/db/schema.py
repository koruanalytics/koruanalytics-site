"""
src/db/schema.py - Unified DDL definitions

This is the SINGLE SOURCE OF TRUTH for all table schemas.
All init/migration scripts should import from here.

Naming conventions:
- Tables: snake_case (stg_, fct_, dim_, map_, ops_, bronze_, silver_, gold_)
- Override columns: override_<field_name> (NOT <field_name>_override)
- Timestamps: created_at, updated_at, built_at
- Run tracking: ingest_run_id

Last updated: 2026-01-09
"""
from __future__ import annotations

# =============================================================================
# MEDALLION ARCHITECTURE - BRONZE LAYER
# =============================================================================

BRONZE_NEWS_DDL = """
CREATE TABLE IF NOT EXISTS bronze_news (
    -- Primary key
    incident_id VARCHAR PRIMARY KEY,
    
    -- Source metadata
    source VARCHAR,
    source_title VARCHAR,
    source_article_id VARCHAR,
    
    -- Content
    title VARCHAR,
    body VARCHAR,
    url VARCHAR,
    language VARCHAR,
    
    -- Temporal
    published_at TIMESTAMP,
    retrieved_at TIMESTAMP,
    
    -- API metadata
    original_uri VARCHAR,
    country_location_uri VARCHAR,
    concept_uris VARCHAR[],
    concept_labels VARCHAR[],
    category_uris VARCHAR[],
    category_labels VARCHAR[],
    
    -- Location from API (raw)
    location_uri VARCHAR,
    location_label VARCHAR,
    location_text VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    
    -- Ingestion tracking
    ingest_run_id VARCHAR,
    ingest_file VARCHAR,
    is_duplicate BOOLEAN DEFAULT FALSE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# MEDALLION ARCHITECTURE - SILVER LAYER
# =============================================================================

SILVER_NEWS_ENRICHED_DDL = """
CREATE TABLE IF NOT EXISTS silver_news_enriched (
    -- Primary key
    incident_id VARCHAR PRIMARY KEY,
    
    -- Foreign key to bronze
    bronze_id VARCHAR,
    
    -- LLM Classification flags
    es_relevante BOOLEAN DEFAULT FALSE,
    es_internacional BOOLEAN DEFAULT FALSE,
    es_resumen BOOLEAN DEFAULT FALSE,
    
    -- Event classification
    tipo_evento VARCHAR,
    subtipo VARCHAR,
    confianza DOUBLE,
    
    -- Victims
    muertos INTEGER,
    heridos INTEGER,
    
    -- Geography (LLM extracted)
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    ubicacion_especifica VARCHAR,
    pais_evento VARCHAR DEFAULT 'Perú',
    
    -- Geocoded coordinates
    lat DOUBLE,
    lon DOUBLE,
    
    -- Actors (JSON arrays as strings)
    actores_json VARCHAR,
    organizaciones_json VARCHAR,
    
    -- Summaries
    resumen_es VARCHAR,
    resumen_en VARCHAR,
    
    -- Sentiment
    sentiment VARCHAR,
    
    -- LLM metadata
    modelo_llm VARCHAR,
    tokens_usados INTEGER,
    
    -- Denormalized from bronze for convenience
    title VARCHAR,
    published_at TIMESTAMP,
    source_name VARCHAR,
    url VARCHAR,
    
    -- Audit
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# MEDALLION ARCHITECTURE - GOLD LAYER
# =============================================================================

GOLD_INCIDENTS_DDL = """
CREATE TABLE IF NOT EXISTS gold_incidents (
    -- Primary key
    incident_id VARCHAR PRIMARY KEY,
    
    -- Event classification
    tipo_evento VARCHAR NOT NULL,
    subtipo VARCHAR,
    
    -- Temporal
    fecha_incidente DATE,
    fecha_publicacion TIMESTAMP,
    
    -- Victims
    muertos INTEGER DEFAULT 0,
    heridos INTEGER DEFAULT 0,
    
    -- Geography
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    ubicacion_display VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    tiene_geo BOOLEAN DEFAULT FALSE,
    
    -- Actors (semicolon-separated strings)
    actores VARCHAR,
    organizaciones VARCHAR,
    
    -- Content
    titulo VARCHAR,
    resumen VARCHAR,
    url VARCHAR,
    source_name VARCHAR,
    
    -- Quality metrics
    sentiment VARCHAR,
    relevancia_score DOUBLE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

GOLD_DAILY_STATS_DDL = """
CREATE TABLE IF NOT EXISTS gold_daily_stats (
    -- Primary key
    fecha DATE PRIMARY KEY,
    
    -- Aggregates
    total_incidentes INTEGER DEFAULT 0,
    total_muertos INTEGER DEFAULT 0,
    total_heridos INTEGER DEFAULT 0,
    
    -- Breakdowns (JSON)
    por_tipo_json VARCHAR,
    por_departamento_json VARCHAR,
    
    -- Quality metrics
    incidentes_con_geo INTEGER DEFAULT 0,
    incidentes_alta_relevancia INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# STAGING TABLES (LEGACY - kept for reference)
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
# FACT TABLES (LEGACY)
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

MAP_INCIDENT_PLACE_V2_DDL = """
CREATE TABLE IF NOT EXISTS map_incident_place_v2 (
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
# DDL COLLECTIONS
# =============================================================================

# Medallion tables (active architecture)
MEDALLION_DDLS = [
    BRONZE_NEWS_DDL,
    SILVER_NEWS_ENRICHED_DDL,
    GOLD_INCIDENTS_DDL,
    GOLD_DAILY_STATS_DDL,
]

# Core operational tables
CORE_DDLS = [
    DIM_PLACES_PE_DDL,
    OPS_INGEST_RUNS_DDL,
    OPS_ALERTS_DDL,
    DQ_RUN_METRICS_DDL,
]

# Legacy tables (kept for reference, may be removed)
LEGACY_DDLS = [
    STG_NEWS_NEWSAPI_AI_DDL,
    STG_INCIDENTS_EXTRACTED_DDL,
    STG_INCIDENT_PLACE_CANDIDATES_DDL,
    FCT_INCIDENTS_DDL,
    FCT_INCIDENTS_CURATED_DDL,
    FCT_INCIDENT_PLACES_DDL,
    MAP_INCIDENT_PLACE_DDL,
    MAP_INCIDENT_PLACE_V2_DDL,
    CURATION_INCIDENT_OVERRIDES_DDL,
]

# All DDLs for full initialization
ALL_DDLS = MEDALLION_DDLS + CORE_DDLS + LEGACY_DDLS + [V_INCIDENTS_REVIEW_QUEUE_DDL]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def init_medallion_tables(con) -> dict:
    """
    Initialize Medallion architecture tables.
    
    Args:
        con: DuckDB connection
        
    Returns:
        dict with created table names and status
    """
    results = {}
    for ddl in MEDALLION_DDLS:
        # Extract table name from DDL
        import re
        match = re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', ddl)
        if match:
            table_name = match.group(1)
            try:
                con.execute(ddl)
                results[table_name] = "created"
            except Exception as e:
                results[table_name] = f"error: {e}"
    return results


def init_all_tables(con) -> dict:
    """
    Initialize all tables in the schema.
    
    Args:
        con: DuckDB connection
        
    Returns:
        dict with created table names and status
    """
    results = {}
    for ddl in ALL_DDLS:
        import re
        match = re.search(r'CREATE (?:TABLE|VIEW) (?:IF NOT EXISTS |OR REPLACE )?(\w+)', ddl)
        if match:
            obj_name = match.group(1)
            try:
                con.execute(ddl)
                results[obj_name] = "created"
            except Exception as e:
                results[obj_name] = f"error: {e}"
    return results
