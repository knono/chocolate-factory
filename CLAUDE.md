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

### ✅ Clean Architecture Refactoring (October 6, 2025)

The FastAPI application has been refactored following **Clean Architecture** principles:

```
src/fastapi-app/
├── main.py (76 lines)          # ✨ Ultra-slim entry point (was 3,838 lines)
├── main.bak (3,838 lines)      # Original monolithic file (backup)
├── pyproject.toml              # Python dependencies
│
├── api/                        # 🔷 HTTP Interface Layer (Routers + Schemas)
│   ├── routers/
│   │   ├── health.py          # System health endpoints
│   │   ├── ree.py             # REE electricity prices
│   │   ├── weather.py         # Weather data endpoints
│   │   ├── dashboard.py       # Dashboard data
│   │   ├── optimization.py    # Production optimization (Sprint 08)
│   │   ├── analysis.py        # SIAR historical analysis (Sprint 07)
│   │   ├── gaps.py            # Gap detection & backfill
│   │   ├── insights.py        # Predictive insights (Sprint 09) ✅
│   │   └── chatbot.py         # Chatbot BI conversacional (Sprint 11) ✅
│   └── schemas/
│       ├── common.py          # Shared Pydantic models
│       └── ree.py             # REE-specific schemas
│
├── domain/                     # 🔶 Business Logic Layer (Pure logic)
│   ├── energy/
│   │   └── forecaster.py     # Price forecasting logic
│   └── ml/
│       └── model_trainer.py  # ML validation logic
│
├── services/                   # 🔷 Application Layer (Orchestration)
│   ├── ree_service.py         # REE API + InfluxDB orchestration
│   ├── aemet_service.py       # AEMET API + InfluxDB
│   ├── weather_aggregation_service.py  # Multi-source weather
│   ├── dashboard.py           # Dashboard data consolidation
│   ├── siar_analysis_service.py  # SIAR historical analysis (Sprint 07)
│   ├── hourly_optimizer_service.py  # Production optimization (Sprint 08)
│   ├── predictive_insights_service.py  # Predictive insights (Sprint 09) ✅
│   ├── chatbot_service.py        # Claude Haiku API integration (Sprint 11) ✅
│   └── chatbot_context_service.py  # RAG local con keyword matching (Sprint 11) ✅
│
├── infrastructure/             # 🔷 Infrastructure Layer (External systems)
│   ├── influxdb/
│   │   ├── client.py         # InfluxDB wrapper with retry
│   │   └── queries.py        # Flux query builder
│   └── external_apis/
│       ├── ree_client.py     # REE API client (tenacity retry)
│       ├── aemet_client.py   # AEMET API client (token mgmt)
│       └── openweather_client.py  # OpenWeatherMap client
│
├── core/                       # 🔶 Core Utilities (Shared infrastructure)
│   ├── config.py              # Centralized settings (Pydantic)
│   ├── logging_config.py      # Structured logging
│   └── exceptions.py          # Custom exception hierarchy
│
├── tasks/                      # 🔷 Background Jobs (APScheduler)
│   ├── ree_jobs.py           # REE ingestion job
│   ├── weather_jobs.py       # Weather ingestion job
│   └── scheduler_config.py   # Job registration
│
└── dependencies.py             # Dependency injection container

**Refactoring Stats:**
- main.py: 3,838 → 76 lines (98% reduction)
- 6 routers created (41 Python files total)
- 100% Clean Architecture compliance
- Full backward compatibility maintained
```

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

## Development Status ✅ PRODUCTION SYSTEM

### 🚀 Recent Completion: Sprint 09 - Unified Predictive Dashboard ✅
**Status**: ✅ **COMPLETED** (October 7, 2025)
**Achievements**:
- Dashboard unificado: 5 tarjetas → 1 tarjeta "Dashboard Predictivo Completo"
- Widget ventanas óptimas: 7 días predicción Prophet + periodos tarifarios
- Análisis desviación REE: 87.5% accuracy, MAE ±0.0183 €/kWh
- Alertas predictivas: picos precio + oportunidades producción + clima extremo
- ROI tracking: 1,661€/año con comparativa baseline vs optimizado
- Integración Tailnet: endpoints `/insights/*` en nginx sidecar
**Details**: See [`.claude/sprints/ml-evolution/SPRINT_09_PREDICTIVE_DASHBOARD.md`](.claude/sprints/ml-evolution/SPRINT_09_PREDICTIVE_DASHBOARD.md)
**Sprint Roadmap**: [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)

