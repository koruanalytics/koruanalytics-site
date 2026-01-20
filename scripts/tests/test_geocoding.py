"""
scripts/tests/test_geocoding.py

Script de validación para el servicio de geocoding.
Testea los 5 niveles de precisión geográfica.

Usage:
    python -m scripts.tests.test_geocoding

Last updated: 2026-01-11
"""
from __future__ import annotations

import os
from loguru import logger
from src.enrichment.geocoding_service import get_geocoding_service


def test_geocoding_service():
    """Test all geocoding strategies."""
    
    logger.info("=" * 60)
    logger.info("TESTING GEOCODING SERVICE")
    logger.info("=" * 60)
    
    geocoder = get_geocoding_service()
    stats = geocoder.get_stats()
    logger.info(f"\nGazetteer stats: {stats}")
    
    # =========================================================================
    # TEST 1: Nivel 'distrito' - Exact match
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Nivel 'distrito' (exact match)")
    logger.info("=" * 60)
    
    test_cases_distrito = [
        ("LIMA", "LIMA", "LIMA", None, None, None),
        ("AREQUIPA", "AREQUIPA", "AREQUIPA", None, None, None),
        ("CUSCO", "CUSCO", "CUSCO", None, None, None),
        ("LA LIBERTAD", "TRUJILLO", "TRUJILLO", None, None, None),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_distrito:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel == 'distrito' else "✗"
        logger.info(f"{status} {dist}, {prov}, {depto} → "
                   f"nivel={nivel}, coords=({lat:.4f}, {lon:.4f})" if lat else "Sin coords")
    
    # =========================================================================
    # TEST 2: Nivel 'provincia' - Capital de provincia
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Nivel 'provincia' (provincia capital)")
    logger.info("=" * 60)
    
    test_cases_provincia = [
        ("LIMA", "LIMA", None, None, None, None),  # Should match provincia capital
        ("AREQUIPA", "AREQUIPA", None, None, None, None),
        ("LA LIBERTAD", "TRUJILLO", None, None, None, None),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_provincia:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel == 'provincia' else "✗"
        logger.info(f"{status} {prov}, {depto} → "
                   f"nivel={nivel}, coords=({lat:.4f}, {lon:.4f})" if lat else "Sin coords")
    
    # =========================================================================
    # TEST 3: Nivel 'departamento' - Capital de departamento
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Nivel 'departamento' (departamento capital)")
    logger.info("=" * 60)
    
    test_cases_departamento = [
        ("LIMA", None, None, None, None, None),
        ("AREQUIPA", None, None, None, None, None),
        ("CUSCO", None, None, None, None, None),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_departamento:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel == 'departamento' else "✗"
        logger.info(f"{status} {depto} → "
                   f"nivel={nivel}, coords=({lat:.4f}, {lon:.4f})" if lat else "Sin coords")
    
    # =========================================================================
    # TEST 4: Nivel 'especifico' - LLM coords with ADM4
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Nivel 'especifico' (ADM4 with LLM coords)")
    logger.info("=" * 60)
    
    test_cases_especifico = [
        ("LIMA", "LIMA", "LIMA", "San Juan de Lurigancho", -12.0, -77.0),
        ("AREQUIPA", "AREQUIPA", "AREQUIPA", "Cercado", -16.4, -71.5),
        ("LA LIBERTAD", "TRUJILLO", "TRUJILLO", "Centro Histórico", -8.1, -79.0),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_especifico:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel == 'especifico' and adm4 == ubic else "✗"
        logger.info(f"{status} {ubic}, {dist}, {prov}, {depto} → "
                   f"nivel={nivel}, adm4={adm4}, coords=({lat:.4f}, {lon:.4f})")
    
    # =========================================================================
    # TEST 5: Nivel 'estimado' - LLM coords fallback
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Nivel 'estimado' (LLM coords, no gazetteer match)")
    logger.info("=" * 60)
    
    test_cases_estimado = [
        ("LIMA", "LIMA", "Distrito Inexistente", None, -12.0, -77.0),
        ("AREQUIPA", "Provincia Inexistente", "Distrito X", None, -16.4, -71.5),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_estimado:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel == 'estimado' else "✗"
        logger.info(f"{status} {dist}, {prov}, {depto} → "
                   f"nivel={nivel}, coords=({lat:.4f}, {lon:.4f})" if lat else "Sin coords")
    
    # =========================================================================
    # TEST 6: Sin coordenadas
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Sin coordenadas (no match, no LLM)")
    logger.info("=" * 60)
    
    test_cases_sin_coords = [
        ("DEPARTAMENTO INEXISTENTE", "PROV X", "DIST Y", None, None, None),
        (None, None, None, None, None, None),
    ]
    
    for depto, prov, dist, ubic, llm_lat, llm_lon in test_cases_sin_coords:
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            depto, prov, dist, ubic, llm_lat, llm_lon
        )
        status = "✓" if nivel is None and lat is None else "✗"
        logger.info(f"{status} {dist or 'NULL'}, {prov or 'NULL'}, {depto or 'NULL'} → "
                   f"nivel={nivel}, coords={lat}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("TESTING COMPLETED")
    logger.info("=" * 60)
    logger.success("✓ All geocoding strategies tested")
    logger.info("\nNiveles implementados:")
    logger.info("  1. 'especifico' - LLM coords + ubicacion_especifica única (ADM4)")
    logger.info("  2. 'distrito' - Match exacto en gazetteer (ADM3)")
    logger.info("  3. 'provincia' - Capital de provincia (ADM2)")
    logger.info("  4. 'departamento' - Capital de departamento (ADM1)")
    logger.info("  5. 'estimado' - LLM coords sin match en gazetteer")
    logger.info("  6. NULL - Sin coordenadas disponibles")


if __name__ == "__main__":
    test_geocoding_service()
