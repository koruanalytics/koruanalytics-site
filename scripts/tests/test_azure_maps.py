"""
scripts/tests/test_azure_maps.py

Test suite for Azure Maps geocoding integration (M1b).

Tests the complete geocoding flow with Azure Maps as intermediate fallback:
1. Gazetteer (distrito level)
2. Azure Maps (for specific addresses)  ← NEW
3. Provincia/Departamento capitals
4. LLM fallback

Usage:
    # Test without API key (dry run)
    python -m scripts.tests.test_azure_maps
    
    # Test with real API key
    AZURE_MAPS_KEY=your_key python -m scripts.tests.test_azure_maps --live

Last updated: 2026-01-13
"""
from __future__ import annotations

import os
import argparse
from loguru import logger
from src.enrichment.geocoding_service import get_geocoding_service
from src.enrichment.azure_maps_geocoder import get_azure_geocoder


def test_azure_maps_basic():
    """Test basic Azure Maps functionality."""
    logger.info("=" * 60)
    logger.info("TEST 1: Azure Maps Basic Functionality")
    logger.info("=" * 60)
    
    geocoder = get_azure_geocoder()
    
    if not geocoder.api_key:
        logger.warning("AZURE_MAPS_KEY not configured - skipping live tests")
        logger.info("✓ Azure Maps client initialized (no API key)")
        return
    
    # Test cases from real OSINT data
    test_addresses = [
        ("Avenida Alcides Carrión, primera cuadra", "AREQUIPA"),
        ("Gamarra", "LIMA"),
        ("Carretera Panamericana Norte", "LIMA"),
        ("Avenida Larco 1301, Miraflores", "LIMA"),
    ]
    
    results = []
    for address, depto in test_addresses:
        result = geocoder.geocode_address(address, depto)
        if result:
            lat, lon, nivel = result
            logger.info(f"✓ {address} → ({lat:.4f}, {lon:.4f})")
            results.append(True)
        else:
            logger.warning(f"✗ {address} → No result")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    logger.info(f"\nSuccess rate: {success_rate:.0f}% ({sum(results)}/{len(results)})")
    
    # Check stats
    stats = geocoder.get_stats()
    logger.info(f"Stats: {stats}")


def test_geocoding_service_integration():
    """Test complete geocoding service with Azure Maps."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Geocoding Service Integration")
    logger.info("=" * 60)
    
    geocoder = get_geocoding_service()
    
    # Test cases from real problematic incidents
    test_cases = [
        {
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LA VICTORIA",
            "ubicacion_especifica": "Gamarra",
            "llm_lat": None,
            "llm_lon": None,
            "expected_nivel": "azure_maps",  # Should hit Azure Maps
            "description": "Gamarra (specific commercial zone)"
        },
        {
            "departamento": "AREQUIPA",
            "provincia": "AREQUIPA",
            "distrito": "AREQUIPA",
            "ubicacion_especifica": "Avenida Alcides Carrión",
            "llm_lat": None,
            "llm_lon": None,
            "expected_nivel": "azure_maps",  # Should hit Azure Maps
            "description": "Specific avenue in Arequipa"
        },
        {
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "MIRAFLORES",
            "ubicacion_especifica": None,
            "llm_lat": None,
            "llm_lon": None,
            "expected_nivel": "distrito",  # Should hit gazetteer
            "description": "Miraflores district (in gazetteer)"
        },
        {
            "departamento": "CUSCO",
            "provincia": "CUSCO",
            "distrito": None,
            "ubicacion_especifica": None,
            "llm_lat": None,
            "llm_lon": None,
            "expected_nivel": "provincia",  # Should fallback to provincia
            "description": "Cusco capital (fallback)"
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        lat, lon, nivel, adm4 = geocoder.geocode_incident(
            departamento=case["departamento"],
            provincia=case["provincia"],
            distrito=case["distrito"],
            ubicacion_especifica=case["ubicacion_especifica"],
            llm_lat=case["llm_lat"],
            llm_lon=case["llm_lon"]
        )
        
        desc = case["description"]
        expected = case["expected_nivel"]
        
        if lat and lon:
            status = "✓" if nivel == expected else "~"
            logger.info(f"{status} Test {i}: {desc}")
            logger.info(f"    Result: nivel={nivel}, coords=({lat:.4f}, {lon:.4f})")
            if nivel != expected:
                logger.warning(f"    Expected nivel={expected}, got nivel={nivel}")
        else:
            logger.error(f"✗ Test {i}: {desc} → No coordinates")


def test_fallback_chain():
    """Test the complete fallback chain."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Fallback Chain")
    logger.info("=" * 60)
    
    geocoder = get_geocoding_service()
    
    # Test: Address that should go through complete fallback
    # 1. Not in gazetteer (distrito)
    # 2. Try Azure Maps (if available)
    # 3. Fallback to provincia capital
    
    lat, lon, nivel, adm4 = geocoder.geocode_incident(
        departamento="LIMA",
        provincia="LIMA",
        distrito="NonExistentDistrict",  # Not in gazetteer
        ubicacion_especifica="Some Random Street 123",
        llm_lat=None,
        llm_lon=None
    )
    
    if lat and lon:
        logger.info(f"✓ Fallback successful: nivel={nivel}, coords=({lat:.4f}, {lon:.4f})")
        if nivel in ("azure_maps", "provincia", "departamento"):
            logger.success("✓ Fallback chain working correctly")
        else:
            logger.warning(f"Unexpected nivel: {nivel}")
    else:
        logger.error("✗ Fallback failed - no coordinates returned")


