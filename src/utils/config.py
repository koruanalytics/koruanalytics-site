from pathlib import Path
import yaml

# Ruta raíz del proyecto (carpeta "2026 EOM Peru")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str = "config/settings.yaml") -> dict:
    """
    Carga el fichero de configuración YAML y lo devuelve como diccionario.
    """
    config_path = PROJECT_ROOT / path
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)