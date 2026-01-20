# PROMPT CONTEXTO - M1b: Geocoding con API externa (Azure Maps)

## COPIAR TODO DESDE AQUÍ 👇

---

Continúo el proyecto "OSINT Perú 2026" - Sistema de monitoreo de incidentes de seguridad para elecciones.

## STACK TECNOLÓGICO
- Python 3.12 + DuckDB (Medallion: Bronze → Silver → Gold)
- LLM: Claude Haiku (dev) / Azure OpenAI (prod)
- Azure: Functions, OpenAI, Maps, Storage (East US)
- Geocoding actual: Gazetteer local (1,893 distritos)

## ESTADO ACTUAL DEL GEOCODING (M1 implementado)

El geocoding con gazetteer local funciona con fallback:
- **Distrito** → coordenadas exactas del distrito
- **Provincia** → coordenadas de capital de provincia  
- **Departamento** → coordenadas de capital de departamento

**Resultado actual:** 100% de incidentes tienen coordenadas (gracias al fallback)

## PROBLEMA DETECTADO

El LLM extrae ubicaciones específicas (direcciones, lugares) que el gazetteer no puede geocodificar:

```
Geocoded (especifico/LLM): Río Pisco, Cooperativa Miguel Grau → (nan, nan)
Geocoded (especifico/LLM): Avenida Alcides Carrión, primera cuadra → (nan, nan)
Geocoded (especifico/LLM): Carretera Panamericana, óvalo cruce - Tambogrande → (nan, nan)
Geocoded (especifico/LLM): Urbanización Semi Rústica El Bosque, Trujillo → (nan, nan)
Geocoded (especifico/LLM): Intersección avenida Los Jardines Oeste con jirón Las Grosellas → (nan, nan)
```

**El fallback funciona** (usa departamento/provincia), pero pierde precisión geográfica.

## MEJORA A IMPLEMENTAR

```
MEJORA: M1b - Geocoding con API externa (Azure Maps)
OBJETIVO: Geocodificar direcciones específicas que el gazetteer local no puede resolver
ARCHIVOS: src/enrichment/geocoding_service.py (nuevo o extender existente)
ESFUERZO: 2-3 horas
IMPACTO: MEDIO - Mejora precisión de mapas, no crítico (fallback funciona)
PRIORIDAD: Baja (hacer después de M10)
```

## ARQUITECTURA PROPUESTA

```
ubicacion_especifica (del LLM)
         ↓
    ┌────────────────────────────────────┐
    │  1. Gazetteer local (distrito)     │ ← Rápido, gratis
    │     ↓ si falla                     │
    │  2. Azure Maps API                 │ ← Preciso, costo por request
    │     ↓ si falla                     │
    │  3. Fallback provincia/depto       │ ← Siempre funciona
    └────────────────────────────────────┘
         ↓
    (lat, lon, nivel_precision)
```

## RECURSOS AZURE DISPONIBLES

Ya tienes configurado en Azure (East US):
- Azure OpenAI ✅
- Azure Storage ✅
- **Azure Maps** → Necesita habilitarse

**Costo Azure Maps:**
- Geocoding: $0.50 por 1,000 requests (S0 tier)
- Estimado: ~50-100 requests/día = ~$1.50/mes

## IMPLEMENTACIÓN SUGERIDA

**Nuevo archivo:** `src/enrichment/azure_maps_geocoder.py`

