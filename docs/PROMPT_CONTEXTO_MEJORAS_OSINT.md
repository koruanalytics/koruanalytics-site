# 🚀 PROMPT DE CONTEXTO - MEJORAS OSINT PERÚ 2026

**Uso:** Copiar este prompt al inicio de un nuevo chat para continuar con las mejoras del backlog.

---

## PROMPT BASE (copiar completo)

```
Continúo el proyecto "OSINT Perú 2026" - Sistema de monitoreo de incidentes de seguridad para elecciones.

## STACK TECNOLÓGICO
- Python 3.12 + DuckDB (Medallion: Bronze → Silver → Gold)
- LLM: Claude Haiku (dev) / Azure OpenAI (prod) via factory pattern
- Ingesta: NewsAPI.ai (7 fuentes peruanas, 8 grupos keywords, ~300 arts/día)
- Producción: Azure (Functions, OpenAI, Maps, Storage) - East US
- Frontend: Power BI + ArcGIS (pendiente)

## ARQUITECTURA ACTUAL
```
NewsAPI.ai → bronze_news → silver_news_enriched → gold_incidents
                              ↓
                         Claude Haiku
                    (clasificación + extracción)
```

## ESTADO DEL PROYECTO
- ✅ P1-P6 completados (pipeline funcional local)
- ⏳ P7 en curso (migración Azure)
- 📋 Backlog de mejoras post-P7 definido

## ARCHIVOS CLAVE
| Archivo | Propósito |
|---------|-----------|
| `src/enrichment/llm_enrichment_pipeline.py` | Pipeline principal, QualityValidator, filtros pre-LLM |
| `src/llm_providers/prompts.py` | Prompt LLM, TIPOS_EVENTO_VALIDOS |
| `config/newsapi_scope_peru_v6.yaml` | 8 grupos keywords (≤15 palabras c/u) |
| `config/geo/peru_gazetteer_full.csv` | 1,893 lugares con lat/lon |
| `src/db/schema.py` | DDLs tablas Medallion |

## FILTROS PRE-LLM EXISTENTES (QualityValidator)
- 40+ países internacionales en blacklist
- 60+ ciudades internacionales
- Patrones regex para títulos internacionales
- Patrones para artículos de resumen/estadísticas
- Patrones de exclusión si menciona Perú explícitamente

## CAMPOS QUE EXTRAE EL LLM ACTUALMENTE
```json
{
  "es_relevante": true/false,
  "es_internacional": true/false,
  "es_resumen": true/false,
  "tipo_evento": "categoria",
  "subtipo": "descripción",
  "muertos": int,
  "heridos": int,
  "departamento": "string",
  "provincia": "string",
  "distrito": "string",
  "actores": [],
  "organizaciones": [],
  "resumen_es": "string",
  "resumen_en": "string",
  "sentiment": "POS/NEG/NEU",
  "confianza": 0.0-1.0
}
```

## TIPOS_EVENTO_VALIDOS (14 categorías)
violencia_armada, crimen_violento, violencia_sexual, secuestro, feminicidio, 
extorsion, accidente_grave, desastre_natural, protesta, disturbio, 
terrorismo, crimen_organizado, violencia_politica, operativo_seguridad, no_relevante

## RUTA DEL PROYECTO
C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru

## MEJORA A IMPLEMENTAR
[ESPECIFICAR MEJORA DEL BACKLOG - ver sección siguiente]

Adjunto el ZIP con el código actual. ¿Empezamos?
```

---

## BACKLOG DE MEJORAS (especificar una)

### 🔴 PRIORIDAD ALTA

**M9 - Fix encoding UTF-8 en pipeline completo**
```
MEJORA: M9 - Fix encoding UTF-8 en pipeline completo
OBJETIVO: Normalizar caracteres especiales (acentos, ñ) en todas las capas del pipeline
ARCHIVOS: src/ingestion/newsapi_ai_ingest.py, src/enrichment/llm_enrichment_pipeline.py, src/processing/normalize_newsapi_ai.py
ESFUERZO: 2-3 horas
IMPACTO: ALTO - Sin esto, datos corruptos en exports y Power BI

PROBLEMA DETECTADO:
- Los campos de texto tienen escapes Unicode: \u00e1 en lugar de á
- Afecta: actores, organizaciones, titulo, resumen, ubicacion_display
- Se propaga desde bronze → silver → gold
- Power BI muestra caracteres corruptos

CAUSA RAÍZ:
1. NewsAPI.ai puede devolver JSON con escapes Unicode
2. El LLM (Claude/OpenAI) puede devolver JSON con escapes
3. No hay normalización UTF-8 en ningún punto del pipeline

SOLUCIÓN REQUERIDA:
1. INGESTA (Bronze): Normalizar textos al guardar en bronze_news
   - Archivo: src/ingestion/newsapi_ai_ingest.py
   - Función: decode unicode escapes antes de INSERT

2. ENRIQUECIMIENTO (Silver): Normalizar respuesta del LLM
   - Archivo: src/enrichment/llm_enrichment_pipeline.py
   - Función: limpiar JSON response antes de INSERT a silver

3. EXPORT: Garantizar UTF-8-sig con BOM para Power BI
   - Archivo: scripts/utils/export_gold_to_csv.py (ya creado)

FUNCIÓN DE NORMALIZACIÓN:
```python
import codecs
import re

