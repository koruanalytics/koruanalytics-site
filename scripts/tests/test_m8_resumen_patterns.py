"""
test_m8_resumen_patterns.py

Test script for M8 improvement: es_resumen detection patterns
Verifies new patterns catch summary articles, predictions, and commemorations.

Usage:
    python scripts/tests/test_m8_resumen_patterns.py
"""
import re

# ============================================================================
# COPY OF RESUMEN_PATTERNS AND VALIDATION LOGIC (for standalone testing)
# ============================================================================

UMBRAL_MUERTOS_SOSPECHOSO = 15
UMBRAL_HERIDOS_SOSPECHOSO = 80

RESUMEN_PATTERNS = [
    # Temporales
    r'en (?:el )?20\d{2}',  # "en 2025", "en el 2024"
    r'durante (?:el )?20\d{2}',
    r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) (?:de )?20\d{2}',
    
    # Balances y estadísticas (robustos a tildes)
    r'balance (?:del )?(?:a[ñn]o|mes|semestre)',
    r'estad[íi]sticas? (?:del )?(?:a[ñn]o|anuales?|mensuales?)',
    r'increment[óo]? en \d+',
    r'aument[óo]? en \d+',
    r'se redujo en \d+',
    r'total de \d+ (?:cr[íi]menes|muertos|v[íi]ctimas|casos|asesinatos|feminicidios)',
    r'\d+ (?:muertos|v[íi]ctimas|asesinados|feminicidios) en (?:el )?20\d{2}',
    
    # Conmemoraciones (con y sin tildes)
    r'recordar[áa]n? a (?:las )?v[íi]ctimas',
    r'conmemoraci[óo]n',
    r'aniversario',
    r'homenaje a (?:las )?v[íi]ctimas',
    r'en memoria de',
    
    # Rankings y comparativas (robustos a tildes)
    r'(?:el )?a[ñn]o m[áa]s (?:letal|violento|mortal|sangriento)',
    r'(?:el )?mes m[áa]s (?:letal|violento|mortal)',
    r'\d+ a[ñn]os (?:de|despu[ée]s)',
    r'los \d+ (?:casos|cr[íi]menes|asesinatos) m[áa]s',
    r'ranking de',
    r'lista de',
    
    # Informes
    r'según (?:el )?(?:informe|reporte|estudio)',
    r'de acuerdo (?:al|con el) (?:informe|reporte)',
    r'reveló? que en 20\d{2}',
    
    # Opinión/análisis
    r'análisis(?:\:| de)',
    r'reflexión(?:\:| sobre)',
    r'¿por qué (?:hay|existe|ocurre)',
    r'las causas de',
    
    # M8: Resúmenes semanales/periódicos
    r'resumen (?:semanal|mensual|diario|del d[íi]a)',
    r'lo m[áa]s (?:le[íi]do|visto|destacado|importante)',
    r'recap(?:itulaci[óo]n)?',
    r'noticias (?:de la semana|del mes|del d[íi]a)',
    r'lo que (?:pas[óo]|sucedi[óo]) (?:esta semana|este mes|hoy)',
    
    # M8: Predicciones y tendencias futuras
    r'predicciones? (?:para|del?) 20\d{2}',
    r'tendencias? (?:para|del?) 20\d{2}',
    r'qu[ée] (?:esperar|viene) (?:en|para) 20\d{2}',
    r'perspectivas? (?:para|del?) 20\d{2}',
    r'pron[óo]sticos? (?:para|del?) 20\d{2}',
    
    # M8: Conmemoraciones con formato temporal
    r'se cumplen? \d+ a[ñn]os',
    r'a \d+ a[ñn]os de',
    r'cumpli[óo] \d+ a[ñn]os',
    r'\d+ a[ñn]os (?:del|de la|desde)',
    r'(?:primer|segundo|tercer|\d+[ºª]?) aniversario',
    r'efe?m[ée]rides?',
]


def es_probable_resumen(titulo: str, cuerpo: str, muertos: int, heridos: int) -> bool:
    """Detecta si un artículo es probablemente un resumen estadístico."""
    texto = f"{titulo} {cuerpo or ''}".lower()
    
    # Buscar patrones de resumen
    for pattern in RESUMEN_PATTERNS:
        if re.search(pattern, texto, re.IGNORECASE):
            # Si además tiene muchas víctimas, muy probable resumen
            if muertos and muertos > UMBRAL_MUERTOS_SOSPECHOSO:
                return True
            if heridos and heridos > UMBRAL_HERIDOS_SOSPECHOSO:
                return True
            # Si el patrón está en el título, más probable
            if re.search(pattern, titulo.lower(), re.IGNORECASE):
                return True
    
    # Detectar compilaciones numéricas en título
    if re.search(r'los \d+ ', titulo.lower()):
        return True
    
    return False


