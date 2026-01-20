# OSINT PERÚ 2026 - CONTEXTO TÉCNICO PARA FRONTEND

## 📋 RESUMEN EJECUTIVO

Sistema de monitoreo de incidentes de seguridad para las elecciones de Perú 2026.
El backend está operativo con arquitectura Medallion en DuckDB, enriquecimiento LLM con Claude Haiku, y pipeline automatizado.

**Objetivo del nuevo chat**: Diseñar e implementar el frontend (Power BI embebido + React + Chat IA).

---

## 🏗️ ARQUITECTURA BACKEND (YA IMPLEMENTADA)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA MEDALLION - BACKEND                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BRONZE (Raw)              SILVER (Enriched)         GOLD (Facts)           │
│  ─────────────             ─────────────────         ────────────           │
│  bronze_news (722)   ───►  silver_news_enriched ───► gold_incidents         │
│  • body COMPLETO           • es_relevante            • Solo relevantes      │
│  • all API fields          • tipo_evento             • Geolocalizado        │
│  • source_uri              • muertos/heridos         • Para dashboard       │
│                            • departamento                                    │
│                            • ubicacion               gold_daily_stats       │
│                            • actores[]               • Agregados            │
│                            • resumen_es/en           • KPIs                 │
│                            • sentiment                                       │
│                            • confidence              vw_daily_report        │
│                                                      • Vista para informes  │
│                                                                              │
│  dim_places_pe (1,893) - Gazetteer de Perú (departamentos, provincias,      │
│                          distritos con UBIGEO)                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tablas Gold (para consumo en Power BI)

**gold_incidents** - Incidentes relevantes de seguridad
```sql
incident_id VARCHAR PRIMARY KEY
tipo_evento VARCHAR          -- violencia_armada, crimen_violento, feminicidio, 
                             -- secuestro, accidente_grave, desastre_natural,
                             -- protesta, disturbio, terrorismo, crimen_organizado,
                             -- violencia_politica, operativo_seguridad, extorsion
subtipo VARCHAR
fecha_incidente DATE
fecha_publicacion TIMESTAMP
muertos INTEGER
heridos INTEGER
departamento VARCHAR         -- 25 departamentos de Perú
provincia VARCHAR
distrito VARCHAR
ubicacion_display VARCHAR    -- Para mostrar en UI
lat DOUBLE                   -- Coordenadas para mapa
lon DOUBLE
tiene_geo BOOLEAN
actores VARCHAR              -- Personas mencionadas
organizaciones VARCHAR       -- Orgs mencionadas
titulo VARCHAR
resumen VARCHAR              -- Generado por LLM
url VARCHAR
source_name VARCHAR          -- El Comercio, La República, Correo, Andina, etc.
sentiment VARCHAR            -- POS, NEG, NEU
relevancia_score DOUBLE      -- 0-1
```

**gold_daily_stats** - Estadísticas diarias agregadas
```sql
fecha DATE PRIMARY KEY
total_incidentes INTEGER
total_muertos INTEGER
total_heridos INTEGER
por_tipo_json VARCHAR        -- {"crimen_violento": 5, "accidente": 3}
por_departamento_json VARCHAR -- {"Lima": 10, "Arequipa": 3}
incidentes_con_geo INTEGER
incidentes_alta_relevancia INTEGER
variacion_vs_ayer DOUBLE
```

**dim_places_pe** - Gazetteer de Perú
```sql
place_id VARCHAR
name VARCHAR
type VARCHAR                 -- department, province, district
ubigeo VARCHAR               -- Código UBIGEO para joins
parent_id VARCHAR
lat DOUBLE
lon DOUBLE
```

### Fuentes de Datos
- **NewsAPI.ai**: 7 fuentes peruanas (~650 artículos/día)
  - elcomercio.pe, larepublica.pe, diariocorreo.pe, andina.pe, gestion.pe, rpp.pe, ojo.pe
- **LLM (Claude Haiku)**: Clasificación, extracción de víctimas, geolocalización, resúmenes
- **Futuro**: GDELT, ACLED oficial, fuentes gubernamentales

---

## 🎯 ARQUITECTURA FRONTEND (A IMPLEMENTAR)

### Decisiones Tomadas

| Componente | Decisión | Razón |
|------------|----------|-------|
| **Visualización** | Power BI Pro embebido | Interactividad, ArcGIS, filtros en tiempo real |
| **Mapas** | ArcGIS for Power BI | Coropléticos + puntos lat/lon, filtrado nativo |
| **Frontend** | React + Azure Static Web Apps | Look de "plataforma", control total |
| **Auth** | Azure AD B2B | Usuarios externos (cualquier cuenta), invitación controlada |
| **Dominio** | osint.tudominio.com | Profesional, independiente |
| **Chat IA** | RAG con Azure OpenAI + AI Search | Consultas en lenguaje natural sobre noticias |
| **PDFs** | Power Automate | Diarios automáticos + on-demand |

