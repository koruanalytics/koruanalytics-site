"""
src/db/schema.py - Unified DDL definitions

This is the SINGLE SOURCE OF TRUTH for all table schemas.
All init/migration scripts should import from here.

Naming conventions:
- Tables: snake_case (stg_, fct_, dim_, map_, ops_, bronze_, silver_, gold_)
- Override columns: override_<field_name> (NOT <field_name>_override)
- Timestamps: created_at, updated_at, built_at
- Run tracking: ingest_run_id

Last updated: 2026-01-18 (M6 - arma_usada field)
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
    victima_perfil VARCHAR,
    arma_usada VARCHAR,
    
    -- Geography (LLM extracted)
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    ubicacion_especifica VARCHAR,
    adm4_name VARCHAR,
    pais_evento VARCHAR DEFAULT 'Perú',
    
    -- Geocoded coordinates (from gazetteer or LLM)
    lat DOUBLE,
    lon DOUBLE,
    nivel_geo VARCHAR,
    
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
    victima_perfil VARCHAR,
    arma_usada VARCHAR,
    
    -- Geography
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    adm4_name VARCHAR,
    ubicacion_display VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    tiene_geo BOOLEAN DEFAULT FALSE,
    nivel_geo VARCHAR,
    
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
    source_title VARCHAR,
    source_article_id VARCHAR,
    
    -- Content
    title VARCHAR,
    body VARCHAR,
    published_at TIMESTAMP,
    language VARCHAR,
    retrieved_at TIMESTAMP,
    
    -- Location (from news API)
    location_uri VARCHAR,
    location_label VARCHAR,
    location_text VARCHAR,
    
    -- Geography (extracted from news metadata)
    lat DOUBLE,
    lon DOUBLE,
    adm1 VARCHAR,
    adm2 VARCHAR,
    adm3 VARCHAR,
    
    -- LLM classification
    es_relevante BOOLEAN,
    es_internacional BOOLEAN,
    tipo_evento VARCHAR,
    subtipo VARCHAR,
    
    -- Extracted entities
    muertos INTEGER,
    heridos INTEGER,
    actores VARCHAR[],
    organizaciones VARCHAR[],
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    
    -- Content generation
    resumen_es VARCHAR,
    resumen_en VARCHAR,
    sentiment VARCHAR,
    
    -- Metadata
    confianza DOUBLE,
    modelo_llm VARCHAR,
    tokens_usados INTEGER,
    processed_at TIMESTAMP
);
"""

# =============================================================================
# FACT TABLES
# =============================================================================

