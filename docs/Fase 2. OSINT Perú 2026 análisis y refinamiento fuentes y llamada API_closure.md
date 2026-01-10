# Acción de Cierre de Chat del Proyecto: OSINT Perú 2026

## Metadatos del Chat
| Campo | Valor |
|-------|-------|
| **Nombre del proyecto** | OSINT Perú 2026 - Sistema de Monitoreo de Incidentes de Seguridad |
| **Fecha de inicio del chat** | 2026-01-05 |
| **Fecha de cierre** | 2026-01-05 |
| **Duración estimada** | 1 sesión corta |
| **Enfoque del chat** | Re-validación de cobertura API y estrategia de grupos temáticos |

---

## 1. RESUMEN EJECUTIVO

Sistema de monitoreo de incidentes de seguridad para elecciones Perú 2026. Pipeline automatizado: NewsAPI.ai → DuckDB (Medallion) → Clasificación ACLED → Casualties → Sentiment → Alertas. **Este chat se enfocó en clarificar la estrategia de 12 grupos temáticos para sortear la limitación de 15 keywords del API**, no se ejecutó código ni se realizaron cambios.

---

## 2. STACK TECNOLÓGICO

| Categoría | Tecnología | Versión/Notas |
|-----------|------------|---------------|
| Lenguaje | Python | 3.x |
| Base de datos | DuckDB | Arquitectura Medallion (Bronze/Silver/Gold) |
| API de noticias | NewsAPI.ai | Cliente custom en `src/ingest/` |
| LLM | Claude Haiku | Clasificación y enriquecimiento |
| NLP | pysentimiento | Análisis de sentimiento (RoBERTuito) |
| Resúmenes | sumy | Extractivos |
| Cloud (pendiente) | Azure | OpenAI, AI Search, Maps |
| IDE | VS Code | - |

---

