#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resolve URIs (location + concept groups) for NewsAPI.ai / EventRegistry.

Qué hace:
- Resuelve Perú -> country/location URI
- Resuelve un catálogo de "ámbitos" -> listas de concept URIs (concept_uris)
- Genera un YAML/JSON versionable para usar en la ingesta.

Compatibilidad de API keys:
- Usa NEWSAPI_KEY (recomendado, tu naming actual)
- Alternativas: NEWSAPI_AI_KEY, EVENTREGISTRY_API_KEY

Ejemplos:
  python scripts/resolve_uris_newsapi.py --out config/newsapi_scope_peru_2025-11.yaml --langs spa eng --allow-archive
  python scripts/resolve_uris_newsapi.py --out config/newsapi_scope_peru_2025-11.json --langs spa eng
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from loguru import logger

from eventregistry import EventRegistry


# -----------------------------
# Seeds de ámbitos (grupos)
# -----------------------------
@dataclass
class ConceptGroupSeed:
    group_id: str
    label: str
    seeds_eng: List[str]
    seeds_spa: List[str]
    notes: str = ""


DEFAULT_GROUPS: List[ConceptGroupSeed] = [
    ConceptGroupSeed(
        group_id="elections",
        label="Elecciones",
        notes="Proceso electoral / comicios / votación",
        seeds_eng=["Election", "Electoral process", "Voting", "General election"],
        seeds_spa=["Elecciones", "Proceso electoral", "Votación", "Comicios"],
    ),
    ConceptGroupSeed(
        group_id="political_violence",
        label="Violencia política",
        notes="Violencia vinculada a actores políticos/electorales",
        seeds_eng=["Political violence", "Electoral violence", "Political repression"],
        seeds_spa=["Violencia política", "Violencia electoral", "Represión política"],
    ),
    ConceptGroupSeed(
        group_id="protests",
        label="Protestas",
        notes="Manifestaciones, disturbios, movilizaciones",
        seeds_eng=["Protest", "Demonstration (protest)", "Civil unrest", "Riot"],
        seeds_spa=["Protesta", "Manifestación", "Disturbios", "Movilización"],
    ),
    ConceptGroupSeed(
        group_id="infra_attacks",
        label="Ataques a infraestructura",
        notes="Ataques a infra crítica, sabotaje, cortes, daños",
        seeds_eng=["Critical infrastructure", "Sabotage", "Infrastructure", "Arson"],
        seeds_spa=["Infraestructura crítica", "Sabotaje", "Infraestructura", "Incendio provocado"],
    ),
    ConceptGroupSeed(
        group_id="intimidation",
        label="Intimidación",
        notes="Amenazas, acoso, intimidación política/electoral",
        seeds_eng=["Intimidation", "Threat", "Harassment"],
        seeds_spa=["Intimidación", "Amenaza", "Acoso"],
    ),
    ConceptGroupSeed(
        group_id="security_forces",
        label="Fuerzas de seguridad",
        notes="Policía, fuerzas armadas, fuerzas de orden",
        seeds_eng=["Police", "Law enforcement", "Armed forces", "Military", "Security forces"],
        seeds_spa=["Policía", "Fuerzas del orden", "Fuerzas armadas", "Ejército", "Fuerzas de seguridad"],
    ),
    ConceptGroupSeed(
        group_id="violent_incidents",
        label="Sucesos (asesinatos, secuestros, violencia sexual, agresiones)",
        notes="Violencia interpersonal / crimen",
        seeds_eng=["Murder", "Homicide", "Kidnapping", "Sexual assault", "Assault"],
        seeds_spa=["Asesinato", "Homicidio", "Secuestro", "Agresión sexual", "Agresión", "Violencia sexual"],
    ),
    ConceptGroupSeed(
        group_id="accidents",
        label="Accidentes (atropellos, caídas de infraestructuras, explosiones)",
        notes="Accidentes de tráfico, derrumbes, explosiones",
        seeds_eng=["Traffic collision", "Road accident", "Structural collapse", "Explosion", "Industrial accident"],
        seeds_spa=["Accidente de tráfico", "Accidente vial", "Atropello", "Colapso estructural", "Explosión", "Accidente industrial"],
    ),
    ConceptGroupSeed(
        group_id="terror_crime",
        label="Terrorismo / grupos armados / crimen organizado",
        notes="Terrorismo, insurgencia, crimen organizado",
        seeds_eng=["Terrorism", "Insurgency", "Organized crime", "Drug cartel", "Armed group"],
        seeds_spa=["Terrorismo", "Insurgencia", "Crimen organizado", "Cártel", "Grupo armado"],
    ),
    ConceptGroupSeed(
        group_id="environmental",
        label="Sucesos medioambientales (inundaciones, fuego, terremoto)",
        notes="Inundaciones, incendios, terremotos, deslizamientos",
        seeds_eng=["Flood", "Wildfire", "Earthquake", "Landslide"],
        seeds_spa=["Inundación", "Incendio forestal", "Terremoto", "Deslizamiento de tierra"],
    ),
    ConceptGroupSeed(
        group_id="health_risks",
        label="Riesgos para la salud (epidemias, plagas, contaminación)",
        notes="Epidemias/brotes, plagas, contaminación",
        seeds_eng=["Epidemic", "Outbreak", "Pandemic", "Air pollution", "Water pollution"],
        seeds_spa=["Epidemia", "Brote", "Pandemia", "Contaminación del aire", "Contaminación del agua", "Plaga"],
    ),
]


