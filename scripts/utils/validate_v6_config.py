"""
scripts/utils/validate_v6_config.py
Last updated: 2026-01-09
Description: Validate newsapi_scope_peru_v6.yaml configuration

Checks:
1. All keyword groups have ≤15 WORDS total (API counts words, not keywords!)
2. Required fields are present
3. Strategy is correct

IMPORTANT: NewsAPI.ai counts individual words, not keyword phrases
Example: "ataque candidato" = 2 words, "asesinato" = 1 word
"""
from pathlib import Path
import yaml
import sys

# API limit constant - counts WORDS not keywords!
MAX_WORDS_PER_QUERY = 15


def count_words(keywords: list) -> int:
    """Count total words across all keywords (spaces split into multiple)."""
    return sum(len(kw.split()) for kw in keywords)


def get_multi_word_keywords(keywords: list) -> list:
    """Get list of keywords that contain multiple words."""
    return [kw for kw in keywords if len(kw.split()) > 1]


def validate_v6_config(config_path: str = "config/newsapi_scope_peru_v6.yaml") -> bool:
    """
    Validate v6 configuration file.
    
    Returns True if valid, False otherwise.
    """
    path = Path(config_path)
    
    if not path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return False
    
    print(f"[INFO] Validating: {config_path}")
    print(f"[INFO] API limit: {MAX_WORDS_PER_QUERY} WORDS per query (not keywords!)")
    
    # Load YAML
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    errors = []
    warnings = []
    
    # Check strategy
    strategy = config.get("strategy")
    if strategy != "source_keywords_by_group":
        errors.append(f"Strategy should be 'source_keywords_by_group', found: '{strategy}'")
    
    # Check source_uris
    source_uris = config.get("source_uris", [])
    if not source_uris:
        errors.append("No source_uris defined")
    else:
        print(f"[OK] Found {len(source_uris)} sources: {', '.join(source_uris)}")
    
    # Check keyword_groups
    keyword_groups = config.get("keyword_groups", [])
    if not keyword_groups:
        errors.append("No keyword_groups defined")
    else:
        print(f"\n[INFO] Checking {len(keyword_groups)} keyword groups:")
        print("-" * 70)
        print(f"{'Group':<25} {'Keywords':>10} {'Words':>10} {'Status':>10}")
        print("-" * 70)
        
        total_keywords = 0
        total_words = 0
        
        for group in keyword_groups:
            group_id = group.get("group_id", "unknown")
            keywords = group.get("keywords", [])
            priority = group.get("priority", 2)
            
            kw_count = len(keywords)
            word_count = count_words(keywords)
            multi_word = get_multi_word_keywords(keywords)
            
            total_keywords += kw_count
            total_words += word_count
            
            # Check against WORD limit (not keyword limit)
            is_valid = word_count <= MAX_WORDS_PER_QUERY
            status = "OK" if is_valid else "ERROR"
            icon = "✓" if is_valid else "✗"
            
            print(f"  [{icon}] {group_id:<22} {kw_count:>8} {word_count:>10} {status:>10}")
            
            if not is_valid:
                errors.append(
                    f"Group '{group_id}' has {word_count} words, exceeds limit of {MAX_WORDS_PER_QUERY}"
                )
                if multi_word:
                    print(f"      Multi-word keywords: {multi_word}")
            elif word_count == 0:
                warnings.append(f"Group '{group_id}' has no keywords")
        
        print("-" * 70)
        print(f"[INFO] Total: {total_keywords} keywords = {total_words} words")
        print(f"[INFO] Expected API queries per run: {len(keyword_groups)}")
    
    # Print results
    print("\n" + "=" * 70)
    
    if errors:
        print("[ERRORS]")
        for e in errors:
            print(f"  ✗ {e}")
    
    if warnings:
        print("[WARNINGS]")
        for w in warnings:
            print(f"  ! {w}")
    
    if not errors:
        print("[RESULT] Configuration is VALID ✓")
        return True
    else:
        print(f"[RESULT] Configuration has {len(errors)} ERROR(s) ✗")
        return False


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/newsapi_scope_peru_v6.yaml"
    valid = validate_v6_config(config_path)
    sys.exit(0 if valid else 1)