### Sprint History (Completed)
- ✅ **Sprint 01-02**: Monolithic → Microservices migration
- ✅ **Sprint 03**: Service Layer + Repository pattern
- ✅ **Sprint 04**: SIAR ETL + 25 years historical data (88,935 records)
- ✅ **Sprint 05**: Unified Dashboard + BusinessLogicService
- ✅ **Sprint 06**: Prophet Price Forecasting + Dashboard Integration (Oct 3, 2025)
- ✅ **Sprint 07**: SIAR Historical Analysis (Oct 4, 2025)
  - Análisis correlaciones históricas: R²=0.049 (temp), R²=0.057 (humedad) con 88,935 registros
  - Patrones estacionales: Septiembre mejor (48.2%), Enero peor (0%)
  - Umbrales críticos: P90=28.8°C, P95=30.4°C, P99=32.2°C
  - 5 endpoints API: `/analysis/*` + `/forecast/aemet-contextualized`
  - Dashboard card con análisis histórico SIAR integrado
- ✅ **Sprint 08**: Hourly Production Optimization (Oct 6, 2025)
  - Timeline horaria 24h con precio Prophet + periodo tarifario + proceso activo
  - Clasificación periodos P1/P2/P3 con códigos de color
  - Vista granular: identificación cruces proceso/periodo
  - ROI 228k€/año (85.33% ahorro vs horario fijo)
  - Validación NaN/inf para JSON compliance
- ✅ **Sprint 09**: Unified Predictive Dashboard (Oct 7, 2025)
  - Dashboard unificado: Pronóstico Semanal + 4 widgets Sprint 09 en 1 tarjeta
  - Componentes: Ventanas Óptimas, REE Deviation, Alertas Predictivas, Savings Tracking
  - 4 endpoints `/insights/*`: optimal-windows, ree-deviation, alerts, savings-tracking
  - Tailnet integration: nginx sidecar bind mount template + envsubst processing
  - UX fix: fuente compacta 0.85rem + colores oscuros legibles sobre fondo blanco
  - Flujo temporal: presente → 24h → semana → mes
- ✅ **Sprint 11**: Chatbot BI Conversacional - Claude Haiku API (Oct 10, 2025)
  - Chatbot con Claude Haiku 3.5 integrado en dashboard
  - RAG local sin vector DB: keyword matching 7 categorías
  - Optimización latencia: asyncio.gather() (80% reducción HTTP calls)
  - Context optimizado: 600-1200 tokens/pregunta (6x vs mal diseñado)
  - Costo: €1.74-5.21/mes (uso normal/intensivo)
  - 3 endpoints `/chat/*`: ask, stats, health
  - Widget conversacional con quick questions
  - Tests: 100% passing (5/5 preguntas)
  - Métricas: 10-13s latencia, $0.0012/pregunta
  - Rate limiting: 20 requests/minuto con slowapi

### Infrastructure Sprints (Remaining)
- 🔴 **Sprint 10**: ML Consolidation & Cleanup
- 🔴 **Sprint 12**: Forgejo CI/CD

### Core Infrastructure (2-Container Architecture)
- **FastAPI Brain** (chocolate_factory_brain) - API + Dashboard + Direct ML
- **InfluxDB Storage** (chocolate_factory_storage) - Time series database
- **Tailscale Sidecar** (chocolate-factory) - HTTPS remote access (optional)

### Data Integration
- **REE API**: Real Spanish electricity prices 
- **Hybrid Weather**: AEMET + OpenWeatherMap (24/7 coverage)
- **Historical Data**: 25+ years weather records via SIAR system ETL (2000-2025)
- **Automatic Backfill**: Gap detection and recovery every 2 hours

### Machine Learning (Direct Implementation)
- **Prophet Forecasting**: 168-hour REE price prediction (MAE: 0.033 €/kWh, R²: 0.49)
- **Direct Training**: sklearn + Prophet + pickle storage (no external ML services)
- **Real-time Predictions**: Energy optimization + production recommendations + price forecasting
- **Automated ML**: Model retraining and predictions (hourly for Prophet, every 30 min for sklearn)

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
- `POST /models/train` - Train ML models directly
- `GET /models/status-direct` - Model health and performance
- `POST /predict/energy-optimization` - Energy optimization predictions
- `POST /predict/production-recommendation` - Production recommendations

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

