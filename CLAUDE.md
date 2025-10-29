# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a chocolate factory simulation and monitoring system. The project implements a streamlined containerized architecture with **2 main containers** (+ optional Tailscale sidecar) for automated data ingestion, ML prediction, and monitoring.

## Architecture

The system follows a **simplified 2-container production architecture** (September 2025):

1. **API Unificada** ("El Cerebro Autónomo") - FastAPI with APScheduler + Direct ML Training
2. **Almacén de Series** ("El Almacén Principal") - InfluxDB for time series storage  
3. **Tailscale Sidecar** ("Portal Seguro") - Alpine proxy + SSL (optional)

**✅ Architecture Simplification Completed (Sept 2025):** Direct ML training with sklearn + pickle storage.

The main FastAPI application (`src/fastapi-app/`) acts as the autonomous brain:
- Real-time data ingestion (REE electricity + hybrid weather)
- Direct ML training and predictions (no external ML services)
- Integrated dashboard at `/dashboard/complete`
- APScheduler automation (10+ scheduled jobs)
- Automatic gap detection and backfill recovery

## Project Structure

### ✅ Clean Architecture + Sprint 15 Consolidation (Oct 6 - Oct 29, 2025)

FastAPI application with Clean Architecture:

```
src/fastapi-app/
├── main.py                     # Entry point (136 lines)
├── dependencies.py             # DI container - singleton pattern with @lru_cache()
├── startup_tasks.py            # Startup initialization
│
├── api/                        # 🔷 HTTP Interface (13 routers, ~60 endpoints)
│   ├── routers/
│   │   ├── health.py, ree.py, weather.py               # Core data
│   │   ├── dashboard.py, optimization.py, analysis.py  # Dashboard/analysis
│   │   ├── gaps.py, insights.py                        # Derived data
│   │   ├── chatbot.py, health_monitoring.py            # Features (Sprints 11,13)
│   │   ├── ml_predictions.py, price_forecast.py       # ML predictions
│   │   └── schemas/
│
├── domain/                     # 🔶 Business Logic (14 files)
│   ├── ml/                     # Direct ML, feature engineering, model training
│   ├── recommendations/        # Business logic, production recommendations
│   ├── analysis/               # SIAR historical analysis (88k records)
│   ├── energy/forecaster.py   # Energy forecasting
│   └── weather/
│
├── services/                   # 🔷 Orchestration (21 active files)
│   ├── Core: ree_service, aemet_service, weather_aggregation_service, dashboard
│   ├── Data: siar_etl, gap_detector, backfill_service, data_ingestion
│   ├── Features: chatbot_service, tailscale_health_service, health_logs_service
│   ├── Supporting: scheduler, ml_models, etc.
│   ├── Compatibility: ml_domain_compat, recommendation_domain_compat, analysis_domain_compat
│   └── legacy/                 # 13 archived files (historical_*, initialization/)
│
├── infrastructure/             # 🔷 External Systems (8 files)
│   ├── influxdb/client.py, queries.py
│   └── external_apis/ree_client.py, aemet_client.py, openweather_client.py
│
├── core/                       # 🔶 Utilities (4 files)
│   ├── config.py, logging_config.py, exceptions.py
│
├── tasks/                      # 🔷 Background Jobs (5 files)
│   ├── scheduler_config.py, ree_jobs.py, weather_jobs.py, ml_jobs.py, health_monitoring_jobs.py
│
└── tests/                      # ~11 test files
```

**Final Metrics:**
- **13 routers** (~60 endpoints)
- **21 services** (down from 30 - legacy archived)
- **14 domain files** (business logic properly extracted)
- **3 API clients** consolidated in infrastructure/
- **102 tests** (36 E2E, 100% passing)

