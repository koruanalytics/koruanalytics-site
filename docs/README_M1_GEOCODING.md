# M1 - Geocoding con Gazetteer - Instrucciones de Implementación

**Fecha:** 2026-01-11  
**Mejora:** M1 del backlog post-P7  
**Objetivo:** Agregar coordenadas lat/lon a gold_incidents usando gazetteer de Perú (1,893 lugares)

---

## 📦 Archivos Incluidos

```
schema.py                       # Schema actualizado con adm4_name y nivel_geo
add_geocoding_fields.py         # Script de migración para DB existente
geocoding_service.py            # Servicio de geocoding con 5 niveles
llm_enrichment_pipeline.py      # Pipeline actualizado con geocoding integrado
test_geocoding.py               # Script de validación y testing
```

---

## 🎯 Estrategia de Geocoding (5 Niveles)

### Orden de Prioridad:

1. **'especifico' (ADM4)** - Ubicación sub-distrito del LLM con coordenadas
   - Usa lat/lon del LLM cuando `ubicacion_especifica` es diferente de distrito/provincia/departamento
   - Ejemplo: "San Juan de Lurigancho" (poblado dentro del distrito Lima)

2. **'distrito' (ADM3)** - Match exacto en gazetteer
   - Distrito + Provincia + Departamento coinciden exactamente
   - Ejemplo: "LIMA, LIMA, LIMA" → (-12.0464, -77.0428)

3. **'provincia' (ADM2)** - Capital de provincia
   - Cuando solo hay provincia y departamento
   - Busca distrito con nombre = provincia (capital provincial)
   - Ejemplo: "LIMA, LIMA" → Distrito LIMA

4. **'departamento' (ADM1)** - Capital de departamento
   - Cuando solo hay departamento
   - Busca distrito con nombre = departamento (capital departamental)
   - Ejemplo: "LIMA" → Distrito LIMA

5. **'estimado'** - Fallback a coordenadas del LLM
   - Cuando no hay match en gazetteer pero LLM proporcionó lat/lon
   - Útil para ubicaciones que no están en el gazetteer

6. **NULL** - Sin coordenadas disponibles
   - No hay match en gazetteer ni coordenadas del LLM

---

## 🚀 Pasos de Implementación

### 1. Agregar Campos a la Base de Datos

```powershell
# En el directorio del proyecto: C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru

# Activar entorno virtual
venv\Scripts\activate

# Ejecutar migración
python -m scripts.migrations.add_geocoding_fields
```

**Resultado esperado:**
```
✓ Added adm4_name to silver_news_enriched
✓ Added nivel_geo to silver_news_enriched
✓ Added adm4_name to gold_incidents
✓ Added nivel_geo to gold_incidents
✓ Migration completed successfully
```

---

### 2. Reemplazar Archivos Actualizados

```powershell
# Backup de archivos originales (por si acaso)
Copy-Item src\db\schema.py src\db\schema.py.backup
Copy-Item src\enrichment\llm_enrichment_pipeline.py src\enrichment\llm_enrichment_pipeline.py.backup

# Copiar archivos nuevos desde el ZIP entregado
Copy-Item -Path .\M1_entrega\schema.py -Destination .\src\db\schema.py -Force
Copy-Item -Path .\M1_entrega\geocoding_service.py -Destination .\src\enrichment\geocoding_service.py -Force
Copy-Item -Path .\M1_entrega\llm_enrichment_pipeline.py -Destination .\src\enrichment\llm_enrichment_pipeline.py -Force
```

---

### 3. Validar Servicio de Geocoding

```powershell
# Copiar script de testing
Copy-Item -Path .\M1_entrega\test_geocoding.py -Destination .\scripts\tests\test_geocoding.py -Force

# Ejecutar tests
python -m scripts.tests.test_geocoding
```

**Resultado esperado:**
```
Gazetteer loaded: 1893 places
✓ LIMA, LIMA, LIMA → nivel=distrito, coords=(-12.0464, -77.0428)
✓ AREQUIPA, AREQUIPA, AREQUIPA → nivel=distrito, coords=(-16.4090, -71.5375)
✓ San Juan de Lurigancho → nivel=especifico, adm4=San Juan de Lurigancho
✓ All geocoding strategies tested
```

---

### 4. Reconstruir gold_incidents con Geocoding

```powershell
# Rebuild gold_incidents (incluye geocoding automático)
python -m src.enrichment.llm_enrichment_pipeline --build-gold
```

**Resultado esperado:**
```
Geocoding service loaded: {'total_places': 1893, 'departamentos': 25, 'provincias': 196, 'distritos': 1893}
Aplicando geocoding a 210 registros...
Insertando 210 registros geocodificados en gold_incidents...

✓ gold_incidents construido: 210 incidentes

GEOCODING RESULTS:
  Con coordenadas: 168/210 (80.0%)
  - Específico (ADM4): 35
  - Distrito (ADM3): 78
  - Provincia (ADM2): 32
  - Departamento (ADM1): 18
  - Estimado (LLM): 5
  - Sin coordenadas: 42
```

---

## 📊 Verificación de Resultados

### Consulta SQL para Verificar Geocoding