### Arquitectura Visual

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         osint.tudominio.com                                │
│                    Azure Static Web Apps (React)                           │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐  ┌────────────────────────────────────────────────────┐ │
│  │   SIDEBAR    │  │              ÁREA PRINCIPAL                        │ │
│  │              │  │                                                    │ │
│  │  🏠 Executive│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  🗺️ Mapa     │  │  │                                              │  │ │
│  │  📈 Tendencias│  │  │     POWER BI EMBEBIDO                        │  │ │
│  │  📍 Regiones │  │  │     (report multipágina)                      │  │ │
│  │  📋 Datos    │  │  │     - Sin barras de Power BI                  │  │ │
│  │              │  │  │     - Filtros nativos (slicers)               │  │ │
│  │  ─────────── │  │  │     - ArcGIS para mapas                       │  │ │
│  │              │  │  │                                              │  │ │
│  │  💬 Chat IA  │  │  └──────────────────────────────────────────────┘  │ │
│  │              │  │                                                    │ │
│  │  📥 Descargar│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  📧 Enviar   │  │  │  💬 "¿Qué pasó en Lima ayer?"                │  │ │
│  │              │  │  │  → Respuesta con citas de noticias           │  │ │
│  └──────────────┘  │  └──────────────────────────────────────────────┘  │ │
│                    └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   POWER BI        │    │  AZURE FUNCTIONS  │    │   AZURE AI        │
│   SERVICE         │    │                   │    │                   │
│                   │    │  /api/chat        │    │  AI Search        │
│  Workspace OSINT  │    │  /api/refresh     │    │  (índice noticias)│
│  - Dataset        │    │  /api/report      │    │                   │
│  - Report 5 pág   │    │                   │    │  OpenAI           │
│  - ArcGIS visual  │    │                   │    │  (embeddings+chat)│
└─────────┬─────────┘    └───────────────────┘    └───────────────────┘
          │
          ▼
┌───────────────────┐
│  AZURE DATABASE   │
│  (PostgreSQL o    │
│   Synapse)        │
│                   │
│  gold_incidents   │
│  gold_daily_stats │
│  dim_places_pe    │
└───────────────────┘
```

---

## 📊 DASHBOARDS POWER BI (5 Páginas)

### Página 1: Executive / Daily Brief
- KPIs principales (incidentes hoy, muertos, heridos, variación vs ayer)
- Top 5 incidentes del día
- Alertas activas
- Mini-mapa de calor

### Página 2: Mapa Operacional (ArcGIS)
- **Capa 1**: Puntos con lat/lon de incidentes (clustering, color por tipo)
- **Capa 2**: Coroplético por departamento (gradiente por conteo)
- Tooltips enriquecidos (título, fuente, víctimas, sentiment)
- Slicers: fecha, tipo, región, severidad

### Página 3: Tendencias Temporales
- Serie temporal por tipo de evento
- Comparativa semanal/mensual
- Predicción (si aplica)

### Página 4: Análisis Regional
- Ranking de departamentos
- Small multiples por región
- Drill-down a provincia/distrito

### Página 5: Tabla de Datos / Detalle
- Tabla completa con drill-through
- Exportable
- Búsqueda

### Filtros Globales (sincronizados)
- Fecha (rango)
- Tipo de evento
- Departamento
- Severidad (muertos > 0, heridos > 5, etc.)
- Fuente
- Confianza (relevancia_score)

---

## 💬 CHAT IA (RAG sobre noticias)

### Capacidades
1. **Consultas sobre noticias**: "¿Qué incidentes hubo en Lima esta semana?"
2. **Resúmenes contextuales**: "Dame un briefing de seguridad de Arequipa"
3. **Búsqueda semántica**: "Noticias relacionadas con narcotráfico en la frontera"
4. **Respuestas con citas**: Links a fuentes originales

### Arquitectura RAG
```
Usuario pregunta
      ↓
Azure Function (/api/chat)
      ↓
Azure AI Search (vector + filtros)
      ↓
Top 5-10 noticias relevantes
      ↓
Azure OpenAI (genera respuesta con contexto)
      ↓