### Legacy Project Structure (Pre-Refactoring)
```
├── docker/                    # Docker infrastructure
│   ├── docker-compose.yml     # 2-container orchestration
│   ├── docker-compose.override.yml # Tailscale sidecar
│   └── services/              # Persistent data
│       ├── influxdb/data/     # Time series data
│       └── fastapi/models/    # ML models (pickle)
├── docs/                      # Technical documentation
└── logs/                      # Application logs
```

## Development Status

### Recent Completion: Sprint 13 - Health Monitoring + Event Logs (Pivoted from Analytics)
**Status**: COMPLETED (October 21, 2025 - Pivoted 18:00, Finished 19:30)
**Documentation**: [`.claude/sprints/infrastructure/SPRINT_13_TAILSCALE_OBSERVABILITY.md`](.claude/sprints/infrastructure/SPRINT_13_TAILSCALE_OBSERVABILITY.md)

**Pivote Crítico**: Analytics inicial NO aportaba valor → Reenfocado a Health Monitoring + Event Logs

Implemented:
- HTTP proxy server in Tailscale sidecar (socat, port 8765)
- TailscaleHealthService + HealthLogsService (537 lines total)
- 6 endpoints `/health-monitoring/*` (summary, critical, alerts, nodes, uptime, **logs**)
- Event logs paginados con filtros (severity + event_type, 20 eventos/página)
- Filtro `project_only` para mostrar solo nodos del proyecto (3/12)
- Dashboard VPN completo en `/vpn` con logs en tiempo real
- 3 APScheduler jobs (health metrics every 5 min, critical check every 2 min)
- Critical nodes monitoring (production/development/git) - 100% healthy
- Zero Docker socket exposure + Zero información sensible expuesta (placeholders)

### Recent Completion: Sprint 12 Fase 11 - E2E Testing Suite
**Status**: COMPLETED (October 20, 2025)
**Documentation**: [`.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`](.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md)

Implemented:
- 36 E2E tests (smoke, pipeline, resilience, performance)
- Smoke tests integrated in CI/CD pipeline (post-deploy validation)
- Automatic rollback on test failures (dev + prod)
- 102 total tests (100% passing, 19% coverage)
- Fixtures and markers for E2E testing

### Sprint History (Completed)
- Sprint 01-02: Monolithic → Microservices migration
- Sprint 03: Service Layer + Repository pattern
- Sprint 04: SIAR ETL (88,935 records, 25 years)
- Sprint 05: Unified Dashboard + BusinessLogicService
- Sprint 06: Prophet Price Forecasting (Oct 3, 2025)
- Sprint 07: SIAR Historical Analysis (Oct 4, 2025)
  - Correlaciones: R²=0.049 (temp), R²=0.057 (humedad)
  - 5 endpoints `/analysis/*`
- Sprint 08: Hourly Production Optimization (Oct 6, 2025)
  - Timeline 24h con precio Prophet + periodo tarifario
  - Clasificación P1/P2/P3
- Sprint 09: Unified Predictive Dashboard (Oct 7, 2025)
  - 4 endpoints `/insights/*`
  - Tailnet integration
- Sprint 10: ML Consolidation & Documentation (Oct 20, 2025)
  - Feature Engineering validado (NO código sintético)
  - docs/ML_ARCHITECTURE.md creado (1,580 líneas)
  - ROI tracking verificado (1,661€/año)
  - Decisión: NO unificar servicios ML (evitar riesgo)
- Sprint 11: Chatbot BI - Claude Haiku API (Oct 10, 2025)
  - RAG local, keyword matching
  - 3 endpoints `/chat/*`
  - Latencia 10-13s, rate limiting 20/min
- Sprint 12: Forgejo CI/CD Fase 1-11 (Oct 13-20, 2025)
  - Forgejo + Runners + Registry + SOPS
  - CI/CD dual environment (dev/prod)
  - 102 tests (36 E2E), 100% passing, coverage 19%
  - Tests ML (Prophet + sklearn), servicios, integration, E2E
  - Smoke tests + automatic rollback integrated in pipeline
