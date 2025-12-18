# Fase 1: Instrucciones de Implementación

## Archivos generados

1. `fase1_schema.py` - Schema actualizado con campos del API
2. `fase1_migrate_add_api_fields.py` - Script de migración
3. `fase1_extract_baseline.py` - Extractor actualizado
4. `fase1_run_incident_extract_baseline.py` - Runner actualizado

## Pasos de Implementación

### Paso 1: Backup de archivos originales (opcional pero recomendado)

```powershell
# Crear carpeta de backup
New-Item -ItemType Directory -Path "src\_backup_pre_fase1" -Force

# Backup
Copy-Item "src\db\schema.py" "src\_backup_pre_fase1\schema.py"
Copy-Item "src\incidents\extract_baseline.py" "src\_backup_pre_fase1\extract_baseline.py"
Copy-Item "scripts\run_incident_extract_baseline.py" "src\_backup_pre_fase1\run_incident_extract_baseline.py"
```

### Paso 2: Copiar archivos nuevos

```powershell
# Desde la carpeta donde descargaste los archivos (ajusta la ruta):
$downloadPath = "$env:USERPROFILE\Downloads"

# Copiar schema actualizado
Copy-Item "$downloadPath\fase1_schema.py" "src\db\schema.py" -Force

# Copiar extractor actualizado
Copy-Item "$downloadPath\fase1_extract_baseline.py" "src\incidents\extract_baseline.py" -Force

# Copiar runner actualizado
Copy-Item "$downloadPath\fase1_run_incident_extract_baseline.py" "scripts\run_incident_extract_baseline.py" -Force

# Copiar script de migración
Copy-Item "$downloadPath\fase1_migrate_add_api_fields.py" "scripts\migrate_add_api_fields.py" -Force
```

### Paso 3: Ejecutar migración (DRY-RUN primero)

```powershell
# Ver qué cambios se harían (sin ejecutar)
python scripts/migrate_add_api_fields.py --dry-run

# Si todo se ve bien, ejecutar la migración real
python scripts/migrate_add_api_fields.py
```

### Paso 4: Verificar migración

```powershell
# Verificar que las columnas se añadieron
python -c "
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')
cols = [r[1] for r in con.execute('PRAGMA table_info(stg_incidents_extracted)').fetchall()]
new_cols = ['sub_event_type', 'disorder_type', 'source_title', 'is_duplicate', 'api_category', 'api_location', 'concept_labels']
print('Columnas nuevas presentes:')
for c in new_cols:
    status = '✓' if c in cols else '✗'
    print(f'  {status} {c}')
"
```

### Paso 5: Test con un run existente

```powershell
# Obtener el último run_id
$runId = python -c "
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')
r = con.execute('SELECT DISTINCT ingest_run_id FROM stg_news_newsapi_ai_dedup ORDER BY ingest_run_id DESC LIMIT 1').fetchone()
print(r[0] if r else 'NO_RUNS')
"
Write-Host "Último run_id: $runId"

# Re-ejecutar extracción para ese run
python scripts/run_incident_extract_baseline.py --run-id $runId
```

### Paso 6: Verificar datos enriquecidos

```powershell
python -c "
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')
print('=== Muestra de datos enriquecidos ===')
df = con.execute('''
    SELECT 
        incident_id,
        source_title,
        api_category,
        api_location,
        concept_labels,
        incident_type,
        sub_event_type
    FROM stg_incidents_extracted
    ORDER BY incident_id DESC
    LIMIT 5
''').fetchdf()
print(df.to_string())
"
```

### Paso 7: Commit de cambios

```powershell
git add .
git commit -m 'feat: add API enrichment fields to incident extraction

- Add sub_event_type, disorder_type columns (ACLED)
- Add source_title, is_duplicate, api_category, api_location, concept_labels
- Update schema.py with new DDL
- Update extract_baseline.py to extract API fields
- Update run_incident_extract_baseline.py to read API fields
- Add migrate_add_api_fields.py for existing databases'
```

## Verificación Final

Después de implementar, ejecuta un pipeline completo:

```powershell
# Pipeline completo con datos nuevos
python scripts/run_newsapi_ai_job.py `
    --scope config/newsapi_scope_peru.yaml `
    --date-start 2025-12-17 `
    --date-end 2025-12-18 `
    --max-total 20

# Ver resultados
python -c "
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')

print('=== Cobertura de campos API ===')
stats = con.execute('''
    SELECT
        COUNT(*) as total,
        COUNT(source_title) as source_title,
        COUNT(api_category) as api_category,
        COUNT(api_location) as api_location,
        COUNT(concept_labels) as concept_labels,
        COUNT(sub_event_type) as sub_event_type,
        COUNT(disorder_type) as disorder_type
    FROM stg_incidents_extracted
''').fetchdf()
print(stats.T)
"
```

## Rollback (si algo sale mal)

```powershell
# Restaurar archivos originales
Copy-Item "src\_backup_pre_fase1\schema.py" "src\db\schema.py" -Force
Copy-Item "src\_backup_pre_fase1\extract_baseline.py" "src\incidents\extract_baseline.py" -Force
Copy-Item "src\_backup_pre_fase1\run_incident_extract_baseline.py" "scripts\run_incident_extract_baseline.py" -Force

# Las columnas añadidas a la BD no afectan funcionamiento (quedan NULL)
```

## Siguiente: Fase 2

Una vez verificado que Fase 1 funciona, proceder con:
- Crear `fct_daily_report` 
- Script `build_fct_daily_report.py`
- Integrar resúmenes con `sumy`