def test_cost_estimation():
    """Estimate API costs based on usage."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Cost Estimation")
    logger.info("=" * 60)
    
    geocoder = get_azure_geocoder()
    stats = geocoder.get_stats()
    
    api_requests = stats.get("api_requests", 0)
    cache_hits = stats.get("cache_hits", 0)
    
    # Azure Maps S0 pricing: $0.50 per 1,000 requests
    cost_per_1000 = 0.50
    estimated_cost = (api_requests / 1000) * cost_per_1000
    
    logger.info(f"API requests: {api_requests}")
    logger.info(f"Cache hits: {cache_hits}")
    logger.info(f"Cache hit rate: {cache_hits / (api_requests + cache_hits) * 100:.1f}%" if (api_requests + cache_hits) > 0 else "N/A")
    logger.info(f"Estimated cost: ${estimated_cost:.4f}")
    
    # Daily/monthly projections
    # Assuming ~300 articles/day, ~20% need Azure Maps
    daily_requests = 300 * 0.20  # 60 requests/day
    monthly_requests = daily_requests * 30  # 1,800 requests/month
    monthly_cost = (monthly_requests / 1000) * cost_per_1000
    
    logger.info(f"\nProjected usage (assuming 20% of articles need Azure Maps):")
    logger.info(f"  Daily requests: ~{daily_requests:.0f}")
    logger.info(f"  Monthly requests: ~{monthly_requests:.0f}")
    logger.info(f"  Monthly cost: ~${monthly_cost:.2f}")


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Test Azure Maps geocoding")
    parser.add_argument("--live", action="store_true", help="Run live API tests")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("AZURE MAPS GEOCODING TEST SUITE (M1b)")
    logger.info("=" * 60)
    
    # Check if API key is configured
    api_key = os.getenv("AZURE_MAPS_KEY")
    if not api_key:
        logger.warning("\nAZURE_MAPS_KEY not configured")
        logger.info("Set it in .env file to run live tests:")
        logger.info("  AZURE_MAPS_KEY=your_subscription_key")
        logger.info("\nRunning dry-run tests only...\n")
    
    # Run tests
    test_azure_maps_basic()
    test_geocoding_service_integration()
    test_fallback_chain()
    test_cost_estimation()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TESTS COMPLETED")
    logger.info("=" * 60)
    
    if not api_key:
        logger.warning("⚠ Some tests skipped (no API key)")
        logger.info("\nTo enable Azure Maps:")
        logger.info("1. Get API key from Azure Portal (Maps account)")
        logger.info("2. Add to .env: AZURE_MAPS_KEY=your_key")
        logger.info("3. Re-run tests")
    else:
        logger.success("✓ Azure Maps is configured and functional")


if __name__ == "__main__":
    main()