- Sprint 13: Health Monitoring (Oct 21, 2025) - **Pivoted from Analytics**
  - HTTP proxy server (socat) en sidecar - maintained
  - 5 endpoints `/health-monitoring/*` (summary, critical, alerts, nodes, uptime)
  - Uptime tracking + proactive alerts for critical nodes
  - 3 APScheduler jobs (metrics 5min, critical check 2min, status log hourly)
  - Critical nodes: 100% healthy (production/development/git)
  - Zero Docker socket exposure (secure)
- Sprint 14: HYBRID ML Training Optimization (Oct 24, 2025)
  - Problem: merge INNER with timestamp mismatch (REE hourly vs Weather diario/5min)
  - Solution Phase 1: RESAMPLE weather to hourly (mean/max/min)
  - Solution Phase 2: HYBRID training with SIAR historical (8,885 samples, 25 years)
  - Result: R² 0.334 → 0.963 (191% improvement)
  - New endpoints: POST /predict/train/hybrid
  - Prophet router integrated: GET /predict/prices/weekly, /hourly, /train, /status

### Core Infrastructure
- **FastAPI Brain** (chocolate_factory_brain) - API + Dashboard + Direct ML
- **InfluxDB Storage** (chocolate_factory_storage) - Time series database
- **Tailscale Sidecar** (optional) - HTTPS remote access via Tailnet

### Data Integration
- **REE API**: Real Spanish electricity prices 
- **Hybrid Weather**: AEMET + OpenWeatherMap (24/7 coverage)
- **Historical Data**: 25+ years weather records via SIAR system ETL (2000-2025)
- **Automatic Backfill**: Gap detection and recovery every 2 hours

### Machine Learning (Direct Implementation)
- **Prophet Forecasting**: 168-hour REE price prediction (MAE: 0.033 €/kWh, R²: 0.49)
- **sklearn Models**: RandomForest with real data + business rules (Oct 28, 2025)
  - Data: REE 12,493 records (2022-2025) + SIAR 8,900 records (2000-2025)
  - Merged: 481 days with both price + weather
  - Regression: Energy score (0-100), R²: 0.9986 (test set)
  - Classification: Production state (Optimal/Moderate/Reduced/Halt), Accuracy: 1.0 (test set)
- **Direct Training**: sklearn + Prophet + pickle storage (no external ML services)
- **Real ML Training (Oct 28, 2025)**:
  - Target: Business rules (not synthetic) - price/temp thresholds
  - Train/Test: 80/20 split (384/97 samples)
  - Validation: Proper test set metrics (honest, no data leakage)
- **Feature Engineering**: 5 core features (price, hour, dow, temperature, humidity)
  - SIAR sources: temperature, humidity from 2 stations (J09, J17)
  - REE source: price_eur_kwh hourly data
- **Real-time Predictions**: Energy optimization + production recommendations + price forecasting
- **Automated ML**: Model retraining every 30 min (sklearn), hourly (Prophet)
- **ROI Tracking**: 1,661€/año ahorro energético demostrable (Sprint 09)
- **Testing**: 102 tests (36 E2E), 100% passing, 19% coverage (Sprint 12)
- **Documentation**: `docs/ML_ARCHITECTURE.md` (Sprint 10, updated Oct 24)

### Operations
- **APScheduler**: 11 automated jobs (ingestion, ML, Prophet forecasting, backfill, health)
- **Integrated Dashboard**: `/dashboard/complete` (replaces Node-RED)
- **Visual Dashboard**: `/dashboard` with Prophet ML heatmap and interactive tooltips
- **Weekly Forecast**: 7-day Prophet predictions with color-coded price zones (Safari/Chrome/Brave compatible)
- **Self-healing**: Automatic gap detection and recovery

## Key Design Principles

- **Autonomous Operation**: APScheduler handles all automation
- **Integrated Dashboard**: Served directly from FastAPI
- **Stack Unification**: 100% Python ecosystem
- **Self-healing**: Automatic gap detection and backfill recovery

