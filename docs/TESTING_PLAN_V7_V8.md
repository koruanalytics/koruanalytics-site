# Testing Plan v7 → v8 (ACLED)

**Date:** 2026-01-17  
**Objective:** Validate v8 ACLED configuration before production deployment  
**Duration:** 3-4 hours  
**Prerequisites:** ✅ v8 validated (all groups ≤15 words)

---

## Overview

This testing plan validates v8 in 3 phases:

1. **Phase 1:** Ingestion Test (v7 vs v8 article counts)
2. **Phase 2:** Classification Test (LLM prompt v1 vs v2)
3. **Phase 3:** Decision & Deployment

---

## Phase 1: Ingestion Test (1-2 hours)

### Objective
Compare article ingestion between v7 and v8 for same date to ensure similar coverage.

### Prerequisites
- ✅ Both config files present: `config/newsapi_scope_peru_v7.yaml` and `v8.yaml`
- ✅ API key configured in environment variables
- ✅ Database accessible: `data/database.duckdb`

### Execution

```powershell
# Navigate to project
cd "C:\Users\carlo\OneDrive - KoruAnalytics\Prj_OSINT\2026_Peru"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run ingestion comparison test
python -m scripts.tests.test_v7_vs_v8_ingestion --date 2026-01-16

# Optional: Keep test tables for manual inspection
python -m scripts.tests.test_v7_vs_v8_ingestion --date 2026-01-16 --keep-tables
```

### Expected Output

```
================================================================================
v7 vs v8 INGESTION COMPARISON TEST
================================================================================
Test date: 2026-01-16
Database: data/database.duckdb
================================================================================

==============================================================================
FETCHING ARTICLES - V7
==============================================================================
Fetching for date: 2026-01-16
✅ v7: Fetched 285 articles

==============================================================================
FETCHING ARTICLES - V8
==============================================================================
Fetching for date: 2026-01-16
✅ v8: Fetched 327 articles

================================================================================
ANALYSIS: v7 vs v8
================================================================================

📊 Article Counts:
  v7: 285 articles
  v8: 327 articles
  Difference: +14.7%

📂 Category Distribution:
  [... detailed breakdown ...]

🔑 Keyword Group Distribution (v8):
  battles: 42
  violence_civilians: 98
  sexual_violence: 18
  protests: 45
  riots: 23
  strategic_developments: 67
  electoral_violence: 12
  terrorism: 8
  corruption: 31  ← NEW
  natural_disasters: 15
  electoral_process: 38
  accidents: 27

🆕 Articles Unique to v8: 52
⚠️  Articles Lost in v8: 10
🔵 Common Articles: 275

================================================================================
RECOMMENDATION
================================================================================
✅ RECOMMEND DEPLOYMENT (with monitoring)
Reasons:
  • Article count increased 14.7% (expected from 3 new groups)
  • v8 adds 52 new articles
  • Monitor first week for quality
```

### Success Criteria

**✅ Pass** if:
- Article count within -10% to +25% of v7
- Less than 5% of v7 articles lost
- New groups (battles, riots, corruption) return results
- No API errors

**⚠️ Review Required** if:
- Article count -10% to -20%
- 5-10% of v7 articles lost
- Review which articles were lost (are they low-value?)

**❌ Fail** if:
- Article count change >±25%
- More than 10% of v7 articles lost
- Critical groups return zero results
- API errors or quota issues

### Troubleshooting

**Issue:** v7 or v8 returns 0 articles
- **Cause:** API key issue, date too old, or connectivity problem
- **Fix:** Check API key, try yesterday's date, verify internet connection

**Issue:** v8 count significantly lower than v7
- **Cause:** Keywords too specific, API query formation issue
- **Fix:** Review v8 YAML for syntax errors, check logs for API errors

**Issue:** "Coverage ratio: 79.3%" warning
- **Cause:** Script counts literal keywords, not semantic coverage
- **Fix:** This is EXPECTED - see Migration Guide explanation

---

## Phase 2: Classification Test (1-2 hours)

### Objective
Verify new ACLED prompt (v2) classifies articles correctly and detects new 'corrupcion' type.

### Prerequisites
- ✅ Phase 1 completed successfully
- ✅ Bronze table has recent articles (from Phase 1 or existing data)
- ✅ LLM provider configured (Anthropic or Azure OpenAI)

### Execution