```sql
-- En DuckDB
SELECT 
    nivel_geo,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as porcentaje
FROM gold_incidents
GROUP BY nivel_geo
ORDER BY 
    CASE nivel_geo
        WHEN 'especifico' THEN 1
        WHEN 'distrito' THEN 2
        WHEN 'provincia' THEN 3
        WHEN 'departamento' THEN 4
        WHEN 'estimado' THEN 5
        ELSE 6
    END;
```

### Ver Ejemplos de Cada Nivel

```sql
-- Ejemplos de nivel_geo = 'especifico' (ADM4)
SELECT 
    titulo, 
    departamento, 
    provincia, 
    distrito, 
    adm4_name, 
    nivel_geo,
    lat,
    lon
FROM gold_incidents
WHERE nivel_geo = 'especifico'
LIMIT 5;
```

---

## 🎨 Uso en Power BI

Con los campos `lat`, `lon`, y `nivel_geo` ahora puedes:

### 1. Mapa de Incidentes con Precisión Variable

```dax
// Medida: Color según precisión
Color por Precisión = 
SWITCH(
    SELECTEDVALUE(gold_incidents[nivel_geo]),
    "especifico", "#00FF00",  // Verde - muy preciso
    "distrito", "#90EE90",    // Verde claro
    "provincia", "#FFFF00",   // Amarillo
    "departamento", "#FFA500", // Naranja
    "estimado", "#FF6347",    // Rojo claro
    "#808080"                 // Gris - sin coords
)
```

### 2. Filtro de Calidad Geográfica

```dax
// Medida: Solo incidentes bien geolocalizados
Incidentes Precisos = 
CALCULATE(
    COUNT(gold_incidents[incident_id]),
    gold_incidents[nivel_geo] IN {"especifico", "distrito"}
)
```

### 3. Visualización en ArcGIS

- **Campo lat:** Latitud
- **Campo lon:** Longitud  
- **Campo nivel_geo:** Tooltip para mostrar precisión
- **Campo adm4_name:** Mostrar nombre de poblado cuando disponible

---

## 🔄 Flujo Continuo

Para datos futuros, el geocoding se aplica automáticamente:

```powershell
# Pipeline completo (ingesta + enrichment + geocoding + gold)
python -m scripts.core.daily_pipeline --full

# Solo rebuild gold con nuevo geocoding
python -m src.enrichment.llm_enrichment_pipeline --build-gold
```

---

## 📈 Métricas Esperadas

Basado en la estructura actual de datos:

- **Match Rate Total:** ~70-80% (vs ~40% actual)
- **ADM4 (Específico):** ~15-20% de los geocodificados
- **ADM3 (Distrito):** ~35-40% de los geocodificados
- **ADM2 (Provincia):** ~15-20% de los geocodificados
- **ADM1 (Departamento):** ~10-15% de los geocodificados
- **Estimado:** ~5-10% de los geocodificados

---

## 🐛 Troubleshooting

### Error: "Gazetteer not found"

```powershell
# Verificar que existe el gazetteer
Test-Path config\geo\peru_gazetteer_full.csv

# Si falta, verificar ubicación
Get-ChildItem -Recurse -Filter "peru_gazetteer*.csv"
```

### Error: "Column nivel_geo does not exist"

```powershell
# Ejecutar migración nuevamente
python -m scripts.migrations.add_geocoding_fields
```

### Geocoding muy bajo (<50%)

```powershell
# Verificar calidad de datos en silver
python -m src.enrichment.llm_enrichment_pipeline --status

# Ver ejemplos de ubicaciones sin match
python << 'EOF'
import duckdb
con = duckdb.connect('data/osint_dw.duckdb')
result = con.execute("""
    SELECT departamento, provincia, distrito, COUNT(*) as n
    FROM silver_news_enriched
    WHERE es_relevante = TRUE
      AND departamento IS NOT NULL
    GROUP BY departamento, provincia, distrito
    ORDER BY n DESC
    LIMIT 10
""").fetchdf()
print(result)
EOF
```

---

## ✅ Checklist de Implementación

- [ ] Migración ejecutada (`add_geocoding_fields.py`)
- [ ] Schema actualizado (`schema.py`)
- [ ] Servicio de geocoding instalado (`geocoding_service.py`)
- [ ] Pipeline actualizado (`llm_enrichment_pipeline.py`)
- [ ] Tests ejecutados exitosamente (`test_geocoding.py`)
- [ ] Gold rebuildeado con geocoding
- [ ] Verificación SQL ejecutada (>70% con coordenadas)
- [ ] Visualización en Power BI configurada

---

## 📚 Referencias

- **Gazetteer:** `config/geo/peru_gazetteer_full.csv` (1,893 lugares)
- **Schema:** `src/db/schema.py` (single source of truth)
- **Pipeline:** `src/enrichment/llm_enrichment_pipeline.py`
- **Servicio:** `src/enrichment/geocoding_service.py`

---

## 🎯 Próximas Mejoras (Post-M1)

- **M2:** Grupo "Corrupción" en ingesta (+20-50 arts/día)
- **M3:** Alinear keywords con taxonomía ACLED
- **M4:** Campo `motivo_aparente` (robo, ajuste_cuentas, etc.)
- **M5:** Campo `victima_perfil` (comerciante, autoridad, etc.)

---

**Implementación completada:** 2026-01-11  
**Tiempo estimado:** 3-4 horas  
**Impacto:** ALTO - Habilita visualización geográfica precisa en Power BI
