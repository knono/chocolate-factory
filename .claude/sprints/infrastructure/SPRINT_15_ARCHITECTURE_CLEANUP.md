# Sprint 15 - Architecture Cleanup & Consolidation

**Date**: October 29, 2025
**Status**: IN PROGRESS
**Goal**: Fix critical architecture issues before proceeding with further development

## Overview

This sprint addresses 6 critical issues preventing Clean Architecture from being production-ready:
1. Consolidate duplicate API clients
2. Clean up bloated services layer
3. Develop domain layer properly
4. Fix main.py bugs
5. Document missing pieces (dependencies.py)
6. Establish clear layer boundaries

## Problem Summary

| # | Issue | Files Affected | Gravedad |
|---|-------|-----------------|----------|
| 1 | API client duplication | services/ + infrastructure/external_apis/ | 🔴 CRÍTICA |
| 2 | Services bloat (30 files) | services/ | 🟠 ALTA |
| 3 | Domain layer empty | domain/ | 🟠 ALTA |
| 4 | main.py bugs | main.py line 131 | 🟡 MEDIA |
| 5 | dependencies.py undocumented | dependencies.py | 🟡 MEDIA |
| 6 | Unclear service boundaries | services/ | 🟡 MEDIA |

## Task 1: Consolidate API Clients (IN PROGRESS)

### Current State
- `services/ree_client.py` (612 lines) - OLD/REDUNDANT
- `infrastructure/external_apis/ree_client.py` (259 lines) - CLEAN/MODERN
- Same pattern for aemet_client.py and openweathermap_client.py

