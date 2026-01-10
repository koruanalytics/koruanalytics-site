# Acción de Cierre de Chat del Proyecto: OSINT Perú 2026

## Metadatos del Chat
| Campo | Valor |
|-------|-------|
| **Nombre del proyecto** | OSINT Perú 2026 - Sistema de Monitoreo de Incidentes de Seguridad |
| **Fecha de inicio del chat** | 2026-01-03 |
| **Fecha de cierre** | 2026-01-04 |
| **Duración estimada** | 1 sesión extensa (~4 horas) |
| **Chat ID/Referencia** | refinamiento_backend_1 |

---

## 1. RESUMEN EJECUTIVO

Sistema de monitoreo de incidentes de seguridad para las elecciones de Perú 2026. Pipeline de ingesta desde NewsAPI.ai con clasificación mediante Claude Haiku. Esta sesión implementó la arquitectura Medallion completa (Bronze→Silver→Gold), procesó 722 artículos y extrajo 210 incidentes relevantes de seguridad, filtrando 71% de ruido (farándula, deportes, economía).

---

## 2. STACK TECNOLÓGICO

| Categoría | Tecnología | Versión |
|-----------|------------|---------|
| Lenguaje | Python | 3.12 |
| Base de datos | DuckDB | Latest |
| LLM | Claude Haiku (Anthropic) | claude-3-5-haiku-20241022 |
| API de noticias | NewsAPI.ai | v1 |
| Cloud (futuro) | Azure (Functions, PostgreSQL, AI Search) | - |
| IDE | VS Code | - |
| Dependencias | anthropic, duckdb, pandas, loguru, pyyaml, python-dotenv | - |

---

## 3. ESTRUCTURA DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── newsapi_scope_peru_v4.yaml    # Scope activo (7 fuentes)
│   ├── settings.yaml                  # Configuración general
│   └── geo/                           # Configuraciones geo
├── src/
│   ├── ingestion/
│   │   └── newsapi_ai_ingest.py      # Ingestor multi-estrategia
│   ├── processing/
│   │   ├── normalize_newsapi_ai.py
│   │   └── dedupe_newsapi_ai_in_duckdb.py
│   ├── enrichment/                    # NUEVO
│   │   └── llm_enrichment_pipeline.py # Pipeline Bronze→Silver→Gold
│   ├── classification/                # NUEVO
│   │   └── llm_classifier.py          # Clasificador LLM standalone
│   ├── incidents/
│   │   └── acled_rules.py             # Reglas ACLED (legacy)
│   ├── geoparse/
│   ├── nlp/
│   ├── ops/
│   ├── pipelines/
│   ├── models/
│   └── utils/
├── scripts/
│   ├── core/                          # Pipeline principal
│   │   ├── daily_pipeline.py          # NUEVO - Pipeline unificado
│   │   ├── run_newsapi_ai_job.py
│   │   ├── build_fct_daily_report.py
│   │   ├── extract_casualties.py
│   │   ├── extract_sentiment.py
│   │   ├── generate_alerts.py
│   │   └── scheduled_run_newsapi_ai_job.ps1
│   ├── geo/                           # Gazetteer
│   │   ├── build_peru_gazetteer.py
│   │   ├── load_gazetteer_pe.py
│   │   └── validate_gazetteer_*.py
│   ├── utils/                         # Utilidades
│   │   ├── dump_duckdb_schema.py
│   │   ├── compute_run_quality_metrics.py
│   │   ├── get_latest_run_id.py
│   │   └── init_ops_tables.py
│   └── _legacy/                       # Scripts obsoletos (~35 archivos)
├── data/
│   ├── osint_dw.duckdb                # Base de datos principal
│   ├── osint_dw_backup_20260103.duckdb
│   ├── raw/newsapi_ai/
│   ├── interim/
│   └── processed/
├── _legacy/
│   └── config/                        # Scopes obsoletos (v2, v3)
└── .env                               # API keys
```

---

## 4. ARCHIVOS CLAVE Y SU ESTADO

| Archivo | Estado | Descripción | Última modificación |
|---------|--------|-------------|---------------------|
| `src/enrichment/llm_enrichment_pipeline.py` | ✅ Completo | Pipeline LLM Bronze→Silver→Gold | 2026-01-04 |
| `src/classification/llm_classifier.py` | ✅ Completo | Clasificador standalone con 14 categorías | 2026-01-03 |
| `scripts/core/daily_pipeline.py` | ✅ Completo | Pipeline diario unificado (ingesta+LLM+alertas) | 2026-01-04 |
| `config/newsapi_scope_peru_v4.yaml` | ✅ Completo | Scope con 7 fuentes peruanas (source_based) | 2026-01-03 |
| `src/ingestion/newsapi_ai_ingest.py` | ✅ Completo | Ingestor con soporte source_based y location_based | 2026-01-03 |
| `data/osint_dw.duckdb` | ✅ Completo | BD con arquitectura Medallion | 2026-01-04 |

**Leyenda:** ✅ Completo | 🔄 En progreso | ❌ Pendiente | ⚠️ Requiere revisión

---

## 5. FUNCIONALIDADES IMPLEMENTADAS

### Completadas
- [x] **Arquitectura Medallion** - bronze_news → silver_news_enriched → gold_incidents
- [x] **Pipeline LLM** - Clasificación con Claude Haiku (14 categorías)
- [x] **Extracción de víctimas** - muertos/heridos desde texto
- [x] **Geolocalización** - Departamento/provincia/distrito desde texto
- [x] **Generación de resúmenes** - Español e inglés
- [x] **Análisis de sentimiento** - POS/NEG/NEU
- [x] **Dedupe mejorado** - Por primeros 100 chars del título
- [x] **Estadísticas diarias** - gold_daily_stats agregadas
- [x] **Reorganización scripts** - core/, geo/, utils/, _legacy/

### Pendientes
- [ ] **Limpiar registros no_relevante** - 3 registros en gold que no deberían estar
- [ ] **Mejorar geolocalización** - 13 incidentes sin departamento
- [ ] **Detectar artículos agregados** - Resúmenes anuales inflando estadísticas
- [ ] **Migración Azure** - PostgreSQL, Functions, Container Apps
- [ ] **Automatización diaria** - Task Scheduler / Azure Functions

---

## 6. CONFIGURACIÓN Y VARIABLES DE ENTORNO

```bash
# Variables requeridas (.env)
ANTHROPIC_API_KEY=sk-ant-api03-...
NEWSAPI_KEY=your_newsapi_ai_key

