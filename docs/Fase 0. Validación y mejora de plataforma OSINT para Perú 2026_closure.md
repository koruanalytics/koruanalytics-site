# Acción de Cierre de Chat del Proyecto: OSINT Perú 2026 - Auditoría de Calidad

## Metadatos del Chat
| Campo | Valor |
|-------|-------|
| **Nombre del proyecto** | OSINT Perú 2026 - Electoral Security Monitoring Platform |
| **Fecha de inicio del chat** | 2025-01-05 |
| **Fecha de cierre** | 2025-01-05 |
| **Duración estimada** | 1 sesión / ~30 minutos |
| **Chat ID/Referencia** | Auditoría inicial arquitectura y código |

---

## 1. RESUMEN EJECUTIVO
Inicio de auditoría completa de calidad e integridad para plataforma OSINT de monitoreo electoral Perú 2026. Sistema funcional en local (Windows/DuckDB/Python) procesando 650+ artículos diarios desde 7 fuentes peruanas, identificando ~210 incidentes reales con 71% de filtrado de ruido. Primera auditoría reveló 4 issues críticos en orquestación del pipeline. Pendiente: recibir schemas completos DuckDB y código de 4 scripts core para auditoría code-level detallada.

---

## 2. STACK TECNOLÓGICO

| Categoría | Tecnología | Versión |
|-----------|------------|---------|
| Lenguaje | Python | 3.x (.venv) |
| Base de datos | DuckDB | Latest (columnar) |
| Logging | loguru | - |
| Ingesta APIs | NewsAPI.ai / EventRegistry | - |
| LLM Classification | Claude Haiku | API |
| Orquestación local | PowerShell + Task Scheduler | Windows |
| IDE | VS Code | - |
| OS | Windows 10/11 | - |
| Target Cloud | Azure (OpenAI, AI Search, Maps, Storage) | Parcialmente configurado |
| Arquitectura datos | Medallion (Bronze→Silver→Gold) | DuckDB |

---

## 3. ESTRUCTURA DEL PROYECTO

```
C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru\
├── scripts/
│   ├── run_incidents_job.py                    # ✅ Orquestador pipeline (auditado)
│   ├── run_incident_extract_baseline.py        # 🔍 Extrae incidentes desde stg_news
│   ├── run_geo_resolve_incidents.py            # 🔍 Geocoding contra dim_places_pe
│   ├── build_fct_incidents.py                  # 🔍 Construye fact table
│   ├── check_incidents_run.py                  # 🔍 Validaciones post-pipeline
│   ├── run_newsapi_ai_job.py                   # ✅ Job ingesta NewsAPI
│   ├── scheduled_run_newsapi_ai_job.ps1        # ✅ Wrapper PowerShell con lock
│   ├── load_gazetteer_pe.py                    # ✅ Carga dim geográfica
│   ├── reset_dim_places_pe.py                  # ✅ Reset dimensión geo
│   ├── inspect_dim_places_pe.py                # ⚠️ Auditado - schemas incompletos
│   ├── inspect_stg_incidents_extracted.py      # Inspect staging incidents
│   ├── validate_gazetteer_pe.py                # ✅ Validación gazetteer
│   ├── write_gazetteer_checksums.py            # ✅ Genera SHA256
│   ├── validate_gazetteer_checksum.py          # ✅ Verifica integridad
│   └── [legacy scripts - no usar sin validar]
├── config/
│   └── geo/
│       ├── peru_gazetteer_full.csv             # ✅ Gazetteer versionado
│       └── peru_gazetteer_full.csv.sha256      # ✅ Checksum integridad
├── data/
│   └── osint_dw.duckdb                         # ✅ Data warehouse principal
├── .venv/                                       # ✅ Python virtual environment
├── pyproject.toml / requirements.txt           # 🔍 Pendiente revisar
└── README.md                                    # Documentación proyecto
```

---

## 4. ARCHIVOS CLAVE Y SU ESTADO

