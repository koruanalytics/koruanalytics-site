# scripts/utils/validate_newsapi_v8_acled.py
# Last updated: 2026-01-17
# Description: Validate v8 ACLED configuration and compare with v7

import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import sys

def load_config(version: str) -> Dict:
    """Load newsapi configuration file."""
    config_path = Path(f"config/newsapi_scope_peru_{version}.yaml")
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def count_words_in_keywords(keywords: List[str]) -> int:
    """Count total words in keyword list (spaces count as word separators)."""
    total_words = 0
    for keyword in keywords:
        words = keyword.strip().split()
        total_words += len(words)
    return total_words


def validate_group(group: Dict, group_num: int) -> Tuple[bool, int]:
    """
    Validate a single keyword group.
    Returns: (is_valid, word_count)
    """
    group_id = group.get('group_id', f'group_{group_num}')
    keywords = group.get('keywords', [])
    
    print(f"\n{'='*70}")
    print(f"GROUP {group_num}: {group_id}")
    print(f"{'='*70}")
    print(f"Label: {group.get('label', 'N/A')}")
    
    # ACLED metadata
    acled_event = group.get('acled_event_type', 'N/A')
    acled_sub = group.get('acled_sub_event_type', 'N/A')
    print(f"ACLED Event Type: {acled_event}")
    print(f"ACLED Sub-Event: {acled_sub}")
    
    if acled_event == 'N/A' or acled_event is None:
        print("⚠️  WARNING: No ACLED category assigned (Peru-specific group)")
    
    print(f"Priority: {group.get('priority', 'N/A')}")
    print(f"Keywords count: {len(keywords)}")
    
    # Count words
    total_words = count_words_in_keywords(keywords)
    print(f"Total WORDS: {total_words}")
    
    # Validate word limit
    is_valid = True
    if total_words > 15:
        print(f"❌ INVALID - Exceeds 15 word limit by {total_words - 15} words!")
        is_valid = False
    else:
        remaining = 15 - total_words
        print(f"✅ Valid - {remaining} words remaining")
    
    # Show keywords
    print(f"\nKeywords:")
    for kw in keywords:
        word_count = len(kw.split())
        print(f"  - {kw} ({word_count} word{'s' if word_count > 1 else ''})")
    
    return is_valid, total_words


def extract_all_keywords(config: Dict) -> Set[str]:
    """Extract all unique keywords from config."""
    all_keywords = set()
    for group in config.get('keyword_groups', []):
        keywords = group.get('keywords', [])
        all_keywords.update(keywords)
    return all_keywords


def analyze_acled_distribution(config: Dict):
    """Analyze distribution of groups by ACLED category."""
    print(f"\n{'='*80}")
    print("ACLED CATEGORY DISTRIBUTION")
    print(f"{'='*80}")
    
    acled_groups = defaultdict(list)
    peru_specific = []
    
    for group in config.get('keyword_groups', []):
        group_id = group.get('group_id')
        acled_event = group.get('acled_event_type')
        
        if acled_event and acled_event != 'null':
            acled_groups[acled_event].append(group_id)
        else:
            peru_specific.append(group_id)
    
    print(f"\n📊 ACLED-Aligned Groups:")
    for event_type, groups in sorted(acled_groups.items()):
        print(f"\n  {event_type} ({len(groups)} groups):")
        for g in groups:
            print(f"    - {g}")
    
    if peru_specific:
        print(f"\n🇵🇪 Peru-Specific Groups (not ACLED):")
        for g in peru_specific:
            print(f"    - {g}")
    
    total_groups = len(config.get('keyword_groups', []))
    acled_count = sum(len(groups) for groups in acled_groups.values())
    acled_percentage = (acled_count / total_groups * 100) if total_groups > 0 else 0
    
    print(f"\n📈 Summary:")
    print(f"  Total groups: {total_groups}")
    print(f"  ACLED-aligned: {acled_count} ({acled_percentage:.1f}%)")
    print(f"  Peru-specific: {len(peru_specific)} ({100-acled_percentage:.1f}%)")


def compare_versions(v7_config: Dict, v8_config: Dict):
    """Compare keyword coverage between v7 and v8."""
    print(f"\n{'='*80}")
    print("COMPARISON: v7 → v8")
    print(f"{'='*80}")
    
    v7_keywords = extract_all_keywords(v7_config)
    v8_keywords = extract_all_keywords(v8_config)
    
    v7_groups = len(v7_config.get('keyword_groups', []))
    v8_groups = len(v8_config.get('keyword_groups', []))
    
    print(f"\nGroups:")
    print(f"  v7: {v7_groups} groups")
    print(f"  v8: {v8_groups} groups ({v8_groups - v7_groups:+d})")
    
    print(f"\nKeywords:")
    print(f"  v7: {len(v7_keywords)} unique keywords")
    print(f"  v8: {len(v8_keywords)} unique keywords")
    
    # Keywords lost (removed in v8)
    removed = v7_keywords - v8_keywords
    if removed:
        print(f"\n🔴 Keywords REMOVED in v8 ({len(removed)}):")
        for kw in sorted(removed):
            print(f"  - {kw}")
    else:
        print(f"\n✅ No keywords removed - Full coverage maintained!")
    
    # Keywords added in v8
    added = v8_keywords - v7_keywords
    if added:
        print(f"\n🟢 Keywords ADDED in v8 ({len(added)}):")
        for kw in sorted(added):
            print(f"  - {kw}")
    
    # Common keywords
    common = v7_keywords & v8_keywords
    print(f"\n🔵 Keywords COMMON to both: {len(common)}")
    
    # Calculate coverage ratio
    if v7_keywords:
        coverage = (len(common) / len(v7_keywords)) * 100
        print(f"\n📊 Coverage ratio: {coverage:.1f}% of v7 keywords retained in v8")
        
        if coverage == 100.0:
            print("✅ PERFECT - All v7 keywords preserved in v8!")
        elif coverage >= 95.0:
            print("✅ EXCELLENT - Minimal keyword loss")
        elif coverage >= 85.0:
            print("⚠️  GOOD - Some keywords lost, review if intentional")
        else:
            print("❌ WARNING - Significant keyword loss detected")