# Variables opcionales (futuro Azure)
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_KEY=xxx
AZURE_STORAGE_CONNECTION_STRING=xxx
```

**Archivos de configuración:**
| Archivo | Propósito | Notas |
|---------|-----------|-------|
| `.env` | API keys | No commitear |
| `config/settings.yaml` | Configuración general | Paths, parámetros |
| `config/newsapi_scope_peru_v4.yaml` | Scope de ingesta | 7 fuentes peruanas |

---

## 7. DECISIONES TÉCNICAS TOMADAS

| # | Decisión | Razón | Alternativa descartada |
|---|----------|-------|------------------------|
| 1 | Arquitectura Medallion (Bronze/Silver/Gold) | Separación clara de capas, re-procesamiento fácil | Tabla única monolítica |
| 2 | Claude Haiku para clasificación | Mejor seguimiento de instrucciones, JSON consistente | GPT-4o-mini, reglas ACLED |
| 3 | Estrategia source_based para ingesta | 27x más volumen que location_based | location_based + keywords |
| 4 | DuckDB local | Rápido, sin setup, portable | PostgreSQL local |
| 5 | Dedupe por título (100 chars) | Robusto ante URLs duplicadas/faltantes | Dedupe por URI |
| 6 | 14 categorías de eventos | Cobertura completa para OSINT electoral | Categorías ACLED estándar |

---

## 8. PROBLEMAS RESUELTOS

### [P1] Bajo volumen de artículos (6/día)
- **Síntoma:** Solo 6 artículos/día con estrategia locationUri
- **Causa raíz:** NewsAPI.ai indexa pocas noticias con locationUri="Peru"
- **Solución aplicada:** Cambiar a estrategia source_based con 7 fuentes específicas
- **Archivos afectados:** `newsapi_scope_peru_v4.yaml`, `newsapi_ai_ingest.py`
- **Resultado:** 650+ artículos/día (27x mejora)

### [P2] 79% de ruido en clasificación
- **Síntoma:** La mayoría de artículos clasificados como "other" (farándula, deportes)
- **Causa raíz:** Reglas ACLED demasiado permisivas
- **Solución aplicada:** Clasificador LLM con filtro de relevancia
- **Archivos afectados:** `llm_classifier.py`, `llm_enrichment_pipeline.py`
- **Resultado:** 71% filtrado como no_relevante, 210 incidentes genuinos

### [P3] 44% de duplicados en bronze
- **Síntoma:** 1,298 registros con 576 duplicados
- **Causa raíz:** Mismo artículo de múltiples fuentes, dedupe por URI fallaba
- **Solución aplicada:** Dedupe por primeros 100 chars del título normalizado
- **Archivos afectados:** `dedupe_newsapi_ai_in_duckdb.py`
- **Resultado:** 722 artículos únicos

---

## 9. PROBLEMAS CONOCIDOS / DEUDA TÉCNICA

| # | Problema | Impacto | Solución propuesta | Prioridad |
|---|----------|---------|-------------------|-----------|
| 1 | 3 registros `no_relevante` en gold | Bajo | DELETE WHERE tipo_evento='no_relevante' | Alta |
| 2 | 13 incidentes sin departamento | Medio | Mejorar prompt o post-procesar | Media |
| 3 | Artículos de resumen anual | Alto | Detectar y marcar como `es_agregado` | Alta |
| 4 | Pipeline no actualiza bronze existente | Medio | Añadir dedupe en ingesta | Media |

---

## 10. PRÓXIMOS PASOS (PRIORIZADO)

### Alta Prioridad
1. **[INMEDIATO]** Limpiar 3 registros no_relevante de gold_incidents
2. **[INMEDIATO]** Analizar 13 incidentes sin geolocalización
3. **[INMEDIATO]** Identificar y marcar artículos de resumen/agregados
4. **[ESTA SEMANA]** Hacer commit de todo el trabajo

### Media Prioridad
5. **[PRÓXIMA SESIÓN]** Generar informe de prueba con datos actuales
6. **[PRÓXIMA SESIÓN]** Mejorar prompt de geolocalización
7. **[PRÓXIMA SESIÓN]** Añadir validación para evitar no_relevante en gold

### Baja Prioridad (Azure)
8. **[CUANDO SEA POSIBLE]** Migrar DuckDB → Azure PostgreSQL
9. **[CUANDO SEA POSIBLE]** Containerizar pipeline para Azure
10. **[CUANDO SEA POSIBLE]** Configurar Azure Functions para ejecución diaria

---

## 11. CÓDIGO CRÍTICO PARA REFERENCIA

### Pipeline de enriquecimiento LLM
```python
# src/enrichment/llm_enrichment_pipeline.py - Uso principal
from src.enrichment.llm_enrichment_pipeline import EnrichmentPipeline

