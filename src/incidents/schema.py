STG_EXTRACTED_DDL = """
CREATE TABLE IF NOT EXISTS stg_incidents_extracted (
  incident_id VARCHAR,
  source VARCHAR,

  original_uri VARCHAR,
  url VARCHAR,

  published_at TIMESTAMP,
  ingest_run_id VARCHAR,

  title VARCHAR,
  body VARCHAR,

  incident_type VARCHAR,
  actors_json VARCHAR,
  victims_json VARCHAR,

  location_text VARCHAR,
  lat DOUBLE,
  lon DOUBLE,
  adm1 VARCHAR,
  adm2 VARCHAR,
  adm3 VARCHAR,

  confidence DOUBLE,
  extraction_version VARCHAR,

  review_status VARCHAR,
  review_notes VARCHAR
);
"""

FACT_DDL = """
CREATE TABLE IF NOT EXISTS fct_incidents (
  incident_id VARCHAR,
  source VARCHAR,

  original_uri VARCHAR,
  url VARCHAR,

  published_at TIMESTAMP,
  ingest_run_id VARCHAR,

  title VARCHAR,
  body VARCHAR,

  incident_type VARCHAR,
  actors_json VARCHAR,
  victims_json VARCHAR,

  location_text VARCHAR,
  lat DOUBLE,
  lon DOUBLE,
  adm1 VARCHAR,
  adm2 VARCHAR,
  adm3 VARCHAR,

  confidence DOUBLE,
  extraction_version VARCHAR,

  review_status VARCHAR,
  review_notes VARCHAR,

  updated_at TIMESTAMP
);
"""

CURATION_INCIDENT_OVERRIDES_DDL = """
CREATE TABLE IF NOT EXISTS curation_incident_overrides (
  incident_id VARCHAR,

  incident_type_override VARCHAR,
  actors_json_override VARCHAR,
  victims_json_override VARCHAR,

  location_text_override VARCHAR,
  place_id_override VARCHAR,
  lat_override DOUBLE,
  lon_override DOUBLE,
  adm1_override VARCHAR,
  adm2_override VARCHAR,
  adm3_override VARCHAR,

  review_notes VARCHAR,
  updated_at TIMESTAMP,
  updated_by VARCHAR
);
"""
