#!/usr/bin/env python
"""
scripts/tests/test_m7_patrones_internacionales.py

Test de validación para patrones M7 de detección de noticias internacionales.
Verifica que los nuevos patrones de entretenimiento, deportes, tech y conflictos
funcionen correctamente en el filtro pre-LLM.

Uso:
    python scripts/tests/test_m7_patrones_internacionales.py
"""

import re
import sys
from typing import List

# ============================================================================
# COPIA DE PATRONES PARA TEST INDEPENDIENTE
# (Debe mantenerse sincronizado con llm_enrichment_pipeline.py)
# ============================================================================

PATRONES_INTERNACIONALES_TITULO = [
    # Países explícitos en título
    r'^(?:en|desde) (?:ee\.?uu\.?|estados unidos|colombia|venezuela|ecuador|bolivia|chile|brasil|argentina|méxico)',
    r'(?:ee\.?uu\.?|estados unidos|colombia|venezuela|ecuador|bolivia|chile|brasil|argentina|méxico)[\:\,\.]',
    
    # Líderes políticos extranjeros
    r'\b(?:maduro|petro|lula|biden|trump|milei|boric|bukele|xi jinping|putin|zelensky|netanyahu|papa francisco|papa león)\b',
    
    # Eventos claramente internacionales
    r'en (?:la )?(?:casa blanca|kremlin|vaticano|onu|otan|unión europea)',
    r'guerra (?:en|de) (?:ucrania|gaza|siria|irak)',
    r'elecciones? (?:en|de) (?:ee\.?uu\.?|estados unidos|colombia|venezuela|ecuador|bolivia|chile|brasil|argentina|méxico)',
    
    # Deportes internacionales (que no son de Perú)
    r'\b(?:nba|nfl|mlb|premier league|la liga española|bundesliga|serie a italiana|champions league)\b',
    r'\b(?:real madrid|barcelona fc|manchester|juventus|psg|bayern)\b',
    # M7: Torneos mundiales
    r'\b(?:mundial|copa del mundo|eurocopa|copa am[ée]rica|nations league)\b',
    r'\b(?:fifa|uefa|conmebol)\b',
    
    # Netflix, Hollywood, farándula internacional
    r'\b(?:netflix|hollywood|grammy|oscar|emmy|golden globe)\b',
    r'\bserie (?:de netflix|sueca|coreana|americana|española)\b',
    r'\bk-drama[s]?\b',
    # M7: K-pop y entretenimiento asiático/global
    r'\b(?:k-?pop|bts|blackpink|twice|stray kids|enhypen)\b',
    r'\b(?:anime|manga|studio ghibli|crunchyroll)\b',
    r'\b(?:taylor swift|bad bunny|shakira|drake|beyonc[eé]|rihanna)\b',
    r'\b(?:disney\+?|hbo max|amazon prime|apple tv)\b',
    
    # M7: Empresas tech y magnates
    r'\b(?:elon musk|jeff bezos|mark zuckerberg|sam altman|bill gates)\b',
    r'\b(?:tesla|spacex|neuralink|boring company)\b',
    r'\b(?:meta|facebook|instagram|whatsapp)\b(?! peru| perú)',
    r'\b(?:amazon|google|apple|microsoft|openai|nvidia)\b(?! peru| perú)',
    r'\b(?:twitter|x\.com|tiktok|snapchat)\b',
    
    # M7: Conflictos y fronteras internacionales específicos
    r'\bfrontera (?:colombo-?venezolana|mexico-?estadounidense|israelí-?palestina)\b',
    r'\bconflicto (?:en|de) (?:ucrania|gaza|siria|yemen|sudán|myanmar)\b',
    r'\bcrisis (?:en|de) (?:venezuela|haiti|siria|afganistán)\b',
    r'\bmigratoria (?:en|de|hacia) (?:ee\.?uu\.?|europa|méxico)\b',
]

PATRONES_PERU_EXPLICITO = [
    r'\bperú\b', r'\bperu\b', r'\blima\b', r'\bcallao\b',
    r'\barequipa\b', r'\btrujillo\b', r'\bchiclayo\b', r'\bpiura\b',
    r'\bcusco\b', r'\biquit[oa]s\b', r'\bhuancayo\b', r'\btacna\b',
    r'\bpuno\b', r'\bayacucho\b', r'\bcajamarca\b', r'\bhuánuco\b',
    r'\bpolicía nacional\b', r'\bpnp\b', r'\bministerio público\b',
    r'\bfiscalía\b', r'\bcongreso (?:de la república|peruano)\b',
    r'\bjne\b', r'\bonpe\b', r'\breniec\b',
    r'\bperuano[as]?\b', r'\bciudadano[as]? peruano',
    r'\bvraem\b', r'\bsendero luminoso\b',
]

