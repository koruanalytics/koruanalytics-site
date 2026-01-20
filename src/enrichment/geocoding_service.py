"""
src/enrichment/geocoding_service.py

Geocoding service using Peru gazetteer with Azure Maps and LLM fallback.

Geocoding strategy (priority order):
1. 'especifico': LLM provided lat/lon with specific location (ADM4 level)
2. 'azure_maps': Azure Maps API for specific addresses (ADM4) - MORE PRECISE
3. 'distrito': Exact match in gazetteer (distrito + provincia + departamento)
4. 'provincia': Match to province capital (distrito name = provincia name)
5. 'departamento': Match to department capital (distrito name = departamento name)
6. 'estimado': LLM lat/lon as fallback (no gazetteer match)
7. NULL: No coordinates available

Last updated: 2026-01-19 (M1b v2 - Azure Maps prioritized for ADM4 locations)
"""
from __future__ import annotations

import os
from typing import Optional, Tuple
import pandas as pd
from loguru import logger

# Azure Maps integration (M1b)
try:
    from src.enrichment.azure_maps_geocoder import geocode_address_azure
    AZURE_MAPS_AVAILABLE = True
except ImportError:
    AZURE_MAPS_AVAILABLE = False
    logger.warning("Azure Maps geocoder not available")


class GeocodingService:
    """
    Service for geocoding incidents using Peru gazetteer with LLM fallback.
    
    Prioritizes specific locations (ADM4) from LLM when available, then falls
    back to hierarchical gazetteer matching (distrito → provincia → departamento).
    """
    
    def __init__(self, gazetteer_path: str = "config/geo/peru_gazetteer_full.csv"):
        """
        Initialize geocoding service with gazetteer data.
        
        Args:
            gazetteer_path: Path to Peru gazetteer CSV file (1,893 places)
        """
        self.gazetteer_path = gazetteer_path
        self.gazetteer: Optional[pd.DataFrame] = None
        self._load_gazetteer()
    
    def _load_gazetteer(self):
        """Load gazetteer into memory with normalized search columns."""
        if not os.path.exists(self.gazetteer_path):
            logger.error(f"Gazetteer not found: {self.gazetteer_path}")
            self.gazetteer = pd.DataFrame()
            return
        
        self.gazetteer = pd.read_csv(self.gazetteer_path, encoding='utf-8')
        logger.info(f"Gazetteer loaded: {len(self.gazetteer)} places")
        
        # Create normalized search columns (lowercase, stripped)
        self.gazetteer['distrito_norm'] = (
            self.gazetteer['adm3_name'].str.lower().str.strip()
        )
        self.gazetteer['provincia_norm'] = (
            self.gazetteer['adm2_name'].str.lower().str.strip()
        )
        self.gazetteer['departamento_norm'] = (
            self.gazetteer['adm1_name'].str.lower().str.strip()
        )
    
    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Normalize text for matching: lowercase, strip whitespace."""
        if not text:
            return ""
        return text.lower().strip()
    
    def geocode_incident(
        self, 
        departamento: Optional[str],
        provincia: Optional[str],
        distrito: Optional[str],
        ubicacion_especifica: Optional[str],
        llm_lat: Optional[float],
        llm_lon: Optional[float]
    ) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
        """
        Geocode an incident using optimized multi-level strategy.
        
        Strategy (M1b v2 - Azure Maps prioritized for ADM4):
        1. If LLM provided lat/lon AND ubicacion_especifica is unique 
           → Use LLM coords, nivel='especifico', adm4=ubicacion_especifica
        2. Try Azure Maps for specific addresses (ADM4) - MORE PRECISE
           → nivel='azure_maps'
        3. Try exact gazetteer match: distrito + provincia + departamento
           → nivel='distrito'
        4. Try provincia capital match: distrito name = provincia name
           → nivel='provincia'
        5. Try departamento capital match: distrito name = departamento name
           → nivel='departamento'
        6. If LLM provided lat/lon (fallback)
           → Use LLM coords, nivel='estimado'
        7. No match
           → Return None
        
        Args:
            departamento: Department name from LLM
            provincia: Province name from LLM
            distrito: District name from LLM
            ubicacion_especifica: Specific location (poblado, barrio, etc.) from LLM
            llm_lat: Latitude from LLM/NewsAPI
            llm_lon: Longitude from LLM/NewsAPI
        
        Returns:
            Tuple of (lat, lon, nivel_geo, adm4_name):
            - lat/lon: Coordinates
            - nivel_geo: 'especifico' | 'azure_maps' | 'distrito' | 'provincia' | 'departamento' | 'estimado' | None
            - adm4_name: Name of ADM4 place if nivel_geo in ('especifico', 'azure_maps'), else None
        """
        if self.gazetteer is None or len(self.gazetteer) == 0:
            # No gazetteer, use LLM fallback if available
            if llm_lat and llm_lon:
                adm4 = ubicacion_especifica if self._is_adm4(
                    ubicacion_especifica, distrito, provincia, departamento
                ) else None
                nivel = 'especifico' if adm4 else 'estimado'
                return (llm_lat, llm_lon, nivel, adm4)
            return (None, None, None, None)
        
        # Normalize inputs
        depto_norm = self.normalize_text(departamento)
        prov_norm = self.normalize_text(provincia)
        dist_norm = self.normalize_text(distrito)
        ubic_norm = self.normalize_text(ubicacion_especifica)
        
        # STRATEGY 1: LLM coords with specific location (ADM4)
        if llm_lat and llm_lon and self._is_adm4(
            ubicacion_especifica, distrito, provincia, departamento
        ):
            logger.debug(f"Geocoded (especifico/LLM): {ubicacion_especifica} → "
                        f"({llm_lat:.4f}, {llm_lon:.4f})")
            return (llm_lat, llm_lon, 'especifico', ubicacion_especifica)
        
        # STRATEGY 2: Azure Maps FIRST if we have a specific ADM4 location
        # This gives more precise coordinates than district centroids
        has_adm4 = self._is_adm4(ubicacion_especifica, distrito, provincia, departamento)
        
        if AZURE_MAPS_AVAILABLE and has_adm4:
            result = geocode_address_azure(ubicacion_especifica, departamento)
            if result:
                lat, lon, nivel = result
                logger.debug(f"Geocoded (azure_maps): {ubicacion_especifica} → "
                           f"({lat:.4f}, {lon:.4f})")
                return (lat, lon, 'azure_maps', ubicacion_especifica)
        
        # STRATEGY 3: Exact match on distrito + provincia + departamento (gazetteer)
        if dist_norm and prov_norm and depto_norm:
            match = self.gazetteer[
                (self.gazetteer['distrito_norm'] == dist_norm) &
                (self.gazetteer['provincia_norm'] == prov_norm) &
                (self.gazetteer['departamento_norm'] == depto_norm)
            ]
            if len(match) > 0:
                row = match.iloc[0]
                logger.debug(f"Geocoded (distrito): {distrito}, {provincia}, {departamento} → "
                           f"({row['lat']:.4f}, {row['lon']:.4f})")
                return (row['lat'], row['lon'], 'distrito', None)
        
        # STRATEGY 4: Provincia capital (distrito name = provincia name)
        if prov_norm and depto_norm:
            match = self.gazetteer[
                (self.gazetteer['distrito_norm'] == prov_norm) &
                (self.gazetteer['provincia_norm'] == prov_norm) &
                (self.gazetteer['departamento_norm'] == depto_norm)
            ]
            if len(match) > 0:
                row = match.iloc[0]
                logger.debug(f"Geocoded (provincia): {provincia}, {departamento} → "
                           f"({row['lat']:.4f}, {row['lon']:.4f})")
                return (row['lat'], row['lon'], 'provincia', None)
        
        # STRATEGY 5: Departamento capital (distrito name = departamento name)
        if depto_norm:
            match = self.gazetteer[
                (self.gazetteer['distrito_norm'] == depto_norm) &
                (self.gazetteer['departamento_norm'] == depto_norm)
            ]
            if len(match) > 0:
                row = match.iloc[0]
                logger.debug(f"Geocoded (departamento): {departamento} → "
                           f"({row['lat']:.4f}, {row['lon']:.4f})")
                return (row['lat'], row['lon'], 'departamento', None)
        
        # STRATEGY 6: LLM coords as fallback (no gazetteer match)
        if llm_lat and llm_lon:
            logger.debug(f"Geocoded (estimado/LLM): Using LLM coordinates → "
                        f"({llm_lat:.4f}, {llm_lon:.4f})")
            return (llm_lat, llm_lon, 'estimado', None)
        
        # No match found
        logger.debug(f"No geocoding match for: {ubicacion_especifica}, {distrito}, "
                    f"{provincia}, {departamento}")
        return (None, None, None, None)
    
    def _is_adm4(
        self,
        ubicacion_especifica: Optional[str],
        distrito: Optional[str],
        provincia: Optional[str],
        departamento: Optional[str]
    ) -> bool:
        """
        Check if ubicacion_especifica represents a sub-district location (ADM4).
        
        Returns True if ubicacion_especifica is populated and different from
        distrito, provincia, and departamento names.
        """
        if not ubicacion_especifica:
            return False
        
        ubic_norm = self.normalize_text(ubicacion_especifica)
        dist_norm = self.normalize_text(distrito)
        prov_norm = self.normalize_text(provincia)
        depto_norm = self.normalize_text(departamento)
        
        # Check if it's different from all ADM levels
        is_different = (
            ubic_norm != dist_norm and 
            ubic_norm != prov_norm and 
            ubic_norm != depto_norm and
            ubic_norm != ""
        )
        
        return is_different
    
    def geocode_batch(
        self,
        incidents: pd.DataFrame,
        depto_col: str = 'departamento',
        prov_col: str = 'provincia',
        dist_col: str = 'distrito',
        ubic_col: str = 'ubicacion_especifica',
        lat_col: str = 'lat',
        lon_col: str = 'lon'
    ) -> pd.DataFrame:
        """
        Geocode a batch of incidents.
        
        Args:
            incidents: DataFrame with location columns
            depto_col: Column name for departamento
            prov_col: Column name for provincia
            dist_col: Column name for distrito
            ubic_col: Column name for ubicacion_especifica
            lat_col: Column name for existing lat (from LLM)
            lon_col: Column name for existing lon (from LLM)
        
        Returns:
            DataFrame with updated columns: lat, lon, nivel_geo, adm4_name
        """
        results = []
        
        for _, row in incidents.iterrows():
            lat, lon, nivel, adm4 = self.geocode_incident(
                row.get(depto_col),
                row.get(prov_col),
                row.get(dist_col),
                row.get(ubic_col),
                row.get(lat_col),
                row.get(lon_col)
            )
            results.append({
                'lat_geocoded': lat,
                'lon_geocoded': lon,
                'nivel_geo': nivel,
                'adm4_name': adm4
            })
        
        result_df = pd.DataFrame(results)
        
        # Merge back, replacing lat/lon if geocoded
        output = incidents.copy()
        output['lat'] = result_df['lat_geocoded'].fillna(output[lat_col])
        output['lon'] = result_df['lon_geocoded'].fillna(output[lon_col])
        output['nivel_geo'] = result_df['nivel_geo']
        output['adm4_name'] = result_df['adm4_name']
        
        return output
    
    def get_stats(self) -> dict:
        """Get statistics about the gazetteer."""
        if self.gazetteer is None or len(self.gazetteer) == 0:
            return {}
        
        return {
            'total_places': len(self.gazetteer),
            'departamentos': self.gazetteer['adm1_name'].nunique(),
            'provincias': self.gazetteer['adm2_name'].nunique(),
            'distritos': len(self.gazetteer),
        }


# Module-level singleton instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get or create the singleton geocoding service instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
