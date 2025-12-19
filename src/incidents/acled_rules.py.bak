"""
src/incidents/acled_rules.py - ACLED-based incident classification (v2)

Based on ACLED Codebook methodology:
- 6 Event Types
- 25 Sub-Event Types  
- 3 Disorder Types (Political Violence, Demonstrations, Strategic Developments)

IMPROVEMENTS in v2:
- Fixed short/generic keywords that caused false positives
- Added word boundary matching to avoid partial matches
- Expanded English keywords for bilingual support (Spanish/English)
- Added Peru-specific electoral violence keywords

Reference: https://acleddata.com/knowledge-base/codebook/
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


# =============================================================================
# ACLED EVENT TYPES (6)
# =============================================================================

EVENT_TYPES = {
    "battles": "Violent interactions between two organized armed groups",
    "explosions_remote_violence": "One-sided events using remote/explosive weapons",
    "violence_against_civilians": "Armed group deliberately targets unarmed non-combatants",
    "protests": "Public demonstrations without participant violence",
    "riots": "Violent demonstrations, property destruction, mob violence",
    "strategic_developments": "Non-violent but strategically important activities",
}

# =============================================================================
# ACLED SUB-EVENT TYPES (25)
# =============================================================================

SUB_EVENT_TYPES = {
    # BATTLES (3 sub-types)
    "armed_clash": ("battles", "Armed clash without clear territorial outcome"),
    "government_regains_territory": ("battles", "Government forces recapture territory"),
    "non_state_actor_overtakes_territory": ("battles", "Non-state group captures territory"),
    
    # EXPLOSIONS/REMOTE VIOLENCE (6 sub-types)
    "chemical_weapon": ("explosions_remote_violence", "Use of chemical weapons"),
    "air_drone_strike": ("explosions_remote_violence", "Air strikes or drone attacks"),
    "suicide_bomb": ("explosions_remote_violence", "Suicide bombing"),
    "shelling_artillery_missile": ("explosions_remote_violence", "Shelling, artillery, or missile attacks"),
    "remote_explosive_ied": ("explosions_remote_violence", "IEDs, landmines, remote explosives"),
    "grenade": ("explosions_remote_violence", "Grenade attacks"),
    
    # VIOLENCE AGAINST CIVILIANS (4 sub-types)
    "sexual_violence": ("violence_against_civilians", "Sexual violence against individuals"),
    "attack": ("violence_against_civilians", "Direct attack on civilians"),
    "abduction_disappearance": ("violence_against_civilians", "Kidnapping or forced disappearance"),
    
    # PROTESTS (3 sub-types)
    "peaceful_protest": ("protests", "Non-violent public demonstration"),
    "protest_with_intervention": ("protests", "Protest where authorities intervene"),
    "excessive_force_against_protesters": ("protests", "Disproportionate force used against protesters"),
    
    # RIOTS (3 sub-types)
    "violent_demonstration": ("riots", "Demonstrators engage in violence/vandalism"),
    "mob_violence": ("riots", "Spontaneous mob violence"),
    
    # STRATEGIC DEVELOPMENTS (6 sub-types)
    "agreement": ("strategic_developments", "Peace agreement, ceasefire, negotiation"),
    "arrest": ("strategic_developments", "Politically significant arrests"),
    "change_to_group_activity": ("strategic_developments", "Changes in armed group behavior"),
    "disrupted_weapons_use": ("strategic_developments", "Intercepted attacks or weapons"),
    "headquarters_base_established": ("strategic_developments", "New military/group base"),
    "looting_property_destruction": ("strategic_developments", "Looting or destruction of property"),
}

# =============================================================================
# DISORDER TYPES (3)
# =============================================================================

DISORDER_TYPES = {
    "political_violence": ["battles", "explosions_remote_violence", "violence_against_civilians"],
    "demonstrations": ["protests", "riots"],
    "strategic_developments": ["strategic_developments"],
}


# =============================================================================
# KEYWORD RULES FOR CLASSIFICATION (v2 - IMPROVED)
# =============================================================================
# Format: Each keyword should be specific enough to avoid false positives
# Short keywords (<5 chars) are marked and should use word boundary matching
# Bilingual: Spanish (primary) + English

KEYWORD_RULES = {
    # =========================================================================
    # BATTLES
    # =========================================================================
    "armed_clash": [
        # Spanish
        "enfrentamiento armado", "tiroteo", "balacera", "intercambio de disparos",
        "combate armado", "batalla", "enfrentamiento con", "fuego cruzado",
        "choque armado", "refriega",
        # English
        "armed clash", "firefight", "shootout", "gunfight", "armed confrontation",
        "exchange of fire", "gun battle",
    ],
    "government_regains_territory": [
        # Spanish
        "fuerzas del orden recuperan", "policia retoma", "militar retoma",
        "desalojo de invasores", "erradicacion de", "intervencion policial exitosa",
        "recuperacion de territorio",
        # English
        "government forces recapture", "police retake", "military retakes",
        "territory recovered",
    ],
    "non_state_actor_overtakes_territory": [
        # Spanish
        "toma de local", "invasion de terrenos", "ocupacion ilegal",
        "narcotrafico controla", "grupo armado controla", "toma de instalaciones",
        # English
        "territory seized", "armed group controls", "takeover of",
    ],
    
    # =========================================================================
    # EXPLOSIONS/REMOTE VIOLENCE
    # =========================================================================
    "air_drone_strike": [
        # Spanish
        "ataque aereo", "bombardeo aereo", "ataque con dron", "drone ataca",
        # English
        "airstrike", "air strike", "drone strike", "drone attack", "aerial bombing",
    ],
    "suicide_bomb": [
        # Spanish
        "atentado suicida", "coche bomba", "bomba suicida", "terrorista suicida",
        # English
        "suicide bomb", "suicide bomber", "suicide attack", "car bomb", "truck bomb",
        "vehicle-borne explosive",
    ],
    "shelling_artillery_missile": [
        # Spanish
        "bombardeo de artilleria", "proyectil de mortero", "ataque con mortero",
        "fuego de artilleria", "ataque con misil", "misil impacta",
        # English
        "shelling", "artillery fire", "artillery attack", "mortar attack",
        "missile strike", "missile attack", "rocket attack",
    ],
    "remote_explosive_ied": [
        # Spanish
        "artefacto explosivo", "bomba casera", "explosivo improvizado",
        "mina antipersona", "mina terrestre", "campo minado", "mina explosiva",
        "petardo explosivo", "dinamita", "detonacion de explosivo",
        "paquete bomba", "carta bomba",
        # English  
        "improvised explosive", "explosive device", "landmine", "land mine",
        "roadside bomb", "pipe bomb", "letter bomb", "package bomb",
        "detonation", "bomb explodes", "bomb explosion", "bombing",
    ],
    "grenade": [
        # Spanish
        "granada de mano", "ataque con granada", "lanzamiento de granada",
        "granada explosiva",
        # English
        "grenade attack", "hand grenade", "grenade thrown", "grenade explosion",
    ],
    
    # =========================================================================
    # VIOLENCE AGAINST CIVILIANS
    # =========================================================================
    "sexual_violence": [
        # Spanish
        "violacion sexual", "abuso sexual", "acoso sexual", "violencia sexual",
        "agresion sexual", "ataque sexual", "asalto sexual",
        # English
        "sexual assault", "sexual violence", "sexual abuse", "rape victim",
        "sexually assaulted", "sexual attack",
    ],
    "attack": [
        # Spanish
        "asesinato", "asesinado", "homicidio", "fue asesinado", "matan a",
        "ataque contra", "agresion contra", "golpiza", "linchamiento",
        "sicariato", "crimen violento", "disparo contra", "herido de bala",
        "herido de gravedad", "lesiones graves", "apuñalado", "acuchillado",
        "atacado con", "victima de ataque",
        # English
        "murdered", "murder of", "homicide", "killed in attack", "fatally shot",
        "shot dead", "stabbed to death", "beaten to death", "lynched",
        "assassination", "assassinated", "attack on civilian", "attack against",
        "violent attack", "victim of attack",
        # Electoral violence (Peru specific)
        "ataque a candidato", "agresion a politico", "atentado contra candidato",
        "amenaza de muerte a candidato", "intimidacion electoral",
        "violencia electoral", "ataque a local partidario",
        "attack on candidate", "political violence", "electoral violence",
    ],
    "abduction_disappearance": [
        # Spanish
        "secuestro", "secuestrado", "secuestraron", "desaparicion forzada",
        "desaparecido", "reportado desaparecido", "rapto de", "plagiado",
        "retenido ilegalmente", "privacion ilegal de libertad",
        "levantado por", "se lo llevaron",
        # English
        "kidnapped", "kidnapping", "abducted", "abduction", "forcibly disappeared",
        "missing person", "taken hostage", "held captive", "forced disappearance",
    ],
    
    # =========================================================================
    # PROTESTS
    # =========================================================================
    "peaceful_protest": [
        # Spanish
        "marcha pacifica", "manifestacion pacifica", "protesta pacifica",
        "planton pacifico", "concentracion pacifica", "vigilia", "caminata",
        "movilizacion pacifica", "marcha de protesta", "protesta ciudadana",
        "manifestantes marchan", "miles marchan",
        # English
        "peaceful protest", "peaceful demonstration", "peaceful march",
        "peaceful rally", "sit-in", "vigil", "protesters march peacefully",
        # Electoral (Peru)
        "marcha electoral", "protesta por resultados", "reclamo electoral",
        "manifestacion politica", "mitin politico", "concentracion politica",
        "election protest", "electoral demonstration",
    ],
    "protest_with_intervention": [
        # Spanish
        "policia dispersa", "policia disperso", "intervencion policial en protesta",
        "gases lacrimogenos contra", "desalojo de manifestantes",
        "policia interviene en marcha", "disuelven manifestacion",
        # English
        "police disperse", "tear gas used", "protesters dispersed",
        "police intervention", "demonstration broken up",
    ],
    "excessive_force_against_protesters": [
        # Spanish
        "represion policial", "brutalidad policial", "fuerza excesiva contra",
        "violencia policial contra manifestantes", "abuso policial",
        "golpean a manifestantes", "disparan contra manifestantes",
        # English
        "police brutality", "excessive force", "police violence against protesters",
        "violent crackdown", "protesters beaten", "protesters shot",
    ],
    
    # =========================================================================
    # RIOTS
    # =========================================================================
    "violent_demonstration": [
        # Spanish
        "disturbios", "vandalismo", "destruccion de propiedad",
        "quema de llantas", "bloqueo violento", "enfrentamiento con policia",
        "manifestantes violentos", "protesta violenta", "desmanes",
        "destrozos", "atacan vehiculos", "rompen ventanas",
        # English
        "rioting", "rioters", "violent protest", "violent demonstration",
        "vandalism", "property destruction", "clashes with police",
        "violent clashes", "protesters clash",
        # Electoral (Peru)
        "protesta electoral violenta", "disturbios electorales",
        "enfrentamiento entre partidarios", "violencia en mitin",
        "electoral riot", "election violence",
    ],
    "mob_violence": [
        # Spanish
        "turba enfurecida", "turba ataca", "linchamiento popular",
        "violencia de masas", "ajusticiamiento popular", "quema de vehiculo",
        "saqueo masivo", "muchedumbre ataca", "turbas violentas",
        # English
        "mob attack", "mob violence", "lynching", "vigilante violence",
        "crowd violence", "mass looting",
    ],
    
    # =========================================================================
    # STRATEGIC DEVELOPMENTS
    # =========================================================================
    "agreement": [
        # Spanish
        "acuerdo de paz", "tregua", "negociacion de paz", "dialogo de paz",
        "cese al fuego", "alto al fuego", "firma de acuerdo", "pacto de paz",
        # English
        "peace agreement", "peace deal", "ceasefire", "truce", "peace talks",
        "peace negotiations", "peace accord",
    ],
    "arrest": [
        # Spanish
        "detencion de", "detenido por", "arrestado por", "captura de",
        "prision preventiva", "intervenido por policia", "fue arrestado",
        "operativo de captura", "cae presunto",
        # English
        "arrested for", "detention of", "detained by", "captured by police",
        "taken into custody", "placed under arrest", "apprehended",
    ],
    "change_to_group_activity": [
        # Spanish
        "disolucion de grupo", "reorganizacion de", "cambio de liderazgo",
        "grupo se desintegra", "faccion se separa",
        # English
        "group dissolved", "leadership change", "faction splits",
        "organization restructured",
    ],
    "disrupted_weapons_use": [
        # Spanish
        "incautacion de armas", "decomiso de explosivos", "interceptado",
        "frustrado atentado", "desactivan bomba", "armas decomisadas",
        "arsenal incautado",
        # English
        "weapons seized", "explosives seized", "attack foiled", "bomb defused",
        "intercepted shipment", "arms cache found",
    ],
    "looting_property_destruction": [
        # Spanish
        "saqueo de", "saqueos", "robo masivo", "destruccion de local",
        "incendio provocado", "incendio de local", "quema de edificio",
        # English
        "looting", "mass looting", "arson attack", "building burned",
        "property destroyed", "stores looted",
        # Electoral (Peru)
        "destruccion de material electoral", "quema de anforas",
        "ataque a local de votacion", "sabotaje electoral",
        "electoral sabotage", "ballot destruction",
    ],
}


# =============================================================================
# CLASSIFICATION RESULT
# =============================================================================

@dataclass
class ACLEDClassification:
    """Result of ACLED-based classification."""
    event_type: str
    sub_event_type: str
    disorder_type: str
    confidence: float
    matched_keywords: list[str]
    
    @property
    def event_type_label(self) -> str:
        return EVENT_TYPES.get(self.event_type, self.event_type)
    
    @property
    def sub_event_type_label(self) -> str:
        info = SUB_EVENT_TYPES.get(self.sub_event_type)
        return info[1] if info else self.sub_event_type


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = (text or "").lower()
    # Remove accents for matching
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def keyword_matches(text: str, keyword: str) -> bool:
    """
    Check if keyword matches in text using word boundaries for short keywords.
    This prevents 'mina' from matching inside 'determinación'.
    """
    keyword_norm = normalize_text(keyword)
    
    # For short keywords (<=5 chars), use word boundary matching
    if len(keyword_norm) <= 5:
        pattern = r'\b' + re.escape(keyword_norm) + r'\b'
        return bool(re.search(pattern, text))
    else:
        # For longer keywords, simple substring match is fine
        return keyword_norm in text


def classify_incident(title: str, body: str) -> ACLEDClassification:
    """
    Classify an incident using ACLED methodology.
    
    Args:
        title: Article title
        body: Article body text
        
    Returns:
        ACLEDClassification with event_type, sub_event_type, confidence
    """
    text = normalize_text(f"{title}\n{body}")
    
    # Count keyword matches for each sub-event type
    scores: dict[str, tuple[int, list[str]]] = {}
    
    for sub_type, keywords in KEYWORD_RULES.items():
        hits = []
        for kw in keywords:
            if keyword_matches(text, kw):
                hits.append(kw)
        if hits:
            scores[sub_type] = (len(hits), hits)
    
    if not scores:
        # Default: strategic_developments/other
        return ACLEDClassification(
            event_type="strategic_developments",
            sub_event_type="other",
            disorder_type="strategic_developments",
            confidence=0.2,
            matched_keywords=[],
        )
    
    # Find best match (most keyword hits)
    best_sub_type = max(scores.keys(), key=lambda k: scores[k][0])
    hit_count, matched_keywords = scores[best_sub_type]
    
    # Get event type from sub-event type
    sub_info = SUB_EVENT_TYPES.get(best_sub_type)
    if sub_info:
        event_type = sub_info[0]
    else:
        event_type = "strategic_developments"
    
    # Determine disorder type
    disorder_type = "strategic_developments"
    for dt, event_types in DISORDER_TYPES.items():
        if event_type in event_types:
            disorder_type = dt
            break
    
    # Calculate confidence based on number of hits and specificity
    base_confidence = 0.4
    confidence = min(0.95, base_confidence + 0.08 * hit_count)
    
    # Boost confidence for longer/more specific keywords
    if matched_keywords:
        avg_kw_len = sum(len(k) for k in matched_keywords) / len(matched_keywords)
        if avg_kw_len > 15:
            confidence = min(0.95, confidence + 0.1)
        elif avg_kw_len > 10:
            confidence = min(0.95, confidence + 0.05)
    
    return ACLEDClassification(
        event_type=event_type,
        sub_event_type=best_sub_type,
        disorder_type=disorder_type,
        confidence=round(confidence, 2),
        matched_keywords=matched_keywords[:5],  # Limit to top 5
    )


def classify_simple(title: str, body: str) -> Tuple[str, str, float]:
    """
    Simple classification returning tuple (event_type, sub_event_type, confidence).
    For backward compatibility.
    """
    result = classify_incident(title, body)
    return (result.event_type, result.sub_event_type, result.confidence)


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

def classify(text: str) -> Tuple[str, float]:
    """
    Legacy function - returns (incident_type, confidence).
    Maps to new ACLED event_type.
    """
    result = classify_incident(text, "")
    return (result.event_type, result.confidence)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    test_cases = [
        # Spanish
        ("Enfrentamiento armado deja 3 policías heridos en Vraem", ""),
        ("Marcha pacífica en Lima por reformas electorales", ""),
        ("Explosión de coche bomba cerca de comisaría", ""),
        ("Candidato a alcaldía denuncia amenazas de muerte", ""),
        ("Turba enfurecida lincha a presunto ladrón en mercado", ""),
        ("Detenidos 5 sospechosos de terrorismo", ""),
        ("Protesta de agricultores bloquea carretera", "Miles de agricultores bloquearon la vía exigiendo mejores precios."),
        ("Perú expulsa a Ecuador a 120 migrantes extranjeros", "Los migrantes fueron determinados a salir por ingreso irregular."),
        # English
        ("Peaceful protest in Lima demands electoral reform", "Thousands marched peacefully through downtown."),
        ("Armed clash between police and drug traffickers", "A firefight erupted in the border region."),
        ("Candidate receives death threats", "The politician reported intimidation by unknown individuals."),
        ("Riot breaks out after election results announced", "Violent clashes with police left several injured."),
    ]
    
    print("=" * 70)
    print("ACLED Classification Test (v2 - Improved)")
    print("=" * 70)
    
    for title, body in test_cases:
        result = classify_incident(title, body)
        print(f"\nTitle: {title[:55]}...")
        print(f"  Event Type:     {result.event_type}")
        print(f"  Sub-Event Type: {result.sub_event_type}")
        print(f"  Disorder Type:  {result.disorder_type}")
        print(f"  Confidence:     {result.confidence}")
        print(f"  Keywords:       {result.matched_keywords[:3]}")