# OSINT Framework - Diseño y Validación

## 📋 Análisis de Estructura Actual

### Componentes Genéricos (Reutilizables)

#### ✅ Core de Pipeline
- **`src/ingestion/newsapi_ai_ingest.py`**: Cliente genérico NewsAPI.ai
  - ✅ Genérico (solo lee scope YAML, no hardcodea país)
  - ⚠️ Necesita: scope YAML parametrizable por misión

- **`src/processing/normalize_newsapi_ai.py`**: Normalización genérica
  - ✅ Genérico (transforma JSON → Parquet)
  - ✅ Usa `normalize_unicode` (genérico)

- **`src/enrichment/llm_enrichment_pipeline.py`**: Pipeline LLM genérico
  - ⚠️ Parcialmente genérico
  - ❌ Hardcodea: patrones Perú, "Perú" en prompts, `pais_evento DEFAULT 'Perú'`
  - ✅ Genérico: arquitectura Medallion, flujo Bronze→Silver→Gold

- **`src/db/schema.py`**: Schema Medallion
  - ✅ Genérico (solo estructura de tablas)
  - ⚠️ Algunos campos tienen defaults específicos (`pais_evento DEFAULT 'Perú'`)

- **`src/llm_providers/`**: Abstracción LLM
  - ✅ Completamente genérico (multi-proveedor)

- **`src/utils/`**: Utilidades
  - ✅ `text_utils.py`: Genérico
  - ✅ `config.py`: Genérico (lee YAML)
  - ✅ `time.py`: Genérico (si se crea)

#### ⚠️ Componentes Específicos de Perú (Necesitan Parametrización)

- **`src/llm_providers/prompts.py`**:
  - ❌ Hardcodea: "Perú", lista de departamentos, patrones de exclusión
  - ✅ Genérico: estructura de prompt, taxonomía ACLED

- **`src/classification/llm_classifier.py`**:
  - ❌ Hardcodea: `DEPARTAMENTOS_PERU`, prompt con "Perú"
  - ✅ Genérico: lógica de clasificación

- **`src/enrichment/geocoding_service.py`**:
  - ❌ Hardcodea: `gazetteer_path = "config/geo/peru_gazetteer_full.csv"`
  - ✅ Genérico: lógica de geocoding

- **`src/geoparse/extract_locations.py`**:
  - ❌ Hardcodea: patrones de exclusión con países vecinos, palabras españolas
  - ✅ Genérico: extracción de ubicaciones

- **`config/newsapi_scope_peru_v*.yaml`**:
  - ❌ Específico de Perú (keywords, sources, grupos temáticos)

- **`config/geo/peru_gazetteer_full.csv`**:
  - ❌ Específico de Perú

### Scripts de Ejecución

- **`scripts/core/daily_pipeline.py`**: Entrypoint principal
  - ⚠️ Hardcodea: `DB_PATH`, `SCOPE_PATH`, `RAW_DIR`, `INTERIM_DIR`
  - ✅ Genérico: lógica de orquestación

- **`scripts/utils/init_medallion_tables.py`**: Inicialización
  - ✅ Genérico (solo ejecuta DDLs)

## 🎯 Arquitectura Propuesta: OSINT Framework

### Estructura de Directorios

```
osint_framework/                    # Repo principal (framework)
├── osint_core/                     # Core genérico (paquete Python)
│   ├── ingestion/
│   │   └── newsapi_ai.py          # Cliente NewsAPI.ai genérico
│   ├── processing/
│   │   └── normalize.py           # Normalización genérica
│   ├── enrichment/
│   │   ├── llm_pipeline.py        # Pipeline LLM (sin hardcodes)
│   │   └── geocoding.py           # Geocoding genérico
│   ├── db/
│   │   ├── schema.py              # DDLs Medallion genéricos
│   │   └── queries.py             # Queries reutilizables
│   ├── pipelines/
│   │   └── daily_pipeline.py      # Orquestador genérico
│   ├── llm_providers/             # Abstracción LLM (ya genérico)
│   ├── utils/
│   │   ├── config.py              # Carga de config genérica
│   │   ├── time.py                # Helpers de tiempo
│   │   └── text_utils.py          # Normalización texto
│   └── mission/                   # Sistema de configuración por misión
│       ├── config.py              # MissionConfig loader
│       └── templates/             # Templates de prompts/configs
│
├── missions/                      # Configuraciones por misión
│   ├── peru_2026/                 # Misión Perú 2026
│   │   ├── mission.yaml           # País, periodo, contexto
│   │   ├── incident_types.yaml    # Taxonomía de incidentes
│   │   ├── keywords.yaml          # Keywords por grupo
│   │   ├── sources.yaml           # Fuentes de noticias
│   │   ├── gazetteer/             # Gazetteer del país
│   │   │   └── gazetteer.csv
│   │   └── prompts/               # Overrides de prompts (opcional)
│   │
│   ├── template/                  # Template para nuevas misiones
│   │   ├── mission.yaml.template
│   │   ├── incident_types.yaml.template
│   │   ├── keywords.yaml.template
│   │   └── README.md
│   │
│   └── colombia_2027/             # Ejemplo: Nueva misión
│       └── ...
│
├── scripts/                       # Scripts de ejecución
│   ├── init_mission.py            # Crear nueva misión
│   ├── run_pipeline.py            # Ejecutar pipeline con misión
│   └── utils/                     # Utilidades
│       ├── init_tables.py
│       └── export_data.py
│
├── tests/                         # Tests genéricos
├── docs/                          # Documentación
├── pyproject.toml                  # Package config
├── setup.py                        # Setup para pip install
└── README.md
```

## 🔧 Cambios Necesarios para Hacerlo Genérico

### 1. Sistema de Configuración por Misión

**Crear**: `osint_core/mission/config.py`

```python
class MissionConfig:
    """Carga y expone configuración de una misión OSINT."""
    
    def __init__(self, mission_path: Path):
        self.mission_path = mission_path
        self.mission = self._load_yaml("mission.yaml")
        self.incident_types = self._load_yaml("incident_types.yaml")
        self.keywords = self._load_yaml("keywords.yaml")
        self.sources = self._load_yaml("sources.yaml")
    
    @property
    def country(self) -> str:
        return self.mission["mission"]["country"]
    
    @property
    def gazetteer_path(self) -> Path:
        return self.mission_path / "gazetteer" / "gazetteer.csv"
```

### 2. Prompts Dinámicos

**Modificar**: `osint_core/llm_providers/prompts.py`

- Remover hardcodes de "Perú"
- Usar templates con placeholders
- Cargar desde `MissionConfig`

### 3. Geocoding Configurable

**Modificar**: `osint_core/enrichment/geocoding.py`

- Recibir `gazetteer_path` desde `MissionConfig`
- No hardcodear ruta

### 4. Pipeline Parametrizado

**Modificar**: `osint_core/pipelines/daily_pipeline.py`

- Recibir `MissionConfig` como parámetro
- Cargar paths desde config, no hardcodeados

## 📦 Plan de Extracción

### Fase 1: Crear Estructura Base
1. Crear nuevo repo `osint_framework`
2. Copiar código genérico a `osint_core/`
3. Remover hardcodes de Perú

### Fase 2: Sistema de Misiones
1. Crear `MissionConfig`
2. Extraer configs de Perú a `missions/peru_2026/`
3. Crear templates

### Fase 3: Scripts de Inicialización
1. `init_mission.py`: Crear nueva misión
2. `run_pipeline.py`: Ejecutar con misión específica

### Fase 4: Documentación y Testing
1. README con ejemplos
2. Tests genéricos
3. Guía de migración desde repo Perú