Respuesta + citas + "Ver fuentes"
```

### Índice AI Search
Campos a indexar:
- title, body (texto completo)
- fecha_incidente, departamento, tipo_evento (filtros)
- embedding (vector para búsqueda semántica)
- url, source_name (para citas)

### Integración con filtros del dashboard
- Los filtros activos en Power BI se pasan al chat
- El chat responde en el mismo contexto (ej: si filtras "Lima", el chat solo busca en Lima)

---

## 🔐 SEGURIDAD Y ACCESO

### Usuarios
- 2-3 viewers externos (cualquier cuenta: Gmail, empresa, etc.)
- Control via Azure AD B2B (invitación)
- Grupo: grp-osint-peu-2026-viewers

### Permisos
| Capa | Control |
|------|---------|
| Azure AD | Quién puede entrar |
| Power BI | Qué report ve |
| (Opcional) RLS | Qué datos ve |

---

## 💰 COSTOS ESTIMADOS

| Componente | Costo/mes |
|------------|-----------|
| Power BI Pro (3 usuarios) | $30 |
| Azure Static Web Apps | $0-9 |
| Azure Functions | ~$5 |
| Azure PostgreSQL Basic | ~$15 |
| Azure AI Search (Basic) | ~$25 |
| Azure OpenAI | ~$10 |
| Claude Haiku (backend) | ~$5 |
| **TOTAL** | **~$90-100/mes** |

---

## 📁 ESTRUCTURA ACTUAL DEL PROYECTO

```
2026_Peru/
├── config/
│   ├── newsapi_scope_peru_v4.yaml    # Scope activo (7 fuentes)
│   └── settings.yaml
├── src/
│   ├── ingestion/                    # Ingesta NewsAPI.ai
│   ├── processing/                   # Normalización, dedupe
│   ├── enrichment/                   # Pipeline LLM (NUEVO)
│   │   └── llm_enrichment_pipeline.py
│   ├── classification/               # Clasificador LLM (NUEVO)
│   │   └── llm_classifier.py
│   └── ...
├── scripts/
│   ├── daily_pipeline.py             # Pipeline diario unificado (NUEVO)
│   ├── run_newsapi_ai_job.py         # Ingesta
│   └── ...
├── data/
│   └── osint_dw.duckdb               # Base de datos
└── dashboards/                       # (Para Power BI files)
```

---

## ✅ ESTADO ACTUAL

| Componente | Estado |
|------------|--------|
| Ingesta NewsAPI.ai | ✅ Operativo |
| Arquitectura Medallion | ✅ Implementada |
| Pipeline LLM (clasificación) | ✅ Funcionando |
| Dedupe | ✅ Corregido |
| bronze_news | ✅ 722 artículos únicos |
| silver_news_enriched | 🔄 Procesando (692 pendientes) |
| gold_incidents | 🔄 Se construye desde silver |
| gold_daily_stats | 🔄 Se construye desde silver |
| Frontend Power BI | ⏳ Pendiente |
| Embedding React | ⏳ Pendiente |
| Chat IA | ⏳ Pendiente |
| Azure deployment | ⏳ Pendiente |

---

## 🎯 PRÓXIMOS PASOS FRONTEND

### Fase 1: Infraestructura Azure (2-3 días)
1. Resource Group + Storage Account
2. App Registration (Entra ID)
3. Static Web App + dominio
4. Migrar datos a Azure (PostgreSQL o Synapse)

### Fase 2: Power BI + ArcGIS (5-7 días)
1. Conexión a datos Azure
2. Crear report 5 páginas
3. Configurar ArcGIS (puntos + coroplético)
4. Slicers globales

### Fase 3: Frontend React + Embedding (3-4 días)
1. Layout (sidebar, header)
2. Auth con MSAL.js
3. Power BI JS SDK (embebido)
4. Navegación entre páginas

### Fase 4: Chat IA (3-5 días)
1. Azure AI Search (índice de noticias)
2. Azure OpenAI (embeddings + chat)
3. Function /api/chat
4. Integración con filtros

### Fase 5: Automatización (2 días)
1. Power Automate (PDF diario)
2. Alertas condicionales
3. Refresh programado

---

## 📝 NOTAS IMPORTANTES

1. **Power BI es el motor, no la plataforma** - El usuario ve tu web, no Power BI
2. **Un solo report multipágina** - No múltiples reports separados
3. **ArcGIS dentro del report** - Para que los filtros funcionen en tiempo real
4. **Chat complementa, no reemplaza** - Para consultas ad-hoc sobre noticias
5. **B2B para externos** - Cualquier cuenta (Gmail incluido) via invitación

---

## 🔑 CREDENCIALES Y RECURSOS

- **API Key Anthropic**: Configurada en .env (ANTHROPIC_API_KEY)
- **NewsAPI.ai**: Configurada en .env (NEWSAPI_KEY)
- **Azure**: Pendiente de configurar
- **Power BI**: Pendiente de configurar

---

*Documento generado: 2026-01-03*
*Proyecto: OSINT Perú 2026*
