# Acción de Cierre de Chat del Proyecto: OSINT Perú 2026

## Metadatos del Chat
| Campo | Valor |
|-------|-------|
| **Nombre del proyecto** | OSINT Perú 2026 - Sistema de Monitoreo de Incidentes de Seguridad |
| **Fecha de inicio del chat** | 2026-01-04 |
| **Fecha de cierre** | 2026-01-05 |
| **Duración estimada** | 1 sesión intensiva |
| **Fase del proyecto** | Refinamiento Backend v2 |

---

## 1. RESUMEN EJECUTIVO

Sistema de monitoreo de incidentes de seguridad para las elecciones de Perú 2026. Arquitectura Medallion (Bronze → Silver → Gold) con enriquecimiento LLM. Durante esta sesión se intentó refinar el pipeline pero se introdujeron cambios que rompieron la estrategia original de ingesta multi-grupo. **El proyecto necesita restaurar la arquitectura de ingesta por grupos temáticos (v3) que funcionaba correctamente.**

---

## 2. STACK TECNOLÓGICO

| Categoría | Tecnología | Versión |
|-----------|------------|---------|
| Lenguaje | Python | 3.12 |
| Base de datos | DuckDB | - |
| LLM | Claude Haiku | claude-3-5-haiku-20241022 |
| API Noticias | NewsAPI.ai (EventRegistry) | - |
| Cloud (pendiente) | Azure | OpenAI, AI Search, Maps |
| IDE | VS Code | - |

---

## 3. ESTRUCTURA DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── newsapi_scope_peru_v3.yaml    # ✅ SCOPE CORRECTO - 7 grupos temáticos
│   ├── newsapi_scope_peru_v4.yaml    # ⚠️ source_based - trae TODO
│   ├── newsapi_scope_peru_v5.yaml    # ❌ ROTO - excede límite 15 keywords
│   └── settings.yaml
├── src/
│   ├── ingestion/
│   │   └── newsapi_ai_ingest.py      # ⚠️ Necesita restaurar multi_query_by_group
│   ├── processing/
│   │   ├── normalize_newsapi_ai.py   # 🔄 Actualizado con ingest_run_id
│   │   └── dedupe_newsapi_ai_in_duckdb.py
│   ├── enrichment/
│   │   └── llm_enrichment_pipeline.py # 🔄 Actualizado pero con bugs de esquema
│   ├── classification/
│   │   └── llm_classifier.py
│   └── geoparse/
├── scripts/
│   ├── core/
│   │   ├── daily_pipeline.py         # 🔄 Actualizado pero apunta a scope v5 roto
│   │   └── run_newsapi_ai_job.py
│   └── utils/
├── data/
│   ├── osint_dw.duckdb               # Base de datos principal
│   └── raw/newsapi_ai/               # JSONs crudos
└── .env                              # ANTHROPIC_API_KEY, NEWSAPI_KEY
```

---

## 4. ESTADO DE LAS TABLAS (DuckDB)

| Tabla | Filas | Estado | Descripción |
|-------|-------|--------|-------------|
| `stg_news_newsapi_ai` | ~250 | ✅ Con datos | Staging original que funcionaba |
| `bronze_news` | 0 | ❌ Vaciada | Se vació durante pruebas |
| `silver_news_enriched` | 0 | ❌ Vaciada | Se vació durante pruebas |
| `gold_incidents` | 0 | ❌ Vaciada | Se vació durante pruebas |
| `gold_daily_stats` | 0 | ❌ Vaciada | Se vació durante pruebas |
| `dim_places_pe` | 1,893 | ✅ Intacta | Gazetteer de Perú |

---

## 5. EL PROBLEMA CRÍTICO

### Arquitectura Original (v3) - FUNCIONABA
```
newsapi_scope_peru_v3.yaml
├── strategy: multi_query_by_group
├── 7 grupos temáticos (electoral, violencia_politica, violencia_comun, etc.)
├── Cada grupo: ≤15 keywords (respeta límite API)
├── 7 queries separadas al API
├── Deduplicación entre grupos
└── Resultado: ~50-100 artículos relevantes/día
```

### Lo que se rompió (v4/v5)
```
v4: source_based
├── Trae TODO de las 7 fuentes sin filtrar
├── ~500+ artículos/día (mayoría irrelevantes)
└── Desperdicio de tokens LLM

