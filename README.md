# OSINT Peru 2026 - Sistema de Monitoreo de Incidentes

Sistema de inteligencia de fuentes abiertas (OSINT) para monitorear y clasificar incidentes de seguridad en Perú, enfocado en el contexto electoral 2026.

## 🎯 Objetivo

Automatizar la recolección, clasificación y geolocalización de noticias relacionadas con:
- Violencia política y electoral
- Protestas y manifestaciones
- Crimen organizado
- Terrorismo
- Desastres naturales
- Incidentes de seguridad

## 📊 Pipeline de Datos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OSINT PERU 2026 PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   INGESTA    │───▶│ NORMALIZAR   │───▶│   CARGAR     │───▶│  DEDUPLICAR  │
│  NewsAPI.ai  │    │   Parquet    │    │   DuckDB     │    │   Global     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                                                            │
       ▼                                                            ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   EXTRAER    │◀───│  CLASIFICAR  │◀───│  RESOLVER    │◀───│   LUGARES    │
│  Incidentes  │    │    ACLED     │    │    GEO       │    │  Candidatos  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐
│    CURAR     │───▶│  DASHBOARD   │
│   Manual     │    │  Streamlit   │
└──────────────┘    └──────────────┘
```

## 🏗️ Estructura del Proyecto

```
2026_Peru/
├── config/                     # Configuración
│   ├── newsapi_scope_peru.yaml # Scope de búsqueda (grupos, keywords, concepts)
│   ├── settings.yaml           # Configuración general
│   └── geo/                    # Gazetteer de Perú
│       ├── peru_gazetteer_full.parquet
│       └── peru_gazetteer_full.csv
│
├── src/                        # Código fuente
│   ├── ingestion/              # Ingesta de datos
│   │   └── newsapi_ai_ingest.py    # Multi-query ingestion
│   ├── processing/             # Procesamiento
│   │   ├── normalize_newsapi_ai.py # JSON → Parquet
│   │   ├── load_newsapi_ai_to_dw.py # Parquet → DuckDB
│   │   └── dedupe_newsapi_ai_in_duckdb.py
│   ├── incidents/              # Extracción de incidentes
│   │   ├── acled_rules.py      # Clasificación ACLED
│   │   ├── extract_baseline.py # Extracción con LLM
│   │   └── rules.py            # Reglas de clasificación
│   ├── geoparse/               # Geolocalización
│   │   ├── extract_locations.py
│   │   └── resolve_places.py   # Nominatim + Gazetteer
│   ├── db/                     # Base de datos
│   │   └── schema.py           # DDL de todas las tablas
│   ├── ops/                    # Operaciones
│   │   ├── runs.py             # Gestión de runs
│   │   └── alerts.py           # Alertas
│   └── utils/                  # Utilidades
│       ├── config.py
│       └── dq_checks.py        # Data quality
│
├── scripts/                    # Scripts ejecutables
│   ├── run_newsapi_ai_job.py   # ⭐ Runner principal
│   ├── run_location_candidates.py
│   ├── run_geo_resolve_incidents.py
│   ├── run_incidents_job.py
│   ├── build_fct_incidents.py
│   └── compute_run_quality_metrics.py
│
├── data/                       # Datos (no versionado)
│   ├── raw/newsapi_ai/         # JSON crudo
│   ├── interim/newsapi_ai/     # Parquet normalizado
│   └── osint_dw.duckdb         # Data warehouse
│
├── dashboards/streamlit/       # Visualización
│   └── app_basic.py
│
├── tests/                      # Tests
│   ├── test_config.py
│   ├── test_duckdb.py
│   └── integration/
│
├── docs/                       # Documentación
│   ├── README_GEO.md
│   ├── README_scripts.md
│   └── schema_duckdb.txt
│
└── _legacy/                    # Código archivado (no versionado)
```

## 🚀 Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd 2026_Peru

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy env.example .env
# Editar .env con tu API key de NewsAPI.ai
```

## 📖 Uso