def normalize_unicode(text: str) -> str:
    """Convierte escapes Unicode a caracteres reales."""
    if not text or not isinstance(text, str):
        return text
    # Detectar y convertir \uXXXX a caracteres
    if '\\u' in text:
        try:
            return codecs.decode(text, 'unicode_escape')
        except:
            # Fallback con regex
            pattern = r'\\u([0-9a-fA-F]{4})'
            return re.sub(pattern, lambda m: chr(int(m.group(1), 16)), text)
    return text
```

VALIDACIÓN:
- Verificar que bronze_news tenga acentos correctos
- Verificar que silver_news_enriched tenga acentos correctos  
- Verificar que gold_incidents tenga acentos correctos
- Export CSV debe mostrar: José, María, Ángel, Perú (no \u00e9, \u00ed, etc.)
```

**M1 - Geocoding con gazetteer**
```
MEJORA: M1 - Geocoding con gazetteer
OBJETIVO: Agregar lat/lon a gold_incidents usando dim_places_pe (1,893 lugares)
ARCHIVOS: src/enrichment/llm_enrichment_pipeline.py
ESFUERZO: 3-4 horas
IMPACTO: ALTO - Habilita mapas en Power BI

DETALLE:
- Crear método geocode_incident(departamento, provincia, distrito)
- Estrategia fallback: distrito → provincia → departamento capital
- Añadir campo nivel_geo ('distrito'|'provincia'|'departamento')
- Integrar en build_gold_incidents()
```

**M2 - Grupo "Corrupción" en ingesta**
```
MEJORA: M2 - Grupo "Corrupción" en ingesta
OBJETIVO: Añadir grupo 9 de keywords para capturar noticias de corrupción
ARCHIVOS: config/newsapi_scope_peru_v6.yaml, src/llm_providers/prompts.py
ESFUERZO: 30 minutos
IMPACTO: MEDIO - +20-50 artículos/día relevantes para contexto electoral

KEYWORDS PROPUESTOS (14 palabras):
corrupcion, corrupto, soborno, coima, peculado, malversacion, 
lavado dinero, enriquecimiento ilicito, contraloria, fiscalia, 
investigado, detenido, prision preventiva, allanamiento

TAMBIÉN: Añadir 'corrupcion' a TIPOS_EVENTO_VALIDOS en prompts.py
```

---

### 🟡 PRIORIDAD MEDIA

**M3 - Alinear keywords con ACLED**
```
MEJORA: M3 - Alinear keywords con taxonomía ACLED
OBJETIVO: Refactorizar grupos para mapear a ACLED (Battles, VAC, Protests, etc.)
ARCHIVOS: config/newsapi_scope_peru_v7.yaml (nuevo), src/llm_providers/prompts.py
ESFUERZO: 6-8 horas
IMPACTO: MEDIO - Mejor clasificación, facilita export ACLED

MAPEO ACLED:
- Battles: Armed clash → enfrentamiento armado, tiroteo, balacera
- Violence against civilians: Attack → asesinato, homicidio, sicariato
- Sexual violence → violacion, abuso sexual, feminicidio
- Protests: Peaceful → protesta, manifestacion, marcha
- Riots: Violent demonstration → disturbios, vandalismo, saqueo
- Strategic developments: Arrests → detencion, captura, operativo
```

**M4 - Campo motivo_aparente**
```
MEJORA: M4 - Campo motivo_aparente
OBJETIVO: Extraer motivo del incidente para análisis de patrones
ARCHIVOS: src/llm_providers/prompts.py, src/db/schema.py
ESFUERZO: 1 hora
IMPACTO: MEDIO - Análisis de patrones de violencia

VALORES: robo, ajuste_cuentas, violencia_familiar, riña, 
resistencia_autoridad, extorsion, pasional, politico, desconocido, accidental

CAMBIOS:
1. Añadir al ENRICHMENT_PROMPT en prompts.py
2. ALTER TABLE silver_news_enriched ADD COLUMN motivo_aparente VARCHAR
3. ALTER TABLE gold_incidents ADD COLUMN motivo_aparente VARCHAR
4. Actualizar INSERT en llm_enrichment_pipeline.py
```

**M5 - Campo victima_perfil**
```
MEJORA: M5 - Campo victima_perfil
OBJETIVO: Clasificar perfil de víctima para análisis de targeting
ARCHIVOS: src/llm_providers/prompts.py, src/db/schema.py
ESFUERZO: 45 minutos
IMPACTO: BAJO - Análisis de targeting

VALORES: comerciante, transportista, autoridad, candidato, periodista, 
abogado, empresario, estudiante, mujer, menor, civil, desconocido
```

