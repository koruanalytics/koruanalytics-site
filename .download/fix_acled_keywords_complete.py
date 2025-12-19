#!/usr/bin/env python3
"""
Expande las keywords de ACLED con conjugaciones verbales y géneros.
"""

# Keywords expandidas por categoría
EXPANDED_KEYWORDS = {
    "attack": [
        # Spanish - Asesinato (todas las conjugaciones y géneros)
        "asesinato", "asesinatos", "asesinado", "asesinada", "asesinados", "asesinadas",
        "asesinan", "asesinaron", "asesina", "asesinó",
        "fue asesinado", "fue asesinada", "fueron asesinados", "fueron asesinadas",
        # Homicidio
        "homicidio", "homicidios", "homicida", "homicidas",
        # Matar
        "matan a", "mataron a", "mata a", "mató a", "lo mataron", "la mataron",
        "muerto a balazos", "muerta a balazos", "muertos", "muertas",
        # Ataques
        "ataque contra", "ataques contra", "ataque a", "atacan a", "atacaron a",
        "agresion contra", "agresiones contra", "agreden a", "agredieron a",
        "agredido", "agredida", "agredidos", "agredidas",
        # Golpiza/Golpes
        "golpiza", "golpizas", "golpeado", "golpeada", "golpeados", "golpeadas",
        "golpean a", "golpearon a", "a golpes",
        # Linchamiento
        "linchamiento", "linchamientos", "linchado", "linchada", "linchan a", "lincharon a",
        # Sicariato
        "sicariato", "sicario", "sicaria", "sicarios", "sicarias",
        # Crimen
        "crimen violento", "crimenes violentos",
        # Disparos
        "disparo contra", "disparos contra", "disparan contra", "dispararon contra",
        "baleado", "baleada", "baleados", "baleadas", "balearon", "balean a",
        "herido de bala", "herida de bala", "heridos de bala", "heridas de bala",
        "herido de gravedad", "herida de gravedad", "heridos de gravedad",
        "a balazos", "recibió disparos", "recibieron disparos",
        # Lesiones
        "lesiones graves", "lesionado", "lesionada", "lesionados", "lesionadas",
        # Apuñalamiento
        "apuñalado", "apuñalada", "apuñalados", "apuñaladas", "apuñalan", "apuñalaron",
        "acuchillado", "acuchillada", "acuchillados", "acuchilladas", "acuchillan", "acuchillaron",
        "herido con cuchillo", "herida con cuchillo", "a cuchilladas", "a puñaladas",
        # Víctimas
        "atacado con", "atacada con", "victima de ataque", "victimas de ataque",
        "victima mortal", "victimas mortales", "víctima fatal", "víctimas fatales",
        # English
        "murdered", "murder of", "murders", "homicide", "homicides",
        "killed in attack", "killed by", "fatally shot", "shot dead", "shot to death",
        "stabbed to death", "stabbed", "beaten to death", "beaten", "lynched",
        "assassination", "assassinated", "assassinations",
        "attack on civilian", "attack against", "attacked by",
        "violent attack", "violent attacks", "victim of attack", "victims of attack",
        "gunned down", "gunshot wounds", "bullet wounds",
        # Electoral violence (Peru specific)
        "ataque a candidato", "ataque a candidata", "ataques a candidatos",
        "agresion a politico", "agresion a politica", "agresiones a politicos",
        "atentado contra candidato", "atentado contra candidata",
        "amenaza de muerte", "amenazas de muerte", "amenazado de muerte", "amenazada de muerte",
        "intimidacion electoral", "intimidacion politica",
        "violencia electoral", "violencia politica",
        "ataque a local partidario", "ataques a locales partidarios",
        "attack on candidate", "political violence", "electoral violence",
        "death threat", "death threats",
    ],
    
    "abduction_disappearance": [
        # Spanish - Secuestro (todas las conjugaciones y géneros)
        "secuestro", "secuestros", "secuestrado", "secuestrada", "secuestrados", "secuestradas",
        "secuestran a", "secuestraron a", "lo secuestraron", "la secuestraron",
        "fue secuestrado", "fue secuestrada", "fueron secuestrados",
        # Desaparición
        "desaparicion forzada", "desapariciones forzadas",
        "desaparecido", "desaparecida", "desaparecidos", "desaparecidas",
        "reportado desaparecido", "reportada desaparecida",
        "reportado como desaparecido", "reportada como desaparecida",
        # Rapto/Plagio
        "rapto", "raptos", "rapto de", "raptado", "raptada",
        "plagiado", "plagiada", "plagiados", "plagiadas", "plagio",
        # Retención
        "retenido ilegalmente", "retenida ilegalmente", "retenidos ilegalmente",
        "privacion ilegal de libertad", "privado de libertad", "privada de libertad",
        # Coloquial
        "levantado por", "levantada por", "levantaron a", "se lo llevaron", "se la llevaron",
        # English
        "kidnapped", "kidnapping", "kidnappings", "abducted", "abduction", "abductions",
        "forcibly disappeared", "forced disappearance",
        "missing person", "missing persons", "reported missing",
        "taken hostage", "held captive", "held hostage",
        "hostage", "hostages",
    ],
    
    "sexual_violence": [
        # Spanish (todas las conjugaciones y géneros)
        "violacion", "violacion sexual", "violaciones", "violaciones sexuales",
        "violada", "violado", "violaron a", "fue violada", "fue violado",
        "abuso sexual", "abusos sexuales", "abusado sexualmente", "abusada sexualmente",
        "acoso sexual", "acosado sexualmente", "acosada sexualmente",
        "violencia sexual", "agresion sexual", "agresiones sexuales",
        "ataque sexual", "ataques sexuales", "asalto sexual",
        "agredido sexualmente", "agredida sexualmente",
        "tocamientos indebidos", "tocamientos",
        # English
        "sexual assault", "sexual assaults", "sexual violence",
        "sexual abuse", "sexually abused", "sexually assaulted",
        "rape", "raped", "rape victim", "rape victims",
        "sexual attack", "sexual attacks",
    ],
    
    "peaceful_protest": [
        # Spanish
        "marcha pacifica", "marchas pacificas", "manifestacion pacifica", "manifestaciones pacificas",
        "protesta pacifica", "protestas pacificas",
        "planton pacifico", "plantones pacificos", "planton", "plantones",
        "concentracion pacifica", "concentraciones pacificas", "concentracion",
        "vigilia", "vigilias", "caminata", "caminatas",
        "movilizacion pacifica", "movilizaciones pacificas", "movilizacion",
        "marcha de protesta", "marchas de protesta",
        "protesta ciudadana", "protestas ciudadanas",
        "manifestantes marchan", "manifestantes marcharon",
        "miles marchan", "miles marcharon", "cientos marchan",
        "protestan en", "protestan por", "protestaron por",
        "marchan en", "marchan por", "marcharon por",
        "se manifiestan", "se manifestaron",
        # English
        "peaceful protest", "peaceful protests", "peaceful demonstration", "peaceful demonstrations",
        "peaceful march", "peaceful marches", "peaceful rally", "peaceful rallies",
        "sit-in", "sit-ins", "vigil", "vigils",
        "protesters march", "protesters marched", "protesters gather",
        "demonstrators march", "demonstrators gather",
        # Electoral (Peru)
        "marcha electoral", "marchas electorales",
        "protesta por resultados", "protestas por resultados",
        "reclamo electoral", "reclamos electorales",
        "manifestacion politica", "manifestaciones politicas",
        "mitin politico", "mitines politicos",
        "concentracion politica", "concentraciones politicas",
        "election protest", "electoral demonstration",
    ],
    
    "violent_demonstration": [
        # Spanish
        "disturbios", "disturbio", "vandalismo", "actos vandalicos",
        "destruccion de propiedad", "destruyen propiedad",
        "quema de llantas", "queman llantas", "quemaron llantas",
        "bloqueo violento", "bloqueos violentos",
        "enfrentamiento con policia", "enfrentamientos con policia",
        "se enfrentan a policia", "se enfrentaron a policia",
        "manifestantes violentos", "manifestante violento",
        "protesta violenta", "protestas violentas",
        "desmanes", "desman", "destrozos", "destrozo",
        "atacan vehiculos", "atacaron vehiculos", "atacan a vehiculos",
        "rompen ventanas", "rompieron ventanas", "rompen vidrios",
        "apedrean", "apedrearon", "lanzan piedras", "lanzaron piedras",
        "incendian", "incendiaron", "prenden fuego",
        # English
        "rioting", "riot", "riots", "rioters",
        "violent protest", "violent protests", "violent demonstration", "violent demonstrations",
        "vandalism", "vandals", "property destruction",
        "clashes with police", "clash with police", "clashed with police",
        "violent clashes", "violent clash",
        "protesters clash", "protesters clashed",
        # Electoral (Peru)
        "protesta electoral violenta", "protestas electorales violentas",
        "disturbios electorales", "disturbio electoral",
        "enfrentamiento entre partidarios", "enfrentamientos entre partidarios",
        "violencia en mitin", "violencia en mitines",
        "electoral riot", "election violence",
    ],
    
    "mob_violence": [
        # Spanish
        "turba", "turbas", "turba enfurecida", "turbas enfurecidas",
        "turba ataca", "turba atacó", "turbas atacan",
        "linchamiento", "linchamientos", "linchamiento popular",
        "linchado", "linchada", "linchados", "linchadas",
        "intentan linchar", "intentaron linchar", "casi linchan",
        "violencia de masas", "violencia de multitud",
        "ajusticiamiento popular", "ajusticiamientos populares",
        "quema de vehiculo", "queman vehiculo", "quemaron vehiculo",
        "saqueo masivo", "saqueos masivos",
        "muchedumbre ataca", "muchedumbre atacó",
        "turbas violentas", "turba violenta",
        "justicia popular", "hacen justicia por mano propia",
        # English
        "mob", "mobs", "mob attack", "mob attacks", "mob violence",
        "lynching", "lynched", "lynch mob",
        "vigilante violence", "vigilante justice", "vigilantes",
        "crowd violence", "crowd attacks",
        "mass looting", "looting",
    ],
    
    "armed_clash": [
        # Spanish
        "enfrentamiento armado", "enfrentamientos armados",
        "tiroteo", "tiroteos", "balacera", "balaceras",
        "intercambio de disparos", "intercambio de fuego",
        "combate armado", "combates armados",
        "batalla", "batallas", "enfrentamiento con", "enfrentamientos con",
        "fuego cruzado", "cruce de disparos",
        "choque armado", "choques armados",
        "refriega", "refriegas",
        "se enfrentan a tiros", "se enfrentaron a tiros",
        "atacan con armas", "atacaron con armas",
        # English
        "armed clash", "armed clashes", "firefight", "firefights",
        "shootout", "shootouts", "gunfight", "gunfights",
        "armed confrontation", "armed confrontations",
        "exchange of fire", "gun battle", "gun battles",
    ],
    
    "arrest": [
        # Spanish
        "detencion", "detenciones", "detencion de", "detenido", "detenida", "detenidos", "detenidas",
        "detienen a", "detuvieron a", "fue detenido", "fue detenida", "fueron detenidos",
        "arrestado", "arrestada", "arrestados", "arrestadas",
        "arrestan a", "arrestaron a", "fue arrestado", "fue arrestada",
        "captura", "capturas", "captura de", "capturado", "capturada", "capturados",
        "capturan a", "capturaron a", "fue capturado", "fue capturada",
        "prision preventiva", "prision", "enviado a prision", "enviada a prision",
        "intervenido por policia", "intervenida por policia",
        "operativo de captura", "operativo policial",
        "cae presunto", "caen presuntos", "cayó", "cayeron",
        "aprehendido", "aprehendida", "aprehendidos",
        # English
        "arrested", "arrest", "arrests", "arrested for",
        "detention", "detentions", "detained", "detained by",
        "captured", "capture", "captured by police",
        "taken into custody", "placed under arrest",
        "apprehended", "apprehension",
    ],
}


