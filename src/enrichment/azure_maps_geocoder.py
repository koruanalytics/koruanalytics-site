"""
src/enrichment/azure_maps_geocoder.py

Azure Maps Geocoding client for specific address resolution.
Used as fallback when local gazetteer cannot resolve precise locations.

Features:
- Rate limiting (50 req/sec max for S0 tier)
- Result caching to minimize API costs
- Retry logic with exponential backoff
- Peru-specific search optimization

Cost estimate: $0.50 per 1,000 requests (S0 tier)
Expected usage: ~50-100 requests/day = ~$1.50/month

Last updated: 2026-01-13
"""
from __future__ import annotations

import os
import time
from typing import Optional, Tuple, Dict
from functools import lru_cache
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY")
AZURE_MAPS_ENDPOINT = "https://atlas.microsoft.com/search/address/json"
AZURE_MAPS_TIMEOUT = 5  # seconds
AZURE_MAPS_MAX_RETRIES = 2

# Rate limiting: Azure Maps S0 allows 50 req/sec
RATE_LIMIT_DELAY = 0.02  # 20ms between requests = 50 req/sec


# =============================================================================
# AZURE MAPS CLIENT
# =============================================================================

class AzureMapsGeocoder:
    """Client for Azure Maps Search API with caching and rate limiting."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Azure Maps geocoder.
        
        Args:
            api_key: Azure Maps subscription key (defaults to env var)
        """
        self.api_key = api_key or AZURE_MAPS_KEY
        self.last_request_time = 0
        self.request_count = 0
        self.cache_hits = 0
        
        if not self.api_key:
            logger.warning("Azure Maps API key not configured (AZURE_MAPS_KEY env var)")
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()
    
    @lru_cache(maxsize=500)
    def geocode_address(
        self,
        address: str,
        departamento: Optional[str] = None,
        pais: str = "Peru"
    ) -> Optional[Tuple[float, float, str]]:
        """
        Geocode a specific address using Azure Maps.
        
        Results are cached in memory to reduce API calls for repeated addresses.
        
        Args:
            address: Specific location (e.g., "Avenida Alcides Carrión, primera cuadra")
            departamento: Department for regional context (optional)
            pais: Country (default: "Peru")
        
        Returns:
            (lat, lon, 'azure_maps') if successful, None otherwise
        
        Examples:
            >>> geocoder = AzureMapsGeocoder()
            >>> result = geocoder.geocode_address("Avenida Larco 1301", "LIMA")
            >>> print(result)  # (-12.1234, -77.0345, 'azure_maps')
        """
        if not self.api_key:
            logger.debug("Azure Maps not configured, skipping")
            return None
        
        # Check cache first (via lru_cache decorator)
        # If this is a cache hit, method returns immediately
        
        # Rate limiting
        self._rate_limit()
        
        # Build query with geographic context
        query_parts = [address]
        if departamento:
            query_parts.append(departamento)
        query_parts.append(pais)
        query = ", ".join(query_parts)
        
        params = {
            "api-version": "1.0",
            "subscription-key": self.api_key,
            "query": query,
            "countrySet": "PE",  # Restrict to Peru
            "limit": 1,
            "language": "es-PE"
        }
        
        # Retry logic
        for attempt in range(AZURE_MAPS_MAX_RETRIES + 1):
            try:
                response = requests.get(
                    AZURE_MAPS_ENDPOINT,
                    params=params,
                    timeout=AZURE_MAPS_TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                self.request_count += 1
                
                if data.get("results"):
                    result = data["results"][0]
                    position = result.get("position", {})
                    lat = position.get("lat")
                    lon = position.get("lon")
                    
                    if lat and lon:
                        confidence = result.get("score", 0)
                        logger.debug(
                            f"Azure Maps geocoded: '{address}' → "
                            f"({lat:.4f}, {lon:.4f}), confidence={confidence:.2f}"
                        )
                        return (lat, lon, "azure_maps")
                
                logger.debug(f"Azure Maps: no result for '{address}'")
                return None
            
            except requests.exceptions.Timeout:
                logger.warning(f"Azure Maps timeout for '{address}' (attempt {attempt + 1})")
                if attempt < AZURE_MAPS_MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                return None
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit exceeded
                    logger.warning(f"Azure Maps rate limit hit, waiting...")
                    time.sleep(1)
                    if attempt < AZURE_MAPS_MAX_RETRIES:
                        continue
                logger.error(f"Azure Maps HTTP error for '{address}': {e}")
                return None
            
            except Exception as e:
                logger.error(f"Azure Maps error for '{address}': {e}")
                return None
        
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get usage statistics."""
        cache_info = self.geocode_address.cache_info()
        return {
            "api_requests": self.request_count,
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize
        }
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        self.geocode_address.cache_clear()
        logger.info("Azure Maps cache cleared")


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_azure_geocoder: Optional[AzureMapsGeocoder] = None


def get_azure_geocoder() -> AzureMapsGeocoder:
    """Get or create singleton Azure Maps geocoder instance."""
    global _azure_geocoder
    if _azure_geocoder is None:
        _azure_geocoder = AzureMapsGeocoder()
    return _azure_geocoder


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def geocode_address_azure(
    address: str,
    departamento: Optional[str] = None
) -> Optional[Tuple[float, float, str]]:
    """
    Convenience function for geocoding with Azure Maps.
    
    Uses singleton instance to maintain cache across calls.
    
    Args:
        address: Specific location to geocode
        departamento: Department for context
    
    Returns:
        (lat, lon, 'azure_maps') or None
    """
    geocoder = get_azure_geocoder()
    return geocoder.geocode_address(address, departamento)