# Test cases: (titulo, cuerpo, muertos, heridos, expected_result, description)
TEST_CASES = [
    # M8: Resúmenes semanales/periódicos
    ("Resumen semanal: las noticias más importantes", "", 0, 0, True, "Resumen semanal en título"),
    ("Lo más leído de la semana en seguridad", "", 0, 0, True, "Lo más leído"),
    ("Recap: todo lo que pasó esta semana en Lima", "", 0, 0, True, "Recap"),
    ("Las noticias de la semana en criminalidad", "", 0, 0, True, "Noticias de la semana"),
    ("Lo que pasó esta semana en el Perú", "", 0, 0, True, "Lo que pasó esta semana"),
    ("Noticias del día: resumen de seguridad", "", 0, 0, True, "Noticias del día"),
    
    # M8: Predicciones y tendencias
    ("Predicciones para 2026: la seguridad en Perú", "", 0, 0, True, "Predicciones para año"),
    ("Tendencias para 2026 en criminalidad", "", 0, 0, True, "Tendencias para año"),
    ("Qué esperar en 2026 para la seguridad ciudadana", "", 0, 0, True, "Qué esperar en año"),
    ("Perspectivas para 2026 del crimen organizado", "", 0, 0, True, "Perspectivas para año"),
    ("Pronósticos para 2026: violencia en aumento", "", 0, 0, True, "Pronósticos para año"),
    
    # M8: Conmemoraciones con formato temporal
    ("Se cumplen 5 años del atentado en Tarata", "", 0, 0, True, "Se cumplen X años"),
    ("A 10 años de la masacre de Uchuraccay", "", 0, 0, True, "A X años de"),
    ("El caso cumplió 3 años sin resolver", "", 0, 0, True, "Cumplió X años"),
    ("20 años del inicio del terrorismo", "", 0, 0, True, "X años del/de la"),
    ("Primer aniversario del feminicidio", "", 0, 0, True, "Primer aniversario"),
    ("5º aniversario de la tragedia", "", 0, 0, True, "Nº aniversario"),
    ("Efemérides: 30 años del conflicto armado", "", 0, 0, True, "Efemérides"),
    
    # Casos existentes que deben seguir funcionando
    ("Balance del año 2025 en feminicidios", "", 20, 0, True, "Balance del año (patrón existente)"),
    ("Estadísticas anuales de crímenes", "", 0, 0, True, "Estadísticas anuales (patrón existente)"),
    ("Conmemoración de víctimas del terrorismo", "", 0, 0, True, "Conmemoración (patrón existente)"),
    ("Homenaje a las víctimas de Uchuraccay", "", 0, 0, True, "Homenaje (patrón existente)"),
    
    # Casos que NO deben ser detectados como resumen (incidentes reales)
    ("Asesinan a comerciante en SJL", "", 1, 0, False, "Incidente real - asesinato"),
    ("Balacera deja 2 heridos en Callao", "", 0, 2, False, "Incidente real - balacera"),
    ("Detienen a extorsionador en Chiclayo", "", 0, 0, False, "Incidente real - detención"),
    ("Rescatan a víctima de secuestro", "", 0, 0, False, "Incidente real - rescate"),
    ("Protesta en Arequipa por inseguridad", "", 0, 0, False, "Incidente real - protesta"),
]


def run_tests():
    """Execute all test cases and report results."""
    print("=" * 70)
    print("TEST M8: DETECCIÓN DE ARTÍCULOS DE RESUMEN")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    for titulo, cuerpo, muertos, heridos, expected, description in TEST_CASES:
        result = es_probable_resumen(titulo, cuerpo, muertos, heridos)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        # Show all results, highlight failures
        if result != expected:
            print(f"{status} FAIL: {description}")
            print(f"       Título: {titulo}")
            print(f"       Esperado: {expected}, Obtenido: {result}")
            print()
        else:
            print(f"{status} PASS: {description}")
    
    print()
    print("=" * 70)
    print(f"RESULTADO: {passed}/{len(TEST_CASES)} tests pasaron")
    if failed > 0:
        print(f"           {failed} tests fallaron")
    print("=" * 70)
    
    return failed == 0


def show_patterns():
    """Display all RESUMEN_PATTERNS for reference."""
    print("\n" + "=" * 70)
    print("PATRONES RESUMEN_PATTERNS ACTUALES:")
    print("=" * 70)
    for i, pattern in enumerate(RESUMEN_PATTERNS, 1):
        print(f"  {i:2}. {pattern}")
    print(f"\nTotal: {len(RESUMEN_PATTERNS)} patrones")


if __name__ == "__main__":
    success = run_tests()
    show_patterns()
    
    # Exit with appropriate code
    exit(0 if success else 1)