| Archivo | Estado | Descripción | Última modificación |
|---------|--------|-------------|---------------------|
| `run_incidents_job.py` | ⚠️ Funcional pero mejorable | Orquesta 4 pasos con run_id, sin pre-checks ni logging robusto | 2025-01-05 |
| `inspect_dim_places_pe.py` | ⚠️ Requiere revisión | Count en lugar de DESCRIBE, no muestra schema real | 2025-01-05 |
| `run_incident_extract_baseline.py` | 🔍 Pendiente auditar | Extracción incidentes: stg_news → stg_incidents_extracted (22 cols) | - |
| `run_geo_resolve_incidents.py` | 🔍 Pendiente auditar | Geocoding + escritura map_incident_place | - |
| `build_fct_incidents.py` | 🔍 Pendiente auditar | Schema-aware, fact builder, override_* desactivados | - |
| `check_incidents_run.py` | 🔍 Pendiente auditar | Validaciones integridad post-ejecución | - |
| `scheduled_run_newsapi_ai_job.ps1` | ✅ Completo | Lock anti-solape, parsea run_id, logs maestros | 2025-01-05 |
| `peru_gazetteer_full.csv` | ✅ Completo | Dimensión geo: ADM1/2/3, lat/lon, versionado + SHA256 | 2025-01-05 |
| `osint_dw.duckdb` | ✅ Operativo | DW principal con Medallion: stg → dim → fct → map | 2025-01-05 |

**Leyenda:** ✅ Completo | 🔍 Pendiente auditar | ⚠️ Requiere revisión | ❌ Issues críticos

---

## 5. FUNCIONALIDADES IMPLEMENTADAS

### Completadas
- [x] **Ingesta NewsAPI** - 650+ artículos/día desde 7 fuentes peruanas específicas (source-based)
- [x] **Deduplicación robusta** - Por canonical/original URI en DuckDB staging
- [x] **Dimensión geográfica completa** - Gazetteer Perú versionado con checksum SHA256
- [x] **Pipeline incidentes 4 pasos** - Extract → GEO → Fact → Check, EXIT_CODE=0 validado
- [x] **Trazabilidad run_id** - Propagación completa por toda la pipeline
- [x] **Clasificación LLM** - Claude Haiku: 14 event types, casualty counts, bilingual summaries
- [x] **Arquitectura Medallion** - Bronze/Silver/Gold implementada en DuckDB
- [x] **Scheduling automático** - Task Scheduler integrado con PowerShell wrappers
- [x] **Validación gazetteer** - Scripts de verificación integridad y checksums
- [x] **Data quality tracking** - 408 muertes, 2,046 heridos tracked, 71% ruido filtrado

### En Progreso
- [ ] **Auditoría code-level** - Revisión detallada de 4 scripts core (50% pendiente)
- [ ] **Azure migration prep** - Infraestructura parcialmente configurada (OpenAI, AI Search, Maps)

### Pendientes
- [ ] **Tabla curation_incident_overrides** - Flujo curación manual + override_* columns (Bloque H/F8)
- [ ] **GEO avanzado** - Multi-match, ranking/score, mejor extracción location_text (Bloque H/G1)
- [ ] **Containerización Docker** - Preparación para Azure Container Instances
- [ ] **Frontend** - Power BI Pro + ArcGIS + React + RAG chat
- [ ] **Monitoring & alerting** - Application Insights + alertas proactivas
- [ ] **Tests automatizados** - Suite de unit tests y integration tests
- [ ] **CI/CD pipeline** - Despliegue automatizado a Azure

---

## 6. CONFIGURACIÓN Y VARIABLES DE ENTORNO

```bash
# Variables requeridas (.env o sistema)
NEWSAPI_AI_KEY=your_newsapi_key               # API key para ingesta NewsAPI.ai
AZURE_OPENAI_KEY=your_azure_openai_key        # Para clasificación LLM
AZURE_AI_SEARCH_KEY=your_search_key           # Azure AI Search (RAG futuro)
AZURE_MAPS_KEY=your_maps_key                  # Azure Maps (geocoding avanzado)

# Paths locales
DUCKDB_PATH=data/osint_dw.duckdb              # DW principal
GAZETTEER_PATH=config/geo/peru_gazetteer_full.csv  # Dimensión geo

# Configuración pipeline
PYTHON_VENV=.venv/Scripts/python.exe          # Python virtual environment
LOG_LEVEL=INFO                                # Nivel logging (con loguru)
```

**Archivos de configuración:**
| Archivo | Propósito | Notas |
|---------|-----------|-------|
| `.env` | Variables de entorno sensibles | No commitear, gitignore |
| `peru_gazetteer_full.csv` | Dimensión geográfica completa | Versionado + SHA256 |
| `peru_gazetteer_full.csv.sha256` | Checksum integridad | Validar antes de cargar |
| `scheduled_run_newsapi_ai_job.ps1` | Task Scheduler wrapper | Lock anti-solape integrado |

