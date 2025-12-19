#!/usr/bin/env python3
"""
Fix para corregir la función normalize_text en acled_rules.py

El problema: los caracteres de reemplazo tienen mojibake (UTF-8 mal interpretado)
"""

# El texto incorrecto (mojibake)
OLD_CODE = """def normalize_text(text: str) -> str:
    \"\"\"Normalize text for matching.\"\"\"
    text = (text or "").lower()
    # Remove accents for matching
    replacements = {
        'Ã¡': 'a', 'Ã©': 'e', 'Ã­': 'i', 'Ã³': 'o', 'Ãº': 'u',
        'Ã±': 'n', 'Ã¼': 'u'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Normalize whitespace
    text = re.sub(r'\\s+', ' ', text)
    return text.strip()"""

# El texto correcto
NEW_CODE = """def normalize_text(text: str) -> str:
    \"\"\"Normalize text for matching.\"\"\"
    import unicodedata
    text = (text or "").lower()
    # Remove accents using unicodedata (proper way)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Normalize whitespace
    text = re.sub(r'\\s+', ' ', text)
    return text.strip()"""

if __name__ == "__main__":
    # Leer archivo
    with open("src/incidents/acled_rules.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Buscar y reemplazar la función problemática
    # Usamos un enfoque más robusto buscando por patrón
    import re
    
    pattern = r"def normalize_text\(text: str\) -> str:.*?return text\.strip\(\)"
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, NEW_CODE.strip(), content, flags=re.DOTALL)
        
        with open("src/incidents/acled_rules.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print("✓ normalize_text corregido en acled_rules.py")
    else:
        print("✗ No se encontró la función normalize_text")