## Data Sources

### REE (Spanish Electricity Market)
- **Real-time prices**: Spanish electricity prices (PVPC)
- **Automation**: Hourly ingestion via APScheduler
- **Status**: ✅ Fully operational

### Weather Data (Hybrid Integration)
- **Primary**: AEMET official observations (00:00-07:00)
- **Secondary**: OpenWeatherMap real-time (08:00-23:00)
- **Fallback**: Automatic source switching
- **Historical**: SIAR system ETL (25+ years, 88,935 records from 2000-2025)
- **Status**: ✅ 24/7 coverage achieved
- **AEMET OpenData**: https://opendata.aemet.es/dist/index.html

### Token Management
- **AEMET**: Auto-renewal every 6 days
- **OpenWeatherMap**: Free tier (60 calls/min)
- **REE**: No authentication required

## ML Feature Pipeline

### Core Features
```python
# Energy data
- ree_price_eur_kwh          # Real electricity prices
- tariff_period              # P1-P6 classification

# Weather data (hybrid)
- temperature                # AEMET + OpenWeatherMap
- humidity                   # AEMET + OpenWeatherMap  
- pressure                   # Weather observations

# Derived features
- chocolate_production_index # Comfort index for chocolate
- heat_stress_factor        # Extreme weather detection
- energy_optimization_score # Price + weather optimization
```

## Key Endpoints

> **📌 Note**: All endpoints below have been migrated to Clean Architecture routers (October 6, 2025).
> See `src/fastapi-app/api/routers/` for implementation details.

### Health & System (health_router)
- `GET /health` - System health check
- `GET /ready` - Readiness probe
- `GET /version` - API version info

### Data Ingestion (ree_router, weather_router)
- `POST /ingest-now` - Manual data ingestion
- `GET /weather/hybrid` - Hybrid weather data
- `GET /ree/prices` - Current electricity prices

### ML Operations
- `POST /predict/energy-optimization` - Energy optimization score (0-100) predictions
- `POST /predict/production-recommendation` - Production class predictions (Optimal/Moderate/Reduced/Halt)
- `POST /predict/train` - Train sklearn models manually (energy + production)
- `POST /predict/train/hybrid` - Hybrid training: Phase 1 SIAR (88k records) + Phase 2 REE fine-tune (100 days)

### Price Forecasting (Sprint 06 - Prophet ML)
- `GET /predict/prices/weekly` - 168-hour Prophet forecast with confidence intervals
- `GET /predict/prices/hourly?hours=N` - Configurable forecast horizon (1-168 hours)
- `POST /models/price-forecast/train` - Train Prophet model with historical REE data
- `GET /models/price-forecast/status` - Model metrics (MAE, RMSE, R², coverage)

### SIAR Historical Analysis (Sprint 07 - analysis_router) ✅
- `GET /analysis/weather-correlation` - Correlaciones R² temperatura/humedad → eficiencia (25 años evidencia)
- `GET /analysis/seasonal-patterns` - Patrones estacionales con 88,935 registros SIAR (mejores/peores meses)
- `GET /analysis/critical-thresholds` - Umbrales críticos basados en percentiles históricos (P90, P95, P99)
- `GET /analysis/siar-summary` - Resumen ejecutivo completo análisis histórico
- `POST /analysis/forecast/aemet-contextualized` - Predicciones AEMET + contexto histórico SIAR

### Hourly Production Optimization (Sprint 08 - optimization_router) ✅
- `POST /optimize/production/daily` - Plan optimizado 24h con timeline horaria granular
  - **Input**: `target_date` (opcional), `target_kg` (opcional, default 200kg)
  - **Output**: Plan batches + **hourly_timeline** (24 elementos) + ahorro vs baseline
  - **Timeline horaria incluye**: precio Prophet/hora, periodo tarifario (P1/P2/P3), proceso activo, batch, clima