---

## 7. DECISIONES TÉCNICAS TOMADAS

| # | Decisión | Razón | Alternativa descartada |
|---|----------|-------|------------------------|
| 1 | DuckDB en lugar de PostgreSQL | Simplicidad local + performance columnar + embeddable | PostgreSQL (overengineering para prototipo local) |
| 2 | Ingesta source-based (7 outlets peruanos) | Aumentó volumen 6→650 artículos/día con mejor calidad | Location-based queries (cobertura insuficiente) |
| 3 | Claude Haiku para clasificación | 71% filtrado ruido efectivo, costos controlados | Rule-based (10% precision) |
| 4 | Arquitectura Medallion (Bronze→Silver→Gold) | Data quality + trazabilidad + analytics complejos | Flat tables (no escalable, no auditable) |
| 5 | Gazetteer como artefacto versionado local | Evita HTTP 403 en ejecución diaria, garantiza reproducibilidad | Download on-demand (API inestable) |
| 6 | PowerShell + Task Scheduler | Setup rápido Windows, lock anti-solape robusto | Apache Airflow (overhead innecesario en local) |
| 7 | run_id como identificador universal | Trazabilidad end-to-end desde ingesta hasta fact | Timestamps (colisiones posibles) |
| 8 | Separación Extract→GEO→Fact→Check | Debugging granular, reprocess selectivo posible | Pipeline monolítico (difícil debuggear) |

---

## 8. PROBLEMAS RESUELTOS

### [P1] Baja cobertura de ingesta (6 artículos/día)
- **Síntoma:** Pipeline ingesta solo 6 artículos relevantes por día, insuficiente para monitoreo
- **Causa raíz:** Location-based queries muy específicas generaban poca cobertura
- **Solución aplicada:**
  - Cambio estratégico: source-based ingestion targeting 7 Peruvian outlets
  - NewsAPI.ai configurado para scrape completo de fuentes específicas
  - Resultado: 650+ artículos/día, ~210 incidentes reales identificados
- **Archivos afectados:** `run_newsapi_ai_job.py`, configuración NewsAPI
- **Lección aprendida:** Filtrar en source es más efectivo que filtrar en query para OSINT regional

### [P2] Clasificación rule-based con 90% ruido
- **Síntoma:** Sistema rule-based clasificaba 90% de artículos como incidentes (falsos positivos masivos)
- **Causa raíz:** Keywords simples capturaban noticias generales de crimen/política sin valor OSINT
- **Solución aplicada:**
```python
# Reemplazo completo por LLM-based classification con Claude Haiku
# Extrae 14 event types específicos + confidence + metadata estructurada
# Result: 71% noise filtering, solo 210 genuine incidents de 650+ articles
```
- **Archivos afectados:** `run_incident_extract_baseline.py` (extracción LLM completa)
- **Lección aprendida:** LLM classification >> rule-based para contenido no estructurado en español

### [P3] HTTP 403 en descarga gazetteer durante ejecución diaria
- **Síntoma:** Pipeline fallaba aleatoriamente por rate limiting en API geográfica
- **Causa raíz:** Gazetteer Peru descargado on-demand en cada ejecución
- **Solución aplicada:**
```python
# Gazetteer versionado como artefacto en repo
# config/geo/peru_gazetteer_full.csv + SHA256 checksum
# Scripts: validate_gazetteer_checksum.py antes de load_gazetteer_pe.py
# Update: manual solo cuando necesario, no en daily runs
```
- **Archivos afectados:** `load_gazetteer_pe.py`, `validate_gazetteer_checksum.py`
- **Lección aprendida:** Artefactos críticos deben ser versionados localmente, no dependientes de APIs externas

---

## 9. PROBLEMAS CONOCIDOS / DEUDA TÉCNICA

