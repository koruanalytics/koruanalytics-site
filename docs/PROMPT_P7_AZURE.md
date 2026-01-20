# PROMPT PARA P7 - MIGRACIÓN AZURE

```
Continúo el proyecto "OSINT Perú 2026".

Stack actual: Python 3.12 + DuckDB + Claude Haiku + NewsAPI.ai
IDE: VS Code
Target: Azure

CONTEXTO:
- Sistema de monitoreo de incidentes de seguridad para elecciones Perú 2026
- Arquitectura Medallion (Bronze → Silver → Gold) con clasificación LLM
- Pipeline funcionando en local, listo para producción cloud

COMPLETADO:
- P1: Estrategia de ingesta restaurada (v6 source_keywords_by_group)
- P2: Schema ops_alerts alineado, validador funcionando
- P3: Código legacy movido a carpetas _legacy/
- P4: Pipeline LLM corregido (validación robusta, tests 17/17 passing)
- P5: Re-ingesta histórica - Scripts listos, validado con 1 día de muestra
- P6: venv optimizado (1.7GB → 288MB)

MEJORA IMPLEMENTADA:
- Filtro PRE-LLM que detecta artículos internacionales ANTES de llamar al LLM
- Ahorra ~35% tokens/costo al filtrar Chile, Ecuador, EEUU, etc. sin gastar API

PAQUETE DE TRABAJO: P7 - Migración Azure

ARQUITECTURA TARGET:
```
Local (actual)              →    Azure (target)
─────────────────────────        ─────────────────────────
DuckDB                      →    Azure PostgreSQL
Anthropic Claude API        →    Azure OpenAI (gpt-4o-mini)
Local files (raw/interim)   →    Azure Blob Storage
Task Scheduler              →    Azure Functions (timer)
-                           →    Power BI (dashboards)
```

RECURSOS AZURE DISPONIBLES (o a crear):
- Subscription: [especificar]
- Resource Group: [especificar o crear]
- Región preferida: East US / West Europe

REQUISITOS:
1. Mantener misma lógica de pipeline (Bronze → Silver → Gold)
2. Poder ejecutar diariamente de forma automática
3. Conectar Power BI para visualización
4. Costos controlados (tier básico/desarrollo)
5. Las mejoras futuras (más keywords, geocoding, etc.) no deben requerir re-arquitectura

ENTREGABLES P7:
1. Infraestructura Azure (Terraform o scripts ARM/CLI)
2. Migración de schema DuckDB → PostgreSQL
3. Adaptación de pipeline para Azure OpenAI
4. Azure Function para ejecución diaria
5. Conexión Power BI
6. Documentación de despliegue

ARCHIVOS CLAVE DEL PROYECTO:
- scripts/core/daily_pipeline.py - Pipeline principal
- src/enrichment/llm_enrichment_pipeline.py - Clasificación LLM
- src/ingestion/newsapi_ai_ingest.py - Ingesta NewsAPI
- config/newsapi_scope_peru_v6.yaml - Configuración keywords
- src/db/schema.py - Definiciones de tablas

ESTRUCTURA BD ACTUAL:
- bronze_news: Artículos raw (incident_id, title, body, url, published_at, source_title)
- silver_news_enriched: Clasificados LLM (es_relevante, es_internacional, tipo_evento, muertos, heridos, departamento, resumen_es, etc.)
- gold_incidents: Solo relevantes de Perú (filtrados y limpios)
- gold_daily_stats: Agregados diarios
- dim_places_pe: Gazetteer Perú (1,893 lugares)

¿Empezamos con el diseño de infraestructura Azure?
```

---

## NOTAS PARA EL CHAT P7

### Decisiones a tomar:
1. **Azure OpenAI vs seguir con Anthropic** - Azure OpenAI simplifica billing pero cambia modelo
2. **PostgreSQL vs Cosmos DB** - PostgreSQL es más similar a DuckDB
3. **Azure Functions vs Container Apps** - Functions es más simple para timer jobs
4. **Managed Identity vs Connection Strings** - Seguridad

### Archivos que necesitarás subir al chat P7:
- `src/db/schema.py` (para migrar DDLs)
- `requirements-minimal.txt` (dependencias)
- `.env.example` (variables necesarias)

### Costos estimados Azure (tier básico):
| Servicio | Tier | Costo/mes |
|----------|------|-----------|
| PostgreSQL Flexible | Burstable B1ms | ~$15-25 |
| Azure Functions | Consumption | ~$0-5 |
| Blob Storage | Hot | ~$1-2 |
| Azure OpenAI | Pay-per-use | ~$10-30 |
| **Total** | | **~$30-60/mes** |

---

## COMANDO PARA EJECUTAR PIPELINE LOCAL (referencia)

```powershell
# Pipeline completo un día
python -m scripts.core.daily_pipeline --full --date-start 2026-01-01 --date-end 2026-01-01

# Solo ingesta
python -m scripts.core.daily_pipeline --ingest-only --date-start 2026-01-01 --date-end 2026-01-01

# Solo enriquecimiento
python -m scripts.core.daily_pipeline --enrich-only

# Estado
python -m scripts.core.daily_pipeline --status
```