# -----------------------------
# Helpers
# -----------------------------
def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_api_key_from_env() -> str:
    """
    Compatibilidad:
      - NEWSAPI_KEY (tu naming actual)
      - NEWSAPI_AI_KEY
      - EVENTREGISTRY_API_KEY
    """
    load_dotenv()
    api_key = (
        os.getenv("NEWSAPI_KEY")
        or os.getenv("NEWSAPI_AI_KEY")
        or os.getenv("EVENTREGISTRY_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "Falta NEWSAPI_KEY (o NEWSAPI_AI_KEY / EVENTREGISTRY_API_KEY) en tu entorno o en el .env"
        )
    return api_key


def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def resolve_location_uri(er: EventRegistry, candidates: List[str]) -> Optional[str]:
    for name in candidates:
        name = (name or "").strip()
        if not name:
            continue
        try:
            uri = er.getLocationUri(name)
            if uri:
                return uri
        except Exception as e:
            logger.debug(f"Fallo resolviendo locationUri para '{name}': {e}")
    return None


def resolve_concept_uri(er: EventRegistry, term: str) -> Optional[str]:
    term = (term or "").strip()
    if not term:
        return None
    try:
        return er.getConceptUri(term)
    except Exception as e:
        logger.debug(f"Fallo resolviendo conceptUri para '{term}': {e}")
        return None


# -----------------------------
# Build catálogo
# -----------------------------
def build_catalog(
    country_name: str,
    langs: List[str],
    allow_archive: bool,
    groups: List[ConceptGroupSeed],
) -> Dict[str, Any]:
    api_key = get_api_key_from_env()
    er = EventRegistry(apiKey=api_key, allowUseOfArchive=allow_archive)

    catalog: Dict[str, Any] = {
        "generated_at_utc": utc_now_iso_z(),
        "provider": "newsapi.ai (EventRegistry)",
        "allow_archive": bool(allow_archive),
        "langs": langs,
        "scope": {
            "country_name": country_name,
            "location_uri": None,
            "concept_groups": [],
        },
    }

    # 1) Resolver locationUri país
    loc_uri = resolve_location_uri(er, [country_name, "Peru", "Perú"] if country_name.lower() in ["peru", "perú"] else [country_name])
    catalog["scope"]["location_uri"] = loc_uri

    if loc_uri:
        logger.success(f"{country_name} locationUri resuelta: {loc_uri}")
    else:
        logger.warning(f"No pude resolver locationUri para '{country_name}'. Prueba con 'Peru' o revisa la API key.")

    # 2) Resolver conceptos por grupo (semillas ENG -> SPA)
    for g in groups:
        resolved: List[str] = []
        misses: List[str] = []

        for seed in g.seeds_eng + g.seeds_spa:
            uri = resolve_concept_uri(er, seed)
            if uri:
                resolved.append(uri)
            else:
                misses.append(seed)

        resolved = unique_preserve_order(resolved)

        if resolved:
            logger.success(f"[OK] {g.label} -> {len(resolved)} conceptUri(s)")
        else:
            logger.warning(f"[MISS] No conceptUri para: {g.label} (probé semillas EN/ES)")

        catalog["scope"]["concept_groups"].append(
            {
                "group_id": g.group_id,
                "label": g.label,
                "notes": g.notes,
                "seeds_eng": g.seeds_eng,
                "seeds_spa": g.seeds_spa,
                "concept_uris": resolved,
                "misses": misses,
            }
        )

    catalog["generated_at_utc"] = utc_now_iso_z()
    return catalog


def write_output(catalog: Dict[str, Any], out_path: Path) -> None:
    ensure_parent(out_path)
    if out_path.suffix.lower() in [".yaml", ".yml"]:
        out_path.write_text(
            yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True),
            encoding="utf-8"
        )
    else:
        out_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resuelve URIs (location + concepts) para NewsAPI.ai/EventRegistry y guarda un YAML/JSON versionable."
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Ruta salida YAML/JSON (ej: config/newsapi_scope_peru_2025-11.yaml)"
    )
    parser.add_argument(
        "--langs",
        nargs="+",
        default=["spa", "eng"],
        help="Idiomas a capturar (códigos ER). Ej: --langs spa eng"
    )
    parser.add_argument(
        "--allow-archive",
        action="store_true",
        help="Permite buscar en archive (si tu plan lo soporta)."
    )
    parser.add_argument(
        "--country",
        default="Peru",
        help="Nombre país para resolver locationUri. Ej: Peru"
    )

    args = parser.parse_args()
    out_path = Path(args.out)

    # Si también quieres permitir esto desde env:
    load_dotenv()
    allow_archive_env = os.getenv("NEWSAPI_AI_ALLOW_ARCHIVE", "").lower() == "true"
    allow_archive = bool(args.allow_archive or allow_archive_env)

    catalog = build_catalog(
        country_name=args.country,
        langs=args.langs,
        allow_archive=allow_archive,
        groups=DEFAULT_GROUPS,
    )

    write_output(catalog, out_path)
    logger.success(f"Catálogo con URIs guardado en: {out_path.as_posix()}")


if __name__ == "__main__":
    main()