pipeline = EnrichmentPipeline("data/osint_dw.duckdb")

# Procesar artículos pendientes
result = pipeline.run_full_pipeline(limit=100)
# Resultado: {"silver": {...}, "gold": {...}, "stats": {...}}

# Solo construir gold desde silver existente
pipeline.build_gold_incidents()
pipeline.build_gold_daily_stats()
```

### Prompt de clasificación LLM (extracto clave)
```python
CATEGORÍAS = [
    "violencia_armada", "crimen_violento", "violencia_sexual", "secuestro",
    "feminicidio", "extorsion", "accidente_grave", "desastre_natural",
    "protesta", "disturbio", "terrorismo", "crimen_organizado",
    "violencia_politica", "operativo_seguridad", "no_relevante"
]

# Output esperado del LLM:
{
    "es_relevante": true,
    "tipo_evento": "crimen_violento",
    "muertos": 1,
    "heridos": 0,
    "departamento": "Lima",
    "resumen_es": "...",
    "confianza": 0.9
}
```

---

## 12. COMANDOS ÚTILES

```bash
# Ver estado del sistema
python -m src.enrichment.llm_enrichment_pipeline --status

# Procesar artículos pendientes (Bronze → Silver → Gold)
python -m src.enrichment.llm_enrichment_pipeline --full 100