PAISES_INTERNACIONALES = [
    'colombia', 'venezuela', 'ecuador', 'bolivia', 'chile', 'brasil', 'brazil',
    'argentina', 'uruguay', 'paraguay', 'guyana', 'surinam',
    'méxico', 'mexico', 'nicaragua', 'el salvador', 'honduras', 'guatemala', 
    'panamá', 'panama', 'cuba', 'haiti', 'haití', 'república dominicana',
    'puerto rico', 'costa rica', 'belice',
    'estados unidos', 'eeuu', 'ee.uu.', 'usa', 'u.s.a.', 'canadá', 'canada',
    'españa', 'espana', 'francia', 'alemania', 'italia', 'reino unido', 
    'inglaterra', 'rusia', 'ucrania', 'polonia', 'suecia',
    'china', 'japón', 'japon', 'corea', 'india', 'israel', 'gaza', 'palestina',
    'irán', 'iran', 'irak', 'siria', 'turquía', 'turquia', 'arabia saudita',
    'taiwán', 'taiwan', 'filipinas',
    'sudáfrica', 'nigeria', 'egipto', 'australia', 'nueva zelanda',
]

CIUDADES_INTERNACIONALES = [
    'california', 'nueva york', 'new york', 'texas', 'florida', 'miami',
    'los angeles', 'los ángeles', 'chicago', 'washington d.c.', 'las vegas',
    'san francisco', 'boston', 'seattle', 'denver', 'phoenix', 'atlanta',
    'bogotá', 'bogota', 'medellín', 'medellin', 'caracas', 'quito', 'guayaquil',
    'la paz', 'santiago de chile', 'buenos aires', 'montevideo', 'asunción', 'asuncion',
    'são paulo', 'sao paulo', 'río de janeiro', 'rio de janeiro', 'brasilia',
    'ciudad de méxico', 'guadalajara', 'monterrey',
    'madrid', 'barcelona', 'londres', 'london', 'parís', 'paris', 'berlín', 'berlin',
    'roma', 'moscú', 'moscu', 'kiev', 'kyiv',
    'beijing', 'pekín', 'pekin', 'shanghai', 'tokio', 'tokyo', 'seúl', 'seoul',
    'nueva delhi', 'mumbai', 'tel aviv', 'jerusalén', 'teherán',
]


def filtro_pre_llm_internacional(titulo: str, body: str = None) -> bool:
    """
    FILTRO PRE-LLM: Detecta si un artículo es claramente internacional.
    
    Returns:
        True si es claramente internacional (NO enviar al LLM)
        False si podría ser de Perú (enviar al LLM para clasificar)
    """
    titulo_lower = titulo.lower()
    body_lower = (body or "")[:500].lower()
    texto_completo = f"{titulo_lower} {body_lower}"
    
    # PRIMERO: Si menciona explícitamente Perú, NO es internacional
    for pattern in PATRONES_PERU_EXPLICITO:
        if re.search(pattern, texto_completo, re.IGNORECASE):
            return False
    
    # SEGUNDO: Verificar patrones de título claramente internacional
    for pattern in PATRONES_INTERNACIONALES_TITULO:
        if re.search(pattern, titulo_lower, re.IGNORECASE):
            return True
    
    # TERCERO: Verificar países en título
    for pais in PAISES_INTERNACIONALES:
        if pais in titulo_lower:
            if f'peruano en {pais}' in texto_completo or f'peruana en {pais}' in texto_completo:
                return False
            if f'peruanos en {pais}' in texto_completo or f'peruanas en {pais}' in texto_completo:
                return False
            return True
    
    # CUARTO: Verificar ciudades extranjeras en título
    for ciudad in CIUDADES_INTERNACIONALES:
        if ciudad in titulo_lower:
            return True
    
    return False


