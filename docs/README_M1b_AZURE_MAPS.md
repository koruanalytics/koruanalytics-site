# M1b - Azure Maps Geocoding - Guía de Activación

**Fecha:** 2026-01-13  
**Mejora:** M1b - Geocoding con Azure Maps API  
**Prerequisito:** M1 (Gazetteer local) ya implementado  
**Prioridad:** BAJA (hacer después de M10)

---

## 📊 Problema que Resuelve

Después de implementar M1, tienes **100% de incidentes con coordenadas** gracias al fallback jer (gazetteer → provincia → departamento). Sin embargo, muchas ubicaciones específicas no se pueden geocodificar con precisión:

```
❌ "Gamarra" → Fallback a LA VICTORIA (distrito completo)
❌ "Avenida Alcides Carrión, primera cuadra" → Fallback a AREQUIPA (capital)
❌ "Carretera Panamericana, óvalo" → Fallback a LIMA (departamento)
```

**M1b agrega Azure Maps** para geocodificar estas direcciones específicas con alta precisión.

---

## 🎯 Nueva Estrategia de Geocoding

### Antes (Solo M1):
```
1. Gazetteer (distrito) → 1 match
2. Provincia capital → 3 matches
3. Departamento capital → 7 matches
4. LLM fallback → 5 matches
5. ❌ Sin coords: ubicaciones específicas → 49 sin precisión
```

### Después (M1 + M1b):
```
1. Gazetteer (distrito) → 1 match
2. 🆕 Azure Maps (direcciones) → ~30-40 matches ✨
3. Provincia capital → 3 matches
4. Departamento capital → 7 matches  
5. LLM fallback → 5 matches
6. ✅ Mejora: ~60-80% de ubicaciones específicas ahora precisas
```

---

## 💰 Costo Estimado

**Azure Maps - Tier S0:**
- Precio: $0.50 por 1,000 requests
- Uso estimado: 50-100 requests/día (20% de artículos)
- **Costo mensual: ~$0.75 - $1.50**

**Con caching (LRU 500 items):**
- Direcciones repetidas (ej: "Gamarra") no consumen API
- Costo real probablemente < $1/mes

---

## 🚀 Instalación

### Prerequisito: Crear Recurso Azure Maps

#### 1. En Azure Portal

```
1. Ir a portal.azure.com
2. Buscar "Azure Maps"
3. Crear nueva cuenta:
   - Subscription: Tu subscription actual
   - Resource group: osint-peru-2026-rg (o el tuyo)
   - Name: osint-peru-maps
   - Region: East US (mismo que otros recursos)
   - Pricing tier: S0 (Standard)
4. Review + Create
5. Esperar deployment (~2 min)
```

#### 2. Obtener API Key

```
1. Ir al recurso creado: osint-peru-maps
2. En el menú lateral: Settings → Authentication
3. Copiar "Primary Key"
```

---

### Paso 1: Configurar Variable de Entorno

Agregar a tu archivo `.env`:

```bash
# Azure Maps (M1b - Geocoding preciso)
AZURE_MAPS_KEY=tu_primary_key_aqui
```

**Validar:**
```powershell
# Verificar que se cargó correctamente
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'Key: {os.getenv(\"AZURE_MAPS_KEY\")[:10]}...')"
```

---

### Paso 2: Copiar Archivos Nuevos

```powershell
# Desde el directorio del proyecto
Copy-Item M1b_entrega\azure_maps_geocoder.py src\enrichment\ -Force
Copy-Item M1b_entrega\geocoding_service.py src\enrichment\ -Force
Copy-Item M1b_entrega\test_azure_maps.py scripts\tests\ -Force
```

---

### Paso 3: Instalar Dependencia (si no está)

```powershell
# Requests ya debería estar instalado, pero por si acaso:
pip install requests --break-system-packages
```

---

### Paso 4: Ejecutar Tests

```powershell
# Test básico (sin API key - dry run)
python -m scripts.tests.test_azure_maps

# Test completo (con API key)
python -m scripts.tests.test_azure_maps --live
```

**Salida esperada:**
```
✓ Gamarra → (-12.0653, -77.0153)
✓ Avenida Alcides Carrión → (-16.3952, -71.5350)
✓ All tests passed

Projected monthly cost: ~$1.20
```

---

### Paso 5: Rebuild Gold con Azure Maps

```powershell
# Reconstruir gold_incidents con Azure Maps habilitado
python -m src.enrichment.llm_enrichment_pipeline --build-gold
```

**Resultado esperado:**
```
GEOCODING RESULTS:
  Con coordenadas: 65/65 (100.0%)
  - Específico (ADM4): 5-10  ← Menos (LLM directo)
  - Azure Maps: 30-40        ← NUEVO - Alta precisión ✨
  - Distrito (ADM3): 1
  - Provincia (ADM2): 3
  - Departamento (ADM1): 7
  - Estimado (LLM): 3-5
  - Sin coordenadas: 0
```

---

## 📊 Verificar Resultados

### SQL: Ver incidentes geocodificados por Azure Maps

```sql
SELECT 
    titulo,
    departamento,
    distrito,
    adm4_name,
    nivel_geo,
    ROUND(lat, 4) as lat,
    ROUND(lon, 4) as lon
FROM gold_incidents
WHERE nivel_geo = 'azure_maps'
LIMIT 10;
```

