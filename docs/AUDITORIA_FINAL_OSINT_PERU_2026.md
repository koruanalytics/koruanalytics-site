# 🔍 AUDITORÍA FINAL CONSOLIDADA - OSINT PERÚ 2026

**Fecha:** 2026-01-05  
**Versión:** 1.0  
**Propósito:** Documento de referencia para continuar desarrollo en chats independientes

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Evolución del Proyecto (Fases 0-4)](#2-evolución-del-proyecto)
3. [Estado Actual del Código](#3-estado-actual-del-código)
4. [Problema Central: Estrategia de Ingesta](#4-problema-central-estrategia-de-ingesta)
5. [Arquitectura de Datos](#5-arquitectura-de-datos)
6. [Paquetes de Trabajo Independientes](#6-paquetes-de-trabajo-independientes)
7. [Inventario de Archivos](#7-inventario-de-archivos)
8. [Stack Tecnológico](#8-stack-tecnológico)
9. [Configuración y Variables](#9-configuración-y-variables)

---

## 1. RESUMEN EJECUTIVO

### Qué es el proyecto
Sistema de monitoreo de incidentes de seguridad para las elecciones de Perú 2026. Pipeline automatizado que ingesta noticias de 7 medios peruanos, clasifica con LLM, y genera inteligencia sobre violencia, protestas, terrorismo y otros eventos relevantes.

### Estado actual
- ✅ **Arquitectura Medallion implementada** (Bronze → Silver → Gold)
- ✅ **Clasificación LLM funcionando** (Claude Haiku, 14 categorías)
- ⚠️ **Estrategia de ingesta rota** (v5 excede límite API de 15 keywords)
- ⚠️ **Dos pipelines coexisten** (legacy ACLED vs Medallion LLM)
- ⚠️ **Schema.py desactualizado** (no define tablas Medallion)

### Métricas del último run exitoso
| Métrica | Valor |
|---------|-------|
| Artículos procesados | 722 |
| Incidentes relevantes | 210 (29%) |
| Ruido filtrado | 512 (71%) |
| Muertos registrados | 408 |
| Heridos registrados | 2,046 |
| Costo LLM | ~$0.50 USD |

---

## 2. EVOLUCIÓN DEL PROYECTO

### Fase 0: Setup Inicial
- Arquitectura base con DuckDB
- Ingesta con location-based queries (6 artículos/día - muy bajo)
- Clasificación rule-based ACLED (90% ruido)

### Fase 2: Análisis de Cobertura API
- Diseño de estrategia de **12 grupos temáticos** para sortear límite de 15 keywords
- Cada grupo hace una query independiente con ≤15 keywords
- **Esta era la solución correcta** para el problema del API

### Fase 3: Arquitectura Medallion + LLM
- Cambio a **source_based** (7 fuentes peruanas): 6→650 artículos/día
- Implementación de clasificación con **Claude Haiku**: 90%→29% ruido
- Creación de **Bronze/Silver/Gold** tables
- Pipeline LLM funcionando correctamente
- **Problema:** source_based trae TODO, gastando tokens LLM en ruido

### Fase 4: Refinamiento (ROMPIÓ COSAS)
- Intento de crear v5 con source_keywords
- **ERROR:** v5 pone 38 keywords en una query (límite es 15)
- Tablas Bronze/Silver/Gold vaciadas durante pruebas
- Pipeline quedó en estado inconsistente

### Línea Temporal de Estrategias de Ingesta

```
v3: multi_query_by_group     ✅ FUNCIONABA
    └─ 7 grupos × ≤15 keywords cada uno = 7 queries al API
    └─ ~50-100 artículos relevantes/día
    └─ Respeta límite del API
    
v4: source_based             ⚠️ FUNCIONA PERO INEFICIENTE  
    └─ 1 query: 7 fuentes, SIN filtro de keywords
    └─ ~650 artículos/día (70% ruido)
    └─ Desperdicia tokens LLM en clasificar ruido
    
v5: source_keywords          ❌ ROTO
    └─ 1 query: 7 fuentes + 38 keywords
    └─ ERROR: excede límite de 15 keywords
    └─ 0 artículos
```

---

## 3. ESTADO ACTUAL DEL CÓDIGO

### Pipelines en Conflicto

| Pipeline | Entry Point | Tablas | Estado |
|----------|-------------|--------|--------|
| **Legacy (ACLED)** | `run_newsapi_ai_job.py` | stg_news_newsapi_ai → stg_incidents_extracted → fct_incidents | Obsoleto pero presente |
| **Medallion (LLM)** | `daily_pipeline.py` | bronze_news → silver_news_enriched → gold_incidents | Activo pero roto (v5) |

### Scripts Activos vs Obsoletos

**ACTIVOS (usar):**
```
scripts/core/daily_pipeline.py          # Pipeline principal Medallion
src/enrichment/llm_enrichment_pipeline.py   # Bronze→Silver→Gold
src/ingestion/newsapi_ai_ingest.py      # Ingestor (necesita fix)
src/processing/normalize_newsapi_ai.py  # JSON→Parquet
```

**OBSOLETOS (mover a _legacy):**
```
scripts/core/run_newsapi_ai_job.py      # Usa pipeline ACLED
src/processing/load_newsapi_ai_to_dw.py # Carga a stg_news (legacy)
src/processing/dedupe_newsapi_ai_in_duckdb.py  # Dedupe legacy
src/incidents/extract_baseline.py       # Extracción ACLED
src/incidents/acled_rules.py            # Clasificación rules
```

### Estado de Tablas en DuckDB

**Tablas Medallion (ACTIVAS):**
| Tabla | Estado | Rows (último conocido) |
|-------|--------|------------------------|
| bronze_news | ⚠️ Posiblemente vacía | 722 antes de fase 4 |
| silver_news_enriched | ⚠️ Posiblemente vacía | 722 antes de fase 4 |
| gold_incidents | ⚠️ Posiblemente vacía | 210 antes de fase 4 |
| gold_daily_stats | ⚠️ Posiblemente vacía | 31 antes de fase 4 |
| dim_places_pe | ✅ Intacta | 1,893 |

**Tablas Legacy (ELIMINAR):**
```
stg_news_newsapi_ai, stg_news_newsapi_ai_dedup, stg_news_newsapi_ai_dedup_run,
stg_incidents_extracted, fct_incidents, fct_incidents_curated,
fct_incident_places, map_incident_place, map_incident_place_v2,
stg_incident_place_candidates, curation_incident_overrides, incidents_test, stg_news_dummy
```

---

## 4. PROBLEMA CENTRAL: ESTRATEGIA DE INGESTA

### El Dilema
NewsAPI.ai tiene **límite de 15 keywords por query**. El proyecto necesita ~100 keywords para cubrir todas las categorías.

### Soluciones Intentadas

| Estrategia | Cómo funciona | Resultado |
|------------|---------------|-----------|
| **v3: multi_query_by_group** | 7 queries separadas, cada una con ≤15 keywords | ✅ Funciona, ~100 artículos relevantes/día |
| **v4: source_based** | 1 query con 7 fuentes, sin keywords | ⚠️ Funciona pero trae 650 artículos (70% ruido) |
| **v5: source_keywords** | 1 query con fuentes + todos los keywords | ❌ Rompe API (>15 keywords) |

### Solución Recomendada: Híbrido v3+v5

```yaml
# Propuesta: source_keywords POR GRUPO
strategy: source_keywords_by_group

groups:
  - group_id: violencia
    source_uris: [elcomercio.pe, larepublica.pe, ...]
    keywords: [asesinato, homicidio, sicariato, ...]  # ≤15
    
  - group_id: electoral  
    source_uris: [elcomercio.pe, larepublica.pe, ...]
    keywords: [elecciones, candidato, JNE, ONPE, ...]  # ≤15
    
  # ... 5-7 grupos más
```

**Beneficios:**
- ✅ Respeta límite de 15 keywords por query
- ✅ Filtra en ingesta (menos tokens LLM)
- ✅ Cobertura completa de temas
- ✅ Combina lo mejor de v3 y v5

---

## 5. ARQUITECTURA DE DATOS

### Flujo Correcto (Medallion)

```
NewsAPI.ai
    ↓ [7 queries por grupo temático]
data/raw/*.json
    ↓ [normalize_newsapi_ai.py]
data/interim/*.parquet
    ↓ [load_to_bronze_with_dedupe]
bronze_news (DuckDB)
    ↓ [llm_enrichment_pipeline.py + Claude Haiku]
silver_news_enriched (DuckDB)
    ↓ [build_gold_incidents - filtros de calidad]
gold_incidents + gold_daily_stats (DuckDB)
```

### Esquema de Tablas Medallion

**bronze_news:**
- incident_id, title, body, url, published_at
- source, source_title, language
- ingest_run_id, retrieved_at

**silver_news_enriched:**
- bronze_id (FK), es_relevante, es_internacional, es_resumen
- tipo_evento, subtipo, muertos, heridos
- departamento, provincia, distrito
- resumen_es, resumen_en, sentiment, confianza
- modelo_llm, tokens_usados, processed_at

**gold_incidents:**
- incident_id, bronze_id, fecha_incidente
- tipo_evento, subtipo, muertos, heridos
- departamento, provincia, distrito, lat, lon
- titulo, resumen, source_name, url
- created_at

---

## 6. PAQUETES DE TRABAJO INDEPENDIENTES

### 📦 PAQUETE 1: Restaurar Estrategia de Ingesta
**Prioridad:** 🔴 CRÍTICA  
**Estimación:** 2-3 horas  
**Dependencias:** Ninguna

**Tareas:**
1. Crear/restaurar estrategia `source_keywords_by_group` en `newsapi_ai_ingest.py`
2. Crear `newsapi_scope_peru_v6.yaml` con grupos + keywords (≤15 por grupo)
3. Actualizar `daily_pipeline.py` para usar v6
4. Testear ingesta de 1 día

**Archivos a modificar:**
- `src/ingestion/newsapi_ai_ingest.py`
- `config/newsapi_scope_peru_v6.yaml` (nuevo)
- `scripts/core/daily_pipeline.py`

**Criterio de éxito:**
- Ingesta ejecuta sin errores
- ~50-150 artículos por día
- Cada query usa ≤15 keywords

---

### 📦 PAQUETE 2: Consolidar Schema y Limpiar BD
**Prioridad:** 🟡 ALTA  
**Estimación:** 1-2 horas  
**Dependencias:** Ninguna (puede ir en paralelo con P1)

**Tareas:**
1. Añadir DDLs de tablas Medallion a `src/db/schema.py`
2. Crear script `init_medallion_tables.py`
3. Eliminar tablas legacy de la BD
4. Documentar schema final

**Archivos a modificar:**
- `src/db/schema.py`
- `scripts/utils/init_medallion_tables.py` (nuevo)

**Criterio de éxito:**
- Schema.py es fuente única de verdad
- BD solo tiene tablas activas
- Script de inicialización funciona

---

### 📦 PAQUETE 3: Limpiar Código Legacy
**Prioridad:** 🟡 ALTA  
**Estimación:** 1 hora  
**Dependencias:** P1, P2 completados

**Tareas:**
1. Mover scripts obsoletos a `scripts/_legacy/`
2. Mover módulos obsoletos a `src/_legacy/`
3. Actualizar imports si hay dependencias
4. Verificar que pipeline sigue funcionando

**Archivos a mover:**
```
→ scripts/_legacy/:
  - run_newsapi_ai_job.py
  - build_fct_incidents.py
  - run_incident_extract.py

→ src/_legacy/:
  - processing/load_newsapi_ai_to_dw.py
  - processing/dedupe_newsapi_ai_in_duckdb.py
  - incidents/extract_baseline.py
  - incidents/acled_rules.py
```

---

### 📦 PAQUETE 4: Fix Pipeline LLM
**Prioridad:** 🟡 ALTA  
**Estimación:** 1-2 horas  
**Dependencias:** P1 completado

**Tareas:**
1. Verificar/corregir INSERT en `llm_enrichment_pipeline.py` vs esquema silver
2. Añadir validación para evitar `no_relevante` en gold
3. Mejorar detección de artículos de resumen
4. Testear procesamiento de 100 artículos

**Archivos a modificar:**
- `src/enrichment/llm_enrichment_pipeline.py`

**Criterio de éxito:**
- INSERT alineado con esquema
- 0 registros `no_relevante` en gold
- Artículos de resumen marcados correctamente

---

### 📦 PAQUETE 5: Re-ingesta Histórica
**Prioridad:** 🟢 MEDIA  
**Estimación:** 2-4 horas (incluye tiempo de ejecución)  
**Dependencias:** P1, P4 completados

**Tareas:**
1. Vaciar tablas Medallion (backup primero)
2. Ingestar desde 2025-12-15 hasta hoy
3. Procesar con LLM
4. Validar calidad de datos

**Comandos:**
```powershell
# Backup
Copy-Item data/osint_dw.duckdb data/osint_dw_backup_pre_reingesta.duckdb

# Vaciar
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); [con.execute(f'DELETE FROM {t}') for t in ['gold_daily_stats','gold_incidents','silver_news_enriched','bronze_news']]"

# Ingestar
python -m scripts.core.daily_pipeline --full --date-start 2025-12-15 --date-end 2026-01-05
```

---

### 📦 PAQUETE 6: Optimizar venv
**Prioridad:** 🟢 BAJA  
**Estimación:** 30 min  
**Dependencias:** Ninguna

**Problema:** venv pesa 1.7GB con paquetes innecesarios (torch, spacy, transformers)

**Tareas:**
1. Generar `requirements-minimal.txt`
2. Documentar paquetes necesarios vs innecesarios
3. (Opcional) Recrear venv limpio

**Paquetes a eliminar:**
- torch (432MB) - No usado, clasificación es via API
- spacy (85MB) - No usado
- transformers (87MB) - No usado
- sympy (66MB) - No usado

**Paquetes necesarios:**
- anthropic, duckdb, pandas, pyarrow, loguru
- pyyaml, python-dotenv, eventregistry
- requests

---

### 📦 PAQUETE 7: Migración Azure (Futuro)
**Prioridad:** ⚪ FUTURA  
**Estimación:** 1-2 días  
**Dependencias:** P1-P5 completados, pipeline estable

**Tareas:**
1. Containerizar con Docker
2. Migrar DuckDB → Azure PostgreSQL
3. Configurar Azure Functions para ejecución diaria
4. Configurar Azure AI Search para RAG
5. Configurar monitoreo

---

## 7. INVENTARIO DE ARCHIVOS

### Configuración
| Archivo | Estado | Notas |
|---------|--------|-------|
| `config/newsapi_scope_peru_v3.yaml` | ✅ Referencia | Estrategia multi-grupo correcta |
| `config/newsapi_scope_peru_v4.yaml` | ⚠️ Funciona | Source-based (trae todo) |
| `config/newsapi_scope_peru_v5.yaml` | ❌ Roto | Excede 15 keywords |
| `config/settings.yaml` | ✅ OK | Configuración general |
| `.env` | ✅ Requerido | ANTHROPIC_API_KEY, NEWSAPI_KEY |

### Scripts Core
| Archivo | Estado | Función |
|---------|--------|---------|
| `scripts/core/daily_pipeline.py` | ⚠️ Fix scope | Pipeline principal |
| `scripts/core/run_newsapi_ai_job.py` | ❌ Legacy | Mover a _legacy |

### Módulos Src
| Archivo | Estado | Función |
|---------|--------|---------|
| `src/ingestion/newsapi_ai_ingest.py` | ⚠️ Fix estrategia | Ingestor |
| `src/enrichment/llm_enrichment_pipeline.py` | ⚠️ Fix INSERT | Pipeline LLM |
| `src/classification/llm_classifier.py` | ✅ OK | Clasificador standalone |
| `src/processing/normalize_newsapi_ai.py` | ✅ OK | Normalización |
| `src/db/schema.py` | ⚠️ Incompleto | Añadir Medallion DDLs |

---

## 8. STACK TECNOLÓGICO

| Categoría | Tecnología | Versión/Notas |
|-----------|------------|---------------|
| Lenguaje | Python | 3.12 |
| Base de datos | DuckDB | Arquitectura Medallion |
| LLM | Claude Haiku | claude-3-5-haiku-20241022 |
| API Noticias | NewsAPI.ai | EventRegistry client |
| Logging | loguru | Timestamps, rotation |
| Config | pyyaml, python-dotenv | .env + YAML |
| Cloud (futuro) | Azure | Functions, PostgreSQL, AI Search |
| IDE | VS Code | - |
| OS | Windows 10/11 | Task Scheduler para automation |

---

## 9. CONFIGURACIÓN Y VARIABLES

### Variables de Entorno (.env)
```bash
# Requeridas
ANTHROPIC_API_KEY=sk-ant-api03-...
NEWSAPI_KEY=...                    # También: NEWSAPI_AI_KEY

# Opcionales (futuro Azure)
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_KEY=xxx
AZURE_STORAGE_CONNECTION_STRING=xxx
```

### Paths Importantes
```
data/osint_dw.duckdb              # BD principal
data/raw/newsapi_ai/              # JSONs crudos
data/interim/newsapi_ai/          # Parquets normalizados
config/geo/peru_gazetteer_full.csv # Gazetteer
logs/newsapi_ai/                  # Logs de ejecución
```

### Límites del API
| Límite | Valor | Notas |
|--------|-------|-------|
| Keywords por query | **15** | CRÍTICO - causa del problema v5 |
| Artículos por query | ~100-500 | Depende del plan |

---

## 📌 PROMPT PARA INICIAR CHAT DE DESARROLLO

```
Continúo el proyecto "OSINT Perú 2026".

Stack: Python 3.12 + DuckDB + Claude Haiku + NewsAPI.ai
IDE: VS Code

CONTEXTO:
- Sistema de monitoreo de incidentes de seguridad para elecciones Perú 2026
- Arquitectura Medallion (Bronze → Silver → Gold) con clasificación LLM
- El proyecto tiene código funcional pero necesita reparaciones

PROBLEMA PRINCIPAL:
La estrategia de ingesta está rota. NewsAPI.ai tiene límite de 15 keywords/query.
- v3 (multi_query_by_group) funcionaba con 7 grupos × ≤15 keywords
- v5 (source_keywords) pone 38 keywords en 1 query → ERROR

PAQUETE DE TRABAJO: [ESPECIFICAR CUAL]

Adjunto: AUDITORIA_FINAL_OSINT_PERU_2026.md

¿Empezamos?
```

---

*Documento generado: 2026-01-05*  
*Auditoría realizada sobre: ZIP del proyecto + documentos de cierre Fases 0-4*
