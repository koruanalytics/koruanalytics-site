# Guía Rápida de Scripts

## Comandos del día a día

### 🔄 Ingesta diaria completa

```bash
# Ejecutar pipeline completo (ingesta → normalizar → cargar → dedup)
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --max-total 200
```

### 📅 Ingesta con fechas específicas

```bash
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --date-start 2025-12-15 \
    --date-end 2025-12-18 \
    --max-total 500
```

### 🎯 Solo grupos prioritarios

```bash
python scripts/run_newsapi_ai_job.py \
    --scope config/newsapi_scope_peru.yaml \
    --priority 1 2
```

---

## Scripts individuales

### Geo-resolución

```bash
# Extraer candidatos de lugares
python scripts/run_location_candidates.py --run-id 20251217235651

# Resolver lugares a coordenadas
python scripts/run_geo_resolve_incidents.py --run-id 20251217235651
```

### Incidentes

```bash
# Extraer incidentes de artículos
python scripts/run_incident_extract_baseline.py --run-id 20251217235651

# Construir tabla de hechos
python scripts/build_fct_incidents.py

# Construir tabla curada
python scripts/build_fct_incidents_curated.py
```

### Pipeline completo post-ingesta (Block H)

```bash
# Ejecuta: location_candidates → geo_resolve → incidents
python scripts/run_block_h_job.py --run-id 20251217235651
```

---

## Diagnóstico y utilidades

### Ver estado de la DB

```bash
# Dump del schema
python scripts/dump_duckdb_schema.py

# Inspeccionar tabla de noticias
python scripts/inspect_newsapi_ai_dw.py

# Inspeccionar incidentes extraídos
python scripts/inspect_stg_incidents_extracted.py
```

### Métricas de calidad

```bash
python scripts/compute_run_quality_metrics.py --run-id 20251217235651
```

### Obtener último run_id

```bash
python scripts/get_latest_run_id.py
```

---

## Mantenimiento

### Gazetteer

```bash
# Cargar gazetteer a DuckDB
python scripts/load_gazetteer_pe.py

# Validar integridad
python scripts/validate_gazetteer_pe.py

# Verificar checksums
python scripts/validate_gazetteer_checksum.py
```

### Migraciones

```bash
# Migrar columnas ACLED
python scripts/migrate_acled_columns.py

# Limpiar schema de curación
python scripts/cleanup_curation_schema.py
```

### Exportar datos

```bash
# Exportar cola de revisión manual
python scripts/export_review_queue.py --output review_queue.csv

# Exportar proyecto como ZIP
.\scripts\export_project_zip.ps1
```

---

## Flags comunes

| Flag | Descripción | Ejemplo |
|------|-------------|---------|
| `--scope` | Path al YAML de scope | `--scope config/newsapi_scope_peru.yaml` |
| `--date-start` | Fecha inicio (YYYY-MM-DD) | `--date-start 2025-12-01` |
| `--date-end` | Fecha fin (YYYY-MM-DD) | `--date-end 2025-12-15` |
| `--max-total` | Máximo de artículos total | `--max-total 500` |
| `--max-per-group` | Máximo por grupo temático | `--max-per-group 100` |
| `--priority` | Filtrar por prioridad | `--priority 1 2` |
| `--run-id` | ID del run a procesar | `--run-id 20251217235651` |
| `--skip-normalize` | Saltar normalización | |
| `--skip-load` | Saltar carga a DuckDB | |
| `--skip-dedupe` | Saltar deduplicación | |
| `--dry-run` | Ejecutar sin escribir | |

---

## Ejecución programada

### Windows Task Scheduler

```powershell
# Registrar tarea
.\scripts\register_newsapi_tasks.ps1

# O manualmente:
schtasks /create /tn "OSINT_Peru_Daily" /tr "python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru.yaml" /sc daily /st 06:00
```

### Script programado

```powershell
# Ejecutar con logging
.\scripts\scheduled_run_newsapi_ai_job.ps1
```

---

## Troubleshooting

### Error: "No module named 'src'"

```bash
# Asegúrate de estar en el directorio raíz
cd C:\path\to\2026_Peru
# Activa el entorno virtual
.venv\Scripts\activate
```

### Error: API key no encontrada

```bash
# Verifica que existe .env con la key
cat .env | grep NEWSAPI
```

### Error: DuckDB locked

```bash
# Cierra otras conexiones a la DB
# O usa una copia:
cp data/osint_dw.duckdb data/osint_dw_backup.duckdb
```

### Ver logs detallados

```bash
# Aumentar verbosidad
LOG_LEVEL=DEBUG python scripts/run_newsapi_ai_job.py ...
```