### Action Items
- [ ] Verify infrastructure/ clients are being used (check imports in services/)
- [ ] Remove services/*_client.py files
- [ ] Update all imports to use infrastructure/external_apis/
- [ ] Run tests to ensure no breakage
- [ ] Document which clients are in use

### Expected Result
- Single source of truth for each API client
- All clients in `infrastructure/external_apis/`
- Services layer uses DI to get clients from infrastructure

---

## Task 2: Clean up Services Layer

### Current State
**30 files including legacy:**
- `historical_analytics.py` (10KB) - Not used in current flows
- `historical_data_service.py` (31KB) - Replaced by modern services
- `initialization/` folder - Startup legacy code

### Action Items
- [ ] Identify which legacy files are actually used
- [ ] Move unused code to `services/legacy/` (archive)
- [ ] Update imports if anything still uses legacy code
- [ ] Document which services are current vs legacy

### Target Structure
```
services/
├── core/                          # Core orchestration (keep)
│   ├── ree_service.py
│   ├── aemet_service.py
│   └── weather_aggregation_service.py
├── data/                          # Data processing (keep)
│   ├── siar_etl.py
│   ├── siar_analysis_service.py
│   ├── gap_detector.py
│   └── backfill_service.py
├── ml/                            # ML services (keep)
│   ├── direct_ml.py
│   ├── ml_models.py
│   └── feature_engineering.py
├── features/                      # Feature services (keep)
│   ├── chatbot_service.py
│   ├── chatbot_context_service.py
│   ├── tailscale_health_service.py
│   └── health_logs_service.py
├── legacy/                        # ARCHIVE - Old code (move)
│   ├── historical_analytics.py
│   ├── historical_data_service.py
│   └── initialization/
└── __init__.py
```

### Expected Result
- Services organized by domain
- Legacy code archived but accessible
- ~15 core service files (down from 30)

---

## Task 3: Develop Domain Layer

### Current State
**5 files with minimal content:**
- `domain/energy/forecaster.py` - Exists but sparse
- `domain/ml/model_trainer.py` - Exists but sparse
- `domain/weather/` - EMPTY

### Action Items
- [ ] Identify business logic in services/ that should move to domain/
- [ ] Extract price forecasting logic → domain/energy/
- [ ] Extract ML training logic → domain/ml/
- [ ] Create domain/weather/ logic (classification, validation)
- [ ] Create domain/optimization/ (production rules)

### Example: Move from Services to Domain

**From**: `services/business_logic_service.py` (business rules)
**To**: `domain/production/optimization_rules.py`

**From**: `services/siar_analysis_service.py` (correlations calculation)
**To**: `domain/analysis/historical_analyzer.py`

### Expected Result
- Domain layer contains pure business logic
- No infrastructure dependencies in domain/
- Services only orchestrate domain + infrastructure
- Clear separation of concerns

---

## Task 4: Fix main.py Bugs

### Bug 1: uvicorn.run() Reference
**Location**: src/fastapi-app/main.py:131
**Current**:
```python
uvicorn.run(
    "main_new:app",  # ❌ WRONG
    ...
)
```
**Fix**:
```python
uvicorn.run(
    "main:app",  # ✅ CORRECT
    ...
)
```

### Action Items
- [ ] Fix line 131 in main.py
- [ ] Test running `python main.py` directly
- [ ] Verify Docker still works

---

## Task 5: Document dependencies.py

### Current State
- Critical DI container file exists
- Not documented anywhere
- Pattern: `@lru_cache()` for singletons

### Action Items
- [ ] Add section to docs/CLEAN_ARCHITECTURE_REFACTORING.md
- [ ] Document each get_*() function
- [ ] Explain singleton pattern usage
- [ ] Add usage example for new services
- [ ] Create DEPENDENCIES.md if needed

### Example Documentation
```markdown
## Dependency Injection (dependencies.py)

Provides singleton instances via FastAPI Depends():

- get_influxdb_client() → InfluxDBClient
- get_ree_service() → REEService (uses REEClient from infrastructure/)
- get_aemet_service() → AemetService
- init_scheduler() → APScheduler
```

---

## Task 6: Establish Clear Service Boundaries

### Current Problem
Services don't have clear responsibility boundaries. Example:
- `siar_analysis_service.py` - Does analysis but also data retrieval
- `gap_detector.py` - Detects gaps but also does backfilling logic
- `backfill_service.py` - Same pattern, unclear scope

### Action Items
- [ ] Define clear responsibility for each service group
- [ ] Document what each service DOES and DOES NOT do
- [ ] Create service interaction diagram
- [ ] Update docstrings in each service file

### Service Groups (Proposed)
```
Core Data Services:
- REEService: Fetch + store electricity prices
- AemetService: Fetch + store weather data
- WeatherAggregationService: Combine multiple weather sources

Data Processing:
- SIARETLService: Historical data ingestion
- SIARAnalysisService: Calculate correlations/patterns
- GapDetectorService: Identify missing data
- BackfillService: Recover missing data

ML Services:
- DirectMLService: Train/predict with sklearn
- MLModelsService: Load/save models
- FeatureEngineeringService: Create features

Features:
- ChatbotService: Conversational interface
- TailscaleHealthService: Monitor Tailnet nodes
```

---

## Checklist

### Task 1: API Client Consolidation
- [ ] Verify which clients are imported where
- [ ] Remove services/*_client.py
- [ ] Update all imports
- [ ] Test endpoints
- [ ] Commit changes

### Task 2: Services Layer Cleanup
- [ ] Move legacy files to services/legacy/
- [ ] Update imports
- [ ] Organize services into subdirectories
- [ ] Test all services
- [ ] Commit changes

### Task 3: Domain Layer Development
- [ ] Extract business logic from services/
- [ ] Create domain/ subdirectories
- [ ] Write business logic classes
- [ ] Update services to use domain/
- [ ] Test domain logic
- [ ] Commit changes

### Task 4: Fix main.py
- [ ] Change "main_new" to "main"
- [ ] Test: `python main.py`
- [ ] Test: Docker startup
- [ ] Commit changes

### Task 5: Document dependencies.py
- [ ] Update docs/CLEAN_ARCHITECTURE_REFACTORING.md
- [ ] Document each dependency function
- [ ] Add architecture diagram
- [ ] Commit changes

### Task 6: Service Boundaries
- [ ] Define responsibilities per service
- [ ] Update docstrings
- [ ] Create interaction diagram
- [ ] Commit changes

---

## Expected Outcomes

### After Sprint 15
✅ Single source of truth for API clients
✅ Services layer reduced from 30 → 15 core files
✅ Domain layer with actual business logic
✅ main.py bugs fixed and documented
✅ dependencies.py documented
✅ Clear service responsibility boundaries
✅ Codebase ready for maintenance/extension

### Metrics
- API client files: 6 → 3 (remove duplicates)
- Services files: 30 → 15 (archive legacy)
- Domain files: 5 → 12 (add business logic)
- Architecture clarity: ⭐⭐⭐ (was ⭐)
- Technical debt: Reduced significantly

---

## Notes

- Main goal is cleanup, not new features
- All changes must maintain backward compatibility
- Tests must pass throughout
- Document everything
- No architectural changes to Docker setup

---

**Sprint Started**: October 29, 2025
**Target Completion**: Before Sprint 16
**Owner**: Architecture Cleanup Task Force
