# Prompt para Nuevo Chat - Continuar OSINT Perú 2026

## COPIAR Y PEGAR ESTE PROMPT:

```
Estoy trabajando en OSINT Perú 2026. Te adjunto el documento CONTEXTO_SESION_ACTUAL.md con el estado actual.

**Resumen rápido:**
- Sistema de monitoreo de incidentes de seguridad electoral
- Pipeline: NewsAPI.ai → DuckDB → Clasificación ACLED → Casualties → Sentiment
- BD: data/osint_dw.duckdb

**Lo que acabamos de hacer:**
1. Mejorado dedupe (ahora por título, no solo URI)
2. Corregido falsos positivos en casualties (sismos, estadísticas)
3. Creado nuevo scope v3 con 7 grupos optimizados

**Tareas pendientes inmediatas:**
1. Verificar estado final del dedupe
2. Reconstruir incidentes con datos limpios
3. Integrar dedupe por título en script core (src/processing/dedupe_newsapi_ai_in_duckdb.py)
4. Commit de cambios

**Lo que necesito ahora:**
[INDICA QUÉ TAREA QUIERES CONTINUAR]

Por favor revisa el documento adjunto antes de responder.
```

---

## ARCHIVOS A ADJUNTAR:
1. CONTEXTO_SESION_ACTUAL.md (obligatorio)
2. Opcionalmente: CONTEXTO_INTERNO_OSINT_PERU.md (contexto general del proyecto)

---

## VARIANTES DEL PROMPT

### Para continuar tareas pendientes:
```
OSINT Perú 2026. Adjunto CONTEXTO_SESION_ACTUAL.md.

Quiero continuar con la tarea: [NÚMERO DE TAREA]
- 1: Verificar estado dedupe
- 2: Reconstruir incidentes
- 3: Integrar dedupe en script core
- 4: Commit cambios
- 5: Mejorar geo-parsing
```

### Para verificar estado:
```
OSINT Perú 2026. Adjunto contexto.

Dame comandos para verificar el estado actual de:
- Artículos (raw vs dedup)
- Incidentes
- Víctimas (muertos/heridos)
- Geo-parsing
```

### Para debugging:
```
OSINT Perú 2026. Adjunto contexto.

Error al ejecutar [COMANDO]:
[PEGA EL ERROR]

¿Cómo lo soluciono?
```