### SQL: Comparar precisión antes/después

```sql
SELECT 
    nivel_geo,
    COUNT(*) as cantidad,
    ROUND(AVG(CASE WHEN adm4_name IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as pct_especifico
FROM gold_incidents
GROUP BY nivel_geo
ORDER BY cantidad DESC;
```

---

## 🎨 Uso en Power BI

Con Azure Maps, ahora tienes:

- **nivel_geo = 'azure_maps'** → Coordenadas precisas de direcciones
- **adm4_name** → Nombre de la ubicación específica
- **lat/lon** → Coordenadas exactas (no fallback)

### Visualización Mejorada

```dax
// Color por precisión
Precisión Color = 
SWITCH(
    [nivel_geo],
    "azure_maps", "#00FF00",    // Verde brillante - Muy preciso
    "distrito", "#90EE90",      // Verde claro
    "provincia", "#FFFF00",     // Amarillo
    "departamento", "#FFA500",  // Naranja
    "#808080"                   // Gris
)

// Tooltip mejorado
Ubicación Detalle = 
IF(
    [nivel_geo] = "azure_maps",
    "📍 " & [adm4_name] & " (preciso)",
    [ubicacion_display]
)
```

---

## 💡 Optimización de Costos

### 1. Cache Automático (Ya implementado)

El sistema cachea las últimas 500 direcciones en memoria:

```python
# Direcciones repetidas NO consumen API
geocode_address_azure("Gamarra", "LIMA")  # 1ra vez → API call
geocode_address_azure("Gamarra", "LIMA")  # 2da vez → Cache (gratis)
```

### 2. Monitorear Uso

```powershell
# Ver estadísticas de uso
python -c "
from src.enrichment.azure_maps_geocoder import get_azure_geocoder
stats = get_azure_geocoder().get_stats()
print(f'API requests: {stats[\"api_requests\"]}')
print(f'Cache hits: {stats[\"cache_hits\"]}')
print(f'Cache hit rate: {stats[\"cache_hits\"]/(stats[\"api_requests\"]+stats[\"cache_hits\"])*100:.1f}%')
"
```

### 3. Limitar Uso (Opcional)

Si el costo aumenta mucho, puedes:

**Opción A:** Desactivar temporalmente
```bash
# En .env, comentar o eliminar:
# AZURE_MAPS_KEY=...
```

**Opción B:** Limitar a ciertos tipos de incidentes
```python
# En geocoding_service.py, agregar filtro:
if ubicacion_especifica and muertos > 0:  # Solo violentos
    result = geocode_address_azure(...)
```

---

## 🔄 Flujo Automático

Una vez configurado, Azure Maps funciona **automáticamente** en:

```powershell
# Pipeline diario
python -m scripts.core.daily_pipeline --full

# Solo rebuild gold
python -m src.enrichment.llm_enrichment_pipeline --build-gold
```

**No requiere cambios en el pipeline** - se integra transparentemente.

---

## 🐛 Troubleshooting

### Error: "Azure Maps API key not configured"

```powershell
# Verificar .env
Get-Content .env | Select-String "AZURE_MAPS"

# Si no existe, agregar:
Add-Content .env "`nAZURE_MAPS_KEY=tu_key_aqui"
```

### Error: HTTP 401 Unauthorized

- La API key es incorrecta
- Solución: Verificar en Azure Portal → Maps → Authentication

### Error: HTTP 429 Too Many Requests

- Rate limit excedido (50 req/sec)
- El sistema tiene retry automático, espera unos segundos

### No se ven mejoras en nivel_geo

```powershell
# Verificar que Azure Maps está activo
python -c "
from src.enrichment.geocoding_service import AZURE_MAPS_AVAILABLE
print(f'Azure Maps available: {AZURE_MAPS_AVAILABLE}')
"

# Si es False, revisar imports
```

---

## 📈 Métricas de Éxito

**Antes de M1b:**
- 100% con coordenadas ✅
- 75% fallback genérico (provincia/departamento) ⚠️

**Después de M1b:**
- 100% con coordenadas ✅  
- 60-80% con precisión alta (Azure Maps + gazetteer) ✨
- Costo: < $1.50/mes 💰

---

## ✅ Checklist

- [ ] Recurso Azure Maps creado en portal
- [ ] API key agregada a `.env`
- [ ] Archivos copiados (azure_maps_geocoder.py, geocoding_service.py)
- [ ] Tests ejecutados exitosamente
- [ ] Gold rebuildeado con Azure Maps
- [ ] Verificación SQL: nivel_geo='azure_maps' visible
- [ ] Power BI actualizado con nuevos datos

---

## 🎯 Próximos Pasos

M1b es **opcional** y de prioridad baja. Si prefieres:

1. **Implementar primero M10** (recupera artículos perdidos) - Mayor impacto
2. Validar M1b en producción por 1 semana
3. Monitorear costos reales
4. Ajustar si es necesario

**Recomendación:** Activar M1b solo si la falta de precisión geográfica está afectando análisis en Power BI.

---

**Documentación:** README_M1b_AZURE_MAPS.md  
**Tests:** scripts/tests/test_azure_maps.py  
**Costo estimado:** $0.75 - $1.50/mes