# Pipeline diario completo
python scripts/core/daily_pipeline.py --full
python scripts/core/daily_pipeline.py --ingest-only
python scripts/core/daily_pipeline.py --enrich-only

# Consultas rápidas DuckDB
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT tipo_evento, COUNT(*) FROM gold_incidents GROUP BY 1 ORDER BY 2 DESC').fetchdf())"

# Test del clasificador LLM
python src/classification/llm_classifier.py --test
```

---

## 13. ENLACES Y RECURSOS

| Recurso | URL | Notas |
|---------|-----|-------|
| NewsAPI.ai | https://newsapi.ai | API de noticias |
| Anthropic API | https://console.anthropic.com | Claude Haiku |
| DuckDB Docs | https://duckdb.org/docs | Base de datos |

---

## 14. NOTAS PARA EL PRÓXIMO CHAT

### ⚠️ Trampas / Cosas que costó descubrir
- PowerShell no soporta comillas simples dobles (`''`) - usar here-strings `@"..."@`
- NewsAPI.ai `locationUri` es muy restrictivo - mejor usar `sourceUri`
- El LLM a veces clasifica artículos de resumen anual como incidentes puntuales
- DuckDB requiere `INSERT OR REPLACE` explícito, no `UPSERT`

### 💡 Tips importantes
- Siempre filtrar `WHERE es_relevante = TRUE` al construir gold
- El costo del LLM es ~$0.50 por 722 artículos (~$15/mes proyectado)
- Los artículos de resumen ("Arequipa: Muerte en carreteras se incrementó en 2025") inflan estadísticas

### 📝 Contexto adicional
- El frontend se desarrollará en un chat separado (Power BI + React + Azure)
- Ya existe documento de contexto para frontend: `OSINT_Peru_2026_Frontend_Context.md`
- El sistema está diseñado para migrar a Azure (PostgreSQL + Functions + Container Apps)

---

## 15. PROMPT DE CONTINUACIÓN

> **Copia esto al inicio del nuevo chat:**
>
> ```
> Continúo el proyecto "OSINT Perú 2026" - Refinamiento del backend.
> 
> Stack: Python 3.12 + DuckDB + Claude Haiku + NewsAPI.ai
> IDE: VS Code
> 
> Estado actual: Arquitectura Medallion completa, 722 artículos procesados, 210 incidentes relevantes extraídos.
> 
> Último avance: Pipeline LLM funcionando, scripts reorganizados, 71% de ruido filtrado.
> 
> Errores detectados a corregir:
> 1. 3 registros `no_relevante` en gold (deben eliminarse)
> 2. 13 incidentes sin departamento (analizar y mejorar)
> 3. Artículos de resumen anual inflando estadísticas
> 
> Siguiente tarea: Limpiar errores en gold_incidents, luego preparar para Azure.
> 
> Adjunto documento de contexto: cierre_chat_osint_peru_2026_refinamiento1_2026-01-04.md
> ```

---

## Historial de Sesiones

| Sesión | Fecha | Enfoque principal | Logros |
|--------|-------|-------------------|--------|
| refinamiento_1 | 2026-01-03/04 | Arquitectura Medallion + Pipeline LLM | Bronze/Silver/Gold, 210 incidentes, scripts reorganizados |

---

## Estadísticas Finales de la Sesión

| Métrica | Valor |
|---------|-------|
| Artículos procesados | 722 |
| Incidentes relevantes | 210 (29%) |
| Ruido filtrado | 512 (71%) |
| Muertos registrados | 408 |
| Heridos registrados | 2,046 |
| Departamentos cubiertos | 24/25 |
| Costo LLM | ~$0.50 USD |
| Tablas eliminadas | 15 |
| Scripts movidos a legacy | ~35 |

---

*Documento generado: 2026-01-04*
*Sesión: Refinamiento Backend - Parte 1*
*Proyecto: OSINT Perú 2026*