| # | Problema | Impacto | Solución propuesta | Prioridad |
|---|----------|---------|-------------------|-----------|
| 1 | Scripts inspect no muestran schemas reales | Medio | Usar `DESCRIBE table_name` en lugar de `pragma_table_info` count | Media |
| 2 | Pipeline sin rollback en fallo parcial | Alto | Pre-flight checks + transaccionalidad + cleanup automático | Alta |
| 3 | Logging sin timestamps ni métricas | Medio | Integrar loguru con duración steps + structured logging | Alta |
| 4 | No hay validación pre-vuelo | Alto | Checks: dim_places_pe populated, run_id no duplicado, DuckDB accessible | Alta |
| 5 | Schemas no documentados formalmente | Medio | Generar DDL completo + documentación ER diagram | Media |
| 6 | override_* columns no implementadas | Medio | Tabla `curation_incident_overrides` + flujo curación (Bloque H) | Media |
| 7 | Scripts legacy coexisten con actuales | Bajo | Mover a `/archive` o eliminar, documentar cuáles usar | Baja |
| 8 | No hay tests automatizados | Alto | Suite pytest: unit tests + integration tests para pipeline | Media |
| 9 | Alerting inexistente | Alto | Azure Application Insights + alertas por email/SMS en fallos | Alta |
| 10 | Logs no centralizados | Medio | Agregación logs en Azure Log Analytics o similar | Baja |

---

## 10. PRÓXIMOS PASOS (PRIORIZADO)

### Alta Prioridad
1. **[INMEDIATO]** Recibir schemas completos DuckDB para continuar auditoría
   - Ejecutar: `python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('DESCRIBE dim_places_pe').df()); print(con.execute('DESCRIBE stg_incidents_extracted').df()); print(con.execute('DESCRIBE fct_incidents').df())"`
   - Archivos: todos los `DESCRIBE` de tablas del Medallion

2. **[INMEDIATO]** Compartir código de 4 scripts core del pipeline
   - `run_incident_extract_baseline.py` (extracción LLM)
   - `run_geo_resolve_incidents.py` (geocoding)
   - `build_fct_incidents.py` (fact builder)
   - `check_incidents_run.py` (validaciones)

3. **[CRÍTICO]** Implementar mejoras en `run_incidents_job.py`
   - Pre-flight checks function
   - Logging con loguru + timestamps + duración
   - Error handling robusto con stderr capture
   - Cleanup automático en caso de fallo parcial

### Media Prioridad
4. **[PRÓXIMA SESIÓN]** Completar auditoría code-level con código recibido
   - Revisar manejo errores, idempotencia, SQL injection risks
   - Validar data quality checks en cada paso
   - Verificar consistencia schemas vs código

5. **[PRÓXIMA SESIÓN]** Revisar dependencias y configuración
   - `pyproject.toml` o `requirements.txt` completo
   - Versiones pinned de librerías críticas
   - Conflictos de dependencias potenciales

6. **[SIGUIENTE FASE]** Preparación Azure migration
   - Dockerfile para containerización
   - Azure Key Vault para secretos
   - CI/CD pipeline básico (GitHub Actions / Azure DevOps)

### Baja Prioridad
7. **[CUANDO SEA POSIBLE]** Refactoring y optimizaciones
   - Type hints completos en todos los scripts
   - Docstrings exhaustivos (Google style)
   - Eliminar scripts legacy o mover a `/archive`

8. **[CUANDO SEA POSIBLE]** Testing automatizado
   - Unit tests con pytest
   - Integration tests para pipeline end-to-end
   - Mock de APIs externas (NewsAPI, Claude)

---

## 11. CÓDIGO CRÍTICO PARA REFERENCIA

