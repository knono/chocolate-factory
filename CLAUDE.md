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
├── api/                        # 🔷 HTTP Interface (12 routers, 45 endpoints)
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
├── services/                   # 🔷 Orchestration (20 active files)
│   ├── Core: ree_service, aemet_service, weather_aggregation_service, dashboard
│   ├── Data: siar_etl, gap_detector, backfill_service, data_ingestion
│   ├── Features: chatbot_service, tailscale_health_service, health_logs_service
│   ├── Supporting: scheduler, ml_models, etc.
│   ├── Compatibility: ml_domain_compat, recommendation_domain_compat, analysis_domain_compat
│   └── legacy/                 # 7 archived files (2 root + 4 in initialization/)
│
├── infrastructure/             # 🔷 External Systems (8 files)
│   ├── influxdb/client.py, queries.py
│   └── external_apis/ree_client.py, aemet_client.py, openweather_client.py
│
├── core/                       # 🔶 Utilities (4 files)
│   ├── config.py, logging_config.py, exceptions.py
│
├── tasks/                      # 🔷 Background Jobs (6 files)
│   ├── scheduler_config.py, ree_jobs.py, weather_jobs.py, ml_jobs.py,
│   ├── health_monitoring_jobs.py, sklearn_jobs.py (Sprint 14)
│
└── tests/                      # ~11 test files
```

**Final Metrics:**
- **12 routers** (45 endpoints)
- **20 services** (down from 30 - legacy archived)
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

### Recent Completion: Sprint 18 - Tailscale Auth + Telegram Alerting
**Status**: COMPLETED (November 2-3, 2025)
**Documentation**: [`.claude/sprints/infrastructure/SPRINT_18_TAILSCALE_AUTH_ALERTING.md`](.claude/sprints/infrastructure/SPRINT_18_TAILSCALE_AUTH_ALERTING.md)

Implemented:
- Tailscale auth middleware (403 lines): admin vs viewer roles, `/vpn` protected
- Telegram alerts (190 lines): 5 alert types, 15min rate limiting
- Configuration: `TAILSCALE_ADMINS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Uvicorn fix: `--proxy-headers --forwarded-allow-ips 192.168.100.0/24`
- Test endpoint: `POST /test-telegram`
- Unit tests: 12 test cases (252 lines)

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
- Sprint 06: Prophet Price Forecasting (Oct 3, 2025 - Nov 10, 2025)
  - R² optimizado: 0.49 (inicial) → 0.48 (walk-forward validation Nov 2025)
  - Walk-forward validation: train hasta Oct 31, test Nov 1-10 (datos no vistos)
  - Eliminación lags autoregressivos (evita overfitting temporal)
  - Fourier orders: daily=8, weekly=5, yearly=8 (punto óptimo)
  - Features exógenas: 7 (holidays ES, peak/valley hours, seasons)
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
  - Result: Deterministic scoring function (circular - predicts own formula)
  - Note: Not predictive ML, rule-based optimization scoring
  - New endpoints: POST /predict/train/hybrid
  - Prophet router integrated: GET /predict/prices/weekly, /hourly, /train, /status
- Sprint 15: Architecture Cleanup & Consolidation (Oct 29, 2025)
  - API client duplication resolved (3 files consolidated in infrastructure/)
  - Services layer reduced: 30 → 20 active files
  - Legacy archived: 7 files in services/legacy/
  - Domain layer developed: 14 files with proper business logic
  - main.py bug fixed: "main_new:app" → "main:app"
  - dependencies.py documented (DI container with @lru_cache())
  - sklearn_jobs.py added to tasks layer