def test_m7_patrones():
    """Test de patrones M7 añadidos al filtro pre-LLM."""
    
    # Casos que DEBEN ser detectados como internacionales (True)
    casos_internacionales = [
        # Entretenimiento K-pop
        ("BTS anuncia nueva gira mundial para 2026", True),
        ("Blackpink rompe récord en Spotify", True),
        ("K-pop: Stray Kids llega a Latinoamérica", True),
        
        # Anime y entretenimiento asiático
        ("Nuevo anime de Studio Ghibli se estrena en Netflix", True),
        ("Crunchyroll anuncia exclusivas para el verano", True),
        
        # Artistas globales
        ("Taylor Swift extiende su gira Eras Tour", True),
        ("Bad Bunny lanza nuevo álbum", True),
        ("Shakira se presenta en el Super Bowl", True),
        
        # Streaming platforms
        ("Disney+ estrena nueva serie de Star Wars", True),
        ("HBO Max cancela producción millonaria", True),
        ("Amazon Prime sube precios en Latinoamérica", True),
        
        # Deportes mundiales - torneos
        ("Mundial 2026: sedes confirmadas en Norteamérica", True),
        ("Copa del Mundo: selección argentina entrena", True),
        ("Eurocopa 2024: Francia vs Alemania en semifinales", True),
        ("UEFA confirma cambios en Champions League", True),
        ("FIFA sanciona a federación por incidentes", True),
        
        # Tech y magnates
        ("Elon Musk compra nueva empresa", True),
        ("Tesla presenta nuevo modelo eléctrico", True),
        ("SpaceX lanza cohete hacia Marte", True),
        ("Mark Zuckerberg anuncia cambios en Meta", True),
        ("OpenAI presenta GPT-5 con nuevas capacidades", True),
        ("Nvidia supera a Apple en capitalización", True),
        
        # Conflictos específicos
        ("Crisis en la frontera colombo-venezolana se agrava", True),
        ("Conflicto en Ucrania: nueva ofensiva rusa", True),
        ("Crisis de Venezuela: miles huyen del país", True),
        ("Crisis migratoria hacia EEUU alcanza nuevo récord", True),
    ]
    
    # Casos que NO deben ser detectados como internacionales (False)
    # porque mencionan Perú o son claramente locales
    casos_peru = [
        ("Concierto de K-pop en Lima reúne a miles de fans", False),
        ("Netflix Perú: series más vistas en el país", False),
        ("Peruano gana concurso de cosplay de anime", False),
        ("Taylor Swift: fans peruanos esperan anuncio de concierto", False),
        ("Meta Perú anuncia inversión en el país", False),
        ("Amazon abre nuevo centro logístico en Lima", False),
        ("Mundial 2026: Perú busca clasificar", False),
        ("Peruanos en frontera colombo-venezolana", False),
        ("Migrantes peruanos retornan de Venezuela", False),
        ("Operativo policial en Lima deja detenidos", False),
        ("Feminicidio en Arequipa conmociona al país", False),
    ]
    
    print("=" * 70)
    print("TEST M7: PATRONES DE DETECCIÓN INTERNACIONAL")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    # Test casos internacionales
    print("\n[1/2] Testing casos que DEBEN ser internacionales...")
    print("-" * 70)
    for titulo, esperado in casos_internacionales:
        resultado = filtro_pre_llm_internacional(titulo)
        status = "✓" if resultado == esperado else "✗"
        if resultado == esperado:
            passed += 1
        else:
            failed += 1
            print(f"  {status} FAIL: '{titulo[:50]}...'")
            print(f"       Esperado: {esperado}, Obtenido: {resultado}")
    
    # Test casos Perú
    print("\n[2/2] Testing casos que NO deben ser internacionales (Perú)...")
    print("-" * 70)
    for titulo, esperado in casos_peru:
        resultado = filtro_pre_llm_internacional(titulo)
        status = "✓" if resultado == esperado else "✗"
        if resultado == esperado:
            passed += 1
        else:
            failed += 1
            print(f"  {status} FAIL: '{titulo[:50]}...'")
            print(f"       Esperado: {esperado}, Obtenido: {resultado}")
    
    # Resumen
    total = passed + failed
    print("\n" + "=" * 70)
    print(f"RESUMEN: {passed}/{total} tests pasaron")
    if failed > 0:
        print(f"         {failed} tests fallaron")
        return 1
    else:
        print("         ✓ Todos los patrones M7 funcionan correctamente")
        return 0


def test_patrones_existentes_no_rotos():
    """Verifica que los patrones existentes siguen funcionando."""
    
    casos_existentes = [
        # Líderes políticos (ya existían)
        ("Trump anuncia candidatura presidencial", True),
        ("Putin ordena movilización militar", True),
        ("Milei implementa nuevas medidas económicas", True),
        
        # Deportes existentes
        ("Real Madrid gana la Champions League", True),
        ("Barcelona FC ficha nuevo jugador", True),
        ("NBA: Lakers vs Celtics en finales", True),
        
        # Netflix/Hollywood existentes
        ("Netflix cancela serie popular", True),
        ("Oscar 2026: nominaciones anunciadas", True),
        
        # Países en título
        ("Colombia: protestas en Bogotá", True),
        ("Venezuela: crisis humanitaria se agrava", True),
    ]
    
    print("\n" + "=" * 70)
    print("TEST: PATRONES EXISTENTES (no deben romperse)")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for titulo, esperado in casos_existentes:
        resultado = filtro_pre_llm_internacional(titulo)
        if resultado == esperado:
            passed += 1
        else:
            failed += 1
            print(f"  ✗ REGRESSION: '{titulo}'")
            print(f"       Esperado: {esperado}, Obtenido: {resultado}")
    
    total = passed + failed
    print(f"\nPatrones existentes: {passed}/{total} funcionan correctamente")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = 0
    exit_code += test_m7_patrones()
    exit_code += test_patrones_existentes_no_rotos()
    
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✓ TODOS LOS TESTS PASARON - M7 implementado correctamente")
    else:
        print("✗ ALGUNOS TESTS FALLARON - revisar patrones")
    print("=" * 70)
    
    sys.exit(exit_code)