```python
"""
Geocoding con Azure Maps para direcciones específicas.
Fallback del gazetteer local cuando no encuentra match.
"""

import os
import requests
from typing import Optional, Tuple
from loguru import logger

AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY")
AZURE_MAPS_ENDPOINT = "https://atlas.microsoft.com/search/address/json"


def geocode_address_azure(
    address: str,
    departamento: str = None,
    pais: str = "Peru"
) -> Optional[Tuple[float, float, str]]:
    """
    Geocodifica una dirección usando Azure Maps.
    
    Args:
        address: Dirección específica (ej: "Avenida Alcides Carrión, Arequipa")
        departamento: Para contexto regional
        pais: País (default: Peru)
    
    Returns:
        (lat, lon, 'azure_maps') o None si falla
    """
    if not AZURE_MAPS_KEY:
        logger.warning("AZURE_MAPS_KEY not configured")
        return None
    
    # Construir query con contexto
    query = f"{address}, {departamento}, {pais}" if departamento else f"{address}, {pais}"
    
    params = {
        "api-version": "1.0",
        "subscription-key": AZURE_MAPS_KEY,
        "query": query,
        "countrySet": "PE",  # Limitar a Perú
        "limit": 1
    }
    
    try:
        response = requests.get(AZURE_MAPS_ENDPOINT, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            result = data["results"][0]
            position = result.get("position", {})
            lat = position.get("lat")
            lon = position.get("lon")
            
            if lat and lon:
                logger.debug(f"Azure Maps geocoded: {address} → ({lat}, {lon})")
                return (lat, lon, "azure_maps")
        
        logger.debug(f"Azure Maps no result for: {address}")
        return None
        
    except Exception as e:
        logger.warning(f"Azure Maps error for '{address}': {e}")
        return None
```

**Modificar:** `src/enrichment/geocoding_service.py`

En el método `geocode_incident()`, añadir Azure Maps como paso intermedio:

```python
def geocode_incident(self, departamento, provincia, distrito, ubicacion_especifica, lat_llm, lon_llm):
    # 1. Si LLM ya dio coordenadas válidas, usarlas
    if lat_llm and lon_llm and not pd.isna(lat_llm):
        return (lat_llm, lon_llm, "llm_directo")
    
    # 2. Intentar gazetteer local (distrito)
    result = self._geocode_from_gazetteer(departamento, provincia, distrito)
    if result:
        return result
    
    # 3. NUEVO: Intentar Azure Maps para ubicación específica
    if ubicacion_especifica:
        result = geocode_address_azure(ubicacion_especifica, departamento)
        if result:
            return result
    
    # 4. Fallback a provincia/departamento
    return self._geocode_fallback(departamento, provincia)
```

## VARIABLES DE ENTORNO REQUERIDAS

Añadir a `.env`:
```
AZURE_MAPS_KEY=your_azure_maps_subscription_key
```

## TESTING

```powershell
# Test unitario del geocoder
python -c "
from src.enrichment.azure_maps_geocoder import geocode_address_azure
result = geocode_address_azure('Avenida Alcides Carrión', 'Arequipa')
print(f'Result: {result}')
"

# Re-procesar un día
python -m scripts.utils.reset_medallion_tables
python -m scripts.core.daily_pipeline --full --date-start 2026-01-15 --date-end 2026-01-15

# Verificar mejora en precisión
python -m scripts.utils.analyze_pipeline_funnel --date 2026-01-15 --show sin_geo
```

## CONSIDERACIONES

1. **Rate limiting:** Azure Maps tiene límites (50 req/seg en S0). El pipeline actual procesa ~300 arts/día, no debería ser problema.

2. **Caching:** Considerar cachear resultados de Azure Maps en DuckDB para no repetir queries.

3. **Costo:** Monitorear uso. Si aumenta mucho, considerar:
   - Cache más agresivo
   - Solo usar para ubicaciones que fallen gazetteer
   - Batch geocoding (más eficiente)

4. **Fallback:** Siempre mantener el fallback a gazetteer/departamento para garantizar 100% con coordenadas.

## RUTA DEL PROYECTO
C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru

## PRIORIDAD

⚠️ **Esta mejora es de prioridad BAJA** porque:
- El fallback actual garantiza 100% con coordenadas
- Los mapas funcionan (solo con menos precisión)
- Implementar M10 primero (recupera artículos perdidos)

Adjunto el ZIP con el código actual. ¿Empezamos?

---

## FIN DEL PROMPT 👆