### Mejora propuesta: run_incidents_job.py con pre-flight checks y logging robusto
```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import subprocess
import time
import duckdb
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")

# Configure loguru
logger.add(
    PROJECT_ROOT / "logs" / "incidents_job_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

def preflight_checks(run_id: str) -> None:
    """
    Validate prerequisites before starting pipeline.
    
    Args:
        run_id: Unique identifier for this ingestion run
        
    Raises:
        SystemExit: If any prerequisite check fails
    """
    logger.info("Running pre-flight checks")
    
    con = duckdb.connect(str(PROJECT_ROOT / "data" / "osint_dw.duckdb"))
    
    try:
        # Check 1: dim_places_pe is populated
        places_count = con.execute(
            "SELECT COUNT(*) FROM dim_places_pe"
        ).fetchone()[0]
        
        if places_count == 0:
            logger.error("dim_places_pe is EMPTY - run load_gazetteer_pe.py first!")
            raise SystemExit(1)
        
        logger.info(f"✓ dim_places_pe populated: {places_count:,} places")
        
        # Check 2: Verify run_id not already processed
        existing_incidents = con.execute(
            "SELECT COUNT(*) FROM fct_incidents WHERE ingest_run_id = ?",
            [run_id]
        ).fetchone()[0]
        
        if existing_incidents > 0:
            logger.warning(
                f"run_id {run_id} already processed ({existing_incidents} incidents). "
                "Pipeline will reprocess (idempotent mode)."
            )
        else:
            logger.info(f"✓ run_id {run_id} is new")
        
        # Check 3: Verify staging data exists for this run_id
        staging_articles = con.execute(
            "SELECT COUNT(*) FROM stg_news_newsapi_ai WHERE run_id = ?",
            [run_id]
        ).fetchone()[0]
        
        if staging_articles == 0:
            logger.error(
                f"No staging data found for run_id {run_id}. "
                "Run run_newsapi_ai_job.py first."
            )
            raise SystemExit(1)
        
        logger.info(f"✓ Staging data ready: {staging_articles} articles for run_id {run_id}")
        
    finally:
        con.close()
    
    logger.info("All pre-flight checks passed ✓")

def run_step(cmd: list[str], step_name: str) -> str:
    """
    Execute a pipeline step with logging and error handling.
    
    Args:
        cmd: Command to execute as list of strings
        step_name: Human-readable name for logging
        
    Returns:
        stdout from the command
        
    Raises:
        SystemExit: If command fails with non-zero exit code
    """
    logger.info(f"Starting step: {step_name}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            logger.error(f"❌ {step_name} FAILED (exit code {result.returncode})")
            logger.error(f"STDERR:\n{result.stderr}")
            logger.error(f"STDOUT:\n{result.stdout}")
            raise SystemExit(result.returncode)
        
        logger.info(f"✅ {step_name} completed in {elapsed:.2f}s")
        
        # Log key metrics from stdout if present
        if "Extracted=" in result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        
        return result.stdout
        
    except Exception as e:
        logger.exception(f"💥 {step_name} CRASHED: {e}")
        raise SystemExit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Run end-to-end incidents extraction pipeline"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Unique identifier for this ingestion run"
    )
    args = parser.parse_args()
    
    logger.info(f"========== INCIDENTS PIPELINE START ==========")
    logger.info(f"Run ID: {args.run_id}")
    
    pipeline_start = time.time()
    
    try:
        # Pre-flight validation
        preflight_checks(args.run_id)
        
        # Step 1: Extract incidents from staging news
        run_step(
            [PYTHON, "scripts/run_incident_extract_baseline.py", "--run-id", args.run_id],
            "Incident Extraction"
        )
        
        # Step 2: Resolve geocoding
        run_step(
            [PYTHON, "scripts/run_geo_resolve_incidents.py", "--run-id", args.run_id],
            "GEO Resolution"
        )
        
        # Step 3: Build fact table
        run_step(
            [PYTHON, "scripts/build_fct_incidents.py", "--run-id", args.run_id],
            "Fact Table Build"
        )
        
        # Step 4: Run data quality checks
        run_step(
            [PYTHON, "scripts/check_incidents_run.py", "--run-id", args.run_id],
            "Data Quality Checks"
        )
        
        total_elapsed = time.time() - pipeline_start
        logger.info(f"========== PIPELINE SUCCESS ==========")
        logger.info(f"Total duration: {total_elapsed:.2f}s")
        logger.info(f"Run ID: {args.run_id}")
        
        print("EXIT_CODE=0")
        
    except SystemExit as e:
        total_elapsed = time.time() - pipeline_start
        logger.error(f"========== PIPELINE FAILED ==========")
        logger.error(f"Duration before failure: {total_elapsed:.2f}s")
        logger.error(f"Run ID: {args.run_id}")
        logger.error(f"Exit code: {e.code}")
        raise

if __name__ == "__main__":
    main()
```

### Mejora propuesta: inspect_dim_places_pe.py con schema real
```python
import duckdb
from pathlib import Path

def inspect_dim_places():
    """
    Inspect dim_places_pe table structure and contents.
    """
    db_path = Path(__file__).resolve().parents[1] / "data" / "osint_dw.duckdb"
    con = duckdb.connect(str(db_path))
    
    try:
        print("=" * 80)
        print("DIM_PLACES_PE - TABLE SCHEMA")
        print("=" * 80)
        schema_df = con.execute("DESCRIBE dim_places_pe").df()
        print(schema_df.to_string(index=False))
        
        print("\n" + "=" * 80)
        print("DIM_PLACES_PE - STATISTICS")
        print("=" * 80)
        stats_df = con.execute("""
            SELECT 
                COUNT(*) as total_places,
                COUNT(DISTINCT adm1_name) as departments,
                COUNT(DISTINCT adm2_name) as provinces,
                COUNT(DISTINCT adm3_name) as districts,
                COUNT(DISTINCT CASE WHEN lat IS NOT NULL THEN place_id END) as geocoded_places,
                MIN(lat) as min_lat,
                MAX(lat) as max_lat,
                MIN(lon) as min_lon,
                MAX(lon) as max_lon
            FROM dim_places_pe
        """).df()
        print(stats_df.to_string(index=False))
        
        print("\n" + "=" * 80)
        print("DIM_PLACES_PE - SAMPLE ROWS")
        print("=" * 80)
        sample_df = con.execute("""
            SELECT
                place_id, 
                adm1_name, 
                adm2_name, 
                adm3_name, 
                lat, 
                lon
            FROM dim_places_pe
            LIMIT 10
        """).df()
        print(sample_df.to_string(index=False))
        
    finally:
        con.close()

if __name__ == "__main__":
    inspect_dim_places()
```

