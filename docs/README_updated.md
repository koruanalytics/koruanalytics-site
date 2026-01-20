# OSINT Peru 2026 - Electoral Monitoring Pipeline

Sistema de monitoreo OSINT para las elecciones de Perú 2026. Ingesta, procesa y clasifica noticias de fuentes abiertas para detectar incidentes de violencia política, protestas, crimen organizado y otros eventos relevantes.

## 🎯 Objetivo

Monitorear el entorno de seguridad electoral en Perú mediante:
- Ingesta automatizada de noticias (NewsAPI.ai)
- Clasificación ACLED de incidentes
- Geo-parsing a nivel distrito
- Generación de reportes diarios

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OSINT Pipeline v2                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ NewsAPI  │──▶│ Normalize │──▶│  DuckDB  │──▶│ Daily Report   │  │
│  │   .ai    │   │ (Parquet) │   │   DW     │   │   (Excel)      │  │
│  └──────────┘   └───────────┘   └──────────┘   └────────────────┘  │
│       │                              │                              │
│       │                              ▼                              │
│       │         ┌─────────────────────────────────┐                │
│       │         │     stg_news_newsapi_ai         │                │
│       │         │     stg_news_newsapi_ai_dedup   │                │
│       │         │     stg_incidents_extracted     │                │
│       │         │     fct_incidents               │                │
│       │         │     fct_daily_report  ◀── NEW   │                │
│       │         │     dim_places_pe               │                │
│       │         └─────────────────────────────────┘                │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ API Enrichment Fields (Fase 1):                              │  │
│  │ • source_title (El Comercio, RPP)                            │  │
│  │ • api_category (Politics, Crime)                             │  │
│  │ • api_location (Lima, Arequipa)                              │  │
│  │ • concept_labels (entidades: personas, orgs, lugares)        │  │
│  │ • is_duplicate                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 Estructura del Proyecto

```
2026_Peru/
├── config/
│   ├── settings.yaml              # Configuración general
│   └── newsapi_scope_peru.yaml    # Scope de búsqueda (12 grupos temáticos)
├── data/
│   ├── raw/newsapi_ai/            # JSON crudo del API
│   ├── interim/newsapi_ai/        # Parquet normalizado
│   ├── osint_dw.duckdb            # Data Warehouse
│   └── daily_report.xlsx          # Reporte exportado
├── scripts/
│   ├── run_newsapi_ai_job.py      # Pipeline principal
│   ├── build_fct_daily_report.py  # Genera reportes diarios
│   ├── run_incident_extract_baseline.py
│   └── migrate_add_api_fields.py  # Migración de BD
├── src/
│   ├── ingestion/                 # Ingesta de NewsAPI.ai
│   ├── processing/                # Normalización, carga, dedupe
│   ├── incidents/                 # Extracción y clasificación ACLED
│   ├── geo/                       # Geo-parsing
│   └── db/                        # Schema y DDL
└── docs/
    └── ARCHITECTURE.md
```

## 🚀 Quickstart

### 1. Instalar dependencias

```powershell
pip install -r requirements.txt
pip install sumy openpyxl
python -c "import nltk; nltk.download('punkt')"
```

### 2. Configurar API key

```powershell
# En config/settings.yaml o variable de entorno
$env:NEWSAPI_AI_KEY = "tu-api-key"
```

### 3. Ejecutar pipeline completo

```powershell
# Ingesta + Normalización + Dedupe + Extracción de incidentes
python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --date-start 2025-12-18 --max-total 50
```

### 4. Generar reporte diario

```powershell
# Construir fct_daily_report con resúmenes
python scripts/build_fct_daily_report.py --days 7
```

### 5. Exportar a Excel

```powershell
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); df=con.execute('SELECT * FROM fct_daily_report ORDER BY incident_date DESC').fetchdf(); df.to_excel('data/daily_report.xlsx', index=False); print(f'Exportado: {len(df)} filas')"
```

## 📊 Tablas Principales

### `stg_incidents_extracted`

Incidentes extraídos con clasificación ACLED y campos del API.