### Historical Data Status (Updated Sept 17, 2025)
- **REE Data**: 42,578 records (2022-2025) including historical backfill
- **Weather Current**: 2,902 records from AEMET/OpenWeatherMap hybrid (Sept 2025)
- **✅ SIAR Historical**: **88,935 records** (2000-2025) - **COMPLETED**
- **REE Historical**: Comprehensive coverage 2022-2024
- **Backfill system**: Auto-detects and recovers gaps every 2 hours

### ✅ SIAR Historical Data ETL Solution (COMPLETED)
- **Data Source**: Sistema de Información Agroclimática para el Regadío (SIAR)
- **Coverage**: 25+ years (August 2000 - September 2025)
- **Total Records**: 88,935 weather observations
- **Stations**:
  - SIAR_J09_Linares (2000-2017): 62,842 records
  - SIAR_J17_Linares (2018-2025): 26,093 records
- **Storage**: Dedicated `siar_historical` bucket (separated from current weather)
- **Fields**: 10 meteorological variables (temperature, humidity, wind, precipitation)
- **Script**: `/scripts/test_siar_simple.py` - Processes all CSV files automatically
- **Format Handling**: Spanish dates (DD/MM/YYYY), comma decimals, Unicode cleaning
- **Data Quality**: Comprehensive 25-year dataset for ML training and analysis

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
- **Backfill strategy**: 48h intelligent strategy - OpenWeatherMap for gaps <48h, AEMET for ≥48h (see `docs/BACKFILL_48H_STRATEGY.md`)

### Documentation Structure

**`docs/`** - Technical documentation (permanent)
- API references (API_REFERENCE.md, ENHANCED_ML_API_REFERENCE.md)
- Troubleshooting guides (AEMET_TROUBLESHOOTING.md, DATA_PIPELINE_TROUBLESHOOTING.md)
- System guides (AUTOMATIC_BACKFILL_SYSTEM.md, GAP_DETECTION_STRATEGY.md)
- Migration docs (GAPS_ROUTER_MIGRATION.md, BACKFILL_48H_STRATEGY.md)

**`.claude/`** - Claude Code context (sprints, rules, completion reports)
- Sprint documentation (`.claude/sprints/ml-evolution/`)
- Business rules (`.claude/rules/`)
- Completion reports (CLEAN_ARCHITECTURE_COMPLETED.md)
- Architecture decisions (architecture.md)

## Recent System Updates

### ⚡ **Intelligent Backfill Strategy 48h (Oct 7, 2025)**
- **Issue**: AEMET API fails for gaps <48h (needs 24-48h to consolidate daily data)
- **Solution**: Dual strategy based on gap age
  - **Gaps <48h**: Use OpenWeatherMap (current data only, free tier limitation)
  - **Gaps ≥48h**: Use AEMET API (consolidated official data)
- **Implementation**: `services/backfill_service.py:183-393`
- **Result**: ✅ System automatically selects optimal data source based on gap age
- **Limitation**: OpenWeatherMap Free doesn't support historical data for gaps
- **Recommendation**: Accept 48h gap window OR implement hourly OWM preventive ingestion
- **Documentation**: `docs/BACKFILL_48H_STRATEGY.md`

### 🔧 **AEMET Integration Fix (Sept 19, 2025)**
- **Issue**: System was only using OpenWeatherMap, AEMET integration broken
- **Root cause**: Import errors + incorrect datosclima references + silent error handling
- **Solution**: Fixed imports to `SiarETL` + enhanced logging + proper error handling
- **Result**: ✅ AEMET official data restored, hybrid system fully operational
- **Status**: Weather gaps closed (0.0 hours), project value restored with official Spanish data

### 🔧 **Backfill Strategy Correction (Sept 23, 2025)**
- **Issue**: Code had incorrect "datosclima" references despite SIAR ETL implementation
- **Problem**: Backfill system referenced non-existent datosclima.es instead of using AEMET + SIAR
- **Solution**:
  - **Primary**: AEMET API for all gaps (days, weeks, months) - official Spanish weather data
  - **Fallback**: Manual SIAR download notification only for large gaps (>30 days) where AEMET fails
  - **Cleanup**: Removed all datosclima references from codebase
