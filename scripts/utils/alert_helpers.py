# daily_pipeline.py - ALERT INSERT FIX
# Last updated: 2026-01-09
# Description: Corrected alert insertion code aligned with ops_alerts schema v2.0
#
# INSTRUCTIONS:
# 1. Find the existing alert INSERT code in daily_pipeline.py (around line 293-301)
# 2. Replace it with this corrected version
# 3. Make sure the imports and helper function are at the top of the file

# =============================================================================
# ADD TO IMPORTS SECTION (top of file)
# =============================================================================

import uuid
from datetime import datetime

# =============================================================================
# ADD HELPER FUNCTION (after imports, before main pipeline functions)
# =============================================================================

def generate_alert_id() -> str:
    """
    Generate unique alert ID with timestamp prefix for sorting.
    Format: ALT-YYYYMMDD-HHMMSS-XXXX (where XXXX is random suffix)
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"ALT-{timestamp}-{suffix}"


def insert_pipeline_alert(
    con,
    alert_type: str,
    severity: str,
    message: str,
    pipeline_name: str = "daily_pipeline",
    run_id: str = None,
    incident_id: str = None,
    context_json: str = None,
    is_active: bool = True
) -> str:
    """
    Insert an alert into ops_alerts table.
    
    Args:
        con: DuckDB connection
        alert_type: Type of alert (e.g., 'classification_error', 'api_limit', 'validation_failed')
        severity: Alert severity ('info', 'warning', 'error', 'critical')
        message: Human-readable alert message
        pipeline_name: Name of the pipeline generating the alert
        run_id: Optional reference to pipeline run
        incident_id: Optional reference to specific incident that triggered alert
        context_json: Optional JSON string with additional context
        is_active: Whether the alert is active (default True)
        
    Returns:
        Generated alert_id
        
    Example:
        alert_id = insert_pipeline_alert(
            con,
            alert_type='classification_error',
            severity='warning',
            message='LLM returned invalid JSON for article xyz',
            incident_id='INC-20260109-001'
        )
    """
    alert_id = generate_alert_id()
    
    con.execute("""
        INSERT INTO ops_alerts (
            alert_id,
            run_id,
            pipeline_name,
            alert_type,
            severity,
            message,
            incident_id,
            context_json,
            is_active,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [
        alert_id,
        run_id,
        pipeline_name,
        alert_type,
        severity,
        message,
        incident_id,
        context_json,
        is_active
    ])
    
    return alert_id


# =============================================================================
# REPLACE EXISTING ALERT INSERT CODE
# =============================================================================

# BEFORE (broken - around line 293-301):
# -----------------------------------------------------------------------------
# INSERT INTO ops_alerts (alert_type, severity, message, incident_id, created_at)
# VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
# -----------------------------------------------------------------------------

# AFTER (fixed):
# -----------------------------------------------------------------------------
# Use the helper function instead of raw SQL:

# Example 1: Alert for classification error with incident reference
# alert_id = insert_pipeline_alert(
#     con,
#     alert_type='classification_error',
#     severity='warning',
#     message=f'Failed to classify article: {article_id}',
#     ingest_run_id=current_run_id,  # if you have it
#     incident_id=article_id  # reference to the problematic article
# )

# Example 2: Alert for API limit without incident reference
# alert_id = insert_pipeline_alert(
#     con,
#     alert_type='api_limit_warning',
#     severity='warning',
#     message='Approaching NewsAPI rate limit'
# )

# Example 3: Critical error
# alert_id = insert_pipeline_alert(
#     con,
#     alert_type='pipeline_failure',
#     severity='critical',
#     message=f'Pipeline crashed: {str(exception)}'
# )


# =============================================================================
# ALERT TYPES REFERENCE
# =============================================================================

ALERT_TYPES = {
    # Ingestion alerts
    'api_error': 'NewsAPI.ai returned an error',
    'api_limit_warning': 'Approaching API rate limit',
    'api_limit_exceeded': 'API rate limit exceeded',
    'no_articles_found': 'Query returned zero articles',
    
    # Classification alerts  
    'classification_error': 'LLM classification failed for an article',
    'classification_timeout': 'LLM request timed out',
    'invalid_llm_response': 'LLM returned unparseable response',
    
    # Data quality alerts
    'duplicate_detected': 'Duplicate article detected',
    'validation_failed': 'Article failed validation rules',
    'missing_required_field': 'Required field is missing',
    
    # Pipeline alerts
    'pipeline_started': 'Pipeline execution started',
    'pipeline_completed': 'Pipeline execution completed',
    'pipeline_failure': 'Pipeline crashed with error',
    'stage_skipped': 'Pipeline stage was skipped',
}

SEVERITY_LEVELS = ['info', 'warning', 'error', 'critical']