```powershell
# Run classification comparison (50 articles)
python -m scripts.tests.test_v7_vs_v8_classification --limit 50

# Optional: Test more articles
python -m scripts.tests.test_v7_vs_v8_classification --limit 100
```

### Expected Output

```
================================================================================
v1 vs v2 LLM CLASSIFICATION COMPARISON
================================================================================
Articles to test: 50
Database: data/database.duckdb
================================================================================

CLASSIFYING ARTICLES
================================================================================
Processing article 1/50: ...
[... progress for all 50 articles ...]

================================================================================
ANALYSIS: v1 vs v2 CLASSIFICATION
================================================================================

📊 Event Type Distribution:

  V1:
    crimen_violento: 18
    protesta: 12
    operativo_seguridad: 8
    violencia_politica: 5
    desastre_natural: 4
    disturbio: 3
    [...]

  V2:
    crimen_violento: 17
    protesta: 8
    riots: 4  ← NEW (split from protesta)
    operativo_seguridad: 7
    corrupcion: 6  ← NEW TYPE
    violencia_politica: 5
    desastre_natural: 4
    battles: 3  ← NEW (split from violencia_armada)
    [...]

🆕 New 'corrupcion' type in v2: 6 cases

✅ Relevant Articles:
  v1: 42/50 (84.0%)
  v2: 43/50 (86.0%)

🤝 Classification Agreement:
  Agreement: 41/50 (82.0%)
  Disagreement: 9

  Sample Disagreements:
    article_123:
      v1: protesta → v2: riots  ← EXPECTED (ACLED separation)
    article_456:
      v1: crimen_violento → v2: corrupcion  ← NEW TYPE DETECTED
    [...]

================================================================================
RECOMMENDATION
================================================================================
✅ EXCELLENT - Deploy v2 (ACLED) prompt
Reasons:
  • High agreement rate: 82.0%
  • New 'corrupcion' type working: 6 cases detected
  • ACLED taxonomy applied successfully
```

### Success Criteria

**✅ Pass** if:
- Agreement rate ≥75%
- 'corrupcion' type detected (>0 cases)
- Disagreements are expected ACLED improvements:
  - `protesta` → `riots` (violent protests correctly separated)
  - `crimen_violento` → `battles` (armed clashes correctly separated)
  - Any type → `corrupcion` (new type detection working)

**⚠️ Review Required** if:
- Agreement rate 60-75%
- No 'corrupcion' detected (might be sample-dependent)
- Review disagreement patterns to ensure they're improvements

**❌ Fail** if:
- Agreement rate <60%
- Systematic misclassification (e.g., all protests → riots)
- 'corrupcion' detection on non-corruption articles

### Troubleshooting

**Issue:** Agreement rate very low (<50%)
- **Cause:** Prompt formatting issue or LLM provider problem
- **Fix:** Check prompts.py for syntax errors, verify LLM API connection

**Issue:** No 'corrupcion' detected in 50 articles
- **Cause:** Sample may not include corruption cases
- **Fix:** Test with 100 articles, or manually select corruption-related articles

**Issue:** Too many 'corrupcion' classifications
- **Cause:** Prompt too broad, classifying non-corruption as corruption
- **Fix:** Review sample classifications, may need prompt refinement

---

## Phase 3: Decision & Deployment (30 min)

### Objective
Make go/no-go decision on v8 deployment based on Phase 1 and 2 results.

### Decision Matrix

| Phase 1 Result | Phase 2 Result | Decision |
|----------------|----------------|----------|
| ✅ Pass | ✅ Pass | **✅ DEPLOY v8** |
| ✅ Pass | ⚠️ Review | Deploy v8, monitor classification for 3 days |
| ⚠️ Review | ✅ Pass | Deploy v8, verify ingestion coverage |
| ✅ Pass | ❌ Fail | Don't deploy, fix prompt issues |
| ❌ Fail | Any | Don't deploy, fix config issues |
| ⚠️ Review | ⚠️ Review | Deploy v8 with caution, daily monitoring |

### Deployment Steps (if Decision = Deploy)

1. **Update production config pointer**
   
   ```powershell
   # Option A: Update daily pipeline to use v8
   # Edit: scripts/core/daily_pipeline.py
   # Change: CONFIG_VERSION = "v8"
   
   # Option B: Set environment variable
   $env:OSINT_CONFIG_VERSION = "v8"
   ```

2. **Run first production day**
   
   ```powershell
   # Run full pipeline with v8
   python -m scripts.core.daily_pipeline --full
   
   # Monitor execution logs
   # Expected: ~325-550 articles/day
   # Expected: 'corrupcion' type in silver/gold
   ```