- **Result**: ✅ Simplified, reliable backfill using official AEMET data primarily
- **Status**: AEMET handles historical data effectively, SIAR reserved for extreme cases only

### 🏗️ **Static Dashboard Architecture Migration (Oct 4, 2025)**
- **Issue**: 5,883 lines in main.py with embedded HTML/CSS/JS difficult to maintain
- **Solution**: Extracted to `/static/` structure
  - `index.html` (432 lines) - Clean HTML without embedded styles/scripts
  - `css/dashboard.css` (826 lines) - All styles separated
  - `js/dashboard.js` (890 lines) - Logic + API calls to `/dashboard/complete`
- **Result**: ✅ main.py reduced to 3,734 lines (-36.5%), cleaner separation of concerns
- **Version**: Updated to v0.41.0
- **Tailscale fix**: Nginx now uses `envsubst` to process `${TAILSCALE_DOMAIN}` variable (requires `gettext` package)
- **Security**: No hardcoded Tailscale domains in tracked files (uses .env)
- **Routes**: `/` and `/dashboard` redirect to `/static/index.html`, JavaScript fetches data from API

### 🎨 **Dashboard Enhancement & BusinessLogicService Integration (Sept 26-27, 2025)**

#### **BusinessLogicService Implementation**
- **Purpose**: Bridge technical ML outputs with human-friendly recommendations
- **Location**: `src/fastapi-app/services/business_logic_service.py`
- **Rules Source**: `.claude/rules/business-logic-suggestions.md`
- **Key Features**:
  - Humanizes drastic ML recommendations (e.g., "halt_production" → "minimal production")
  - Provides context-aware Spanish business messages
  - Integrates with Enhanced ML predictions for gradual operational guidance

#### **Critical Technical Fixes Applied**
1. **BusinessLogicService Integration**:
   - **Docker Mount**: Added `./.claude:/app/.claude` to docker-compose.yml
   - **Path Fix**: Corrected rules file path to `/app/.claude/rules/business-logic-suggestions.md`
   - **Result**: ✅ Business rules now load correctly and generate human recommendations

2. **REE Client Connection Issues**:
   - **Problem**: `RuntimeError: Cannot send a request, as the client has been closed`
   - **Fix**: Corrected context manager usage in dashboard.py line 637
   - **Result**: ✅ REE API calls now work properly with `async with self.ree_client as ree:`

3. **JavaScript Variable Conflicts**:
   - **Problem**: `Identifier 'humanRec' has already been declared` causing dashboard failures
   - **Solution**: Renamed variables to unique names:
     - `renderUnifiedREEAnalysis`: `humanRecUnified`
     - `renderEnhancedMLData`: `humanRecEnhanced` and `humanRecDetails`
   - **Result**: ✅ JavaScript executes without syntax errors

4. **Historical Data Display Issues**:
   - **Problem**: Costo Total showing 0€ instead of 7,902€, Min/Max showing 0.0000
   - **Cause**: JavaScript accessing wrong data properties
   - **Fix**: Corrected property paths:
     - `analytics.total_cost` → `analytics.factory_metrics.total_cost`
     - `priceAnalysis.min_price` → `priceAnalysis.min_price_eur_kwh`
   - **Result**: ✅ Displays correct values: 7,902€, 0.0331-0.3543 €/kWh

5. **Visual Contrast Issues**:
   - **Problem**: White text on white background in metrics cards
   - **Fix**: Changed all color styles from `color: white` to `color: #333` in historical metrics
   - **Result**: ✅ Text fully visible with proper contrast

#### **Dashboard Unification Completed**
- **4 → 1 Card**: Combined location, system status, data sources, and factory state into single "Información del Sistema" card
- **Grid Layout**: 2x2 organized sections with color-coded categories
- **Information Preserved**: All original data maintained in compact, organized format

#### **Recommendation System Architecture**
```
Enhanced ML (Technical) → BusinessLogicService → Human-Friendly Output
     ↓                           ↓                      ↓
"halt_production"         Humanization Layer      "PRODUCCIÓN MÍNIMA"
"critical priority"       Business Rules          Gradual guidance
Raw ML scores            Context-aware            Spanish messages
```

