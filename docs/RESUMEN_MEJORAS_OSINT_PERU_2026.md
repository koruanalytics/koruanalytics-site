# 📊 RESUMEN DE MEJORAS - OSINT PERÚ 2026

**Fecha:** 2026-01-11  
**Priorización:** Geo → Artículos → Enriquecimiento → Filtrado

---

## VISTA CONSOLIDADA POR CATEGORÍA

| # | ID | Categoría | Mejora | Esfuerzo | Impacto | Pre-Azure | Post-Azure | Archivos |
|---|-----|-----------|--------|----------|---------|-----------|------------|----------|
| 1 | **M1** | 🌍 Geocoding | Lookup lat/lon con gazetteer | 3-4h | 🔴 **ALTO** - Habilita mapas Power BI | ✅ Sí | ✅ Sí | `llm_enrichment_pipeline.py`, `dim_places_pe` |
| 2 | **M2** | 📰 Más artículos | Grupo "Corrupción" en ingesta | 30min | 🟡 MEDIO - +20-50 arts/día | ✅ Sí | ✅ Sí | `newsapi_scope_peru_v6.yaml`, `prompts.py` |
| 3 | **M3** | 📰 Más artículos | Alinear keywords con ACLED | 6-8h | 🟡 MEDIO - Mejor clasificación, export ACLED | ⚠️ Parcial | ✅ Sí | `newsapi_scope_peru_v7.yaml`, `prompts.py` |
| 4 | **M4** | 🔍 Enriquecimiento | Campo `motivo_aparente` | 1h | 🟡 MEDIO - Análisis patrones | ✅ Sí | ✅ Sí | `prompts.py`, `schema.py` |
| 5 | **M5** | 🔍 Enriquecimiento | Campo `victima_perfil` | 45min | 🟢 BAJO - Análisis targeting | ✅ Sí | ✅ Sí | `prompts.py`, `schema.py` |
| 6 | **M6** | 🔍 Enriquecimiento | Campo `arma_usada` | 45min | 🟢 BAJO - Análisis modalidad | ✅ Sí | ✅ Sí | `prompts.py`, `schema.py` |
| 7 | **M7** | 🚫 Filtrado pre-LLM | Mejorar detección `es_internacional` | 30min | 🟢 BAJO - Ahorro tokens marginal | ✅ Sí | ✅ Sí | `llm_enrichment_pipeline.py` |
| 8 | **M8** | 🚫 Filtrado pre-LLM | Mejorar detección `es_resumen` | 30min | 🟢 BAJO - Menos ruido en gold | ✅ Sí | ✅ Sí | `llm_enrichment_pipeline.py` |
| 9 | **M9** | 🔧 Calidad datos | Fix encoding UTF-8 en pipeline completo | 2-3h | 🔴 **ALTO** - Datos limpios en todas las capas | ✅ Sí | ✅ Sí | `newsapi_ai_ingest.py`, `llm_enrichment_pipeline.py`, `schema.py` |

---

## DETALLE POR CATEGORÍA

### 🌍 CATEGORÍA 1: GEOCODING

| ID | Mejora | Descripción | Impacto | Esfuerzo | Timing |
|----|--------|-------------|---------|----------|--------|
| M1 | Geocoding con gazetteer | Agregar lat/lon a gold_incidents usando `dim_places_pe` (1,893 lugares) | **ALTO** - Sin esto no hay mapas en Power BI | 3-4h | ✅ Pre-Azure |

**Estado actual:** El LLM extrae departamento/provincia/distrito pero `lat` y `lon` siempre son NULL.

**Archivos:** 
- `src/enrichment/llm_enrichment_pipeline.py` (nuevo método `geocode_incident()`)
- `dim_places_pe` (ya poblada con gazetteer)

---

### 📰 CATEGORÍA 2: MÁS ARTÍCULOS

| ID | Mejora | Descripción | Impacto | Esfuerzo | Timing |
|----|--------|-------------|---------|----------|--------|
| M2 | Grupo "Corrupción" | Añadir keywords: corrupcion, soborno, coima, peculado, malversacion, lavado dinero, etc. | **MEDIO** - +20-50 artículos/día relevantes para contexto electoral | 30min | ✅ Pre-Azure |
| M3 | Alinear con ACLED | Refactorizar grupos para mapear a taxonomía ACLED (Battles, VAC, Protests, Riots, etc.) | **MEDIO** - Mejor clasificación, facilita export/comparación ACLED | 6-8h | ⚠️ Post-Azure |

**Estado actual:** 8 grupos de keywords, ~300 artículos/día, sin grupo corrupción.

**Archivos:**
- `config/newsapi_scope_peru_v6.yaml` (M2: añadir grupo 9)
- `config/newsapi_scope_peru_v7.yaml` (M3: refactor completo)
- `src/llm_providers/prompts.py` (añadir tipo `corrupcion`)

---

### 🔍 CATEGORÍA 3: MEJOR ENRIQUECIMIENTO LLM

| ID | Mejora | Descripción | Impacto | Esfuerzo | Timing |
|----|--------|-------------|---------|----------|--------|
| M4 | `motivo_aparente` | Extraer: robo, ajuste_cuentas, violencia_familiar, riña, extorsion, pasional, politico, desconocido | **MEDIO** - Análisis de patrones de violencia | 1h | ✅ Pre-Azure |
| M5 | `victima_perfil` | Extraer: comerciante, transportista, autoridad, candidato, periodista, mujer, menor, civil | **BAJO** - Análisis de targeting | 45min | ✅ Pre-Azure |
| M6 | `arma_usada` | Extraer: arma_fuego, arma_blanca, explosivo, objeto_contundente, vehiculo, ninguna | **BAJO** - Análisis de modalidad | 45min | ✅ Pre-Azure |