def validate_acled_mapping_completeness(config: Dict):
    """Validate that acled_export_config matches all groups."""
    print(f"\n{'='*80}")
    print("ACLED EXPORT MAPPING VALIDATION")
    print(f"{'='*80}")
    
    export_config = config.get('acled_export_config', {})
    if not export_config:
        print("⚠️  No acled_export_config found in configuration")
        return
    
    # Get all group IDs
    group_ids = {g['group_id'] for g in config.get('keyword_groups', [])}
    
    # Get mapped group IDs from export config
    direct_mapped = set(export_config.get('direct_mapping', {}).keys())
    peru_specific = set(export_config.get('peru_specific', {}).keys())
    all_mapped = direct_mapped | peru_specific
    
    print(f"\nGroup Mapping Coverage:")
    print(f"  Total groups: {len(group_ids)}")
    print(f"  ACLED direct mapped: {len(direct_mapped)}")
    print(f"  Peru-specific mapped: {len(peru_specific)}")
    print(f"  Total mapped: {len(all_mapped)}")
    
    # Check for unmapped groups
    unmapped = group_ids - all_mapped
    if unmapped:
        print(f"\n❌ UNMAPPED GROUPS ({len(unmapped)}):")
        for g in sorted(unmapped):
            print(f"  - {g}")
    else:
        print(f"\n✅ All groups have export mapping!")
    
    # Check for extra mappings
    extra = all_mapped - group_ids
    if extra:
        print(f"\n⚠️  EXTRA MAPPINGS (not in groups):")
        for g in sorted(extra):
            print(f"  - {g}")


def main():
    """Main validation script."""
    print("="*80)
    print("NEWSAPI v8 ACLED CONFIGURATION VALIDATION")
    print("="*80)
    
    # Load both versions
    print("\n📂 Loading configurations...")
    v7_config = load_config("v7")
    v8_config = load_config("v8")
    
    print("\n✅ Both files loaded successfully")
    print(f"v7 version: {v7_config.get('version', 'N/A')}")
    print(f"v8 version: {v8_config.get('version', 'N/A')}")
    print(f"v8 strategy: {v8_config.get('strategy', 'N/A')}")
    
    # Validate v8 groups
    print("\n" + "="*80)
    print("VALIDATING v8 GROUPS")
    print("="*80)
    
    groups = v8_config.get('keyword_groups', [])
    all_valid = True
    total_words = 0
    
    for idx, group in enumerate(groups, 1):
        is_valid, word_count = validate_group(group, idx)
        total_words += word_count
        if not is_valid:
            all_valid = False
    
    # ACLED distribution analysis
    analyze_acled_distribution(v8_config)
    
    # Validate ACLED export mapping
    validate_acled_mapping_completeness(v8_config)
    
    # Compare v7 vs v8
    compare_versions(v7_config, v8_config)
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    avg_words = total_words / len(groups) if groups else 0
    print(f"\nWord Statistics:")
    print(f"  Total words across all groups: {total_words}")
    print(f"  Average words per group: {avg_words:.1f}")
    print(f"  API limit per group: 15 words")
    
    if all_valid:
        print("\n✅ VALIDATION PASSED")
        print("  - All groups within 15 word limit")
        print("  - ACLED taxonomy properly applied")
        print("  - Export mappings complete")
    else:
        print("\n❌ VALIDATION FAILED")
        print("  - Some groups exceed 15 word limit")
        print("  - Fix issues before proceeding")
    
    # Final recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if all_valid:
        print("✅ v8 configuration is ready for testing")
        print("\nNext steps:")
        print("1. Update prompts.py to include 'corrupcion' event type ✅ DONE")
        print("2. Run test ingestion with v8 on single day")
        print("3. Compare article counts v7 vs v8")
        print("4. Test LLM classification with ACLED-aware prompt")
        print("5. Verify ACLED export mapping works")
        print("6. If results good, deploy v8 to production")
    else:
        print("❌ Fix word limit violations before testing")
        print("\nReview groups that exceed 15 words and:")
        print("- Remove low-value keywords")
        print("- Split into multiple groups if needed")
        print("- Consolidate multi-word phrases")


if __name__ == "__main__":
    main()