### Ingesta diaria (comando principal)

```bash
# Ejecutar ingesta completa
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --date-start 2025-12-17 \
    --date-end 2025-12-18 \
    --max-total 200

# Solo ingesta (sin normalizar/cargar)
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --skip-normalize --skip-load --skip-dedupe

# Filtrar por prioridad
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --priority 1 2  # Solo grupos prioritarios
```

### Pipeline completo (Block H)

```bash
# Ejecuta: location_candidates → geo_resolve → incidents
python scripts/run_block_h_job.py --run-id 20251217235651
```

### Scripts individuales

```bash
# Geo-resolución de incidentes
python scripts/run_geo_resolve_incidents.py --run-id <RUN_ID>

# Extraer candidatos de lugares
python scripts/run_location_candidates.py --run-id <RUN_ID>

# Construir tabla de hechos
python scripts/build_fct_incidents.py
```

## 📊 Modelo de Datos (DuckDB)

### Tablas principales

| Tabla | Descripción |
|-------|-------------|
| `stg_news_newsapi_ai` | Noticias crudas de NewsAPI.ai |
| `stg_news_newsapi_ai_dedup` | Noticias deduplicadas |
| `stg_incidents_extracted` | Incidentes extraídos con LLM |
| `map_incident_place` | Mapeo incidente → lugar resuelto |
| `dim_places_pe` | Gazetteer de Perú |
| `fct_incidents` | Tabla de hechos de incidentes |
| `fct_incidents_curated` | Incidentes curados manualmente |

### Clasificación ACLED

Los incidentes se clasifican según taxonomía ACLED:
- **event_type**: Battles, Explosions, Protests, Riots, Violence against civilians, Strategic developments
- **sub_event_type**: 25 subtipos específicos
- **actor1/actor2**: Actores involucrados

## ⚙️ Configuración

### Scope YAML (config/newsapi_scope_peru.yaml)

```yaml
scope:
  name: peru_2026
  country: Peru
  source_locations:
    - "http://en.wikipedia.org/wiki/Peru"

concept_groups:
  elections:
    priority: 1
    acled_event_type: Strategic developments
    concepts:
      - "http://en.wikipedia.org/wiki/Elections_in_Peru"
    keywords:
      - elecciones peru 2026
      - candidato presidencial

  political_violence:
    priority: 1
    acled_event_type: Violence against civilians
    concepts:
      - "http://en.wikipedia.org/wiki/Political_violence"
    keywords:
      - violencia politica
      - atentado
```

### Variables de entorno (.env)

```bash
NEWSAPI_AI_KEY=your-api-key-here
DUCKDB_PATH=data/osint_dw.duckdb
LOG_LEVEL=INFO
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest tests/

# Tests específicos
pytest tests/test_config.py -v
pytest tests/integration/ -v

# Con cobertura
pytest --cov=src tests/
```

## 📈 Métricas de Calidad

```bash
# Ver métricas del último run
python scripts/compute_run_quality_metrics.py --run-id <RUN_ID>
```

Métricas incluidas:
- Artículos por grupo temático
- Tasa de deduplicación
- Cobertura geográfica
- Incidentes extraídos vs clasificados

## 🗓️ Ejecución Programada

### Windows Task Scheduler

```powershell
# Registrar tarea diaria a las 6:00 AM
.\scripts\register_newsapi_tasks.ps1
```

### Cron (Linux)

```bash
0 6 * * * cd /path/to/2026_Peru && .venv/bin/python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml
```

## 📝 Changelog

### v2.0.0 (2025-12-18)
- ✨ Multi-query ingestion con grupos temáticos
- ✨ Clasificación ACLED integrada
- ✨ Deduplicación cross-group y global
- 🔧 Consolidación de estructura del proyecto
- 📚 Documentación actualizada

## 📄 Licencia

Proyecto privado - Koru Analytics

## 👥 Contacto

- **Autor**: Carlos
- **Organización**: Koru Analytics