def main():
    with open("src/incidents/acled_rules.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Backup
    with open("src/incidents/acled_rules.py.bak", "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Backup creado: acled_rules.py.bak")
    
    changes_made = 0
    
    for sub_type, new_keywords in EXPANDED_KEYWORDS.items():
        # Buscar el bloque de keywords para este sub_type
        # Formato: "sub_type": [...]
        import re
        
        pattern = rf'"{sub_type}":\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Formatear nuevas keywords
            kw_formatted = ',\n        '.join(f'"{kw}"' for kw in new_keywords)
            new_block = f'"{sub_type}": [\n        {kw_formatted},\n    ]'
            
            # Reemplazar
            old_block = match.group(0)
            content = content.replace(old_block, new_block)
            changes_made += 1
            print(f"✓ Actualizado: {sub_type} ({len(new_keywords)} keywords)")
        else:
            print(f"✗ No encontrado: {sub_type}")
    
    # Guardar
    with open("src/incidents/acled_rules.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\n✅ {changes_made} categorías actualizadas")
    
    # Verificar
    print("\n=== Verificación ===")
    import sys
    sys.path.insert(0, '.')
    
    import importlib
    import src.incidents.acled_rules as rules
    importlib.reload(rules)
    
    test_cases = [
        ("Asesinan a candidato en Lima", "El político fue baleado"),
        ("Secuestran a empresario", "Piden rescate millonario"),
        ("Miles marchan pacíficamente", "Protesta sin incidentes"),
        ("Turba lincha a presunto ladrón", "Vecinos lo golpearon"),
        ("Detienen a alcalde por corrupción", "Prisión preventiva"),
    ]
    
    for title, body in test_cases:
        r = rules.classify_incident(title, body)
        status = "✓" if r.confidence > 0.3 else "⚠"
        print(f"{status} '{title[:35]}...' -> {r.event_type} ({r.confidence:.1f})")
        if r.matched_keywords:
            print(f"   Keywords: {r.matched_keywords[:3]}")


if __name__ == "__main__":
    main()
