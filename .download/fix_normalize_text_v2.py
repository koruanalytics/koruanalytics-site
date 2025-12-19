#!/usr/bin/env python3
"""
Fix para corregir la función normalize_text en acled_rules.py
"""

if __name__ == "__main__":
    # Leer archivo
    with open("src/incidents/acled_rules.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Reemplazar la función problemática
    old_func = '''def normalize_text(text: str) -> str:
    """Normalize text for matching."""
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
    return text.strip()'''
    
    new_func = '''def normalize_text(text: str) -> str:
    """Normalize text for matching - removes accents properly."""
    import unicodedata
    text = (text or "").lower()
    # Remove accents using unicodedata (proper way)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Normalize whitespace
    text = re.sub(r'\\s+', ' ', text)
    return text.strip()'''
    
    if old_func in content:
        new_content = content.replace(old_func, new_func)
        with open("src/incidents/acled_rules.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✓ normalize_text corregido")
    else:
        # Intentar con variante de espaciado
        print("Buscando variantes...")
        
        # Buscar línea por línea
        lines = content.split('\n')
        found = False
        for i, line in enumerate(lines):
            if "def normalize_text" in line:
                print(f"Encontrado en línea {i+1}: {line}")
                found = True
            if "'Ã¡': 'a'" in line or "Ã¡" in line:
                print(f"Mojibake en línea {i+1}: {line[:60]}...")
                found = True
        
        if not found:
            print("✗ No se encontró la función con el patrón esperado")
            print("Primeras 50 líneas con 'normalize':")
            for i, line in enumerate(lines):
                if 'normalize' in line.lower():
                    print(f"  {i+1}: {line[:70]}")