v5: source_keywords (ROTO)
├── Intenta meter 38 keywords en una query
├── ERROR: "Too many keywords (39), limit is 15"
└── 0 artículos
```

---

## 6. ARCHIVOS QUE NECESITAN RESTAURACIÓN

### 6.1 `src/ingestion/newsapi_ai_ingest.py`
**Problema:** La función `_query_group()` existe pero no se usa cuando `strategy != "location_based"`

**Solución necesaria:** 
- Restaurar/crear estrategia `multi_query_by_group`
- Iterar sobre `concept_groups` del scope v3
- Una query por grupo con sus keywords específicos
- Deduplicar entre grupos

### 6.2 `scripts/core/daily_pipeline.py`
**Problema:** Apunta a `newsapi_scope_peru_v5.yaml` (roto)

**Solución:** Cambiar a `newsapi_scope_peru_v3.yaml`

```python
SCOPE_PATH = "config/newsapi_scope_peru_v3.yaml"  # Restaurar v3
```

### 6.3 `src/enrichment/llm_enrichment_pipeline.py`
**Problema:** El INSERT a `silver_news_enriched` no coincide con el esquema de la tabla

**Esquema de silver (actual):**
- NO tiene `body` (correcto, no queremos el body completo)
- Tiene `modelo_llm` (no `llm_model`)
- Tiene `tokens_usados` (no `tokens_in`, `tokens_out`)
- Tiene `processed_at` (no `enriched_at`)

---

## 7. SCOPE V3 - LA REFERENCIA CORRECTA

```yaml
# config/newsapi_scope_peru_v3.yaml (FUNCIONAL)
strategy: multi_query_by_group  # ← CLAVE

scope:
  location_uri: http://en.wikipedia.org/wiki/Peru
  concept_groups:
    - group_id: electoral
      keywords_spa: [elecciones 2026, candidato presidencial, JNE, ONPE, ...]
    - group_id: violencia_politica
      keywords_spa: [ataque a candidato, amenaza politica, ...]
    - group_id: violencia_comun
      keywords_spa: [asesinato, homicidio, sicariato, secuestro, ...]
    - group_id: protestas
      keywords_spa: [protesta, manifestacion, paro, huelga, ...]
    - group_id: terrorismo
      keywords_spa: [sendero luminoso, terrorismo, VRAEM, ...]
    - group_id: desastres_naturales
      keywords_spa: [terremoto, sismo, inundacion, huayco, ...]
    - group_id: accidentes
      keywords_spa: [accidente de transito, incendio, explosion, ...]

query_strategy:
  mode: multi_query_by_group
  max_per_group: 100
  max_total: 500
```

---

## 8. FLUJO DE DATOS CORRECTO

```
┌─────────────────────────────────────────────────────────────┐
│ INGESTA (multi_query_by_group)                              │
├─────────────────────────────────────────────────────────────┤
│ Para cada grupo en concept_groups:                          │
│   → Query API con locationUri + keywords del grupo          │
│   → Guardar JSON en data/raw/                               │
│ → Deduplicar entre grupos (por URI)                         │
│ → Normalizar a parquet                                      │
│ → Cargar a bronze_news                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ENRIQUECIMIENTO LLM (Bronze → Silver)                       │
├─────────────────────────────────────────────────────────────┤
│ Para cada artículo en bronze (no procesado):                │
│   → Enviar title + body a Claude Haiku                      │
│   → Extraer: tipo_evento, víctimas, geo, resumen            │
│   → Insertar en silver_news_enriched                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PROMOCIÓN A GOLD (Silver → Gold)                            │
├─────────────────────────────────────────────────────────────┤
│ Filtrar:                                                    │
│   - es_relevante = TRUE                                     │
│   - es_internacional = FALSE                                │
│   - es_resumen = FALSE                                      │
│   - tipo_evento != 'no_relevante'                           │
│ → Deduplicar eventos similares                              │
│ → Insertar en gold_incidents                                │
│ → Generar gold_daily_stats                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. MEJORAS IMPLEMENTADAS (CONSERVAR)

### 9.1 Prompt LLM mejorado
- Detecta `es_internacional` (eventos fuera de Perú)
- Detecta `es_resumen` (artículos de estadísticas/conmemoración)
- Resúmenes de 3-4 oraciones (no 1-2)
- Campo `pais_evento`

### 9.2 QualityValidator
- Patrones regex para detectar resúmenes
- Detección de artículos internacionales
- Deduplicación por similitud de título

### 9.3 Filtros en build_gold_incidents()
- Excluye no_relevante, internacionales, resúmenes
- Deduplicación de eventos (mantiene el de más víctimas)

