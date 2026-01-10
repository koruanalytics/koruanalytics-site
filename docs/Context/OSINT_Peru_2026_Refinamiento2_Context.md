# OSINT PERÚ 2026 - CONTEXTO PARA REFINAMIENTO_2

## 📋 RESUMEN EJECUTIVO

Este documento resume todo el trabajo realizado en la sesión anterior de refinamiento del backend.
El sistema de monitoreo de incidentes de seguridad para las elecciones de Perú 2026 ahora tiene:
- Arquitectura Medallion completa (Bronze → Silver → Gold)
- Pipeline de enriquecimiento LLM con Claude Haiku
- 210 incidentes relevantes clasificados de 722 artículos (71% de ruido filtrado)

---

## ✅ TRABAJO COMPLETADO

### Fase 1: Limpieza ✅
| Tarea | Estado |
|-------|--------|
| Eliminar scopes obsoletos (v2, v3) | ✅ Movidos a `_legacy/config/` |
| Eliminar tablas no usadas | ✅ 15 tablas eliminadas |
| Consolidar scripts | ✅ Reorganizados en subcarpetas |

### Fase 2: Arquitectura Medallion ✅
| Tarea | Estado |
|-------|--------|
| Renombrar a `bronze_news` | ✅ 722 artículos únicos |
| Crear `silver_news_enriched` | ✅ 722 procesados por LLM |
| Crear `gold_incidents` | ✅ 210 incidentes relevantes |
| Crear `gold_daily_stats` | ✅ 31 días con estadísticas |
| Crear `vw_daily_report` | ✅ Vista para informes |

### Fase 3: Pipeline LLM ✅
| Tarea | Estado |
|-------|--------|
| Script enriquecimiento batch | ✅ `src/enrichment/llm_enrichment_pipeline.py` |
| Clasificación (14 categorías) | ✅ Funcionando |
| Extracción víctimas | ✅ 408 muertos, 2,046 heridos registrados |
| Geolocalización | ✅ 197/210 con departamento (94%) |
| Resúmenes es/en | ✅ Generados por LLM |
| Análisis sentimiento | ✅ POS/NEG/NEU |

---

## 📊 ESTADO ACTUAL DE LA BASE DE DATOS

### Tablas
```
bronze_news              722 rows   # Raw de NewsAPI.ai
silver_news_enriched     722 rows   # Enriquecido por LLM
gold_incidents           210 rows   # Solo relevantes
gold_daily_stats          31 rows   # Agregados por día
dim_places_pe          1,893 rows   # Gazetteer de Perú
dq_run_metrics            16 rows   # Métricas de calidad
ops_alerts                 0 rows   # Para alertas (vacío)
ops_ingest_runs            0 rows   # Log de ingestas (vacío)
```

### Distribución por Tipo de Evento
| Tipo | Incidentes | Muertos | Heridos |
|------|------------|---------|---------|
| accidente_grave | 52 | 165 | 1,892 |
| violencia_politica | 30 | 3 | 2 |
| desastre_natural | 29 | 0 | 125 |
| crimen_violento | 24 | 48 | 15 |
| crimen_organizado | 16 | 154 | 0 |
| extorsion | 15 | 0 | 5 |
| operativo_seguridad | 14 | 0 | 1 |
| violencia_armada | 11 | 6 | 5 |
| feminicidio | 5 | 3 | 1 |
| protesta | 4 | 18 | 0 |
| secuestro | 4 | 0 | 0 |
| no_relevante | 3 | 0 | 0 | ← ERROR: No deberían estar
| violencia_sexual | 2 | 0 | 0 |
| terrorismo | 1 | 11 | 0 |

### Distribución por Departamento (Top 10)
| Departamento | Incidentes | Muertos |
|--------------|------------|---------|
| Lima | 67 | 15 |
| Cusco | 27 | 25 |
| Arequipa | 24 | 121 |
| La Libertad | 19 | 75 |
| Áncash | 14 | 0 |
| Sin ubicación | 13 | 94 | ← Problema de geolocalización
| Junín | 11 | 30 |
| Piura | 7 | 3 |
| Tacna | 5 | 0 |
| Ucayali | 5 | 5 |

---

