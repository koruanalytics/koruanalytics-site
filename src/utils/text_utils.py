"""
src/utils/text_utils.py
Last updated: 2026-01-16
Description: Text utilities for encoding normalization across the pipeline.

PROBLEM SOLVED:
- NewsAPI.ai may return JSON with Unicode escapes (\u00e1 instead of á)
- LLM responses (Claude/OpenAI) may also include Unicode escapes
- Power BI and Excel expect proper UTF-8 characters, not escapes

USAGE:
    from src.utils.text_utils import normalize_unicode, normalize_dict_unicode
    
    # Single string
    text = normalize_unicode("Jos\\u00e9 Mar\\u00eda")  # → "José María"
    
    # Dictionary with multiple fields
    data = normalize_dict_unicode(api_response, ['title', 'body', 'actores'])
"""
from __future__ import annotations

import codecs
import re
import unicodedata
from typing import Any, Dict, List, Optional, Union


def normalize_unicode(text: Any) -> Any:
    """
    Convert Unicode escape sequences to actual characters.
    
    Handles:
    - \\uXXXX patterns (e.g., \\u00e1 → á)
    - \\xXX patterns (e.g., \\xe1 → á)
    - Already decoded text (passed through unchanged)
    - Non-string values (returned unchanged)
    
    Args:
        text: Input text that may contain Unicode escapes
        
    Returns:
        Text with Unicode escapes converted to real characters,
        or original value if not a string or no escapes found
        
    Examples:
        >>> normalize_unicode("Jos\\u00e9")
        'José'
        >>> normalize_unicode("Mar\\u00eda Ang\\u00e9lica")
        'María Angélica'
        >>> normalize_unicode("Normal text")
        'Normal text'
        >>> normalize_unicode(None)
        None
        >>> normalize_unicode(123)
        123
    """
    if not isinstance(text, str):
        return text
    
    if not text:
        return text
    
    result = text
    
    # Pattern 1: \uXXXX Unicode escapes
    if '\\u' in result:
        try:
            # Try codecs decode first (handles most cases)
            result = codecs.decode(result, 'unicode_escape')
        except (UnicodeDecodeError, ValueError):
            # Fallback: manual regex replacement
            pattern = r'\\u([0-9a-fA-F]{4})'
            result = re.sub(
                pattern,
                lambda m: chr(int(m.group(1), 16)),
                result
            )
    
    # Pattern 2: \xXX hex escapes (less common)
    if '\\x' in result:
        pattern = r'\\x([0-9a-fA-F]{2})'
        result = re.sub(
            pattern,
            lambda m: chr(int(m.group(1), 16)),
            result
        )
    
    # Pattern 3: Escaped backslash + u (\\\\u → already processed)
    # No action needed - codecs.decode handles this
    
    # Normalize to NFC form (canonical composition)
    # This ensures consistent representation of accented characters
    result = unicodedata.normalize('NFC', result)
    
    return result


def normalize_dict_unicode(
    data: Dict[str, Any],
    fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Normalize Unicode escapes in specific dictionary fields.
    
    Args:
        data: Dictionary with potentially escaped strings
        fields: List of field names to normalize. If None, normalizes ALL string fields.
        
    Returns:
        Dictionary with normalized string values
        
    Example:
        >>> data = {'title': 'Polic\\u00eda', 'count': 5}
        >>> normalize_dict_unicode(data, ['title'])
        {'title': 'Policía', 'count': 5}
    """
    if not isinstance(data, dict):
        return data
    
    result = data.copy()
    
    if fields is None:
        # Normalize all string fields
        for key, value in result.items():
            if isinstance(value, str):
                result[key] = normalize_unicode(value)
            elif isinstance(value, list):
                result[key] = normalize_list_unicode(value)
    else:
        # Normalize only specified fields
        for field in fields:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    result[field] = normalize_unicode(value)
                elif isinstance(value, list):
                    result[field] = normalize_list_unicode(value)
    
    return result


def normalize_list_unicode(items: List[Any]) -> List[Any]:
    """
    Normalize Unicode escapes in list items.
    
    Args:
        items: List that may contain strings with Unicode escapes
        
    Returns:
        List with normalized string values
    """
    if not isinstance(items, list):
        return items
    
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(normalize_unicode(item))
        elif isinstance(item, dict):
            result.append(normalize_dict_unicode(item))
        elif isinstance(item, list):
            result.append(normalize_list_unicode(item))
        else:
            result.append(item)
    
    return result


# =============================================================================
# FIELDS TO NORMALIZE BY LAYER
# =============================================================================

# Bronze layer - text fields from NewsAPI.ai
BRONZE_TEXT_FIELDS = [
    'title',
    'body',
    'source_title',
    'location_label',
]

# Silver layer - additional fields from LLM enrichment
SILVER_TEXT_FIELDS = [
    'title',
    'resumen_es',
    'resumen_en',
    'departamento',
    'provincia',
    'distrito',
    'ubicacion_especifica',
    'subtipo',
    'source_name',
]

# Fields that are JSON arrays (need special handling)
SILVER_JSON_ARRAY_FIELDS = [
    'actores',
    'organizaciones',
]

# Gold layer - display fields
GOLD_TEXT_FIELDS = [
    'titulo',
    'resumen',
    'actores',
    'organizaciones',
    'departamento',
    'provincia',
    'distrito',
    'adm4_name',
    'ubicacion_display',
    'source_name',
]


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def has_unicode_escapes(text: str) -> bool:
    """
    Check if text contains Unicode escape sequences.
    
    Args:
        text: String to check
        
    Returns:
        True if escapes found, False otherwise
    """
    if not isinstance(text, str):
        return False
    return bool(re.search(r'\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}', text))


def validate_no_escapes(text: str, field_name: str = "field") -> None:
    """
    Raise an error if text contains Unicode escapes.
    Useful for debugging/validation.
    
    Args:
        text: String to validate
        field_name: Field name for error message
        
    Raises:
        ValueError: If escapes are found
    """
    if has_unicode_escapes(text):
        raise ValueError(
            f"Unicode escapes found in {field_name}: {text[:100]}"
        )


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("Jos\\u00e9 Mar\\u00eda", "José María"),
        ("Polic\\u00eda Nacional", "Policía Nacional"),
        ("Normal text", "Normal text"),
        ("\\u00c1ngel P\\u00e9rez", "Ángel Pérez"),
        ("Ni\\u00f1o de 5 a\\u00f1os", "Niño de 5 años"),
        ("Per\\u00fa", "Perú"),
    ]
    
    print("=== TEXT NORMALIZATION TEST ===\n")
    all_passed = True
    
    for input_text, expected in test_cases:
        result = normalize_unicode(input_text)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} Input:    {input_text}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()
    
    # Test dict normalization
    test_dict = {
        'title': 'Polic\\u00eda captura a delincuente',
        'actores': ['Jos\\u00e9 P\\u00e9rez', 'Mar\\u00eda L\\u00f3pez'],
        'count': 5
    }
    
    print("=== DICT NORMALIZATION TEST ===\n")
    print(f"Input: {test_dict}")
    result = normalize_dict_unicode(test_dict)
    print(f"Output: {result}")
    
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
