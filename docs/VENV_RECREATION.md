# VENV Recreation Guide - OSINT Peru 2026

## Summary
| Metric | Before | After |
|--------|--------|-------|
| Size | 1.65 GB | ~150 MB |
| Packages | 150+ | ~20 |
| Reduction | - | **~90%** |

## Packages Removed (Not Used in Production)

### ML/NLP Stack (~700 MB)
- torch (432 MB) - Classification via Claude API
- transformers (87 MB)
- spacy (85 MB) - Test moved to _legacy
- scipy (115 MB)
- sympy (66 MB)
- datasets, tokenizers, safetensors

### Orchestration (~30 MB)
- prefect - Not used

### Web Frameworks (~50 MB)
- streamlit - Moved to _legacy (using Power BI)
- fastapi, starlette, uvicorn

### Geospatial Extras (~100 MB)
- geopandas, shapely, pyproj, pyogrio, rtree
- Keeping only: geopy (for geocoding)

## Recreation Steps

### 1. Backup current venv
```powershell
deactivate
Rename-Item -Path ".venv" -NewName ".venv_backup"
```

### 2. Create fresh venv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3. Install production dependencies
```powershell
pip install -r requirements-minimal.txt
```

### 4. Verify core imports
```powershell
python -c "import duckdb, pandas, anthropic, eventregistry, loguru, geopy, yaml; print('OK')"
```

### 5. Run tests
```powershell
pip install pytest
python -m pytest tests/ -v --ignore=tests/_legacy
```

### 6. Verify pipeline works
```powershell
# Check database connection  
python -c "import duckdb; con=duckdb.connect('data/osint_peru.duckdb'); print(con.execute('SELECT COUNT(*) FROM bronze_articles').fetchone())"
```

### 7. If all OK, remove backup
```powershell
Remove-Item -Path ".venv_backup" -Recurse -Force
```

## Rollback
```powershell
Remove-Item -Path ".venv" -Recurse -Force
Rename-Item -Path ".venv_backup" -NewName ".venv"
```

## Files Moved to _legacy
- `tests/_legacy/test_nlp_geo_smoke.py`
- `dashboards/_legacy/streamlit/`

## Post-Recreation Checklist
- [ ] Venv size < 300 MB
- [ ] `pip list` shows ~20 packages
- [ ] Database connects OK
- [ ] LLM classification works
- [ ] All active tests pass