FCT_INCIDENTS_DDL = """
CREATE TABLE IF NOT EXISTS fct_incidents (
    incident_id VARCHAR PRIMARY KEY,
    tipo_evento VARCHAR NOT NULL,
    subtipo VARCHAR,
    fecha_incidente DATE NOT NULL,
    muertos INTEGER DEFAULT 0,
    heridos INTEGER DEFAULT 0,
    departamento VARCHAR,
    provincia VARCHAR,
    distrito VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    tiene_geo BOOLEAN DEFAULT FALSE,
    actores VARCHAR,
    organizaciones VARCHAR,
    titulo VARCHAR,
    resumen VARCHAR,
    url VARCHAR,
    source_name VARCHAR,
    sentiment VARCHAR,
    relevancia_score DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# DIMENSION TABLES
# =============================================================================

DIM_DEPARTAMENTOS_DDL = """
CREATE TABLE IF NOT EXISTS dim_departamentos (
    departamento VARCHAR PRIMARY KEY,
    codigo_inei VARCHAR,
    region_natural VARCHAR,
    poblacion INTEGER,
    capital VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DIM_PROVINCIAS_DDL = """
CREATE TABLE IF NOT EXISTS dim_provincias (
    provincia_id VARCHAR PRIMARY KEY,
    departamento VARCHAR,
    provincia VARCHAR,
    codigo_inei VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DIM_TIPO_EVENTO_DDL = """
CREATE TABLE IF NOT EXISTS dim_tipo_evento (
    tipo_evento VARCHAR PRIMARY KEY,
    categoria VARCHAR,
    descripcion VARCHAR,
    severidad INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# GAZETTEER (GEOGRAPHIC REFERENCE)
# =============================================================================

DIM_PLACES_PE_DDL = """
CREATE TABLE IF NOT EXISTS dim_places_pe (
    place_id VARCHAR PRIMARY KEY,
    ubigeo_reniec VARCHAR,
    adm1_code VARCHAR,
    adm2_code VARCHAR,
    adm3_code VARCHAR,
    adm1_name VARCHAR,
    adm2_name VARCHAR,
    adm3_name VARCHAR,
    display_name VARCHAR,
    search_name VARCHAR,
    region VARCHAR,
    macroregion_inei VARCHAR,
    macroregion_minsa VARCHAR,
    iso_3166_2 VARCHAR,
    fips VARCHAR,
    superficie DOUBLE,
    altitud DOUBLE,
    lat DOUBLE,
    lon DOUBLE,
    frontera VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# MAPPING/JUNCTION TABLES
# =============================================================================

MAP_INCIDENT_ACTORS_DDL = """
CREATE TABLE IF NOT EXISTS map_incident_actors (
    incident_id VARCHAR,
    actor_type VARCHAR,
    actor_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (incident_id, actor_name)
);
"""

# =============================================================================
# OPERATIONAL TABLES
# =============================================================================

OPS_INGESTION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS ops_ingestion_runs (
    run_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,
    articles_fetched INTEGER DEFAULT 0,
    articles_stored INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    source_provider VARCHAR,
    error_log VARCHAR
);
"""

OPS_LLM_CALLS_DDL = """
CREATE TABLE IF NOT EXISTS ops_llm_calls (
    call_id VARCHAR PRIMARY KEY,
    incident_id VARCHAR,
    provider VARCHAR,
    model VARCHAR,
    tokens_used INTEGER,
    cost_usd DOUBLE,
    latency_ms INTEGER,
    status VARCHAR,
    error_message VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# =============================================================================
# EXPORT: Lista de todos los DDLs en orden de creación
# =============================================================================

ALL_DDLS = [
    # Medallion Bronze
    BRONZE_NEWS_DDL,
    
    # Medallion Silver
    SILVER_NEWS_ENRICHED_DDL,
    
    # Medallion Gold
    GOLD_INCIDENTS_DDL,
    GOLD_DAILY_STATS_DDL,
    
    # Legacy Staging
    STG_NEWS_NEWSAPI_AI_DDL,
    STG_INCIDENTS_EXTRACTED_DDL,
    
    # Fact Tables
    FCT_INCIDENTS_DDL,
    
    # Dimensions
    DIM_DEPARTAMENTOS_DDL,
    DIM_PROVINCIAS_DDL,
    DIM_TIPO_EVENTO_DDL,
    DIM_PLACES_PE_DDL,
    
    # Mappings
    MAP_INCIDENT_ACTORS_DDL,
    
    # Operational
    OPS_INGESTION_RUNS_DDL,
    OPS_LLM_CALLS_DDL,
]

# Export all DDLs as a dict for easy access
DDL_DICT = {
    'bronze_news': BRONZE_NEWS_DDL,
    'silver_news_enriched': SILVER_NEWS_ENRICHED_DDL,
    'gold_incidents': GOLD_INCIDENTS_DDL,
    'gold_daily_stats': GOLD_DAILY_STATS_DDL,
    'stg_news_newsapi_ai': STG_NEWS_NEWSAPI_AI_DDL,
    'stg_incidents_extracted': STG_INCIDENTS_EXTRACTED_DDL,
    'fct_incidents': FCT_INCIDENTS_DDL,
    'dim_departamentos': DIM_DEPARTAMENTOS_DDL,
    'dim_provincias': DIM_PROVINCIAS_DDL,
    'dim_tipo_evento': DIM_TIPO_EVENTO_DDL,
    'dim_places_pe': DIM_PLACES_PE_DDL,
    'map_incident_actors': MAP_INCIDENT_ACTORS_DDL,
    'ops_ingestion_runs': OPS_INGESTION_RUNS_DDL,
    'ops_llm_calls': OPS_LLM_CALLS_DDL,
}