---

## 12. COMANDOS ÚTILES

```bash
# Activar virtual environment
.\.venv\Scripts\Activate.ps1

# Inspeccionar schemas reales de tablas DuckDB
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('DESCRIBE dim_places_pe').df())"

# Ver todas las tablas en DuckDB
python -c "import duckdb; con=duckdb.connect('data/osint_dw.duckdb'); print(con.execute('SHOW TABLES').df())"

# Ejecutar pipeline completo de incidentes
.\.venv\Scripts\python.exe scripts\run_incidents_job.py --run-id 20251214165627

# Ejecutar solo un paso específico del pipeline
.\.venv\Scripts\python.exe scripts\run_geo_resolve_incidents.py --run-id 20251214165627

# Validar integridad del gazetteer
python scripts\validate_gazetteer_checksum.py

# Cargar/recargar dimensión geográfica
python scripts\reset_dim_places_pe.py
python scripts\load_gazetteer_pe.py

# Ver estructura completa del proyecto
Get-ChildItem -Recurse .\scripts\*.py | Select-Object Name, Length, LastWriteTime

# Inspeccionar tablas específicas
python scripts\inspect_dim_places_pe.py
python scripts\inspect_stg_incidents_extracted.py

# Verificar logs de ejecución (si existen)
Get-Content logs\*.log -Tail 50

# Ejecutar job completo NewsAPI → Incidents (scheduled)
.\scripts\scheduled_run_newsapi_ai_job.ps1
```

---

## 13. ENLACES Y RECURSOS

| Recurso | URL | Notas |
|---------|-----|-------|
| NewsAPI.ai Documentation | https://newsapi.ai/documentation | Event Registry API reference |
| DuckDB Documentation | https://duckdb.org/docs/ | SQL reference y funciones |
| Claude API Documentation | https://docs.anthropic.com/ | Haiku model para classification |
| Azure OpenAI Service | https://learn.microsoft.com/azure/ai-services/openai/ | Setup guide |
| Azure AI Search | https://learn.microsoft.com/azure/search/ | RAG implementation |
| Azure Maps | https://learn.microsoft.com/azure/azure-maps/ | Geocoding services |
| Loguru Documentation | https://loguru.readthedocs.io/ | Python logging library |
| Medallion Architecture | https://www.databricks.com/glossary/medallion-architecture | Bronze/Silver/Gold pattern |

---

## 14. NOTAS PARA EL PRÓXIMO CHAT

### ⚠️ Trampas / Cosas que costó descubrir
- **Gazetteer download en ejecución diaria causa HTTP 403** → Versionar localmente con SHA256
- **Location-based queries dan cobertura terrible** → Source-based ingestion fue game changer (6→650 artículos)
- **Rule-based classification es 90% ruido** → LLM-based con Claude Haiku filtró 71% efectivamente
- **`pragma_table_info` count ≠ schema real** → Usar `DESCRIBE table_name` siempre
- **Subprocess sin capture_output = logs ciegos** → Siempre capture stdout/stderr para debugging
- **Scripts legacy coexisten con actuales** → Verificar fecha modificación antes de ejecutar cualquier script

### 💡 Tips importantes
- **DuckDB es embeddable** → No requiere server, perfecto para local development
- **Medallion architecture vale la pena** → Permite rollback, auditoría, y analytics complejos
- **run_id como UUID universal** → Propagarlo por TODA la pipeline garantiza trazabilidad completa
- **Pre-flight checks previenen desastres** → Validar dim_places_pe, run_id, staging data ANTES de procesar
- **Loguru >> print()** → Timestamps automáticos, rotation,