**M6 - Campo arma_usada**
```
MEJORA: M6 - Campo arma_usada
OBJETIVO: Registrar tipo de arma en incidentes violentos
ARCHIVOS: src/llm_providers/prompts.py, src/db/schema.py
ESFUERZO: 45 minutos
IMPACTO: BAJO - Análisis de modalidad

VALORES: arma_fuego, arma_blanca, objeto_contundente, explosivo, 
vehiculo, fuego, veneno, ninguna, desconocida
```

---

### 🟢 PRIORIDAD BAJA

**M7 - Mejorar detección es_internacional**
```
MEJORA: M7 - Mejorar detección es_internacional
OBJETIVO: Añadir patrones faltantes al filtro pre-LLM
ARCHIVOS: src/enrichment/llm_enrichment_pipeline.py (QualityValidator)
ESFUERZO: 30 minutos
IMPACTO: BAJO - Ahorro marginal de tokens

PATRONES A AÑADIR:
- Entretenimiento: k-pop, bts, blackpink, anime, netflix, taylor swift
- Deportes internacionales: mundial, copa del mundo, eurocopa
- Empresas tech: elon musk, tesla, spacex, meta, amazon
- Conflictos: frontera colombo-venezolana, conflicto en ucrania
```

**M8 - Mejorar detección es_resumen**
```
MEJORA: M8 - Mejorar detección es_resumen
OBJETIVO: Añadir patrones faltantes para artículos de resumen
ARCHIVOS: src/enrichment/llm_enrichment_pipeline.py (QualityValidator)
ESFUERZO: 30 minutos
IMPACTO: BAJO - Menos ruido en gold_incidents

PATRONES A AÑADIR:
- Resúmenes: resumen semanal, lo más leído, recap
- Predicciones: predicciones para 2026, tendencias para
- Conmemoraciones: se cumplen X años, aniversario de
```

---

## EJEMPLO DE USO

Para implementar M2 (Grupo Corrupción), copiar:

```
Continúo el proyecto "OSINT Perú 2026" - Sistema de monitoreo de incidentes de seguridad para elecciones.

## STACK TECNOLÓGICO
- Python 3.12 + DuckDB (Medallion: Bronze → Silver → Gold)
- LLM: Claude Haiku (dev) / Azure OpenAI (prod) via factory pattern
- Ingesta: NewsAPI.ai (7 fuentes peruanas, 8 grupos keywords, ~300 arts/día)

## ARCHIVOS CLAVE
| Archivo | Propósito |
|---------|-----------|
| `config/newsapi_scope_peru_v6.yaml` | 8 grupos keywords (≤15 palabras c/u) |
| `src/llm_providers/prompts.py` | Prompt LLM, TIPOS_EVENTO_VALIDOS |

## RUTA DEL PROYECTO
C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru

## MEJORA A IMPLEMENTAR
MEJORA: M2 - Grupo "Corrupción" en ingesta
OBJETIVO: Añadir grupo 9 de keywords para capturar noticias de corrupción
ARCHIVOS: config/newsapi_scope_peru_v6.yaml, src/llm_providers/prompts.py
ESFUERZO: 30 minutos
IMPACTO: MEDIO - +20-50 artículos/día relevantes para contexto electoral

KEYWORDS PROPUESTOS (14 palabras):
corrupcion, corrupto, soborno, coima, peculado, malversacion, 
lavado dinero, enriquecimiento ilicito, contraloria, fiscalia, 
investigado, detenido, prision preventiva, allanamiento

TAMBIÉN: Añadir 'corrupcion' a TIPOS_EVENTO_VALIDOS en prompts.py

Adjunto el ZIP con el código actual. ¿Empezamos?
```

---

## COMANDOS ÚTILES

```powershell
# Crear ZIP solo con código (sin venv/data)
Compress-Archive -Path src, scripts, config -DestinationPath OSINT_code.zip -Force

# Ejecutar pipeline completo
python -m scripts.core.daily_pipeline --full

# Ver estado de tablas
python -m src.enrichment.llm_enrichment_pipeline --status

# Validar schema
python -m src.enrichment.llm_enrichment_pipeline --validate-schema

# Procesar N artículos
python -m src.enrichment.llm_enrichment_pipeline --process-new 50
```

---

## NOTAS IMPORTANTES

1. **Límite API NewsAPI.ai:** Máximo 15 PALABRAS por query (no keywords)
2. **Cada grupo de keywords = 1 query separada al API**
3. **Todas las mejoras son compatibles con Azure** - solo modifican Python/YAML
4. **El gazetteer tiene 1,893 lugares** con lat/lon listos para geocoding
5. **QualityValidator ya filtra ~10-15% de artículos** antes del LLM

---

*Documento generado: 2026-01-11*
*Backlog completo en: BACKLOG_MEJORAS_POST_P7.md*