## 📁 ESTRUCTURA ACTUAL DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── newsapi_scope_peru_v4.yaml    # Scope activo (7 fuentes)
│   ├── settings.yaml
│   └── geo/
├── src/
│   ├── ingestion/
│   │   └── newsapi_ai_ingest.py      # Ingestor multi-estrategia
│   ├── processing/
│   │   ├── normalize_newsapi_ai.py
│   │   └── dedupe_newsapi_ai_in_duckdb.py
│   ├── enrichment/                   # NUEVO
│   │   └── llm_enrichment_pipeline.py # Pipeline Bronze→Silver→Gold
│   ├── classification/               # NUEVO
│   │   └── llm_classifier.py         # Clasificador LLM standalone
│   ├── incidents/
│   │   └── acled_rules.py            # Reglas ACLED (legacy, reemplazado por LLM)
│   ├── geoparse/
│   ├── nlp/
│   ├── ops/
│   ├── pipelines/
│   ├── models/
│   └── utils/
├── scripts/
│   ├── core/                         # Pipeline principal
│   │   ├── daily_pipeline.py         # NUEVO - Pipeline unificado
│   │   ├── run_newsapi_ai_job.py
│   │   ├── build_fct_daily_report.py
│   │   ├── extract_casualties.py
│   │   ├── extract_sentiment.py
│   │   ├── generate_alerts.py
│   │   └── scheduled_run_newsapi_ai_job.ps1
│   ├── geo/                          # Gazetteer
│   │   ├── build_peru_gazetteer.py
│   │   ├── load_gazetteer_pe.py
│   │   └── validate_gazetteer_*.py
│   ├── utils/                        # Utilidades
│   │   ├── dump_duckdb_schema.py
│   │   ├── compute_run_quality_metrics.py
│   │   ├── get_latest_run_id.py
│   │   └── init_ops_tables.py
│   └── _legacy/                      # Scripts obsoletos (35+ archivos)
├── data/
│   ├── osint_dw.duckdb               # Base de datos principal
│   ├── osint_dw_backup_20260103.duckdb # Backup antes de limpieza
│   ├── raw/
│   ├── interim/
│   └── processed/
├── _legacy/
│   └── config/                       # Scopes obsoletos (v2, v3)
└── .env                              # API keys (ANTHROPIC_API_KEY, NEWSAPI_KEY)
```

---

## 🔧 COMANDOS ÚTILES

### Ver estado del sistema
```powershell
python -m src.enrichment.llm_enrichment_pipeline --status
```

### Procesar artículos pendientes
```powershell
python -m src.enrichment.llm_enrichment_pipeline --full 100
```

### Pipeline diario completo
```powershell
python scripts/core/daily_pipeline.py --full
python scripts/core/daily_pipeline.py --ingest-only
python scripts/core/daily_pipeline.py --enrich-only
```

### Consultas rápidas a la BD
```powershell
# Ver distribución por tipo
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT tipo_evento, COUNT(*) as n FROM gold_incidents GROUP BY 1 ORDER BY 2 DESC').fetchdf())"

