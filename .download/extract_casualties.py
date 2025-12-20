#!/usr/bin/env python3
"""
scripts/extract_casualties.py

Extrae número de muertos y heridos desde el texto de noticias.

Patrones detectados:
- "mata a X personas"
- "X muertos/fallecidos"
- "deja X heridos"
- "asesinan a X"
- Números escritos: "dos", "tres", etc.

Usage:
    python scripts/extract_casualties.py --migrate    # Añadir columnas
    python scripts/extract_casualties.py --backfill   # Rellenar datos
    python scripts/extract_casualties.py --all        # Todo
    python scripts/extract_casualties.py --test       # Probar extracción
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
from loguru import logger


# =============================================================================
# NÚMEROS EN TEXTO
# =============================================================================

NUMEROS_ES = {
    "un": 1, "uno": 1, "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "cien": 100,
    "ciento": 100,
}

NUMEROS_EN = {
    "one": 1, "a": 1, "an": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "twenty": 20,
    "thirty": 30,
    "hundred": 100,
}


def text_to_number(text: str) -> int | None:
    """Convierte texto a número."""
    text = text.lower().strip()
    
    # Número directo
    if text.isdigit():
        return int(text)
    
    # Español
    if text in NUMEROS_ES:
        return NUMEROS_ES[text]
    
    # Inglés
    if text in NUMEROS_EN:
        return NUMEROS_EN[text]
    
    return None


# =============================================================================
# PATRONES DE EXTRACCIÓN
# =============================================================================

# Patrones para MUERTOS
DEATH_PATTERNS = [
    # =========================================================================
    # ESPAÑOL - Con números
    # =========================================================================
    r'(\d+)\s*(?:personas?\s+)?muert[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?fallecid[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?asesinadas?',
    r'(\d+)\s*(?:personas?\s+)?abatid[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?ejecutad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?ultimad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?acribillad[oa]s?',
    r'(\d+)\s+víctimas?\s+(?:mortales?|fatales?)',
    r'(\d+)\s+cadáveres?',
    r'(\d+)\s+cuerpos?\s+(?:sin vida)?',
    # Verbos con número
    r'mata(?:n|ron|r)?\s+a\s+(\d+)',
    r'asesinan?\s+a\s+(\d+)',
    r'asesinan?\s+.*?\s+a\s+(\d+)',
    r'deja(?:n|ron)?\s+(\d+)\s+muert[oa]s?',
    r'cobr[óa]\s+(?:la\s+vida\s+de\s+)?(\d+)',
    r'muere(?:n)?\s+(\d+)',
    r'fallece(?:n)?\s+(\d+)',
    r'pierden?\s+la\s+vida\s+(\d+)',
    r'(\d+)\s+pierden?\s+la\s+vida',
    # Hallazgos
    r'hallan?\s+(\d+)\s+muert[oa]s?',
    r'hallan?\s+(\d+)\s+cadáveres?',
    r'hallan?\s+(\d+)\s+cuerpos?',
    r'encuentran?\s+(\d+)\s+muert[oa]s?',
    r'encuentran?\s+(\d+)\s+cadáveres?',
    # =========================================================================
    # ESPAÑOL - Con números en texto
    # =========================================================================
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+muert[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+fallecid[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+personas?\s+muert[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+asesinadas?',
    r'mata(?:n|ron)?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)',
    r'asesinan?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)',
    r'asesinan?\s+.*?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)',
    r'deja(?:n|ron)?\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+muert[oa]s?',
    # =========================================================================
    # INGLÉS - Con números
    # =========================================================================
    r'(\d+)\s+(?:people\s+)?(?:killed|dead|deaths?)',
    r'(\d+)\s+(?:people\s+)?murdered',
    r'(\d+)\s+(?:people\s+)?slain',
    r'(\d+)\s+(?:people\s+)?shot\s+dead',
    r'(\d+)\s+(?:people\s+)?gunned\s+down',
    r'(\d+)\s+(?:people\s+)?found\s+dead',
    r'(\d+)\s+(?:fatal(?:ities)?|victims?)',
    r'(\d+)\s+(?:bodies|corpses?)',
    r'kills?\s+(\d+)',
    r'killed\s+(\d+)',
    r'murder(?:s|ed)?\s+(\d+)',
    r'claims?\s+(\d+)\s+lives?',
    r'(\d+)\s+(?:people\s+)?(?:die|died|dies)',
    r'(\d+)\s+(?:people\s+)?lost\s+(?:their\s+)?lives?',
    r'death\s+toll[:\s]+(\d+)',
    # =========================================================================
    # INGLÉS - Con números en texto
    # =========================================================================
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:people\s+)?(?:killed|dead)',
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+dead',
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:people\s+)?murdered',
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:people\s+)?shot\s+dead',
    r'kills?\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)',
]

# Patrones para HERIDOS
INJURY_PATTERNS = [
    # =========================================================================
    # ESPAÑOL - Con números
    # =========================================================================
    r'(\d+)\s*(?:personas?\s+)?herid[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?lesionad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?hospitalizad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?afectad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?baleadas?',
    r'(\d+)\s*(?:personas?\s+)?apuñalad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?atropellad[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?golpead[oa]s?',
    r'(\d+)\s*(?:personas?\s+)?contus[oa]s?',
    # Verbos con número
    r'deja(?:n|ron)?\s+(\d+)\s+herid[oa]s?',
    r'hiere(?:n|ron)?\s+a\s+(\d+)',
    r'lesiona(?:n|ron)?\s+a\s+(\d+)',
    r'(\d+)\s+(?:personas?\s+)?(?:resultan?|quedan?)\s+herid[oa]s?',
    r'(\d+)\s+(?:\w+\s+)?resultan?\s+herid[oa]s?',
    r'(\d+)\s+(?:\w+\s+)?quedan?\s+herid[oa]s?',
    r'herid[oa]s?\s+(\d+)\s+personas?',
    r'(\d+)\s+(?:personas?\s+)?trasladad[oa]s?\s+(?:a|al)\s+hospital',
    # =========================================================================
    # ESPAÑOL - Con números en texto
    # =========================================================================
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+(?:\w+\s+)?(?:resultan?|quedan?)\s+herid[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+herid[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+lesionad[oa]s?',
    r'(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+hospitalizad[oa]s?',
    r'deja(?:n|ron)?\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s+herid[oa]s?',
    r'hiere(?:n|ron)?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)',
    # =========================================================================
    # INGLÉS - Con números
    # =========================================================================
    r'(\d+)\s+(?:people\s+)?(?:injured|wounded|hurt)',
    r'(\d+)\s+(?:people\s+)?hospitalized',
    r'(\d+)\s+(?:people\s+)?taken\s+to\s+hospital',
    r'(\d+)\s+(?:people\s+)?in\s+(?:critical|serious|stable)\s+condition',
    r'(\d+)\s+(?:people\s+)?(?:shot|stabbed|beaten)',
    r'injur(?:ed|es|ing)\s+(\d+)',
    r'wound(?:ed|s|ing)\s+(\d+)',
    r'hurt(?:s|ing)?\s+(\d+)',
    r'leaves?\s+(\d+)\s+(?:people\s+)?(?:injured|wounded|hurt)',
    # =========================================================================
    # INGLÉS - Con números en texto
    # =========================================================================
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:people\s+)?(?:injured|wounded|hurt)',
    r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:people\s+)?hospitalized',
    r'injur(?:ed|es|ing)\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)',
]


def extract_number_from_match(match: str) -> int:
    """Extrae número de un match (puede ser dígito o texto)."""
    if not match:
        return 0
    
    match = match.strip()
    
    # Si es dígito
    if match.isdigit():
        return int(match)
    
    # Si es texto
    num = text_to_number(match)
    return num if num else 0


def extract_casualties(title: str, body: str = "") -> dict:
    """
    Extrae número de muertos y heridos del título y cuerpo.
    
    Args:
        title: Título del artículo
        body: Cuerpo del artículo (opcional)
    
    Returns:
        dict con 'deaths' y 'injuries' (int o None)
    """
    text = f"{title or ''} {body or ''}".lower()
    
    # Normalizar texto
    text = re.sub(r'\s+', ' ', text)
    
    deaths = 0
    injuries = 0
    
    # Buscar muertos
    for pattern in DEATH_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            num = extract_number_from_match(match)
            if num > deaths:
                deaths = num
    
    # =========================================================================
    # CASOS ESPECIALES - Detectar 1 muerte implícita
    # =========================================================================
    
    # "hallan/encuentran muerto/a" sin número = 1
    if deaths == 0 and re.search(r'(?:hallan?|encuentran?)\s+(?:el\s+)?(?:cuerpo\s+)?(?:sin\s+vida\s+)?(?:de\s+)?(?:un[oa]?\s+)?(?:\w+\s+)?muert[oa]', text):
        deaths = 1
    
    # "asesinan a [persona]" sin número = 1 (pero no si hay número después)
    if deaths == 0 and re.search(r'asesinan?\s+a\s+(?!.*\d.*muert)', text):
        if not re.search(r'asesinan?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|\d+)', text):
            deaths = 1
    
    # "fue asesinado/a" = 1
    if deaths == 0 and re.search(r'fue\s+asesinada?', text):
        deaths = 1
    
    # "matan a [persona]" sin número = 1
    if deaths == 0 and re.search(r'matan?\s+a\s+(?!.*\d)', text):
        if not re.search(r'matan?\s+a\s+(un[oa]?|dos|tres|cuatro|cinco|\d+)', text):
            deaths = 1
    
    # "muere/fallece [persona]" = 1
    if deaths == 0 and re.search(r'(?:muere|fallece)\s+(?:un[oa]?\s+)?(?:\w+)', text):
        deaths = 1
    
    # "encontrado/a sin vida" = 1
    if deaths == 0 and re.search(r'(?:encontrad[oa]|hallad[oa])\s+sin\s+vida', text):
        deaths = 1
    
    # "perdió la vida" = 1
    if deaths == 0 and re.search(r'perdi[óo]\s+la\s+vida', text):
        deaths = 1
    
    # English: "was killed/murdered/shot dead" = 1
    if deaths == 0 and re.search(r'was\s+(?:killed|murdered|shot\s+dead|found\s+dead|slain)', text):
        deaths = 1
    
    # English: "man/woman/person killed" = 1
    if deaths == 0 and re.search(r'(?:man|woman|person|victim)\s+(?:killed|murdered|shot\s+dead)', text):
        deaths = 1
    
    # English: "found dead" = 1
    if deaths == 0 and re.search(r'(?:man|woman|person|body)\s+found\s+dead', text):
        deaths = 1
    
    # English: "death toll" con número
    if deaths == 0:
        match = re.search(r'death\s+toll\s+(?:rises?\s+to|reaches?|at|is|of)\s+(\d+)', text)
        if match:
            deaths = int(match.group(1))
    
    # Buscar heridos
    for pattern in INJURY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            num = extract_number_from_match(match)
            if num > injuries:
                injuries = num
    
    return {
        "deaths": deaths if deaths > 0 else None,
        "injuries": injuries if injuries > 0 else None,
    }


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def migrate_add_casualty_columns():
    """Añade columnas deaths e injuries a las tablas."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    tables = ["stg_incidents_extracted", "fct_incidents", "fct_daily_report"]
    columns = [
        ("deaths", "INTEGER"),
        ("injuries", "INTEGER"),
    ]
    
    for table in tables:
        for col_name, col_type in columns:
            try:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                logger.success(f"+ {table}.{col_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "Duplicate" in str(e):
                    logger.info(f"✓ {table}.{col_name} ya existe")
                else:
                    logger.warning(f"✗ {table}.{col_name}: {e}")
    
    con.close()
    print("\n✅ Migración completada")


def backfill_casualties():
    """Rellena deaths/injuries desde los textos existentes."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    # Obtener incidentes
    incidents = con.execute("""
        SELECT incident_id, title, body 
        FROM stg_incidents_extracted
    """).fetchdf()
    
    logger.info(f"Procesando {len(incidents)} incidentes...")
    
    updated = 0
    with_deaths = 0
    with_injuries = 0
    
    for _, row in incidents.iterrows():
        result = extract_casualties(row['title'], row['body'])
        
        if result['deaths'] or result['injuries']:
            con.execute("""
                UPDATE stg_incidents_extracted 
                SET deaths = ?, injuries = ?
                WHERE incident_id = ?
            """, [result['deaths'], result['injuries'], row['incident_id']])
            updated += 1
            
            if result['deaths']:
                with_deaths += 1
            if result['injuries']:
                with_injuries += 1
    
    # Propagar a fct_incidents
    con.execute("""
        UPDATE fct_incidents SET 
            deaths = s.deaths,
            injuries = s.injuries
        FROM stg_incidents_extracted s
        WHERE fct_incidents.incident_id = s.incident_id
    """)
    
    # Propagar a fct_daily_report
    con.execute("""
        UPDATE fct_daily_report SET 
            deaths = s.deaths,
            injuries = s.injuries
        FROM stg_incidents_extracted s
        WHERE fct_daily_report.incident_id = s.incident_id
    """)
    
    con.close()
    
    logger.success(f"Actualizados {updated} incidentes")
    logger.info(f"  Con muertos: {with_deaths}")
    logger.info(f"  Con heridos: {with_injuries}")


def test_extraction():
    """Prueba la extracción con casos de ejemplo."""
    
    test_cases = [
        # Español con números
        ("Asesinan de 25 balazos a dos hermanos", "", {"deaths": 2, "injuries": None}),
        ("Pichanaqui: Camioneta mata a dos y deja 12 heridos", "", {"deaths": 2, "injuries": 12}),
        ("Accidente deja 3 muertos y 5 heridos", "", {"deaths": 3, "injuries": 5}),
        ("Balacera deja un muerto y tres heridos", "", {"deaths": 1, "injuries": 3}),
        ("Enfrentamiento cobra la vida de 4 personas", "", {"deaths": 4, "injuries": None}),
        ("7 niños resultan heridos en accidente", "", {"deaths": None, "injuries": 7}),
        # Español implícito (1 muerte)
        ("Hallan muerto a vendedor de motos", "", {"deaths": 1, "injuries": None}),
        ("Asesinan a funcionaria", "", {"deaths": 1, "injuries": None}),
        ("Asesinan a payaso al acudir a show", "", {"deaths": 1, "injuries": None}),
        ("Funcionaria fue asesinada en evento", "", {"deaths": 1, "injuries": None}),
        ("Muere conductor en accidente", "", {"deaths": 1, "injuries": None}),
        ("Hombre encontrado sin vida en su casa", "", {"deaths": 1, "injuries": None}),
        # Español combinado
        ("Asesinan a funcionaria, 7 niños quedan heridos", "", {"deaths": 1, "injuries": 7}),
        # Inglés con números
        ("Explosion kills 10 people", "", {"deaths": 10, "injuries": None}),
        ("Two dead, three injured in crash", "", {"deaths": 2, "injuries": 3}),
        ("Attack leaves 5 dead and 20 injured", "", {"deaths": 5, "injuries": 20}),
        ("Death toll rises to 15", "", {"deaths": 15, "injuries": None}),
        # Inglés implícito
        ("Man was shot dead in robbery", "", {"deaths": 1, "injuries": None}),
        ("Woman found dead in apartment", "", {"deaths": 1, "injuries": None}),
        # Sin víctimas
        ("Marcha pacífica en Lima", "", {"deaths": None, "injuries": None}),
        ("Gobierno anuncia nuevas medidas", "", {"deaths": None, "injuries": None}),
    ]
    
    print("=== TEST DE EXTRACCIÓN DE VÍCTIMAS ===\n")
    
    passed = 0
    failed = 0
    
    for title, body, expected in test_cases:
        result = extract_casualties(title, body)
        
        match = (result['deaths'] == expected['deaths'] and 
                 result['injuries'] == expected['injuries'])
        
        status = "✓" if match else "✗"
        passed += 1 if match else 0
        failed += 0 if match else 1
        
        print(f"{status} '{title[:50]}...'")
        print(f"   Esperado: deaths={expected['deaths']}, injuries={expected['injuries']}")
        print(f"   Obtenido: deaths={result['deaths']}, injuries={result['injuries']}")
        if not match:
            print(f"   ⚠️ FALLO")
        print()
    
    print(f"Resultado: {passed}/{len(test_cases)} tests pasados")
    return failed == 0


def show_results():
    """Muestra incidentes con víctimas extraídas."""
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    print("=== INCIDENTES CON VÍCTIMAS ===\n")
    
    df = con.execute("""
        SELECT 
            incident_date,
            deaths,
            injuries,
            LEFT(title, 60) as title,
            location_display
        FROM fct_daily_report
        WHERE deaths IS NOT NULL OR injuries IS NOT NULL
        ORDER BY COALESCE(deaths, 0) + COALESCE(injuries, 0) DESC
        LIMIT 15
    """).fetchdf()
    
    print(df.to_string(index=False))
    
    # Totales
    totals = con.execute("""
        SELECT 
            SUM(deaths) as total_deaths,
            SUM(injuries) as total_injuries,
            COUNT(*) as incidents_with_casualties
        FROM fct_daily_report
        WHERE deaths IS NOT NULL OR injuries IS NOT NULL
    """).fetchdf()
    
    print(f"\n📊 TOTALES:")
    print(f"   Muertos: {totals['total_deaths'].iloc[0] or 0}")
    print(f"   Heridos: {totals['total_injuries'].iloc[0] or 0}")
    print(f"   Incidentes con víctimas: {totals['incidents_with_casualties'].iloc[0]}")
    
    con.close()


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extraer muertos/heridos de noticias")
    parser.add_argument("--migrate", action="store_true", help="Añadir columnas")
    parser.add_argument("--backfill", action="store_true", help="Rellenar datos")
    parser.add_argument("--test", action="store_true", help="Probar extracción")
    parser.add_argument("--show", action="store_true", help="Mostrar resultados")
    parser.add_argument("--all", action="store_true", help="Ejecutar todo")
    
    args = parser.parse_args()
    
    if args.test:
        success = test_extraction()
        sys.exit(0 if success else 1)
    
    if args.all or args.migrate:
        print("=== Migración ===")
        migrate_add_casualty_columns()
    
    if args.all or args.backfill:
        print("\n=== Backfill ===")
        backfill_casualties()
    
    if args.all or args.show:
        print("\n")
        show_results()
    
    if not any([args.migrate, args.backfill, args.test, args.show, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