- Sprint 16: Documentation Integrity & Transparency (Oct 30, 2025)
  - ML claims corrected: R² 0.9986 removed, labeled as deterministic scoring
  - ROI 1,661€ labeled as theoretical estimate (not measured)
  - MLflow references removed from TROUBLESHOOTING.md (57 lines)
  - Prophet training frequency corrected: 30min → 24h (accurate)
  - Job count corrected: 13+ → 7 (verified from scheduler_config.py)
  - Endpoint paths fixed: /models/* → /predict/prices/models/*
  - ML_ARCHITECTURE.md: Added 87-line "Limitaciones y Disclaimers" section
  - 20+ disclaimers added (ML, testing, security, monitoring limitations)
- Sprint 17: Test Coverage + Business Rules (Oct 30, 2025)
  - Fase 1: Test Coverage
    - Coverage: 19% → 32%
    - Tests: 102 → 134 (+32)
    - Código: +880 líneas
    - Archivos: test_scheduler.py, test_data_ingestion.py, test_api_clients.py
    - Coverage servicios: backfill 53%, gap_detector 66%, API clients 23-26%
  - Fase 2: Business Rules Documentation
    - Creado: machinery_specs.md (98 líneas, 4 máquinas)
    - Expandido: production_rules.md (quality control, failure recovery)
    - Creado: optimization_rules.md (113 líneas, Prophet integration)
  - Tests E2E: 91 passing, 11 failing (performance/resilience)
  - Duración: 1 día
- Sprint 18: Tailscale Auth + Telegram Alerting (Nov 2-3, 2025)
  - Middleware auth: admin/viewer roles, Tailscale IP detection (100.64.0.0/10)
  - Telegram alerts: REE failures, backfill, gaps >12h, nodes offline >5min, ML failures
  - Rate limiting: 15min per topic
  - Uvicorn proxy trust: `--proxy-headers --forwarded-allow-ips`
  - SOPS integration: snake_case + UPPERCASE variables
  - Tests: 12 unit tests (auth middleware)
- Sprint 19: Test Coverage Expansion (Nov 4, 2025) - PARCIAL
  - Fase 1: Backfill tests 11/14 passing (79%) - bloqueado por mock REEAPIClient
  - Fase 2: Gap detector tests 10/10 passing (100%) - coverage 66%→74%
  - Fase 3: API clients tests 1/10 passing (10%) - bloqueado por httpx AsyncClient mocking
  - Tests creados: 34 (backfill 14, gap 10, API clients 10)
  - Tests passing: 22/34 (65%)
  - Bloqueadores técnicos: context manager async mocking complejo
- Sprint 20: Observability & Model Monitoring (Nov 5, 2025) - COMPLETADO
  - Fase 1: Tailscale logs avanzados (COMPLETADO)
    - Endpoints socat: /netcheck, /ping/<host>, /debug
    - TailscaleHealthService: ping_peer, get_connection_stats, get_network_diagnostics
    - InfluxDB: tailscale_connections measurement (latency, traffic, relay)
    - APScheduler: collect_connection_metrics (every 5 min)
    - Telegram alerts: latency >100ms, relay usage
    - API: GET /health-monitoring/connection-stats/{hostname}, /latency-history/{hostname}
  - Fase 2: Structured JSON logging (COMPLETADO Nov 5)
    - StructuredFormatter con user context (Tailscale auth)
    - GET /logs/search (filtros: level, hours, limit, module)
    - Config: LOG_FORMAT_JSON (default False)
    - File logging: /app/logs/fastapi.log
    - Tests: 11/11 passing
  - Fase 3: Model monitoring (COMPLETADO Nov 5)
    - ModelMetricsTracker: CSV tracking (/app/models/metrics_history.csv)
    - Baseline calculation: median over window (30 entries)
    - Degradation detection: MAE >2x, R² <50%
    - Telegram alerts: prophet_model_degradation (WARNING)
    - API: GET /models/metrics-history (filtros: model_name, limit)
    - Tests: 18/18 passing
  - Tests totales: 29/29 passing (Fase 2: 11, Fase 3: 18)
  - Docs: ML_MONITORING.md creado
  - Coverage: 33%
- Sprint 21: Gas Generation Feature (Dec 11, 2025) - COMPLETED
  - Combined Cycle (gas) generation as Prophet regressor
  - Walk-forward validation (10 iter, 90d train, 168h test):
    - MAE: +27.4% improvement (gas wins 9/10 iterations)
    - R²: +57.6pp improvement (-0.20 → 0.37)
  - New components:
    - `gas_generation_service.py`: query/write/detect_gaps
    - `gas_generation_jobs.py`: daily ingestion at 11:00 AM
    - `ree_client.py`: +`get_generation_structure()` (time_trunc=day)
    - `scheduler_config.py`: job registered (10 jobs total)
  - InfluxDB: measurement `generation_mix`, tag `source=ree_generation`
  - Backfill: 1107 records (Dec 2022 → Dec 2025)
  - Prediction: uses last known value for future 168h

### Core Infrastructure
- **FastAPI Brain** (chocolate_factory_brain) - API + Dashboard + Direct ML
- **InfluxDB Storage** (chocolate_factory_storage) - Time series database
- **Tailscale Sidecar** (optional) - HTTPS remote access via Tailnet

### Data Integration
- **REE API**: Real Spanish electricity prices 
- **Hybrid Weather**: AEMET + OpenWeatherMap (24/7 coverage)
- **Historical Data**: 25+ years weather records via SIAR system ETL (2000-2025)
- **Automatic Backfill**: Gap detection and recovery every 2 hours

### Machine Learning & Decision Support Systems
- **Prophet Forecasting + Inercia 3h**: 168-hour REE price prediction ✅ **Real ML Puro**
  - **Modelo híbrido** (Dic 10, 2025): Prophet + corrección por inercia
    - Prophet: captura estacionalidad (hora, día, semana)
    - Inercia 3h: corrige nivel con media últimas 3h reales
    - Walk-forward (7 días, 157 pred): MAE 0.030→0.023 (+24%), R² 0.33→0.61
  - Configuración: Fourier 8/5/8, changepoint_prior_scale 0.08, sin lags
  - Features: is_peak_hour, is_valley_hour, is_winter, is_summer
  - Validation scripts: `scripts/test_prophet_inertia_walkforward.py`
- **Sistemas de Scoring Determinístico** (sklearn RandomForest como motor, Nov 12, 2025)
  - **Energy Optimization Scoring System**: Scoring 0-100 basado en reglas de negocio
    - Implementación: RandomForestRegressor (captura interacciones no lineales)
    - R² test 0.983, train 0.996, diff 0.013 (estabilidad técnica)
    - **Targets circulares**: Calculados con fórmula determinística desde inputs (NO predictivo)
  - **Production Recommendation System**: Clasificación Optimal/Moderate/Reduced/Halt
    - Implementación: RandomForestClassifier (captura interacciones no lineales)
    - Accuracy test 0.928, train 0.998, diff 0.070 (estabilidad técnica)
    - **Targets circulares**: Thresholds de fórmula determinística (NO predictivo)
  - Cross-validation: Energy R² 0.982±0.003, Production Acc 0.947±0.026 (stable)
  - Features: 10 (5 base + 5 machinery-specific from real equipment specs)
  - Machinery features: power_kw, thermal_efficiency, humidity_efficiency, estimated_cost, tariff_multiplier
  - Data: REE 619 records (90 días) + machinery specs (Conchado 48kW, Refinado 42kW, Templado 36kW, Mezclado 30kW)
  - Validation script: `scripts/validate_sklearn_overfitting.py`
  - **Naturaleza**: Motores de reglas de negocio (business rules engines), NO ML predictivo
- **Direct Training**: Prophet ML + sklearn scoring systems + pickle storage (no external services)
- **Feature Engineering**: 10 features total
  - Base (5): price, hour, dow, temperature, humidity
  - Machinery (5): machine_power_kw, thermal_efficiency, humidity_efficiency, estimated_cost, tariff_multiplier
  - Source: `domain/machinery/specs.py` + REE API + AEMET/OpenWeatherMap
- **Real-time Analysis**: Energy optimization scoring + production recommendations + Prophet price forecasting
- **Automated Training**: Scoring systems every 30 min, Prophet ML daily
- **Model Monitoring**: CSV tracking with degradation detection (Sprint 20) - **Solo Prophet ML**
  - Metrics logged: MAE, RMSE, R², samples, duration
  - Baseline: median over 30 entries
  - Alerts: MAE >2x baseline, R² <50% baseline
  - Storage: /app/models/metrics_history.csv
- **ROI Tracking**: 11,045€/año ahorro energético (estimación valle-prioritized vs baseline)
- **Testing**: 186 tests total, 174 passing (93%), coverage ~33% (Sprints 17-20)
- **Documentation**: `docs/ML_ARCHITECTURE.md` (Sprint 10), `docs/ML_MONITORING.md` (Sprint 20)

### Operations
- **APScheduler**: 13+ automated jobs (ingestion, ML, sklearn training, Prophet forecasting, backfill, health monitoring)
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

### Scoring Systems Operations (sklearn)
- `POST /predict/energy-optimization` - Energy optimization score (0-100) - **Sistema de scoring determinístico**
- `POST /predict/production-recommendation` - Production class (Optimal/Moderate/Reduced/Halt) - **Sistema de recomendación determinístico**
- `POST /predict/train` - Train scoring systems manually (energy + production) - **90 días REE data**
- `POST /predict/train/hybrid` - Hybrid training: Phase 1 SIAR (88k records) + Phase 2 REE fine-tune (deprecated)

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
  - ROI calculation (11,045€/año valle-prioritized vs baseline)

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

### Telegram Alerting (Sprint 18) ✅
- `POST /test-telegram` - Test alert endpoint (dev + prod)
  - Sends test message to configured Telegram chat
  - Verifies bot token, chat ID, and API connectivity
  - Returns: status, telegram_enabled, timestamp

### Weekly Forecast System (✅ Sprint 06 Enhanced)
- **7-day Prophet predictions**: Real ML forecasts (not simulated)
- **Color-coded price zones**: Low (<0.10), Medium (0.10-0.20), High (>0.20 €/kWh)
- **Interactive tooltips**: Safari/Chrome/Brave compatible hover details
- **Model info display**: MAE, RMSE, R², last training timestamp
- **Real-time data**: Prophet predictions + AEMET/OpenWeatherMap weather
- **Production guidance**: Daily recommendations based on Prophet forecasts
- **Responsive design**: CSS Grid layout with dynamic color coding

## System Automation

### APScheduler Jobs (9 automated)
- **REE ingestion**: Every 5 minutes
- **Weather ingestion**: Every 5 minutes (hybrid AEMET/OpenWeatherMap)
- **sklearn ML training**: Every 30 minutes (energy + production scoring models) ✅ Sprint 14
- **Prophet forecasting**: Every 24 hours (168h price predictions) ✅ Sprint 06
- **Health monitoring**: Every 5 minutes (metrics collection) ✅ Sprint 13
- **Critical nodes check**: Every 2 minutes ✅ Sprint 13
- **Status logging**: Every hour ✅ Sprint 13
- **Gap detection**: Every 2 hours (Telegram alerts) ✅ Sprint 18
- **Connection metrics**: Every 5 minutes (latency, traffic, relay) ✅ Sprint 20

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


## Machine Learning & Decision Support Systems

### Prophet ML (Real Predictive ML) ✅
- **Model**: Facebook Prophet time series forecasting
- **Purpose**: 168-hour electricity price prediction
- **Performance**: MAE 0.031 €/kWh, R² 0.54 (walk-forward validation Nov 27, 2025)
- **Validation**: Walk-forward on unseen data (Nov 17-27, 2025) - 288 samples
- **Generalization**: Test R² 0.58 → Walk-forward R² 0.54 (degradación 7% - excelente)
- **Training**: Daily automated retraining
- **Storage**: Pickle serialization

### Sistemas de Scoring Determinístico (sklearn, Nov 12, 2025)
- **Energy Optimization Scoring System**: RandomForestRegressor scoring 0-100
  - R²: 0.983 test (estabilidad técnica, NO predictiva)
  - Training samples: 619 (90 días REE data, 100% real)
  - **Naturaleza**: Motor de reglas de negocio basado en especificaciones técnicas
  - **Targets circulares**: Formula determinística (price + temp + humidity + machinery specs)
- **Production Recommendation System**: RandomForestClassifier (Optimal/Moderate/Reduced/Halt)
  - Accuracy: 0.928 test (estabilidad técnica, NO predictiva)
  - Training samples: 619 (90 días REE data, 100% real)
  - **Naturaleza**: Sistema de clasificación basado en thresholds de reglas de negocio
  - **Targets circulares**: Thresholds de fórmula determinística
- **Training**: Direct sklearn + pickle storage (no external services)
- **Integration**: `domain/machinery/specs.py` - Real equipment specifications

### Features (10 total)
- **Base (5)**: price_eur_kwh, hour, day_of_week, temperature, humidity
- **Machinery (5)**: machine_power_kw, thermal_efficiency, humidity_efficiency, estimated_cost_eur, tariff_multiplier
- **Sources**: REE API, AEMET/OpenWeatherMap, machinery specs

### Scoring Requests (Determinístico)
```bash
# Energy optimization score (deterministic scoring system)
curl -X POST http://localhost:8000/predict/energy-optimization \
  -d '{"price_eur_kwh": 0.15, "temperature": 22, "humidity": 55}'

# Production recommendation (deterministic classification system)
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
- cuando vayas a hacer un docker build --no-cache por favor

---

## System Limitations & Disclaimers

### Machine Learning
- **Prophet Forecasting**: Real ML puro con R² 0.54 walk-forward (46% variance unexplained, 54% explained) ✅
  - Generalización validada: degradación test→walk-forward solo 7% (NO overfitting)
- **Sistemas de Scoring (sklearn)**: Motores de reglas de negocio determinísticos, NO ML predictivo
  - Energy Optimization: Scoring 0-100 basado en fórmula (targets circulares)
  - Production Recommendation: Clasificación basada en thresholds (targets circulares)
  - Uso de RandomForest: Solo para capturar interacciones no lineales entre inputs
- **Model Monitoring**: Solo Prophet ML (scoring systems no aplican)
- **A/B Testing**: Not implemented

### Testing & Quality
- **Test Coverage**: 33% (67% code untested)
- **Tests**: 168 total, 156 passing (93%), 12 failing (async mocking issues)
- **Recommended**: 40%+ coverage for production
- **Gaps**: Async context manager mocking, integration tests

### Security Model
- **Network Level**: Tailscale VPN zero-trust mesh (WireGuard encrypted) ✅
- **Application Level**: No authentication/authorization at API endpoints
- **Access Control**:
  - Localhost: Full access (development)
  - Tailscale network: Full access (authorized devices only)
  - Public internet: No access (not exposed)
- **Rate Limiting**: Global per-endpoint, not per-user
- **Deployment Model**: Private infrastructure with network-level security

### Monitoring & Observability
- **Health Checks**: Service availability only
- **Alerting**: Not implemented (manual monitoring)
- **Logs**: Collected, not centralized or analyzed
- **Suitable For**: Development/demo, small-scale private deployments

### Data & Metrics
- **ROI (11,045€/year)**: Estimación valle-prioritized vs baseline (35.7% ahorro), NOT measured from real production
- **Data Volumes**: Verifiable from InfluxDB (42k REE, 88k SIAR records as of Nov 2025)
- **Prophet Metrics**: Walk-forward validado Nov 27, 2025 (MAE 0.031, R² 0.54, Coverage 95.49%)
  - Test set R² 0.58 | Walk-forward R² 0.54 | Degradación 7% (NO overfitting)
- cuando documentes, hazlo de forma austera y directa; sin artefactos de marketing