# Ver incidentes con más víctimas
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT tipo_evento, departamento, muertos, heridos, LEFT(titulo,50) FROM gold_incidents WHERE muertos > 0 ORDER BY muertos DESC LIMIT 10').fetchdf())"
```

---

## ⚠️ ERRORES DETECTADOS (PENDIENTES DE CORREGIR)

### 1. Registros `no_relevante` en gold_incidents
**Problema**: 3 registros con `tipo_evento = 'no_relevante'` pasaron a gold cuando deberían haberse filtrado.

**Solución**: 
```sql
DELETE FROM gold_incidents WHERE tipo_evento = 'no_relevante';
```

**Prevención**: Verificar que `build_gold_incidents()` filtre correctamente `WHERE es_relevante = TRUE`.

### 2. Incidentes sin geolocalización (13 registros)
**Problema**: 13 incidentes tienen `departamento = NULL`.

**Diagnóstico necesario**:
```sql
SELECT titulo, resumen, source_name 
FROM gold_incidents 
WHERE departamento IS NULL;
```

**Posibles causas**:
- Noticias nacionales sin ubicación específica
- Noticias internacionales que pasaron el filtro
- LLM no pudo inferir ubicación del texto

**Solución**: Mejorar prompt del LLM o post-procesar con reglas.

### 3. Artículos de resumen anual con cifras agregadas
**Problema**: Algunos artículos son resúmenes anuales (ej: "Arequipa: Muerte en carreteras se incrementó en 2025" con 111 muertos) que inflan las estadísticas.

**Ejemplo problemático**:
```
tipo_evento: accidente_grave
departamento: Arequipa
muertos: 111
heridos: 783
titulo: "Arequipa: Muerte en carreteras se incrementó en 2025"
```

**Solución propuesta**:
- Añadir campo `es_agregado` o `tipo_articulo` (incidente puntual vs resumen)
- Mejorar prompt para detectar artículos de resumen
- Filtrar en gold solo incidentes puntuales

---

## 🎯 TAREAS PENDIENTES PARA REFINAMIENTO_2

### Alta Prioridad
1. [ ] **Limpiar registros `no_relevante`** de gold_incidents
2. [ ] **Analizar los 13 sin ubicación** y decidir qué hacer
3. [ ] **Identificar artículos de resumen** vs incidentes puntuales
4. [ ] **Hacer commit** de todo el trabajo

### Media Prioridad
5. [ ] **Generar informe de prueba** con datos actuales
6. [ ] **Mejorar prompt de geolocalización** para reducir "Sin ubicación"
7. [ ] **Añadir validación** para evitar que `no_relevante` pase a gold
8. [ ] **Implementar detección de artículos agregados/resumen**

### Para Azure (Fase 4)
9. [ ] **Actualizar `daily_pipeline.py`** para Azure Functions
10. [ ] **Configurar conexión** DuckDB → Azure PostgreSQL/Synapse
11. [ ] **Containerizar** el pipeline para Azure Container Apps
12. [ ] **Configurar alertas** y monitoreo
13. [ ] **Programar ejecución** diaria automática

---

## 📝 NOTAS TÉCNICAS

### Costos LLM (Claude Haiku)
- 722 artículos procesados
- Costo total: ~$0.50 USD
- Proyección: ~$15/mes para 500 artículos/día

### Fuentes de datos activas
7 fuentes peruanas en NewsAPI.ai (~650 artículos/día):
- elcomercio.pe
- larepublica.pe  
- diariocorreo.pe
- andina.pe
- gestion.pe
- rpp.pe
- ojo.pe

### Categorías de eventos (14 tipos)
```
violencia_armada, crimen_violento, violencia_sexual, secuestro, feminicidio,
extorsion, accidente_grave, desastre_natural, protesta, disturbio,
terrorismo, crimen_organizado, violencia_politica, operativo_seguridad,
no_relevante (solo en silver, no debería llegar a gold)
```

### Departamentos de Perú (25)
```
Amazonas, Áncash, Apurímac, Arequipa, Ayacucho, Cajamarca, Callao, Cusco,
Huancavelica, Huánuco, Ica, Junín, La Libertad, Lambayeque, Lima, Loreto,
Madre de Dios, Moquegua, Pasco, Piura, Puno, San Martín, Tacna, Tumbes, Ucayali
```

---

## 🚀 PROMPT PARA INICIAR REFINAMIENTO_2

```
Continuando OSINT Perú 2026 - Refinamiento del backend.

**Estado actual:**
- Arquitectura Medallion completa (bronze → silver → gold)
- Pipeline LLM funcionando (722 artículos → 210 incidentes relevantes)
- Scripts reorganizados en subcarpetas
- Base de datos limpia

**Errores detectados a corregir:**
1. 3 registros `no_relevante` en gold_incidents (deben eliminarse)
2. 13 incidentes sin departamento (analizar y mejorar)
3. Artículos de resumen anual inflando estadísticas (detectar y marcar)

**Tareas pendientes:**
1. Limpiar errores en gold_incidents
2. Mejorar geolocalización
3. Detectar artículos agregados vs puntuales
4. Generar informe de prueba
5. Hacer commit del trabajo
6. Preparar para migración a Azure

¿Empezamos limpiando los errores detectados?
```

---

*Documento generado: 2026-01-04*
*Sesión: Refinamiento Backend - Parte 1*
*Proyecto: OSINT Perú 2026*