#### **Quality Assurance Status**
- ✅ **No JavaScript Errors**: Console completely clean
- ✅ **Data Accuracy**: All metrics showing correct values
- ✅ **Visual Clarity**: All text properly visible
- ✅ **Dual Access**: Local + Tailscale working perfectly
- ✅ **Recommendation Consistency**: Unified source of truth implemented

---

## 📚 Working with Sprints (Sprint 06-10: ML Evolution)

### 🎯 Sprint Workflow for Claude Code

#### On Session Start
1. **Read Sprint Status**: Open [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)
2. **Identify Active Sprint**: Look for 🟡 PENDING or 🟡 EN PROGRESO status
3. **Open Sprint Document**: Read `SPRINT_XX_XXXXX.md` for current sprint details
4. **Review Checklist**: Check `- [ ]` items to see what's pending

#### During Development
1. **Update Checkboxes**: Mark completed items as `- [x]` in sprint document
2. **Document Issues**: Add to "Problemas Encontrados" section if exists
3. **Track Progress**: Use TodoWrite tool for granular task tracking
4. **Commit Incrementally**: Small commits with descriptive messages

#### On Sprint Completion
1. **Verify All Checklists**: Ensure all `- [ ]` are now `- [x]`
2. **Update Sprint Status**: Change 🟡 → ✅ COMPLETADO in sprint document
3. **Update README**: Mark sprint as ✅ in `.claude/sprints/ml-evolution/README.md`
4. **Update CLAUDE.md**: Move completed sprint to "Sprint History"
5. **Create Git Tag**: `git tag -a sprint-XX -m "Sprint XX completed"`
6. **Move to Next Sprint**: Update "Active Sprint" section to next sprint

### 📂 Sprint Documentation Structure

```
.claude/sprints/ml-evolution/
├── README.md                           # Sprint index and roadmap
├── SPRINT_06_PRICE_FORECASTING.md     # 🟡 ACTIVE
├── SPRINT_07_SIAR_TIMESERIES.md       # 🔴 NOT STARTED
├── SPRINT_08_HOURLY_OPTIMIZATION.md   # 🔴 NOT STARTED
├── SPRINT_09_PREDICTIVE_DASHBOARD.md  # 🔴 NOT STARTED
└── SPRINT_10_CONSOLIDATION.md         # 🔴 NOT STARTED
```

### ⚡ Quick Commands

```bash
# Check current sprint status
cat .claude/sprints/ml-evolution/README.md | grep "Sprint 0" | head -10

# View active sprint details
cat .claude/sprints/ml-evolution/SPRINT_06_PRICE_FORECASTING.md

# Update sprint status after completion
# Edit sprint file: change 🟡 → ✅ and update checkboxes
# Edit README.md: update sprint list status
# Edit CLAUDE.md: move sprint to completed section
```

### 🎯 Sprint Philosophy

1. **No Service Interruption**: Each sprint adds functionality without breaking existing features
2. **Incremental Delivery**: Every sprint ends with 100% functional system
3. **Context Preservation**: `.claude/sprints/` maintains state between sessions
4. **Progressive Cleanup**: Remove legacy code only when new code is proven stable

### 📊 Sprint Completion Criteria

A sprint is **COMPLETADO** when:
- ✅ All deliverables implemented and tested
- ✅ System runs without errors
- ✅ Documentation updated (sprint file + CLAUDE.md)
- ✅ Success metrics achieved
- ✅ No critical technical debt introduced

---

## 🔧 Sprint 06 Quick Start (Current Active)

**Goal**: Implement LSTM/Prophet for REE price prediction (168h forecast)

**Key Files to Create/Modify**:
- `src/fastapi-app/services/price_forecasting_service.py` (NEW)
- `src/fastapi-app/main.py` (add endpoints + APScheduler job)
- Dashboard heatmap integration

**Success Metrics**:
- MAE < 0.02 €/kWh
- Heatmap showing real predictions
- API `/predict/prices/weekly` working

**See Full Details**: [`.claude/sprints/ml-evolution/SPRINT_06_PRICE_FORECASTING.md`](.claude/sprints/ml-evolution/SPRINT_06_PRICE_FORECASTING.md)