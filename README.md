# 2026 EOM Peru - Plataforma OSINT

Proyecto de análisis OSINT para misión electoral (Perú 2026):

- Ingesta de noticias y fuentes abiertas.
- Procesamiento con NLP (incidentes, víctimas, actores).
- Geolocalización de incidentes.
- Dashboards y módulo de revisión manual.

## Entorno local

```powershell
# Ir a la carpeta del proyecto
cd "C:\Users\carlo\OneDrive - KoruAnalytics\Projects OSINT\2026 EOM Peru"

# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Instalar dependencias básicas
pip install -r requirements.txt

# Test base
python test_base.py