### 9.4 Columnas nuevas en silver
- `es_internacional` (BOOLEAN)
- `es_resumen` (BOOLEAN)
- `pais_evento` (VARCHAR)

---

## 10. PRÓXIMOS PASOS (PRIORIZADO)

### Alta Prioridad
1. **[INMEDIATO]** Restaurar estrategia `multi_query_by_group` en `newsapi_ai_ingest.py`
2. **[INMEDIATO]** Cambiar `daily_pipeline.py` para usar scope v3
3. **[INMEDIATO]** Arreglar INSERT en `llm_enrichment_pipeline.py` para coincidir con esquema silver

### Media Prioridad
4. **[DESPUÉS]** Reingestar desde 2026-01-01 con estrategia correcta
5. **[DESPUÉS]** Procesar con LLM y verificar calidad
6. **[DESPUÉS]** Hacer commit de todo el trabajo

### Baja Prioridad
7. **[FUTURO]** Migración a Azure
8. **[FUTURO]** Frontend con Power BI + ArcGIS

---

## 11. COMANDOS ÚTILES

```bash
# Ver estado de tablas
python -m src.enrichment.llm_enrichment_pipeline --status

# Ver datos en staging (que funcionaba)
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT COUNT(*) FROM stg_news_newsapi_ai').fetchone())"

# Ver distribución por fecha en staging
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT DATE(published_at) as fecha, COUNT(*) as n FROM stg_news_newsapi_ai GROUP BY 1 ORDER BY 1 DESC').fetchdf())"

# Vaciar tablas para reiniciar
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); con.execute('DELETE FROM gold_daily_stats'); con.execute('DELETE FROM gold_incidents'); con.execute('DELETE FROM silver_news_enriched'); con.execute('DELETE FROM bronze_news'); print('Tablas vaciadas')"
```

---

## 12. VARIABLES DE ENTORNO REQUERIDAS

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
NEWSAPI_KEY=...  # También: NEWSAPI_AI_KEY o EVENTREGISTRY_API_KEY
```

---

## 13. LÍMITES DEL API (CRÍTICO)

| Límite | Valor | Notas |
|--------|-------|-------|
| Keywords por query | 15 | Tu suscripción actual |
| Artículos por query | ~100-500 | Depende del plan |

**Por eso la estrategia multi_query_by_group es esencial:** divide los ~100 keywords en 7 grupos de ~15 cada uno.

---

## 14. NOTAS PARA EL PRÓXIMO CHAT

### ⚠️ Trampas / Cosas que costó descubrir
- El scope v4 (source_based) trae TODO sin filtrar → demasiados artículos irrelevantes
- El scope v5 (source_keywords) rompe porque excede 15 keywords
- El esquema de silver_news_enriched NO tiene columna `body`
- PowerShell tiene problemas con comillas en comandos Python inline

### 💡 Tips importantes
- Usar scope v3 con estrategia `multi_query_by_group`
- Cada grupo debe tener ≤15 keywords
- El LLM trabaja sobre bronze (que sí tiene body)
- Silver solo guarda resumen, no body completo

### 📝 Archivos a restaurar desde uploads/contexto
- La lógica de `_query_group()` iterando sobre `concept_groups`
- El INSERT correcto alineado con esquema de silver

---

## 15. PROMPT DE CONTINUACIÓN

> **Copia esto al inicio del nuevo chat:**
>
> ```
> Continúo el proyecto "OSINT Perú 2026".
> 
> Stack: Python 3.12 + DuckDB + Claude Haiku + NewsAPI.ai
> IDE: VS Code
> 
> Estado actual: Pipeline roto - necesita restaurar estrategia multi_query_by_group
> 
> Problema: Se cambió de estrategia de ingesta (v3 grupos → v4/v5) y se rompió.
> La estrategia correcta está en newsapi_scope_peru_v3.yaml con 7 grupos temáticos.
> 
> Siguiente tarea: 
> 1. Restaurar estrategia multi_query_by_group en newsapi_ai_ingest.py
> 2. Alinear INSERT de silver con esquema de tabla
> 3. Reingestar desde 2026-01-01
> 
> Adjunto documento de contexto con detalles completos.
> ```

---

## Historial de Sesiones

| Sesión | Fecha | Enfoque principal | Resultado |
|--------|-------|-------------------|-----------|
| Refinamiento 1 | 2026-01-03/04 | Arquitectura Medallion, LLM pipeline | ✅ Funcionando |
| Refinamiento 2 | 2026-01-04/05 | Limpieza gold, mejoras prompt | ⚠️ Rompió ingesta |

---

*Documento generado: 2026-01-05*
