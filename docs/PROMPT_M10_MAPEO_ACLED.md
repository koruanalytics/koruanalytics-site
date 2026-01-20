# PROMPT CONTEXTO - M10: Mapeo ACLED inglés → tipos válidos

## COPIAR TODO DESDE AQUÍ 👇

---

Continúo el proyecto "OSINT Perú 2026" - Sistema de monitoreo de incidentes de seguridad para elecciones.

## STACK TECNOLÓGICO
- Python 3.12 + DuckDB (Medallion: Bronze → Silver → Gold)
- LLM: Claude Haiku (dev) / Azure OpenAI (prod) via factory pattern
- Ingesta: NewsAPI.ai (7 fuentes peruanas, 9 grupos keywords)

## PROBLEMA DETECTADO

El LLM (Claude Haiku) a veces devuelve `tipo_evento` usando taxonomía ACLED en inglés en lugar de los tipos válidos en español. Esto causa que artículos **relevantes** se pierdan marcándose como `no_relevante`:

```
2026-01-18 11:57:14 | WARNING | tipo_evento inválido 'violence against civilians', usando 'no_relevante'
2026-01-18 11:57:27 | WARNING | tipo_evento inválido 'protests', usando 'no_relevante'
2026-01-18 11:57:55 | WARNING | tipo_evento inválido 'strategic developments', usando 'no_relevante'
2026-01-18 11:58:51 | WARNING | tipo_evento inválido 'sexual violence', usando 'no_relevante'
```

**Impacto:** En un run de 303 artículos, ~30-40 fueron marcados incorrectamente como `no_relevante` cuando deberían ser incidentes válidos.

## MEJORA A IMPLEMENTAR

```
MEJORA: M10 - Mapeo ACLED inglés → tipos válidos
OBJETIVO: Recuperar artículos relevantes que el LLM clasifica con taxonomía ACLED en inglés
ARCHIVOS: src/enrichment/llm_enrichment_pipeline.py
ESFUERZO: 30 minutos
IMPACTO: ALTO - Recupera ~10-15% de artículos que se pierden actualmente
```

## TIPOS_EVENTO_VALIDOS ACTUALES (14 categorías)

```python
TIPOS_EVENTO_VALIDOS = {
    'violencia_armada',      # Enfrentamientos, tiroteos, balaceras
    'crimen_violento',       # Asesinatos, homicidios, sicariato
    'violencia_sexual',      # Violaciones, abuso sexual
    'secuestro',             # Secuestros, desapariciones forzadas
    'feminicidio',           # Asesinato de mujeres por género
    'extorsion',             # Extorsión, cobro de cupos
    'accidente_grave',       # Accidentes con víctimas
    'desastre_natural',      # Sismos, inundaciones, huaycos
    'protesta',              # Marchas, manifestaciones, paros
    'disturbio',             # Disturbios, vandalismo, saqueos
    'terrorismo',            # Ataques terroristas, VRAEM
    'crimen_organizado',     # Narcotráfico, bandas criminales
    'violencia_politica',    # Ataques a candidatos/funcionarios
    'operativo_seguridad',   # Detenciones, capturas, operativos
    'corrupcion',            # Sobornos, peculado, lavado dinero
    'no_relevante'           # Deportes, farándula, economía
}
```

## MAPEO ACLED INGLÉS → TIPOS VÁLIDOS PROPUESTO

```python
ACLED_TO_TIPOS = {
    # Violence categories
    'violence against civilians': 'crimen_violento',
    'sexual violence': 'violencia_sexual',
    'attack': 'crimen_violento',
    'abduction/forced disappearance': 'secuestro',
    
    # Battle categories  
    'battles': 'violencia_armada',
    'armed clash': 'violencia_armada',
    'government regains territory': 'operativo_seguridad',
    
    # Explosion categories
    'explosions/remote violence': 'terrorismo',
    'remote explosive/landmine/ied': 'terrorismo',
    'grenade': 'terrorismo',
    'shelling/artillery/missile attack': 'terrorismo',
    'suicide bomb': 'terrorismo',
    
    # Protest categories
    'protests': 'protesta',
    'peaceful protest': 'protesta',
    'protest with intervention': 'protesta',
    'excessive force against protesters': 'disturbio',
    
    # Riot categories
    'riots': 'disturbio',
    'violent demonstration': 'disturbio',
    'mob violence': 'disturbio',
    
    # Strategic developments
    'strategic developments': 'operativo_seguridad',
    'arrests': 'operativo_seguridad',
    'agreement': 'operativo_seguridad',
    'looting/property destruction': 'disturbio',
    
    # Variantes con guiones/underscores
    'violence_against_civilians': 'crimen_violento',
    'sexual_violence': 'violencia_sexual',
    'strategic_developments': 'operativo_seguridad',
}
```

## ARCHIVO A MODIFICAR

**Archivo:** `src/enrichment/llm_enrichment_pipeline.py`

**Ubicación:** Método `validar_respuesta_llm()` en clase `QualityValidator` (alrededor de línea 294-352)

**Código actual que genera el warning:**
```python
# Validar tipo_evento contra lista permitida
if tipo_evento not in TIPOS_EVENTO_VALIDOS:
    logger.warning(f"tipo_evento inválido '{tipo_evento}', usando 'no_relevante'")
    tipo_evento = 'no_relevante'
```

**Cambio requerido:** Antes de marcar como `no_relevante`, intentar mapear desde ACLED inglés.

## VALIDACIÓN

Después de implementar, re-ejecutar el pipeline y verificar:
1. Los warnings de "tipo_evento inválido" deben mostrar el mapeo aplicado
2. El número de incidentes en gold debe aumentar (~10-15%)
3. No deben aparecer tipos ACLED en gold_incidents

## COMANDO PARA PROBAR

```powershell
# Vaciar y re-procesar
python -m scripts.utils.reset_medallion_tables
python -m scripts.core.daily_pipeline --full --date-start 2026-01-15 --date-end 2026-01-15

# Verificar funnel
python -m scripts.utils.analyze_pipeline_funnel --date 2026-01-15 --detailed
```

## RUTA DEL PROYECTO
C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru

Adjunto el ZIP con el código actual. ¿Empezamos?

---

## FIN DEL PROMPT 👆
