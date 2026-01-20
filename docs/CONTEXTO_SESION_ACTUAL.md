# OSINT Perú 2026 - Contexto para Continuar Sesión

## ESTADO ACTUAL (2026-01-03 02:20)

### Base de Datos
- **Archivo**: `data/osint_dw.duckdb`
- **Artículos raw**: 700
- **Artículos dedup**: ~140 (después de fix de dedupe por título)
- **Incidentes**: 180
- **Rango fechas**: 2025-11-29 a 2026-01-02

### Problemas Identificados y Parcialmente Resueltos

1. **Dedupe mejorado** ✅ (parcial)
   - Antes: dedupe solo por `original_uri` (64% artículos sin URI)
   - Ahora: dedupe por primeros 100 chars del título normalizado
   - Ejecutado manualmente, **FALTA integrar en script core**

2. **Falsos positivos casualties** ✅
   - Añadido `is_false_positive_context()` en `extract_casualties.py`
   - Filtra: sismos (magnitud, km), estadísticas anuales, videos en vivo
   - Resultados: 180 incidentes, 56 muertos, 451 heridos

3. **Nuevo scope v3** ✅
   - Archivo: `config/newsapi_scope_peru_v3.yaml`
   - 7 grupos (vs 12 antes): electoral, violencia_politica, violencia_comun, protestas, terrorismo, desastres_naturales, accidentes
   - Keywords expandidos con conjugaciones/géneros
   - max_per_group: 100, max_total: 500

### Problemas Pendientes

1. **Volumen bajo de artículos**
   - Solo ~6 artículos/día únicos
   - API NewsAPI.ai puede tener cobertura limitada de Perú
   - Considerar: aumentar max_per_group, otras fuentes

2. **Geo-parsing muy bajo (5%)**
   - Solo 9/180 incidentes tienen ubicación (adm1, lat, lon)
   - Necesita mejora en extracción de ubicaciones del texto

3. **Integrar dedupe mejorado en script core**
   - El fix se ejecutó manualmente en SQL
   - Falta modificar `src/processing/dedupe_newsapi_ai_in_duckdb.py`

---

## TAREAS PENDIENTES (en orden de prioridad)

### Inmediatas
1. [ ] Verificar estado final del dedupe mejorado
2. [ ] Reconstruir incidentes con datos limpios
3. [ ] Integrar dedupe por título en script core
4. [ ] Commit de todos los cambios

### Corto plazo
5. [ ] Mejorar geo-parsing (extraer ubicaciones del texto)
6. [ ] Probar ingesta con scope v3 en fechas nuevas
7. [ ] Crear índices en BD
8. [ ] Crear vistas para dashboard
9. [ ] Configurar Task Scheduler para ingesta diaria

### Medio plazo
10. [ ] Evaluar otras fuentes de noticias (GDELT, MediaCloud)
11. [ ] Dashboard visual (HTML/Streamlit)
12. [ ] Alertas por email

---

## ARCHIVOS CLAVE MODIFICADOS HOY

| Archivo | Cambio |
|---------|--------|
| `scripts/extract_casualties.py` | Añadido filtro falsos positivos |
| `config/newsapi_scope_peru_v3.yaml` | Nuevo scope con 7 grupos |
| `stg_news_newsapi_ai_dedup` | Recreada con dedupe por título |

---

## COMANDOS ÚTILES

### Verificar estado actual
```powershell
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT COUNT(*) as raw FROM stg_news_newsapi_ai').fetchdf()); print(con.execute('SELECT COUNT(*) as dedup FROM stg_news_newsapi_ai_dedup').fetchdf()); print(con.execute('SELECT COUNT(*) as incidents FROM fct_daily_report').fetchdf())"
```

### Reconstruir pipeline completo
```powershell
python scripts/build_fct_daily_report.py --rebuild-all
python scripts/extract_casualties.py --backfill
python scripts/extract_sentiment.py --backfill
```

### Probar nuevo scope
```powershell
python scripts/run_newsapi_ai_job.py --scope config/newsapi_scope_peru_v3.yaml --date-start 2025-12-01 --max-total 500
```

### Exportar Excel
```powershell
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); df=con.execute('SELECT * FROM fct_daily_report ORDER BY incident_date DESC').fetchdf(); df.to_excel('data/daily_report.xlsx', index=False); print(f'Exportado: {len(df)} filas')"
```

---

## SQL PARA DEDUPE MEJORADO (integrar en script)

```sql
CREATE OR REPLACE TABLE stg_news_newsapi_ai_dedup AS
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY 
                LOWER(TRIM(LEFT(REGEXP_REPLACE(title, '[^a-zA-Z0-9 ]', '', 'g'), 100)))
            ORDER BY 
                CASE WHEN original_uri IS NOT NULL THEN 0 ELSE 1 END,
                published_at DESC
        ) as rn
    FROM stg_news_newsapi_ai
)
SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1
```

---

## ESTRUCTURA DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── newsapi_scope_peru.yaml      # Scope v2 (12 grupos)
│   └── newsapi_scope_peru_v3.yaml   # Scope v3 (7 grupos) ← NUEVO
├── data/
│   ├── osint_dw.duckdb              # BD principal
│   └── daily_report.xlsx            # Export
├── scripts/
│   ├── run_newsapi_ai_job.py        # Ingesta
│   ├── build_fct_daily_report.py    # Reportes
│   ├── extract_casualties.py        # Víctimas ← MODIFICADO
│   ├── extract_sentiment.py         # Sentimiento
│   └── daily_ingestion.py           # Ingesta diaria
└── src/
    └── processing/
        └── dedupe_newsapi_ai_in_duckdb.py  # ← PENDIENTE MODIFICAR
```
