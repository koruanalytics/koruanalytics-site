print("=== Test NLP + GEO (smoke test) ===")

# ---- NLP con spaCy (sin descargar modelos pesados) ----
import spacy

nlp = spacy.blank("en")  # modelo en blanco ligero
doc = nlp("An explosion in Lima killed 3 people.")
print("\n[spaCy] Tokens:")
print([t.text for t in doc])

# ---- GEO con geopy ----
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="osint_test_app")
location = geolocator.geocode("Lima, Peru")
print("\n[geopy] Geocodificación 'Lima, Peru':")
if location:
    print(location.latitude, location.longitude)
else:
    print("No se pudo geocodificar 'Lima, Peru'")

print("\n✅ Smoke test NLP + GEO ejecutado (aunque la geocodificación pueda fallar por red o límites de servicio).")