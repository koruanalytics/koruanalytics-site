from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List


@dataclass(frozen=True)
class IncidentRule:
    incident_type: str
    keywords: Tuple[str, ...]


RULES: List[IncidentRule] = [
    IncidentRule("violence_attack", ("asesin", "ataque", "disparo", "explosi", "agresión", "arma", "bomba")),
    IncidentRule("intimidation_threat", ("amenaza", "intimid", "hostig", "coacción", "chantaje")),
    IncidentRule("infrastructure_attack", ("sabotaje", "incendio", "corte", "ataque a local", "destrucción", "vandal")),
    IncidentRule("protest_unrest", ("protesta", "bloqueo", "disturbios", "enfrentamientos", "manifestación")),
    IncidentRule("disinformation", ("bulo", "fake news", "desinformación", "rumor", "engañoso")),
]

def classify_incident_type(text: str) -> tuple[str, float]:
    """
    Clasificador baseline por keywords:
    - Devuelve tipo + score simple (confianza aproximada).
    """
    if not text:
        return ("unknown", 0.0)

    t = text.lower()
    best_type = "unknown"
    best_hits = 0

    for rule in RULES:
        hits = sum(1 for kw in rule.keywords if kw in t)
        if hits > best_hits:
            best_hits = hits
            best_type = rule.incident_type

    if best_type == "unknown":
        return ("unknown", 0.1)

    score = min(0.8, 0.3 + 0.1 * best_hits)
    return (best_type, float(score))
