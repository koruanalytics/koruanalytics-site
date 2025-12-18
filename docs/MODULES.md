# Documentación de Módulos

## Índice

1. [Ingestion](#ingestion)
2. [Processing](#processing)
3. [Incidents](#incidents)
4. [Geoparse](#geoparse)
5. [Database](#database)
6. [Ops](#ops)

---

## Ingestion

### `src/ingestion/newsapi_ai_ingest.py`

**Propósito**: Ingesta multi-query desde NewsAPI.ai con grupos temáticos.

#### Clases principales

```python
@dataclass
class IngestParams:
    scope_path: Path           # Path al YAML de scope
    date_start: date           # Fecha inicio
    date_end: date             # Fecha fin
    max_per_group: int = 50    # Max artículos por grupo
    max_total: int = 200       # Max total artículos
    priority_filter: list = None  # Filtrar por prioridad
    out_dir: Path = "data/raw/newsapi_ai"

class MultiQueryIngestor:
    def run(params: IngestParams) -> IngestResult
```

#### Flujo de ejecución

1. Lee scope YAML con grupos de conceptos/keywords
2. Itera por cada grupo ordenado por prioridad
3. Construye query combinando concepts + keywords + location
4. Llama a NewsAPI.ai Event Registry API
5. Deduplica artículos cross-group (por URI)
6. Genera JSON con metadatos de grupo y run_id

#### Ejemplo de uso

```python
from src.ingestion.newsapi_ai_ingest import IngestParams, MultiQueryIngestor

params = IngestParams(
    scope_path=Path("config/newsapi_scope_peru.yaml"),
    date_start=date(2025, 12, 17),
    date_end=date(2025, 12, 18),
    max_total=100
)

ingestor = MultiQueryIngestor()
result = ingestor.run(params)
print(f"Artículos: {result.total_unique}")
```

---

## Processing

### `src/processing/normalize_newsapi_ai.py`

**Propósito**: Convertir JSON crudo a Parquet normalizado.

#### Función principal

```python
def run_newsapi_ai_normalization(raw_path: Path) -> Path:
    """
    Lee JSON, extrae campos relevantes, genera Parquet.
    Returns: Path al archivo Parquet generado
    """
```

#### Campos extraídos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| uri | string | ID único del artículo |
| title | string | Título |
| body | string | Cuerpo del artículo |
| date_time | timestamp | Fecha/hora publicación |
| source_title | string | Nombre del medio |
| source_uri | string | URI del medio |
| url | string | URL del artículo |
| lang | string | Idioma |
| concepts | list | Conceptos detectados |
| categories | list | Categorías |
| ingest_run_id | string | ID del run de ingesta |
| concept_group | string | Grupo temático asignado |

---

### `src/processing/load_newsapi_ai_to_dw.py`

**Propósito**: Cargar Parquet a DuckDB.

```python
def load_newsapi_ai_into_duckdb(parquet_path: Path, db_path: Path) -> int:
    """
    Carga Parquet a tabla stg_news_newsapi_ai.
    Returns: Número de filas insertadas
    """
```

---

### `src/processing/dedupe_newsapi_ai_in_duckdb.py`

**Propósito**: Deduplicar artículos en DuckDB.

```python
def dedupe_newsapi_ai_in_duckdb(db_path: Path, run_id: str) -> dict:
    """
    Deduplica por URI, mantiene el más reciente.
    Returns: {run_removed: int, global_removed: int}
    """
```

---

## Incidents

### `src/incidents/acled_rules.py`

**Propósito**: Clasificar incidentes según taxonomía ACLED.

#### Función principal

```python
def classify_acled(
    headline: str,
    description: str,
    concept_group: str = None
) -> dict:
    """
    Returns: {
        event_type: str,
        sub_event_type: str,
        confidence: float,
        method: str  # 'rule' | 'keyword' | 'llm'
    }
    """
```

#### Taxonomía ACLED

```python
ACLED_EVENT_TYPES = [
    "Battles",
    "Explosions/Remote violence",
    "Protests",
    "Riots",
    "Violence against civilians",
    "Strategic developments"
]

ACLED_SUB_EVENT_TYPES = {
    "Battles": ["Armed clash", "Government regains territory", ...],
    "Protests": ["Peaceful protest", "Protest with intervention", ...],
    ...
}
```

---

### `src/incidents/extract_baseline.py`

**Propósito**: Extraer incidentes de artículos usando LLM.

```python
def extract_incidents(article: dict) -> list[dict]:
    """
    Usa OpenAI/Claude para extraer incidentes estructurados.
    Returns: Lista de incidentes con campos:
        - headline, description, event_date
        - location_text, actors
        - fatalities, injuries
    """
```

---

## Geoparse

### `src/geoparse/extract_locations.py`

**Propósito**: Extraer menciones de lugares del texto.

```python
def extract_location_candidates(text: str) -> list[dict]:
    """
    Usa spaCy NER + reglas para extraer lugares.
    Returns: [{text: str, start: int, end: int, type: str}]
    """
```

---

### `src/geoparse/resolve_places.py`

**Propósito**: Resolver lugares a coordenadas.

```python
def resolve_place(
    place_text: str,
    country: str = "Peru",
    gazetteer: pd.DataFrame = None
) -> dict:
    """
    1. Busca en gazetteer local
    2. Si no encuentra, llama a Nominatim
    3. Calcula confidence score
    
    Returns: {
        place_id: int,
        name: str,
        admin1: str,
        latitude: float,
        longitude: float,
        confidence: float,
        method: str  # 'gazetteer' | 'nominatim'
    }
    """
```

---

## Database

### `src/db/schema.py`

**Propósito**: Definiciones DDL de todas las tablas.

#### Tablas definidas

```python
# Staging
STG_NEWS_NEWSAPI_AI_DDL = "CREATE TABLE IF NOT EXISTS stg_news_newsapi_ai (...)"
STG_NEWS_NEWSAPI_AI_DEDUP_DDL = "..."

# Incidents
STG_INCIDENTS_EXTRACTED_DDL = "..."
MAP_INCIDENT_PLACE_DDL = "..."

# Dimensions
DIM_PLACES_PE_DDL = "..."

# Facts
FCT_INCIDENTS_DDL = "..."
FCT_INCIDENTS_CURATED_DDL = "..."

# Operations
OPS_RUNS_DDL = "..."
OPS_ALERTS_DDL = "..."
```

#### Función de inicialización

```python
def init_all_tables(con: duckdb.DuckDBPyConnection):
    """Ejecuta todos los DDL para crear tablas."""
```

---

## Ops

### `src/ops/runs.py`

**Propósito**: Gestión de runs de ingesta.

```python
def register_run(con, run_id: str, params: dict) -> None:
    """Registra un nuevo run en ops_runs."""

def get_latest_run_id(con) -> str:
    """Obtiene el run_id más reciente."""

def update_run_status(con, run_id: str, status: str) -> None:
    """Actualiza estado: running, completed, failed."""
```

---

### `src/ops/alerts.py`

**Propósito**: Sistema de alertas por anomalías.

```python
def check_alerts(con, run_id: str) -> list[dict]:
    """
    Evalúa reglas de alerta:
    - Artículos por debajo del mínimo esperado
    - Errores de geo-resolución > threshold
    - Duplicados excesivos
    
    Returns: Lista de alertas disparadas
    """

def send_alert(alert: dict, channel: str = "email") -> None:
    """Envía alerta por email/slack/etc."""
```

---

## Utils

### `src/utils/config.py`

```python
def load_settings() -> dict:
    """Carga config/settings.yaml"""

def get_db_path() -> Path:
    """Obtiene path a DuckDB desde .env o default"""
```

### `src/utils/dq_checks.py`

```python
def run_dq_checks(df: pd.DataFrame, checks: list) -> list[dict]:
    """
    Ejecuta checks de data quality.
    Checks disponibles:
    - min_rows, max_rows
    - not_null(column)
    - unique(column)
    - range(column, min, max)
    """
```
