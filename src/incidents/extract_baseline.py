"""
src/incidents/extract_baseline.py - Baseline incident extraction with ACLED classification

Extracts incidents from news articles using:
1. ACLED-based classification (6 event types, 25 sub-event types)
2. Location extraction from title/body
3. Stable incident ID generation

Reference: https://acleddata.com/knowledge-base/codebook/

Usage:
    from src.incidents.extract_baseline import extract_from_article
    
    incident = extract_from_article(article_dict, run_id, version)
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, Tuple, Optional

# Try to import ACLED rules, fall back to simple rules if not available
try:
    from src.incidents.acled_rules import classify_incident, ACLEDClassification
    USE_ACLED = True
except ImportError:
    USE_ACLED = False


# =============================================================================
# SIMPLE CLASSIFICATION (fallback if acled_rules not available)
# =============================================================================

SIMPLE_RULES = [
    ("battles", [
        "enfrentamiento", "tiroteo", "balacera", "combate", "fuego cruzado"
    ]),
    ("explosions_remote_violence", [
        "explosion", "bomba", "explosivo", "granada", "dinamita", "detonacion"
    ]),
    ("violence_against_civilians", [
        "asesinato", "homicidio", "muerte", "ataque", "agresion", 
        "secuestro", "linchamiento", "sicariato", "violacion"
    ]),
    ("protests", [
        "protesta", "marcha", "manifestacion", "planon", "concentracion"
    ]),
    ("riots", [
        "disturbio", "vandalismo", "saqueo", "turba", "bloqueo violento"
    ]),
    ("strategic_developments", [
        "detencion", "captura", "acuerdo", "negociacion", "incautacion"
    ]),
]


def simple_classify(text: str) -> Tuple[str, str, float]:
    """Simple keyword-based classification (fallback)."""
    t = (text or "").lower()
    
    best_type = "strategic_developments"
    best_sub = "other"
    best_score = 0.2
    
    for event_type, keywords in SIMPLE_RULES:
        hits = sum(1 for kw in keywords if kw in t)
        if hits > 0:
            score = min(0.95, 0.4 + 0.1 * hits)
            if score > best_score:
                best_type = event_type
                best_sub = f"{event_type}_general"
                best_score = score
    
    return (best_type, best_sub, best_score)


# =============================================================================
# INCIDENT ID GENERATION
# =============================================================================

def stable_incident_id(original_uri: str, url: str) -> str:
    """
    Generate stable incident ID from article URI.
    1 incident per article => ID is stable by canonical URI.
    """
    key = (original_uri or url or "").strip()
    if not key:
        key = "unknown"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


# =============================================================================
# LOCATION EXTRACTION
# =============================================================================

# Major Peruvian locations for simple extraction
PERU_LOCATIONS = {
    # Departments
    "lima", "arequipa", "cusco", "cuzco", "piura", "la libertad", "trujillo",
    "lambayeque", "chiclayo", "junin", "huancayo", "ancash", "huaraz",
    "loreto", "iquitos", "cajamarca", "puno", "juliaca", "tacna", "ica",
    "ucayali", "pucallpa", "san martin", "tarapoto", "huanuco", "ayacucho",
    "apurimac", "madre de dios", "puerto maldonado", "amazonas", "tumbes",
    "moquegua", "pasco", "huancavelica", "callao",
    # Zones
    "vraem", "vrae",
    # Major cities/districts in Lima
    "miraflores", "san isidro", "surco", "san borja", "la molina",
    "chorrillos", "barranco", "magdalena", "pueblo libre", "jesus maria",
    "lince", "san miguel", "breña", "rimac", "cercado", "ate", "vitarte",
    "santa anita", "el agustino", "san juan de lurigancho", "comas",
    "los olivos", "san martin de porres", "independencia", "carabayllo",
    "puente piedra", "villa el salvador", "villa maria del triunfo",
    "san juan de miraflores", "surquillo", "lurin", "pachacamac",
    # Other important places
    "chimbote", "sullana", "talara", "paita", "huacho", "chancay",
    "chincha", "nazca", "mollendo", "ilo", "chachapoyas", "moyobamba",
    "jaen", "bagua", "yurimaguas", "contamana", "requena", "nauta",
    "satipo", "la merced", "tarma", "abancay", "andahuaylas",
    "huanta", "huamanga", "pisco", "cerro de pasco",
}


def extract_location_text_simple(title: str, body: str, gazetteer_names: set[str] | None = None) -> Optional[str]:
    """
    Extract location mentions from text.
    
    Args:
        title: Article title
        body: Article body
        gazetteer_names: Optional set of place names from gazetteer
        
    Returns:
        Semicolon-separated list of found locations, or None
    """
    # Use provided gazetteer names if available, otherwise use built-in list
    locations_to_check = gazetteer_names or PERU_LOCATIONS
    
    text = f"{title or ''} {body or ''}".lower()
    
    found = []
    for loc in locations_to_check:
        # Check if location appears as a word (not part of another word)
        if re.search(r'\b' + re.escape(loc) + r'\b', text):
            found.append(loc.title())
    
    if found:
        # Return first 3 unique locations
        unique = []
        seen = set()
        for f in found:
            f_lower = f.lower()
            if f_lower not in seen:
                unique.append(f)
                seen.add(f_lower)
        return "; ".join(unique[:3])
    
    return None


# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================

def extract_from_article(
    row: Dict, 
    ingest_run_id: str, 
    extraction_version: str,
    gazetteer_names: set[str] | None = None,
) -> Dict:
    """
    Extract incident data from a news article.
    
    Uses ACLED methodology for classification:
    - 6 Event Types: battles, explosions_remote_violence, violence_against_civilians,
                     protests, riots, strategic_developments
    - 25 Sub-Event Types for detailed classification
    - 3 Disorder Types: political_violence, demonstrations, strategic_developments
    
    Args:
        row: Article data dict with keys: original_uri, url, title, body, published_at, source
        ingest_run_id: Run ID for tracking
        extraction_version: Version string for the extraction model
        gazetteer_names: Optional set of place names for location extraction
        
    Returns:
        Dict with incident fields including ACLED classification
    """
    original_uri = (row.get("original_uri") or "").strip()
    url = (row.get("url") or "").strip()
    title = row.get("title") or ""
    body = row.get("body") or ""
    published_at = row.get("published_at")
    
    # Classify using ACLED methodology
    if USE_ACLED:
        acled_result = classify_incident(title, body)
        event_type = acled_result.event_type
        sub_event_type = acled_result.sub_event_type
        disorder_type = acled_result.disorder_type
        confidence = acled_result.confidence
    else:
        event_type, sub_event_type, confidence = simple_classify(f"{title}\n{body}")
        disorder_type = "political_violence"  # Default
    
    # Extract location text
    location_text = extract_location_text_simple(title, body, gazetteer_names)
    
    return {
        # Keys
        "incident_id": stable_incident_id(original_uri, url),
        "ingest_run_id": ingest_run_id,
        
        # Source fields
        "source": row.get("source") or "newsapi_ai",
        "original_uri": original_uri or None,
        "url": url or (original_uri or None),
        "published_at": published_at,
        
        # Content
        "title": title,
        "body": body,
        
        # ACLED Classification
        "incident_type": event_type,           # ACLED event_type
        "sub_event_type": sub_event_type,      # ACLED sub_event_type (NEW)
        "disorder_type": disorder_type,        # ACLED disorder_type (NEW)
        "confidence": confidence,
        "extraction_version": extraction_version,
        
        # NLP placeholders
        "actors_json": None,
        "victims_json": None,
        
        # Location
        "location_text": location_text,
        
        # GEO placeholders (filled by geo resolver)
        "place_id": None,
        "lat": None,
        "lon": None,
        "adm1": None,
        "adm2": None,
        "adm3": None,
        
        # Review
        "review_status": "NEW",
        "review_notes": None,
    }


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

def classify(text: str) -> Tuple[str, float]:
    """
    Legacy function - returns (incident_type, confidence).
    """
    if USE_ACLED:
        result = classify_incident(text, "")
        return (result.event_type, result.confidence)
    else:
        event_type, _, confidence = simple_classify(text)
        return (event_type, confidence)


def extract_incidents_from_articles(articles: list[Dict], run_id: str, version: str) -> list[Dict]:
    """
    Extract incidents from multiple articles.
    Legacy function for backward compatibility.
    """
    return [extract_from_article(a, run_id, version) for a in articles]


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with sample articles
    test_articles = [
        {
            "title": "Enfrentamiento armado entre policías y narcotraficantes deja 3 muertos en el VRAEM",
            "body": "Un tiroteo se produjo en la zona de Pichari cuando efectivos policiales realizaban un operativo.",
            "original_uri": "test1",
            "url": "http://test1.com",
            "published_at": "2025-12-15",
            "source": "test",
        },
        {
            "title": "Miles marchan pacíficamente en Lima por reformas electorales",
            "body": "La manifestación recorrió las principales avenidas sin incidentes.",
            "original_uri": "test2",
            "url": "http://test2.com",
            "published_at": "2025-12-15",
            "source": "test",
        },
        {
            "title": "Candidato a alcaldía recibe amenazas de muerte",
            "body": "El político denunció intimidación por parte de desconocidos en Arequipa.",
            "original_uri": "test3",
            "url": "http://test3.com",
            "published_at": "2025-12-15",
            "source": "test",
        },
    ]
    
    print("=" * 70)
    print("Incident Extraction Test (ACLED Classification)")
    print(f"Using ACLED rules: {USE_ACLED}")
    print("=" * 70)
    
    for article in test_articles:
        result = extract_from_article(article, "test_run", "acled_v1")
        print(f"\nTitle: {result['title'][:60]}...")
        print(f"  Event Type:     {result['incident_type']}")
        print(f"  Sub-Event Type: {result.get('sub_event_type', 'N/A')}")
        print(f"  Disorder Type:  {result.get('disorder_type', 'N/A')}")
        print(f"  Confidence:     {result['confidence']}")
        print(f"  Location:       {result['location_text']}")