| Campo | Descripción |
|-------|-------------|
| incident_id | ID único (SHA1 del URI) |
| incident_type | Tipo ACLED (6 tipos) |
| sub_event_type | Subtipo ACLED (25 tipos) |
| disorder_type | political_violence, demonstrations, strategic_developments |
| source_title | Nombre del medio (El Comercio, RPP) |
| api_category | Categoría del API (Politics, Crime) |
| api_location | Ubicación detectada por API |
| concept_labels | Entidades: "Keiko Fujimori; JNE; Lima" |
| adm1, adm2, adm3 | Departamento, Provincia, Distrito |
| lat, lon | Coordenadas |

### `fct_daily_report`

Tabla optimizada para reportes diarios con resúmenes automáticos.

| Campo | Descripción |
|-------|-------------|
| incident_date | Fecha del incidente |
| source_title | Nombre del medio |
| location_display | "Miraflores, Lima, Lima" |
| event_type | Tipo ACLED |
| title | Título del artículo |
| summary_es | Resumen en español (2 oraciones, sumy LSA) |
| url | Link al artículo original |
| concept_labels | Entidades mencionadas |

## 🔍 Clasificación ACLED

El sistema clasifica incidentes según la metodología ACLED:

### Tipos de Evento (6)
- `battles` - Enfrentamientos armados
- `explosions_remote_violence` - Explosiones, ataques remotos
- `violence_against_civilians` - Asesinatos, secuestros
- `protests` - Manifestaciones pacíficas
- `riots` - Disturbios, vandalismo
- `strategic_developments` - Arrestos, acuerdos

### Tipos de Desorden (3)
- `political_violence` - Violencia política
- `demonstrations` - Protestas y manifestaciones
- `strategic_developments` - Desarrollos estratégicos

## 📋 Grupos Temáticos (Scope)

El archivo `newsapi_scope_peru.yaml` define 12 grupos de búsqueda:

| Grupo | Prioridad | Descripción |
|-------|-----------|-------------|
| elections | 1 | Elecciones, JNE, ONPE, candidatos |
| political_violence | 1 | Asesinatos políticos, amenazas |
| protests | 1 | Marchas, manifestaciones |
| terrorism | 1 | Sendero Luminoso, VRAEM |
| organized_crime | 2 | Narcotráfico, extorsión |
| security_forces | 2 | PNP, FFAA, operativos |
| violent_crimes | 2 | Homicidios, sicariato |
| infrastructure | 2 | Bloqueos, sabotaje |
| explosions | 3 | Bombas, atentados |
| disasters | 3 | Emergencias, desastres |
| accidents | 3 | Accidentes de tránsito |
| health | 3 | Epidemias, salud pública |

## 🛠️ Comandos Útiles

```powershell
# Pipeline con fechas específicas
python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --date-start 2025-12-01 --date-end 2025-12-15 --max-total 100

# Solo grupos prioritarios
python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml --priority 1 2 --max-total 50

# Reconstruir todos los reportes
python scripts/build_fct_daily_report.py --rebuild-all

# Reporte de una fecha específica
python scripts/build_fct_daily_report.py --date 2025-12-18

# Ver estadísticas de la BD
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT table_name, estimated_size FROM duckdb_tables()').fetchdf())"
```

## 📈 Métricas del Pipeline

El job muestra métricas al finalizar:

```
[JOB] COMPLETE: run_id=20251219125550 ingested=13 new=2 incidents=2
[JOB] Enrichment: source_title=2/2, category=0/2, location=2/2, concepts=2/2
```

- `ingested`: Artículos descargados
- `new`: Artículos nuevos (no duplicados históricos)
- `incidents`: Incidentes extraídos
- `Enrichment`: Cobertura de campos del API

## 🗓️ Changelog

### Fase 2 (2025-12-19)
- ✅ `fct_daily_report` con resúmenes automáticos (sumy LSA)
- ✅ Exportación a Excel
- ✅ Soporte para `--days`, `--date`, `--rebuild-all`

### Fase 1 (2025-12-18)
- ✅ Campos de enriquecimiento del API (source_title, api_category, concept_labels, etc.)
- ✅ Fix dedupe: crear `_dedup` (global) y `_dedup_run` (por run)
- ✅ Extracción de incidentes integrada en pipeline principal
- ✅ Quality checks mejorados

## 📄 Licencia

Proyecto interno - Koru Analytics

## 👥 Contacto

- Proyecto: OSINT Peru 2026
- Organización: Koru Analytics