## 3. ESTRUCTURA DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── settings.yaml              # API keys, límites, paths
│   └── newsapi_scope_peru.yaml    # 12 grupos de búsqueda temáticos
├── data/
│   ├── osint_dw.duckdb            # BD principal
│   └── raw/newsapi_ai/*.json      # JSON crudos del API
├── scripts/
│   ├── run_newsapi_ai_job.py      # Ingesta de noticias
│   ├── build_fct_daily_report.py  # Generar reportes
│   ├── extract_casualties.py      # Extraer muertos/heridos
│   ├── extract_sentiment.py       # Análisis de sentimiento
│   ├── generate_alerts.py         # Sistema de alertas
│   ├── daily_ingestion.py         # Ingesta diaria completa
│   └── add_concept_fields.py      # Extraer personas/orgs
├── src/
│   ├── ingest/                    # Cliente NewsAPI.ai
│   ├── incidents/                 # Clasificación ACLED
│   ├── processing/                # Dedupe, normalización
│   └── utils/                     # Config, helpers
└── docs/
    └── PLAN_INGESTA.md            # Plan detallado
```

---

## 4. ARCHIVOS CLAVE Y SU ESTADO

| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `config/newsapi_scope_peru.yaml` | ✅ Completo | Define los 12 grupos temáticos de búsqueda |
| `data/osint_dw.duckdb` | 🔄 En progreso | BD con ~43 incidentes deduplicados |
| `scripts/daily_ingestion.py` | ✅ Completo | Orquesta ingesta diaria |
| `src/incidents/acled_rules.py` | ✅ Completo | Keywords ACLED expandidas |

---

## 5. ESTRATEGIA DE GRUPOS TEMÁTICOS (PUNTO CLAVE DEL CHAT)

### El Problema
NewsAPI.ai tiene **límite de 15 keywords por query**. El proyecto necesita cubrir múltiples categorías temáticas.

### La Solución Implementada
El archivo `newsapi_scope_peru.yaml` divide las búsquedas en **12 grupos temáticos**:

| # | Grupo | Enfoque |
|---|-------|---------|
| 1 | `elections` | Proceso electoral, JNE, ONPE, candidatos |
| 2 | `political_violence` | Violencia política, ataques a funcionarios |
| 3 | `protests` | Marchas, manifestaciones, huelgas |
| 4 | `crime_security` | Crimen organizado, asaltos, homicidios |
| 5 | `social_conflict` | Conflictos sociales, bloqueos |
| 6 | `narcotraffic` | Narcotráfico, VRAEM, cocaína |
| 7 | `terrorism` | Sendero Luminoso, terrorismo |
| 8 | `corruption` | Corrupción, Lava Jato, fiscalía |
| 9 | `mining_conflicts` | Conflictos mineros, medio ambiente |
| 10 | `indigenous` | Comunidades indígenas, amazónicas |
| 11 | `migration` | Migración venezolana, frontera |
| 12 | `natural_disasters` | Desastres naturales, emergencias |

### Flujo de Ejecución
```
Por cada fecha de ingesta:
    Para cada uno de los 12 grupos:
        → Llamada al API con ≤15 keywords del grupo
        → Guardar JSON en data/raw/newsapi_ai/
    → Deduplicar entre grupos (título normalizado)
    → Cargar a stg_news_newsapi_ai
```

**Total: 12 llamadas al API por día de ingesta**

### Métricas Actuales
- ~230 artículos raw capturados
- ~43 únicos después de deduplicación (81% duplicados entre grupos)
- Incidentes clasificados: ~43
- Muertos detectados: 10
- Heridos detectados: 33

---

## 6. PROBLEMAS CONOCIDOS / DEUDA TÉCNICA

| # | Problema | Impacto | Solución propuesta | Prioridad |
|---|----------|---------|-------------------|-----------|
| 1 | Errores de API por limitaciones | Alto | Investigar: rate limiting, timeout, o quota | **Alta** |
| 2 | Geo-parsing bajo (21%) | Medio | Mejorar extracción de coordenadas | Media |
| 3 | Sentiment NEU dominante | Bajo | Evaluar otro modelo o ajustar umbral | Baja |
| 4 | Ingesta histórica pendiente (Dec 1-19) | Alto | Ejecutar con delays entre llamadas | Alta |

### ⚠️ Errores del API (Tema Principal del Chat)
El usuario reporta errores recurrentes al usar el API. **Causas probables:**
1. **Rate limiting** - Demasiadas llamadas seguidas (12 por día × días históricos)
2. **Timeout** - Queries muy amplias
3. **Quota excedida** - Límite del plan

**Acción requerida:** Compartir mensaje de error exacto para diagnóstico preciso.

---

## 7. PRÓXIMOS PASOS (PRIORIZADO)

### Alta Prioridad
1. **[INMEDIATO]** Diagnosticar error exacto del API - Capturar mensaje de error completo
2. **[INMEDIATO]** Implementar delays entre llamadas si es rate limiting:
   ```python
   import time
   for group in groups:
       fetch_news(group)
       time.sleep(2)  # 2 segundos entre llamadas
   ```

### Media Prioridad
3. **[PRÓXIMA SESIÓN]** Ejecutar ingesta histórica Dec 1-19 con throttling
4. **[PRÓXIMA SESIÓN]** Validar cobertura por grupo temático con queries diagnósticas

### Baja Prioridad
5. **[CUANDO SEA POSIBLE]** Evaluar fuentes de enriquecimiento estático (ACLED, Defensoría)

---

## 8. QUERIES DIAGNÓSTICAS PENDIENTES

```sql
-- Query 1: Distribución por grupo de búsqueda
SELECT 
    json_extract_string(metadata, '$.search_group') as search_group,
    COUNT(*) as articles,
    MIN(incident_date) as fecha_min,
    MAX(incident_date) as fecha_max
FROM stg_news_newsapi_ai
GROUP BY 1
ORDER BY 2 DESC;

-- Query 2: Tasa de duplicados por fuente
SELECT 
    source_name,
    COUNT(*) as total,
    COUNT(DISTINCT url) as unicos
FROM stg_news_newsapi_ai
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15;

-- Query 3: Cobertura temporal (detectar huecos)
SELECT 
    incident_date,
    COUNT(*) as articles
FROM stg_news_newsapi_ai_dedup
WHERE incident_date >= '2025-12-01'
GROUP BY 1
ORDER BY 1;
```

---

## 9. FUENTES DE ENRIQUECIMIENTO PROPUESTAS

| Fuente | Tipo | Datos que aporta | Prioridad |
|--------|------|------------------|-----------|
| ACLED Perú | Dataset histórico | Incidentes validados, coordenadas | Alta |
| Defensoría del Pueblo | PDF mensual | Reporte de conflictos sociales | Alta |
| OCHA ReliefWeb | API/PDF | Alertas humanitarias | Media |
| JNE/ONPE | PDF/Web | Datos electorales | Media |
| INEI | Excel | Población por distrito | Baja |

---

## 10. COMANDOS ÚTILES

```powershell
# Health check rápido
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SELECT COUNT(*) as incidents, SUM(deaths) as deaths, SUM(injuries) as injuries FROM fct_daily_report').fetchdf())"

# Ingesta diaria (ayer)
python scripts/daily_ingestion.py

# Ingesta histórica con throttling (propuesto)
python scripts/daily_ingestion.py --historical --start 2025-12-01 --max-total 1000 --delay 2

# Reconstruir reportes
python scripts/build_fct_daily_report.py --rebuild-all
```

---

## 11. NOTAS PARA EL PRÓXIMO CHAT

### ⚠️ Trampas / Cosas que costó descubrir
- **81% de duplicados entre grupos:** Es normal, la deduplicación maneja esto
- **PowerShell y comillas:** Usar scripts .py directamente, evitar one-liners complejos
- **pysentimiento es lento:** ~1 segundo por incidente, planificar para lotes grandes

### 💡 Tips importantes
- Siempre verificar el error exacto del API antes de modificar código
- Los 12 grupos temáticos son la estrategia correcta para sortear el límite de 15 keywords
- Ejecutar queries diagnósticas para validar cobertura antes de cambios mayores

### 📝 Contexto adicional
El usuario menciona estar "dando vueltas en círculos" - sugiere simplificar el enfoque y resolver un problema a la vez, empezando por el error específico del API.

---

## 12. PROMPT DE CONTINUACIÓN

> **Copia esto al inicio del nuevo chat:**
>
> ```
> Continúo el proyecto "OSINT Perú 2026".
> 
> Stack: Python 3.x + DuckDB (Medallion) + NewsAPI.ai + Claude Haiku
> IDE: VS Code
> 
> Estado actual: Pipeline funcional con 12 grupos temáticos, ~43 incidentes. Errores recurrentes del API al ejecutar.
> 
> Último avance: Clarificamos la estrategia de 12 grupos para sortear límite de 15 keywords.
> 
> Siguiente tarea: Diagnosticar error exacto del API (rate limit, timeout, o quota) y aplicar fix.
> 
> Adjunto: 
> - cierre_chat_osint_peru_2026_2026-01-05.md
> - CONTEXTO_INTERNO_OSINT_PERU.md
> 
> ERROR DEL API (pegar aquí el mensaje exacto):
> [PEGAR ERROR]
> ```

---

## Historial de Sesiones

| Sesión | Fecha | Enfoque principal | Logros |
|--------|-------|-------------------|--------|
| Este chat | 2026-01-05 | Re-validación cobertura API | Documentada estrategia de 12 grupos, queries diagnósticas preparadas |

---

**Última actualización**: 2026-01-05
**Versión documento contexto base**: 1.0 (2025-12-20)
