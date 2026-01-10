"""
scripts/tests/test_llm_pipeline_validation.py

Tests for LLM pipeline validation logic.
Validates that:
1. QualityValidator correctly identifies resumen/internacional articles
2. LLM response validation normalizes data correctly
3. Gold filters prevent no_relevante from entering

Usage:
    python -m scripts.tests.test_llm_pipeline_validation

Last updated: 2026-01-09
"""
from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_quality_validator_resumen():
    """Test detection of resumen/estadistica articles."""
    from src.enrichment.llm_enrichment_pipeline import QualityValidator
    
    print("\n=== Test: Deteccion de Resumenes ===")
    
    test_cases = [
        ("Estadisticas de feminicidios en 2025", "", 50, 0, True),
        ("En 2024 hubo 150 asesinatos en Lima", "", 150, 0, True),
        ("Los 10 casos mas impactantes del ano", "", 10, 0, True),
        ("Conmemoracion por victimas de Ayacucho", "", 0, 0, True),
        ("Asesinan a comerciante en Chiclayo", "", 1, 0, False),
        ("Accidente deja 3 heridos en Arequipa", "", 0, 3, False),
    ]
    
    passed = 0
    for titulo, cuerpo, muertos, heridos, expected in test_cases:
        result = QualityValidator.es_probable_resumen(titulo, cuerpo, muertos, heridos)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"  [{status}] '{titulo[:40]}...' -> {result} (expected {expected})")
    
    print(f"\n  Resultado: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_quality_validator_internacional():
    """Test detection of international articles."""
    from src.enrichment.llm_enrichment_pipeline import QualityValidator
    
    print("\n=== Test: Deteccion de Internacionales ===")
    
    test_cases = [
        ("Maduro anuncia nuevas medidas en Venezuela", "", None, True),
        ("Tiroteo en Estados Unidos deja 5 muertos", "", None, True),
        ("Biden visita Colombia", "", None, True),
        ("Asesinan a comerciante en Chiclayo", "", "Lambayeque", False),
        ("Protesta en Lima por alza de precios", "", "Lima", False),
        ("Peruano muere en accidente en Chile", "", None, True),
    ]
    
    passed = 0
    for titulo, cuerpo, depto, expected in test_cases:
        result = QualityValidator.es_probable_internacional(titulo, cuerpo, depto)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"  [{status}] '{titulo[:40]}...' depto={depto} -> {result} (expected {expected})")
    
    print(f"\n  Resultado: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_validar_respuesta_llm():
    """Test LLM response validation and normalization."""
    from src.enrichment.llm_enrichment_pipeline import QualityValidator
    
    print("\n=== Test: Validacion de Respuesta LLM ===")
    
    test_cases = [
        # Test 1: no_relevante debe forzar es_relevante=False
        {
            "input": {"es_relevante": True, "tipo_evento": "no_relevante"},
            "expected_relevante": False,
            "expected_tipo": "no_relevante",
            "desc": "no_relevante fuerza es_relevante=False"
        },
        # Test 2: tipo valido con es_relevante=False debe marcar relevante
        {
            "input": {"es_relevante": False, "tipo_evento": "crimen_violento"},
            "expected_relevante": True,
            "expected_tipo": "crimen_violento",
            "desc": "tipo valido con es_relevante=False -> True"
        },
        # Test 3: NULL es_relevante debe ser False
        {
            "input": {"es_relevante": None, "tipo_evento": "no_relevante"},
            "expected_relevante": False,
            "expected_tipo": "no_relevante",
            "desc": "NULL es_relevante -> False"
        },
        # Test 4: tipo invalido debe ser no_relevante
        {
            "input": {"es_relevante": True, "tipo_evento": "categoria_inventada"},
            "expected_relevante": False,
            "expected_tipo": "no_relevante",
            "desc": "tipo invalido -> no_relevante"
        },
        # Test 5: string 'true' debe convertirse a boolean
        {
            "input": {"es_relevante": "true", "tipo_evento": "protesta"},
            "expected_relevante": True,
            "expected_tipo": "protesta",
            "desc": "string 'true' -> boolean True"
        },
    ]
    
    passed = 0
    for case in test_cases:
        result = QualityValidator.validar_respuesta_llm(case["input"].copy())
        
        relevante_ok = result["es_relevante"] == case["expected_relevante"]
        tipo_ok = result["tipo_evento"] == case["expected_tipo"]
        
        if relevante_ok and tipo_ok:
            passed += 1
            print(f"  [PASS] {case['desc']}")
        else:
            print(f"  [FAIL] {case['desc']}")
            print(f"         Got: es_relevante={result['es_relevante']}, tipo={result['tipo_evento']}")
            print(f"         Expected: es_relevante={case['expected_relevante']}, tipo={case['expected_tipo']}")
    
    print(f"\n  Resultado: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_gold_filters_sql():
    """Test that gold filter SQL logic is correct."""
    print("\n=== Test: Filtros Gold SQL ===")
    
    # Simulated silver records
    test_records = [
        {"id": 1, "es_relevante": True, "es_internacional": False, "es_resumen": False, "tipo": "crimen_violento"},
        {"id": 2, "es_relevante": False, "es_internacional": False, "es_resumen": False, "tipo": "crimen_violento"},
        {"id": 3, "es_relevante": True, "es_internacional": True, "es_resumen": False, "tipo": "crimen_violento"},
        {"id": 4, "es_relevante": True, "es_internacional": False, "es_resumen": True, "tipo": "crimen_violento"},
        {"id": 5, "es_relevante": True, "es_internacional": False, "es_resumen": False, "tipo": "no_relevante"},
        {"id": 6, "es_relevante": None, "es_internacional": False, "es_resumen": False, "tipo": "protesta"},
    ]
    
    # Apply filter logic (same as in build_gold_incidents)
    def passes_gold_filter(r):
        es_rel = r["es_relevante"] if r["es_relevante"] is not None else False
        es_intl = r["es_internacional"] if r["es_internacional"] is not None else False
        es_res = r["es_resumen"] if r["es_resumen"] is not None else False
        tipo = r["tipo"] if r["tipo"] else "no_relevante"
        
        return (es_rel == True and 
                es_intl == False and 
                es_res == False and 
                tipo != "no_relevante")
    
    expected_pass = [1]  # Only record 1 should pass
    actual_pass = [r["id"] for r in test_records if passes_gold_filter(r)]
    
    print(f"  Records that pass filter: {actual_pass}")
    print(f"  Expected: {expected_pass}")
    
    if actual_pass == expected_pass:
        print("  [PASS] Gold filters work correctly")
        return True
    else:
        print("  [FAIL] Gold filters have issues")
        return False


def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("LLM PIPELINE VALIDATION TESTS")
    print("=" * 60)
    
    results = {
        "resumen_detection": test_quality_validator_resumen(),
        "internacional_detection": test_quality_validator_internacional(),
        "llm_response_validation": test_validar_respuesta_llm(),
        "gold_filters": test_gold_filters_sql(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  [{status}] {test_name}")
    
    print("\n" + ("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"))
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