- `GET /optimize/production/summary` - Resumen métricas optimización

### Dashboard & Monitoring (dashboard_router) ✅
- `GET /dashboard/complete` - Dashboard completo con SIAR + Prophet + ML predictions
- `GET /dashboard/summary` - Resumen rápido para visualización
- `GET /dashboard/alerts` - Alertas activas del sistema

**Ejemplo hourly_timeline**:
```json
{
  "hour": 10,
  "time": "10:00",
  "price_eur_kwh": 0.0796,
  "tariff_period": "P1",
  "tariff_color": "#dc2626",
  "temperature": 22.0,
  "humidity": 55.0,
  "climate_status": "optimal",
  "active_batch": "P01",
  "active_process": "Conchado Premium",
  "is_production_hour": true
}
```

**Periodos Tarifarios**:
- **P1 (Punta)**: 10-13h, 18-21h → Rojo (#dc2626)
- **P2 (Llano)**: 8-9h, 14-17h, 22-23h → Amarillo (#f59e0b)
- **P3 (Valle)**: 0-7h, resto → Verde (#10b981)

### Predictive Insights (Sprint 09 - insights_router) ✅
- `GET /insights/optimal-windows?days=N` - **Calculated** next N days optimal production windows
  - Uses Prophet forecasts to identify valle/punta hours
  - Classifies price quality (EXCELLENT/GOOD/FAIR/POOR)
  - Returns grouped windows with duration and savings estimates
- `GET /insights/ree-deviation` - **Calculated** D-1 vs Real price comparison (last 24h)
  - Compares Prophet forecasts with actual REE prices
  - Measures prediction reliability by tariff period
  - Identifies worst deviation hour
- `GET /insights/alerts` - **Calculated** predictive alerts (next 24-48h)
  - Price spike detection (>0.30 €/kWh)
  - Heat wave alerts (>28.8°C = SIAR P90 threshold)
  - Optimal window notifications (<0.10 €/kWh)
  - Production boost opportunities
- `GET /insights/savings-tracking` - Real savings vs baseline tracking
  - Historical vs actual consumption comparison
  - Cost reduction metrics
  - ROI calculation (1,661€/año demonstrated)

**Note**: All endpoints perform real calculations using Prophet forecasts, SIAR historical data, and current InfluxDB values. No static data returned.

### Gap Detection & Backfill (gaps_router) ✅
- `GET /gaps/summary` - Quick data status (REE + Weather gap hours)
- `GET /gaps/detect?days_back=N` - Detailed gap analysis with recommended strategy
- `POST /gaps/backfill?days_back=N` - Manual backfill execution (default: 10 days)
- `POST /gaps/backfill/auto?max_gap_hours=N` - Automatic intelligent backfill (default: 6.0h threshold)
- `POST /gaps/backfill/range` - Date range specific backfill with data_source filter

**Migration Note (Oct 7, 2025)**: Endpoints migrated to Clean Architecture router. Hooks updated to use query parameters instead of JSON body. See `docs/GAPS_ROUTER_MIGRATION.md`.

### Chatbot BI Conversacional (Sprint 11 - chatbot_router) ✅
- `POST /chat/ask` - Chatbot conversational endpoint
  - **Input**: `{"question": str}` (max 500 chars)
  - **Output**: `{"answer": str, "tokens": dict, "latency_ms": int, "cost_usd": float}`
  - **Rate limiting**: 20 requests/minute
  - **Features**: RAG local con keyword matching, context 600-1200 tokens
- `GET /chat/stats` - Usage statistics (total questions, tokens, cost)
- `GET /chat/health` - Chatbot service health check

**Example usage**:
```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuándo debo producir hoy?"}'
```

### System Monitoring
- `GET /dashboard` - Visual dashboard with interactive heatmap
- `GET /dashboard/complete` - Integrated dashboard JSON data
- `GET /scheduler/status` - APScheduler job status

### Health Monitoring (Sprint 13 - health_monitoring_router) ✅
- `GET /health-monitoring/summary` - System health overview
- `GET /health-monitoring/critical` - Critical nodes status
- `GET /health-monitoring/alerts` - Active alert summary
- `GET /health-monitoring/nodes` - Detailed node information
- `GET /health-monitoring/uptime/{hostname}` - Uptime metrics for specific node
- `GET /health-monitoring/logs?severity=INFO&event_type=all&page=1` - Event logs with pagination (20 events/page)

### Weekly Forecast System (✅ Sprint 06 Enhanced)
- **7-day Prophet predictions**: Real ML forecasts (not simulated)
- **Color-coded price zones**: Low (<0.10), Medium (0.10-0.20), High (>0.20 €/kWh)
- **Interactive tooltips**: Safari/Chrome/Brave compatible hover details
- **Model info display**: MAE, RMSE, R², last training timestamp
- **Real-time data**: Prophet predictions + AEMET/OpenWeatherMap weather
- **Production guidance**: Daily recommendations based on Prophet forecasts
- **Responsive design**: CSS Grid layout with dynamic color coding

## System Automation

### APScheduler Jobs (11 automated)
- **REE ingestion**: Every 5 minutes
- **Weather ingestion**: Every 5 minutes (hybrid AEMET/OpenWeatherMap)
- **ML training**: Every 30 minutes (direct sklearn)
- **ML predictions**: Every 30 minutes
- **Prophet forecasting**: Every hour at :30 (168h price predictions) ✅ NEW
- **Auto backfill**: Every 2 hours (gap detection & recovery)
- **Health monitoring**: Every 15 minutes
- **Token management**: Daily (AEMET renewal)
- **Weekly cleanup**: Sundays at 2 AM

## Important Notes

### Data Persistence
- All data persists through Docker bind mounts
- **InfluxDB**: `./docker/services/influxdb/data/`
- **ML Models**: `/app/models/` (pickle files)
- **System shutdown safe**: Data persists across restarts

### Historical Data Status
- REE Data: 42,578 records (2022-2025)
- Weather Current: 2,902 records AEMET/OpenWeatherMap hybrid
- SIAR Historical: 88,935 records (2000-2025)
- Backfill system: Auto-recovery every 2 hours

### SIAR Historical Data ETL
- Source: Sistema de Información Agroclimática para el Regadío (SIAR)
- Coverage: 25 years (2000-2025)
- Records: 88,935 weather observations
- Stations: J09_Linares (2000-2017), J17_Linares (2018-2025)
- Storage: `siar_historical` bucket
- Fields: 10 meteorological variables
- Script: `/scripts/test_siar_simple.py`

### SIAR ETL Technical Implementation Details

#### Unicode and Format Challenges Solved
```python
# Character-by-character cleaning for Unicode spaces
def clean_line(line):
    clean_chars = []
    for char in line:
        if char.isprintable() and (char.isalnum() or char in ';,/:.-'):
            clean_chars.append(char)
    return ''.join(clean_chars)

# Spanish decimal and date format handling
def safe_float(value):
    return float(str(value).replace(',', '.'))

# DD/MM/YYYY date parsing
date_obj = pd.to_datetime(fecha_str, format='%d/%m/%Y')
```

#### Station Identification Strategy
- **J09 Station**: Historical SIAR format (2000-2017)
- **J17 Station**: Modern SIAR format (2018-2025)
- **Automatic Detection**: Based on filename pattern
- **InfluxDB Tags**: `station_id`, `data_source=siar_historical`

#### Data Separation Architecture
- **Current Weather**: `energy_data` bucket (AEMET/OpenWeatherMap)
- **Historical Weather**: `siar_historical` bucket (SIAR system)
- **Benefit**: Clear data lineage for ML models and analysis

#### Execution Statistics
- **Files Processed**: 26 CSV files (100% success rate)
- **Processing Time**: ~3 minutes for 25 years of data
- **Error Handling**: Robust encoding detection (latin-1, iso-8859-1, cp1252, utf-8)
- **Batch Processing**: 100-record batches for optimal InfluxDB performance

### Remaining Tasks
- **REE 10-year expansion**: Use ESIOS API for 2015-2021 data (optional)
- **Data integration**: Connect SIAR historical data with ML models


## Machine Learning (Direct Implementation)

### Models
- **Energy Optimization**: RandomForestRegressor for energy score (0-100)
- **Production Classifier**: RandomForestClassifier (Optimal/Moderate/Reduced/Halt)
- **Training**: Direct sklearn + pickle storage (no external services)
- **Performance**: Energy R² = 0.89, Production accuracy = 90%

### Features (13 engineered)
- **Energy**: REE prices, tariff periods
- **Weather**: Temperature, humidity, pressure (hybrid sources)
- **Derived**: Production indices, comfort factors, optimization scores

### Predictions
```bash
# Energy optimization score
curl -X POST http://localhost:8000/predict/energy-optimization \
  -d '{"price_eur_kwh": 0.15, "temperature": 22, "humidity": 55}'

# Production recommendation
curl -X POST http://localhost:8000/predict/production-recommendation \
  -d '{"price_eur_kwh": 0.30, "temperature": 35, "humidity": 80}'
```

## Automatic Backfill System

### Gap Detection & Recovery
- **Automatic detection**: Identifies missing data gaps in REE and weather data
- **Smart strategy**: Current month (AEMET API) vs historical (SIAR system ETL)
- **Auto-recovery**: Every 2 hours via APScheduler
- **Alert system**: Automatic notifications for success/failure

### Key Endpoints
```bash
# Check data gaps
GET /gaps/summary

# Manual backfill
POST /gaps/backfill?days_back=7

# Automatic intelligent backfill
POST /gaps/backfill/auto?max_gap_hours=6.0
```


## Remote Access (Optional Tailscale Sidecar)

### Tailscale Integration
- **Ultra-lightweight**: Alpine container with Tailscale + nginx
- **SSL Automatic**: Tailscale ACME certificates with auto-renewal
- **Security isolation**: Only `/static/index.html` and API endpoints exposed externally
- **Dual access**: External (limited) + Local (complete) for development
- **Static architecture**: HTML/CSS/JS served from `/static/`, JavaScript fetches data from API

### Setup
```bash
# 1. Generate auth key at https://login.tailscale.com/admin/settings/keys
# 2. Configure .env with:
#    - TAILSCALE_AUTHKEY=tskey-auth-xxxxx
#    - TAILSCALE_DOMAIN=your-hostname.your-tailnet.ts.net
# 3. Build and deploy sidecar
docker compose build chocolate-factory
docker compose up -d chocolate-factory
```

### Access URLs
- **External dashboard**: `https://${TAILSCALE_DOMAIN}/` or `/dashboard` (redirects to `/static/index.html`)
- **Local dashboard**: `http://localhost:8000/static/index.html`
- **Local dev API**: `http://localhost:8000/docs` (complete API access)
- **JSON data**: `http://localhost:8000/dashboard/complete`

### Static Dashboard Architecture (v0.41.0)
```
/static/
├── index.html          # Main dashboard HTML (432 lines)
├── css/
│   └── dashboard.css   # Styles (826 lines)
└── js/
    └── dashboard.js    # Logic + API calls (890 lines)
```

**Flow:**
1. User accesses `/` or `/dashboard` → nginx redirects (302) → `/static/index.html`
2. Browser loads `index.html` → loads `css/dashboard.css` + `js/dashboard.js`
3. JavaScript fetches data from `/dashboard/complete` (JSON)
4. JavaScript renders cards dynamically with live data

**Migration from embedded (Sept 2025):**
- Before: 5,883 lines in `main.py` (HTML/CSS/JS embedded in Python strings)
- After: 3,734 lines in `main.py` (only API endpoints) + separate static files
- Reduction: 36.5% in main.py, cleaner separation of concerns


## Important Instructions

- **Placeholder usage**: Keep placeholders in mind to avoid false positives
- **Data freshness**: Always check backfill status when container starts (system not always running)
- **Gap recovery**: Use backfill when necessary to maintain data currency
- **API updates**: Ensure REE and AEMET data stays current (remember OpenWeather for 08:00-23:00)
- **Backfill strategy**: 48h intelligent strategy - OpenWeatherMap for gaps <48h, AEMET for ≥48h (see `docs/BACKFILL_SYSTEM.md`)

### Documentation Structure

**`docs/`** - Technical documentation (permanent)
- API references (API_REFERENCE.md, ENHANCED_ML_API_REFERENCE.md)
- Troubleshooting guide (TROUBLESHOOTING.md - consolidated)
- Backfill system (BACKFILL_SYSTEM.md - consolidated)
- Git workflow (GIT_WORKFLOW.md - consolidated)
- Migration docs (GAPS_ROUTER_MIGRATION.md)

**`.claude/`** - Claude Code context (sprints, rules, completion reports)
- Sprint documentation (`.claude/sprints/ml-evolution/`)
- Business rules (`.claude/rules/`)
- Completion reports (CLEAN_ARCHITECTURE_COMPLETED.md)
- Architecture decisions (architecture.md)

## Recent System Updates

### Intelligent Backfill Strategy (Oct 7, 2025)
Dual strategy based on gap age: OpenWeatherMap for gaps <48h, AEMET for gaps ≥48h.
Implementation: `services/backfill_service.py:183-393`
Documentation: `docs/BACKFILL_SYSTEM.md`

### AEMET Integration Fix (Sept 19, 2025)
Fixed imports to `SiarETL`, enhanced logging, proper error handling.
Result: Hybrid system operational.

### Static Dashboard Architecture Migration (Oct 4, 2025)
Extracted HTML/CSS/JS to `/static/` structure.
main.py: 5,883 → 3,734 lines
Nginx uses `envsubst` for `${TAILSCALE_DOMAIN}`

### BusinessLogicService Integration (Sept 26-27, 2025)
Location: `src/fastapi-app/services/business_logic_service.py`
Rules: `.claude/rules/business-logic-suggestions.md`
Humanizes ML recommendations for Spanish business context.

Technical fixes applied:
- Docker mount for `.claude` directory
- REE client context manager usage
- JavaScript variable naming conflicts
- Property path corrections
- Visual contrast improvements

---

## Working with Sprints

### Sprint Workflow

**Session Start**:
1. Read [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)
2. Identify active sprint
3. Review checklist in `SPRINT_XX_XXXXX.md`

**During Development**:
1. Update checkboxes in sprint document
2. Document issues
3. Use TodoWrite for task tracking
4. Commit incrementally

**Sprint Completion**:
1. Verify all checklist items complete
2. Update sprint status in sprint document
3. Update README sprint list
4. Update CLAUDE.md sprint history
5. Create git tag: `git tag -a sprint-XX -m "Sprint XX completed"`

### Sprint Documentation Structure

```
.claude/sprints/ml-evolution/
├── README.md
├── SPRINT_06_PRICE_FORECASTING.md
├── SPRINT_07_SIAR_TIMESERIES.md
├── SPRINT_08_HOURLY_OPTIMIZATION.md
├── SPRINT_09_PREDICTIVE_DASHBOARD.md
└── SPRINT_10_CONSOLIDATION.md
```

### Sprint Completion Criteria

- All deliverables implemented and tested
- System runs without errors
- Documentation updated (sprint file + CLAUDE.md)
- Metrics achieved
- No critical technical debt