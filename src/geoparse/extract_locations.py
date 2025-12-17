"""
src/geoparse/extract_locations.py - Extract location mentions from text

Extracts mentions of Peruvian places from news text using:
1. Pattern matching for common location phrases
2. Gazetteer lookup for known place names
3. Context clues (prepositions like "en", "de", "desde")

Usage:
    from src.geoparse.extract_locations import LocationExtractor
    
    extractor = LocationExtractor(gazetteer_df)
    locations = extractor.extract("Protesta en Lima deja 5 heridos")
    # Returns: ["Lima"]
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class LocationMention:
    """A location mention found in text."""
    text: str           # Original text found
    normalized: str     # Normalized form
    start: int          # Start position in text
    end: int            # End position in text
    context: str        # Surrounding context
    confidence: float   # Confidence score (0-1)


def normalize_text(s: str) -> str:
    """Normalize text for matching."""
    s = (s or "").strip().lower()
    # Remove accents
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    s = re.sub(r"\s+", " ", s)
    return s


class LocationExtractor:
    """Extract location mentions from text using a gazetteer."""
    
    # Prepositions that often precede location names (Spanish)
    LOCATION_PREPOSITIONS = [
        r'\ben\b', r'\bde\b', r'\bdesde\b', r'\bhacia\b', 
        r'\bhasta\b', r'\bpor\b', r'\bcerca de\b', r'\bregión\b',
        r'\bprovincia\b', r'\bdistrito\b', r'\bdepartamento\b',
        r'\bciudad de\b', r'\blocalidad de\b'
    ]
    
    # Patterns that indicate location context
    LOCATION_PATTERNS = [
        # "en [Location]"
        r'(?:en|de|desde|hacia)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
        # "región/provincia/distrito de [Location]"
        r'(?:región|provincia|distrito|departamento)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',
        # Capitalized words that might be places
        r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})\b',
    ]
    
    # Words to exclude (common Spanish words that are capitalized but not places)
    EXCLUDE_WORDS = {
        'peru', 'perú', 'peruano', 'peruanos', 'peruana', 'peruanas',
        'gobierno', 'estado', 'ministerio', 'congreso', 'presidente',
        'policia', 'policía', 'ejercito', 'ejército', 'fiscal', 'fiscalia',
        'lunes', 'martes', 'miercoles', 'miércoles', 'jueves', 'viernes', 'sabado', 'sábado', 'domingo',
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
        'señor', 'señora', 'doctor', 'doctora',
        'the', 'and', 'for', 'with', 'from',  # English words
        'ecuador', 'colombia', 'brasil', 'brazil', 'chile', 'bolivia', 'argentina',  # Other countries
        'venezuela', 'mexicano', 'mexicana',
    }
    
    def __init__(self, gazetteer_df: pd.DataFrame, min_confidence: float = 0.5):
        """
        Initialize extractor with gazetteer.
        
        Args:
            gazetteer_df: DataFrame with columns like adm1_name, adm2_name, adm3_name
            min_confidence: Minimum confidence to return a mention
        """
        self.min_confidence = min_confidence
        self._build_place_index(gazetteer_df)
    
    def _build_place_index(self, df: pd.DataFrame) -> None:
        """Build index of known place names."""
        self.place_names: set[str] = set()
        self.place_name_to_info: dict[str, dict] = {}
        
        for _, row in df.iterrows():
            # Add different name variants
            names = []
            
            if pd.notna(row.get('adm3_name')):
                names.append(str(row['adm3_name']))
            if pd.notna(row.get('adm2_name')):
                names.append(str(row['adm2_name']))
            if pd.notna(row.get('adm1_name')):
                names.append(str(row['adm1_name']))
            
            for name in names:
                norm = normalize_text(name)
                if len(norm) >= 3 and norm not in self.EXCLUDE_WORDS:
                    self.place_names.add(norm)
                    self.place_name_to_info[norm] = {
                        'original': name,
                        'place_id': row.get('place_id'),
                        'adm1': row.get('adm1_name'),
                        'adm2': row.get('adm2_name'),
                        'adm3': row.get('adm3_name'),
                    }
        
        # Sort by length (longer names first to match "San Juan de Lurigancho" before "San Juan")
        self.place_names_sorted = sorted(self.place_names, key=len, reverse=True)
    
    def extract(self, text: str) -> list[LocationMention]:
        """
        Extract location mentions from text.
        
        Args:
            text: Input text (title, body, etc.)
            
        Returns:
            List of LocationMention objects
        """
        if not text:
            return []
        
        mentions = []
        text_lower = normalize_text(text)
        
        # Method 1: Direct gazetteer lookup (highest confidence)
        for place_name in self.place_names_sorted:
            if len(place_name) < 4:
                continue  # Skip very short names to avoid false positives
                
            # Look for the place name as a whole word
            pattern = r'\b' + re.escape(place_name) + r'\b'
            for match in re.finditer(pattern, text_lower):
                # Check context - is it preceded by a location preposition?
                start = max(0, match.start() - 20)
                context = text_lower[start:match.end() + 20]
                
                confidence = 0.7  # Base confidence for gazetteer match
                
                # Boost confidence if preceded by location preposition
                pre_context = text_lower[max(0, match.start() - 15):match.start()]
                for prep in self.LOCATION_PREPOSITIONS:
                    if re.search(prep, pre_context):
                        confidence = 0.9
                        break
                
                if confidence >= self.min_confidence:
                    mentions.append(LocationMention(
                        text=self.place_name_to_info.get(place_name, {}).get('original', place_name),
                        normalized=place_name,
                        start=match.start(),
                        end=match.end(),
                        context=context,
                        confidence=confidence,
                    ))
        
        # Deduplicate overlapping mentions (keep highest confidence)
        mentions = self._deduplicate_mentions(mentions)
        
        return mentions
    
    def _deduplicate_mentions(self, mentions: list[LocationMention]) -> list[LocationMention]:
        """Remove overlapping mentions, keeping highest confidence."""
        if not mentions:
            return []
        
        # Sort by confidence descending
        mentions = sorted(mentions, key=lambda m: m.confidence, reverse=True)
        
        kept = []
        used_ranges = []
        
        for mention in mentions:
            # Check if this mention overlaps with any kept mention
            overlaps = False
            for start, end in used_ranges:
                if not (mention.end <= start or mention.start >= end):
                    overlaps = True
                    break
            
            if not overlaps:
                kept.append(mention)
                used_ranges.append((mention.start, mention.end))
        
        # Sort by position in text
        return sorted(kept, key=lambda m: m.start)
    
    def extract_as_text(self, text: str, separator: str = "; ") -> Optional[str]:
        """
        Extract locations and return as a single string.
        
        Args:
            text: Input text
            separator: Separator between multiple locations
            
        Returns:
            String of location names or None if none found
        """
        mentions = self.extract(text)
        if not mentions:
            return None
        
        # Return unique location names
        unique_names = []
        seen = set()
        for m in mentions:
            if m.normalized not in seen:
                unique_names.append(m.text)
                seen.add(m.normalized)
        
        return separator.join(unique_names) if unique_names else None


def extract_location_text(text: str, gazetteer_df: pd.DataFrame) -> Optional[str]:
    """
    Convenience function to extract location text.
    
    Args:
        text: Input text (title + body)
        gazetteer_df: Gazetteer DataFrame
        
    Returns:
        Extracted location text or None
    """
    extractor = LocationExtractor(gazetteer_df)
    return extractor.extract_as_text(text)