**Estado actual:** El prompt extrae tipo_evento, subtipo, muertos, heridos, geo, actores, resumen, sentiment. No extrae motivo/víctima/arma.

**Archivos:**
- `src/llm_providers/prompts.py` (modificar ENRICHMENT_PROMPT)
- `src/db/schema.py` (ALTER TABLE silver/gold)

**Nota:** M4-M6 aumentan ligeramente tokens por request (~5-10%), pero el valor analítico lo justifica.

---

### 🔧 CATEGORÍA 4: CALIDAD DE DATOS

| ID | Mejora | Descripción | Impacto | Esfuerzo | Timing |
|----|--------|-------------|---------|----------|--------|
| M9 | Fix encoding UTF-8 pipeline completo | Normalizar caracteres en todas las capas (Bronze → Silver → Gold) | **ALTO** - Sin esto, acentos y ñ se corrompen en exports/Power BI | 2-3h | ✅ Pre-Azure |

**Estado actual:** 
- Los textos en `actores`, `organizaciones` y otros campos tienen escapes Unicode (`\u00e1` en lugar de `á`)
- El problema se origina en la ingesta (NewsAPI.ai) y se propaga a silver/gold
- Afecta exports CSV y conexiones directas a Power BI

**Archivos:**
- `src/ingestion/newsapi_ai_ingest.py` (normalizar en ingesta)
- `src/enrichment/llm_enrichment_pipeline.py` (normalizar respuesta LLM)
- `scripts/utils/export_gold_to_csv.py` (export con UTF-8-sig)

---

### 🚫 CATEGORÍA 5: FILTRADO PRE-LLM

| ID | Mejora | Descripción | Impacto | Esfuerzo | Timing |
|----|--------|-------------|---------|----------|--------|
| M7 | Mejorar `es_internacional` | Añadir patrones: entretenimiento (K-pop, Netflix), deportes internacionales, empresas tech, conflictos específicos | **BAJO** - Ahorro marginal de tokens (~2-5%) | 30min | ✅ Pre-Azure |
| M8 | Mejorar `es_resumen` | Añadir patrones: resúmenes semanales, "lo más leído", predicciones, conmemoraciones específicas | **BAJO** - Menos ruido en gold_incidents | 30min | ✅ Pre-Azure |

**Estado actual:** Ya implementado con 40+ países, 60+ ciudades, múltiples patrones regex. Funciona bien pero tiene gaps menores.

**Archivos:**
- `src/enrichment/llm_enrichment_pipeline.py` (clase `QualityValidator`)

---

## MATRIZ DE DECISIÓN

```
                    ESFUERZO
                    Bajo (<1h)    Medio (1-4h)    Alto (>4h)
                 ┌─────────────┬──────────────┬─────────────┐
         ALTO    │             │     M1 🎯    │             │
                 │             │  (Geocoding) │             │
IMPACTO  ────────┼─────────────┼──────────────┼─────────────┤
         MEDIO   │  M2 🎯      │     M4       │     M3      │
                 │(Corrupción) │  (Motivo)    │   (ACLED)   │
         ────────┼─────────────┼──────────────┼─────────────┤
         BAJO    │ M5,M6,M7,M8 │              │             │
                 │             │              │             │
                 └─────────────┴──────────────┴─────────────┘

🎯 = Quick wins recomendados
```

---

## SECUENCIA RECOMENDADA

### FASE 1: Pre-Azure (esta semana)
| Orden | ID | Mejora | Tiempo | Justificación |
|-------|-----|--------|--------|---------------|
| 1 | **M9** | **Fix encoding UTF-8** | 2-3h | **Crítico** - evita datos corruptos en todas las capas |
| 2 | M2 | Grupo Corrupción | 30min | Quick win, alta relevancia electoral |
| 3 | M4 | motivo_aparente | 1h | Mayor valor analítico de los campos nuevos |

### FASE 2: Post-Azure inmediato (semana siguiente)
| Orden | ID | Mejora | Tiempo | Justificación |
|-------|-----|--------|--------|---------------|
| 4 | **M1** | **Geocoding** | 3-4h | **Crítico para Power BI/mapas** |
| 5 | M5 | victima_perfil | 45min | Complementa M4 |
| 6 | M6 | arma_usada | 45min | Completa el set de enriquecimiento |

### FASE 3: Optimización (semanas 3-4)
| Orden | ID | Mejora | Tiempo | Justificación |
|-------|-----|--------|--------|---------------|
| 7 | M7 | es_internacional | 30min | Refinamiento menor |
| 8 | M8 | es_resumen | 30min | Refinamiento menor |
| 9 | M3 | ACLED alignment | 6-8h | Mejora estructural, puede esperar |

---

## RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| **Total mejoras** | 9 |
| **Esfuerzo total estimado** | ~16-18 horas |
| **Quick wins (pre-Azure)** | M2, M4 (~1.5h) |
| **Mayor impacto** | M1 (Geocoding), M9 (Encoding) |
| **Todas compatibles con Azure** | ✅ Sí |

**Recomendación:** Hacer M9 (Encoding) y M2 antes de Azure para evitar problemas de datos, luego M1 como primera prioridad post-Azure para habilitar mapas en Power BI.