3. **Verify Power BI compatibility**
   
   - Open Power BI dashboards
   - Refresh data sources
   - Verify all visualizations load correctly
   - Check for new 'corrupcion' category in charts

4. **Monitor for 3-7 days**
   
   - Daily article counts stable?
   - Event type distribution reasonable?
   - No anomalies in gold_incidents?
   - Power BI dashboards working?

### Rollback Steps (if Decision = Don't Deploy)

1. **Keep v7 as default**
   
   ```powershell
   # Ensure pipeline uses v7
   # CONFIG_VERSION = "v7" in daily_pipeline.py
   ```

2. **Document issues found**
   
   - Create detailed report of test failures
   - Specific examples of problematic classifications
   - Recommendations for v8 improvements

3. **Fix and re-test**
   
   - Adjust v8 configuration or prompts based on findings
   - Re-run validation: `python -m scripts.utils.validate_newsapi_v8_acled`
   - Re-run Phase 1 and 2 tests

---

## Post-Deployment Monitoring (Days 1-7)

### Daily Checks

```powershell
# Check article counts
python -c @'
import duckdb
con = duckdb.connect("data/database.duckdb")
result = con.execute("""
    SELECT DATE(fecha_publicacion) as date, COUNT(*) as count
    FROM bronze_news
    WHERE fecha_publicacion >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE(fecha_publicacion)
    ORDER BY date DESC
""").fetchall()
for row in result:
    print(f"{row[0]}: {row[1]} articles")
'@

# Check event type distribution
python -c @'
import duckdb
con = duckdb.connect("data/database.duckdb")
result = con.execute("""
    SELECT tipo_evento, COUNT(*) as count
    FROM gold_incidents
    WHERE fecha_publicacion >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY tipo_evento
    ORDER BY count DESC
""").fetchall()
for row in result:
    print(f"{row[0]}: {row[1]}")
'@
```

### Watch for Anomalies

- ⚠️ Article count drops below 250/day (investigate API or keywords)
- ⚠️ 'corrupcion' type >100/day (too broad, review classifications)
- ⚠️ 'corrupcion' type <5/day (too narrow, review sample articles)
- ⚠️ Any group consistently returns 0 articles

### Week 1 Review Meeting

After 7 days of v8 operation:

1. **Quantitative Review:**
   - Average articles/day vs baseline
   - Event type distribution vs expectations
   - Power BI dashboard usage

2. **Qualitative Review:**
   - Sample 20 'corrupcion' incidents - are they actually corruption?
   - Sample 10 'battles' - correctly separated from 'crimen_violento'?
   - Sample 10 'riots' - correctly separated from 'protesta'?

3. **Decision:**
   - ✅ Keep v8 permanently
   - ⚠️ Keep v8, make minor adjustments
   - ❌ Rollback to v7, major issues found

---

## Quick Reference Commands

```powershell
# Validation
python -m scripts.utils.validate_newsapi_v8_acled

# Phase 1: Ingestion Test
python -m scripts.tests.test_v7_vs_v8_ingestion --date 2026-01-16

# Phase 2: Classification Test
python -m scripts.tests.test_v7_vs_v8_classification --limit 50

# Production Run (after deployment)
python -m scripts.core.daily_pipeline --full

# Check Recent Data
python -c "import duckdb; con = duckdb.connect('data/database.duckdb'); print(con.execute('SELECT COUNT(*) FROM bronze_news WHERE fecha_publicacion >= CURRENT_DATE').fetchone()[0])"
```

---

## Troubleshooting Guide

### Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Test script fails to import | Virtual env not activated | `.\.venv\Scripts\Activate.ps1` |
| "Config file not found" | Wrong working directory | `cd` to project root |
| "No articles found" | Empty bronze table | Run regular ingestion first |
| "LLM API error" | Provider credentials missing | Check `.env` file for API keys |
| Very slow classification | Too many articles | Use `--limit 50` for faster tests |

---

## Contact & Support

**Technical Lead:** Carlos @ KoruAnalytics  
**Testing Date:** 2026-01-17  
**Related Docs:**
- `docs/MIGRATION_V7_TO_V8_ACLED.md` - Full migration guide
- `config/newsapi_scope_peru_v8.yaml` - v8 configuration
- `src/llm_providers/prompts.py` - v2 ACLED prompt

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-17  
**Status:** Ready for Execution ✅
