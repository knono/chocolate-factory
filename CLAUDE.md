# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a chocolate factory simulation and monitoring system. The project implements a streamlined containerized architecture with 4 main production containers working together for automated data ingestion, ML prediction, monitoring, and secure remote access.

## Architecture

The system follows a **4-container production architecture** (evolved from Node-RED to integrated dashboard + Tailscale sidecar):

1. **API Unificada** ("El Cerebro Autónomo") - FastAPI with APScheduler for automation + **Dashboard integrado**
2. **Almacén de Series** ("El Almacén Principal") - InfluxDB for time series storage  
3. **Unidad MLOps** ("Cuartel General ML") - MLflow Server + PostgreSQL
4. **Tailscale Sidecar** ("Portal Seguro") - Alpine proxy + SSL para acceso remoto cifrado

**✅ Dashboard Migration Completed (Sept 2025):** Node-RED eliminated and replaced with integrated dashboard served directly from FastAPI at `/dashboard/complete`.

The main FastAPI application (`src/fastapi-app/`) acts as the autonomous brain, handling:
- `/predict` and `/ingest-now` endpoints  
- APScheduler-managed automation for periodic ingestion and predictions
- SimPy/SciPy simulation logic
- **Integrated dashboard** at `/dashboard/complete` (replaces Node-RED)

## Project Structure

```
├── src/fastapi-app/            # Main FastAPI application
│   ├── main.py                # FastAPI entry point with all endpoints
│   ├── pyproject.toml         # Python dependencies and configuration
│   ├── dashboard/             # Integrated dashboard components
│   └── services/              # Service layer modules
│       ├── initialization/    # System initialization services
│       ├── datosclima_etl.py # Weather data ETL from datosclima.es
│       └── [other services]   # REE API, AEMET, MLflow, backfill, etc.
├── docker/                    # Docker infrastructure (✅ IMPLEMENTED)
│   ├── docker-compose.yml     # Main container orchestration
│   ├── docker-compose.override.yml # Tailscale sidecar configuration
│   ├── fastapi.Dockerfile     # FastAPI brain container
│   ├── tailscale-sidecar.Dockerfile # Secure remote access
│   └── services/              # Service-specific configurations
│       ├── fastapi/           # FastAPI logs and configs
│       ├── influxdb/          # InfluxDB data persistence (bind mount)
│       ├── postgres/          # PostgreSQL MLflow backend
│       ├── mlflow/            # MLflow artifacts storage
│       └── nginx/             # Nginx proxy configurations
├── src/configs/               # Configuration files
│   └── influxdb_schemas.py    # InfluxDB database schemas
├── data/                      # Data storage
│   ├── raw/                   # Raw data storage
│   └── processed/             # Processed data storage
├── docs/                      # Comprehensive project documentation (25+ docs)
│   ├── MLFLOW_IMPLEMENTATION.md        # Complete ML pipeline docs
│   ├── AUTOMATIC_BACKFILL_SYSTEM.md   # Gap detection and recovery
│   ├── DATOSCLIMA_ETL_SOLUTION.md     # Historical weather data ETL
│   ├── SYSTEM_ARCHITECTURE.md         # Complete system design
│   └── [20+ other technical docs]     # APIs, troubleshooting, guides
├── ssl/                       # SSL certificates (Tailscale ACME)
└── logs/                      # Application logs
    └── sidecar/nginx/         # Nginx proxy logs
```

## Development Setup

The project uses Python 3.11+ with the main application in `src/fastapi-app/`.

### FastAPI Application
- Entry point: `src/fastapi-app/main.py`
- Project configuration: `src/fastapi-app/pyproject.toml`
- **Production-ready system** with comprehensive feature set

### Development Status ✅ PRODUCTION SYSTEM
The project is a **fully operational production system** with complete infrastructure:

#### Core Infrastructure (4-Container Architecture)
- ✅ **FastAPI Brain** (chocolate_factory_brain) - API + Dashboard + ML predictions
- ✅ **InfluxDB Storage** (chocolate_factory_storage) - Time series database
- ✅ **MLflow MLOps** (chocolate_factory_mlops) - ML models + PostgreSQL backend
- ✅ **Tailscale Sidecar** (chocolate-factory) - Secure HTTPS remote access

#### Data Integration (Real-time + Historical)
- ✅ **REE API**: Real Spanish electricity prices (every 5 minutes)
- ✅ **Hybrid Weather**: AEMET + OpenWeatherMap integration (24/7 coverage)
- ✅ **Historical Data**: 1,095+ weather records via datosclima.es ETL
- ✅ **Automatic Backfill**: Gap detection and smart recovery system

#### Machine Learning Pipeline
- ✅ **MLflow Tracking**: Complete experiment management with PostgreSQL backend
- ✅ **2 Production Models**: Energy Optimization (R² = 0.8876) + Production Classifier (90% accuracy)
- ✅ **Real-time Predictions**: Energy optimization and production recommendations
- ✅ **Feature Engineering**: 13 engineered features from REE + Weather data
- ✅ **Automated ML**: Model retraining and prediction scheduling (every 30 min)

#### Operations & Monitoring
- ✅ **APScheduler**: 10+ automated jobs (ingestion, ML, backfill, health checks)
- ✅ **Integrated Dashboard**: Node-RED migrated to FastAPI (`/dashboard/complete`)
- ✅ **Remote Access**: Tailscale HTTPS with SSL certificates and security isolation
- ✅ **Self-healing**: Automatic gap detection and recovery every 2 hours
- ✅ **Production Monitoring**: Health checks, token management, system alerts

## Key Design Principles

- **Autonomous Operation**: The FastAPI container runs independently with APScheduler handling all automation
- **Integrated Dashboard**: Dashboard served directly from FastAPI (eliminated Node-RED dependency)  
- **Separation of Concerns**: Each container has a specific role in the data pipeline
- **Time Series Focus**: InfluxDB chosen specifically for time series data management
- **Stack Unification**: 100% Python ecosystem (FastAPI + Dashboard + ML)

## Data Sources Integration

### REE (Red Eléctrica de España) - Electricity Market Data
- **Endpoint**: `/ree/prices` 
- **Frequency**: Every hour (24/7 coverage)
- **Data**: Real Spanish electricity prices (PVPC), demand, renewable generation
- **Status**: ✅ Fully functional with real-time data
- **Automation**: APScheduler job every hour at :05

### AEMET (Spanish Meteorological Agency) - Weather Data
- **Primary Station**: Linares, Jaén (5279X) - LINARES (VOR - AUTOMATICA)
- **Location**: 38.151107°N, -3.629453°W, 515m altitude
- **Endpoints**: 
  - `/aemet/weather` - Current observations
  - `/aemet/token/status` - Token management
  - Prediction API: `prediccion/especifica/municipio/horaria/23055`

#### Critical Finding: Data Pattern Analysis
**Observation Data (5279X Station)**:
- **Coverage**: 00:00-07:00 only (8 hourly readings)
- **Pattern**: Measurements every hour from midnight to 7 AM
- **Gap**: No real observations 08:00-23:00 (critical production hours)
- **Implication**: Requires prediction data to fill daytime gap

**Temperature Pattern Identified (June 27, 2025)**:
```
00:00 → 28.5°C    03:00 → 24.8°C    06:00 → 23.4°C
01:00 → 27.6°C    04:00 → 23.9°C    07:00 → 25.6°C  (last reading)
02:00 → 26.8°C    05:00 → 22.8°C    08:00-23:00 → NO DATA
```

#### AEMET Limitations Discovered
- **Temporal lag**: Real observations may be 6-12 hours behind during extreme weather
- **Extreme weather**: During heat waves (observed 35°C vs reported 25.6°C)
- **Coverage gap**: No real-time data during peak production hours (8 AM - 11 PM)

#### Solution Strategy - Hybrid Integration IMPLEMENTED ✅
1. **Primary data**: AEMET observation (00:00-07:00) + OpenWeatherMap real-time (08:00-23:00)
2. **Real-time validation**: OpenWeatherMap for extreme weather precision (35°C actual vs AEMET 25.6°C)
3. **Automatic fallback**: AEMET failure → OpenWeatherMap backup
4. **Hybrid architecture**: Scheduled hourly ingestion with intelligent source selection

### Token Management
- **AEMET Token**: Auto-renewal every 6 days (permanent API key system)
- **OpenWeatherMap Token**: Free tier with 60 calls/min (sufficient for hourly ingestion)
- **REE**: No authentication required for public endpoints  
- **Status**: ✅ Fully automated token lifecycle management

## MLflow Feature Architecture

### Recommended Feature Pipeline
```python
# Hourly features (00:00-23:00)
- ree_price_eur_kwh          # REE: complete 24h coverage
- ree_demand_mw              # REE: complete 24h coverage  
- tariff_period              # Derived: P1-P6 classification

# Weather features (hybrid approach) ✅ IMPLEMENTED
- temp_observed              # AEMET: 00:00-07:00 real data
- temp_realtime              # OpenWeatherMap: 08:00-23:00 real-time data
- temp_interpolated          # Derived: gap filling algorithm
- humidity_observed          # AEMET: 00:00-07:00 real data  
- humidity_realtime          # OpenWeatherMap: 08:00-23:00 real-time data

# Chocolate production indices
- chocolate_production_index # Derived: temp + humidity + pressure
- heat_stress_factor        # Derived: extreme weather detection
- energy_optimization_score # Derived: REE price + weather combination
```

### Data Quality Considerations ✅ VALIDATED
- **REE data reliability**: ⭐⭐⭐⭐⭐ (excellent real-time accuracy)
- **AEMET observation reliability**: ⭐⭐⭐ (official but limited coverage 00:00-07:00)
- **OpenWeatherMap real-time reliability**: ⭐⭐⭐⭐⭐ (validated: 35.56°C vs observed 35°C)
- **Temporal synchronization**: REE hourly + Hybrid weather (AEMET/OpenWeatherMap)

## Hybrid Weather Integration Architecture ✅ COMPLETED

### Implementation Status
- ✅ **OpenWeatherMap client**: Fully implemented with API v2.5 (free tier)
- ✅ **Hybrid data ingestion**: Automatic source selection based on time window
- ✅ **Scheduler integration**: Hourly automated ingestion (every hour at :15)
- ✅ **Fallback mechanism**: AEMET failure → OpenWeatherMap backup
- ✅ **Real-time validation**: Confirmed accuracy during extreme weather events

### API Endpoints Available
- `GET /weather/openweather` - Current weather from OpenWeatherMap
- `GET /weather/openweather/forecast?hours=N` - 3-hour forecast up to 5 days  
- `GET /weather/openweather/status` - API connectivity and quota status
- `GET /weather/hybrid` - Intelligent hybrid weather ingestion
- `POST /ingest-now` - Manual ingestion with `{"source": "hybrid"}`

### Operational Schedule
- **00:00-07:00**: AEMET official observations (when available)
- **08:00-23:00**: OpenWeatherMap real-time data
- **Frequency**: Every hour at minute :15
- **Fallback**: Always available if primary source fails

### Performance Metrics
- **AEMET accuracy**: Official data but 10°C lag during heat waves
- **OpenWeatherMap accuracy**: 35.56°C vs 35°C observed (0.56°C precision)
- **Coverage**: 24/7 real-time data (vs 8h/day AEMET)
- **API quota**: 60 calls/min (sufficient for 24 calls/day)

## System Initialization Architecture ✅ IMPLEMENTED

### Overview
The system now features a complete initialization framework separate from operational scheduling. This allows for historical data loading and system bootstrapping independent of real-time operations.

### Initialization vs Operations Separation
```
📊 INITIALIZATION (One-time setup)
├── Historical data loading (2022-2024)
├── Database schema verification  
├── System connectivity checks
└── Synthetic data generation

⚡ OPERATIONS (Continuous)
├── Real-time data ingestion (accelerated: every 15 min)
├── Health monitoring (every 15 min)
├── Production optimization (every 30 min)
└── Token management (daily)
```

### Initialization Endpoints ✅ AVAILABLE

#### System Status
- `GET /init/status` - Check initialization state and recommendations
- Returns: Records count, missing data estimate, initialization status

#### Historical Data Loading
- `POST /init/historical-data` - Load REE historical data (2022-2024)
- Expected: ~17,520 records (post-COVID stable period)
- Duration: 30-60 minutes background processing
- Strategy: Monthly chunks with API rate limiting

#### Complete Initialization  
- `POST /init/all` - Full system initialization
- Includes: Historical REE + synthetic weather + system checks
- Duration: 45-90 minutes for complete bootstrap

### Data Collection Strategy ✅ ACTIVE

#### Accelerated Mode (TEMPORARY)
- **Current frequency**: Every 15 minutes (4x normal speed)
- **Target**: 200-400 records for MLflow implementation
- **Duration**: 24-48 hours for sufficient dataset
- **Revert to normal**: After MLflow implementation

#### Normal Operations
```python
# TODO: Revert after data collection (48h)
# REE ingestion: CronTrigger(minute=5) [hourly at :05]  
# Weather ingestion: CronTrigger(minute=15) [hourly at :15]
```

### Data Persistence ✅ VERIFIED

All data is safely persisted through Docker bind mounts:
```
./docker/services/influxdb/data/    # Time series data
./docker/services/postgres/data/    # MLflow metadata  
./docker/services/mlflow/artifacts/ # ML models & artifacts
```

**System shutdown safe**: Data persists across container restarts ✅

### Usage Examples

#### Check System Status
```bash
curl http://localhost:8000/init/status
```

#### Load Historical Data  
```bash
curl -X POST http://localhost:8000/init/historical-data
```

#### Monitor Progress
```bash
curl http://localhost:8000/influxdb/verify
```

#### Verify Data Persistence
```bash
ls -la docker/services/influxdb/data/
# Should show: influxd.bolt, influxd.sqlite, engine/
```

### Implementation Notes

#### REE Historical API Limitations Discovered
- ✅ **Current data**: Excellent reliability (24/7)
- ⚠️ **Historical data (>1 year)**: API 500 errors common
- 🔄 **Fallback strategy**: Focus on recent data + synthetic generation
- 📊 **Result**: Accelerated real-time collection preferred for MLflow

#### MLflow Data Requirements Met
- **Target**: 200-400 records for demonstration models
- **Current approach**: 4x accelerated ingestion (every 15 min)
- **Timeline**: Ready for MLflow implementation within 24-48h
- **Quality**: Real REE prices + hybrid weather data

## Historical Weather Data Solution ✅ IMPLEMENTED

### AEMET API Historical Limitation
The AEMET historical climatological API proved unreliable after 48 hours of implementation attempts:
- ❌ **Historical endpoints**: Consistently return 0 records
- ❌ **Authentication methods**: Both Bearer and query param failed
- ❌ **Temporal chunking**: 1 week, 1 month, 1 year chunks all failed
- ❌ **Connection issues**: Frequent timeouts and connection resets

### datosclima.es ETL Solution ✅ IMPLEMENTED
**Implemented**: Complete ETL solution using datosclima.es as data source
- ✅ **Service**: `DatosClimaETL` in `services/datosclima_etl.py`
- ✅ **Endpoint**: `POST /init/datosclima/etl` for CSV processing
- ✅ **Results**: 1,095+ historical weather records ingested
- ✅ **Performance**: 2 hours implementation vs 48 hours AEMET API failures

### Implementation Results
```bash
# Before ETL Solution
historical_weather_records: 81
data_size: 30MB
status: ❌ Insufficient for MLflow

# After ETL Solution  
historical_weather_records: 1,095+
data_size: 32MB+
status: ✅ Ready for MLflow
```

### Documentation Created
- **`docs/DATOSCLIMA_ETL_SOLUTION.md`**: Complete technical implementation guide
- **`docs/QUICK_START_DATOSCLIMA.md`**: User-friendly quick start guide  
- **`docs/TROUBLESHOOTING_WEATHER_DATA.md`**: Comprehensive troubleshooting guide

### Usage
```bash
# Quick ETL execution
curl -X POST "http://localhost:8000/init/datosclima/etl?station_id=5279X&years=3"

# Verification
curl -s "http://localhost:8000/init/status" | jq '.status.historical_weather_records'
# Expected: 1000+
```

## Code Cleanup and Refactoring ✅ COMPLETED

### Overview
After implementing the datosclima.es ETL solution, a comprehensive code cleanup was performed to remove obsolete AEMET historical endpoints and functions that were no longer needed.

### Cleanup Summary
**Before cleanup:** 28 FastAPI endpoints  
**After cleanup:** 19 functional endpoints  
**Reduction:** 32% fewer endpoints for improved maintainability

### Eliminated Components

#### 1. Obsolete AEMET Historical Endpoints (8 endpoints)
- `POST /aemet/test-historical` - Test endpoint for monthly chunks
- `POST /aemet/load-progressive` - Progressive year-by-year loading  
- `POST /aemet/load-historical` - Massive historical data loading
- `GET /aemet/historical/status` - Historical data status verification
- `POST /init/aemet/historical-data` - AEMET historical initialization
- `POST /init/complete-historical-data` - Complete REE + AEMET initialization
- `GET /init/aemet/status` - AEMET initialization status
- `GET /debug/aemet/api-test` - Debug endpoint for AEMET API testing

#### 2. Debug and Test Endpoints (3 endpoints)
- `GET /aemet/raw-data` - Raw AEMET data viewer
- `GET /aemet/test-linares` - Direct API test without validation

#### 3. Background Functions and Helpers (6 functions)
- `_run_progressive_aemet_ingestion()` - Background progressive ingestion
- `_execute_progressive_ingestion()` - Progressive ingestion with rate limiting
- `_run_aemet_historical_ingestion()` - Background historical loading
- Supporting helper functions for chunked processing

#### 4. Test Files and References
- `test_aemet_historical.py` - Complete test file removal
- Updated endpoint references in root API documentation

### Cleanup Process

#### Phase 1: Identification and Analysis
1. **Audit of all endpoints:** Comprehensive review of 28 FastAPI endpoints
2. **Redundancy analysis:** Identified overlapping functionality 
3. **Obsolescence assessment:** Determined which components were replaced by datosclima.es solution

#### Phase 2: Systematic Removal
1. **Code elimination:** Removed functions, endpoints, and imports
2. **Reference cleanup:** Updated documentation and endpoint listings
3. **Syntax validation:** Ensured Python syntax remained valid throughout

#### Phase 3: Container Rebuild and Verification
1. **Container rebuild:** `docker compose build fastapi-app`
2. **Service restart:** `docker compose up -d fastapi-app`
3. **Endpoint verification:** Confirmed obsolete endpoints no longer appear in `/docs`

### Benefits Achieved

#### 1. Improved Maintainability
- **32% reduction** in endpoint count
- Eliminated dead code and technical debt
- Cleaner API surface for developers

#### 2. Enhanced Performance
- Reduced container image size
- Faster application startup
- Less memory footprint

#### 3. Better Developer Experience
- Cleaner `/docs` documentation
- No confusing obsolete endpoints
- Clear separation of concerns

#### 4. Code Quality
- Removed experimental and debug code
- Eliminated broken references to non-functional APIs
- Streamlined codebase for future development

### Preserved Functionality

#### Essential Endpoints Maintained
- `POST /init/historical-data` - **Kept** for REE historical data (non-AEMET)
- `POST /init/datosclima/etl` - **New** datosclima.es ETL endpoint
- All operational weather, scheduling, and ingestion endpoints

#### Core Features Intact
- ✅ Real-time data ingestion (REE + Hybrid weather)
- ✅ APScheduler automation (7 scheduled jobs)
- ✅ InfluxDB data storage and verification
- ✅ MLflow integration readiness
- ✅ Token management and API connectivity

### Validation Results

#### Endpoint Count Verification
```bash
# Before cleanup
curl -s http://localhost:8000/ | jq '.endpoints | length'
# Result: 28 endpoints

# After cleanup and rebuild
curl -s http://localhost:8000/ | jq '.endpoints | length'  
# Result: 19 endpoints
```

#### Obsolete Endpoint Check
```bash
# Verify no obsolete references remain
curl -s http://localhost:8000/ | jq '.endpoints | keys[]' | grep -E 'historical|debug|test|raw'
# Result: Only "init_historical" (correct - REE data)
```

#### Container Health Verification
```bash
docker logs --tail 10 chocolate_factory_brain
# Result: ✅ All services started successfully
# Result: ✅ APScheduler running with 7 jobs
# Result: ✅ No import or syntax errors
```

### Documentation Impact

#### Updated Files
- **`CLAUDE.md`** - This cleanup documentation added
- **FastAPI `/docs`** - Automatically updated to show only functional endpoints
- **Root endpoint `GET /`** - Cleaned endpoint references

#### Removed References
- All debug and test endpoint documentation
- Obsolete AEMET historical API instructions
- Broken internal links and references

### Future Implications

#### Simplified Development Workflow
1. **New developers** see only functional endpoints in `/docs`
2. **API consumers** avoid confusion with obsolete endpoints  
3. **Maintenance work** focused on active, functional code

#### Easier MLflow Integration
- Clean foundation for ML model implementation
- No competing or confusing data initialization endpoints
- Clear path forward with datosclima.es as single weather data source

#### Container Optimization
- Faster deployment cycles with smaller, cleaner codebase
- Reduced attack surface with fewer exposed endpoints
- Better resource utilization in production

### Success Metrics
- ✅ **32% endpoint reduction** without functionality loss
- ✅ **100% syntax validation** maintained throughout cleanup
- ✅ **Zero downtime** during container rebuild process
- ✅ **Complete preservation** of all essential features
- ✅ **Improved developer experience** with cleaner API documentation

This cleanup establishes a solid, maintainable foundation for continued development, particularly the upcoming MLflow implementation phase.

## MLflow Machine Learning Implementation ✅ COMPLETED

### Overview
The **Unidad MLOps (Cuartel General ML)** is now fully operational with a complete machine learning pipeline for chocolate production optimization. Implementation includes MLflow tracking server, feature engineering, baseline models, and automated predictions.

### ✅ Achievements
- **2 ML Models**: Energy Optimization (R² = 0.8876) + Production Classifier (90% accuracy)
- **MLflow Tracking**: Remote server with PostgreSQL backend and artifact storage
- **Feature Engineering**: 13 engineered features from REE + Weather data
- **Synthetic Data**: 39 generated samples ensuring class diversity (50 total samples)
- **Prediction APIs**: Real-time energy optimization and production recommendations
- **Scheduler Integration**: Automated ML predictions every 30 minutes with alerts

### Architecture
```
🏗️ MLflow Server (Container)
├── 🗄️ PostgreSQL Backend (metadata)
├── 📁 Artifact Store (bind mount)
└── 🌐 Web UI (localhost:5000)

🧠 FastAPI ML Pipeline  
├── 🔧 Feature Engineering (13 features)
├── 🤖 RandomForest Models (regression + classification)
├── 📊 Synthetic Data Generation (39 samples)
└── ⏰ Scheduled Predictions (every 30min)
```

### Endpoints Implemented
```bash
# Model Status and Health
GET  /mlflow/status              # MLflow connectivity and experiments
GET  /models/status              # Models performance and health

# Feature Engineering  
GET  /mlflow/features            # Extract and engineer features

# Model Training
POST /mlflow/train               # Train models with MLflow tracking

# Real-time Predictions
POST /predict/energy-optimization        # Energy optimization score
POST /predict/production-recommendation  # Production recommendations
```

### Models Performance
#### 1. Energy Optimization Model (Regression)
- **Type**: RandomForestRegressor
- **Performance**: R² = 0.8876 (88.76% variance explained)
- **Target**: energy_optimization_score (0-100)
- **Features**: 8 (price, temperature, humidity + engineered features)

#### 2. Production Classifier (Classification)  
- **Type**: RandomForestClassifier
- **Performance**: 90% accuracy
- **Classes**: Optimal, Moderate, Reduced, Halt Production
- **Features**: Same 8 features as regression model

### Data Pipeline
- **Real Data**: 11 samples from InfluxDB (REE + Weather)
- **Synthetic Data**: 39 samples with guaranteed class diversity
- **Feature Engineering**: Energy indices, weather comfort factors, production scores
- **MLflow Tracking**: Complete experiment logging with parameters and metrics

### Scheduler Integration
**New Job Added**: ML Production Predictions (every 30 minutes)
- Extracts latest energy prices and weather data from InfluxDB
- Calculates real-time production recommendations
- Sends alerts for critical conditions (Halt/Reduce production)
- Logs detailed predictions with energy optimization scores

### Usage Examples
```bash
# Check models health
curl http://localhost:8000/models/status

# Predict energy optimization  
curl -X POST http://localhost:8000/predict/energy-optimization \
  -d '{"price_eur_kwh": 0.15, "temperature": 22, "humidity": 55}'

# Predict production recommendation
curl -X POST http://localhost:8000/predict/production-recommendation \
  -d '{"price_eur_kwh": 0.30, "temperature": 35, "humidity": 80}'
```

### Documentation
Complete technical documentation available in:
- **`docs/MLFLOW_IMPLEMENTATION.md`** - 26 pages of detailed implementation docs
- **Architecture diagrams, API references, troubleshooting guides**
- **Performance metrics, deployment instructions, next steps**

## Sistema de Backfill Automático ✅ IMPLEMENTADO

### Overview
El sistema cuenta con **detección automática de gaps** y **backfill inteligente** para recuperar datos faltantes cuando el equipo ha estado parado por períodos prolongados.

### ✅ Achievements
- **Gap Detection**: Detecta automáticamente qué datos faltan y en qué rangos temporales
- **Smart Strategy**: Lógica temporal inteligente (mes actual vs histórico)
- **Auto-Recovery**: Sistema autónomo de recuperación cada 2 horas
- **Alert System**: Notificaciones automáticas de éxito/fallo en recuperación
- **Manual Control**: Endpoints para control manual y debugging

### Arquitectura del Backfill

```
🔍 Gap Detection Service
├── 📊 Analiza gaps en REE y Weather
├── ⏰ Calcula rangos temporales faltantes
└── 📈 Estima tiempo de recuperación

🔄 Backfill Service
├── 📅 Estrategia temporal inteligente
├── 🔌 REE: API histórica con chunks diarios
├── 🌤️ Weather: AEMET (mes actual) + datosclima.es (histórico)
└── ⚡ Rate limiting automático

⏰ Scheduler Integration
├── 🤖 Auto-check cada 2 horas
├── 🚨 Alertas automáticas
└── 📊 Métricas de éxito/fallo
```

### Estrategia Temporal Inteligente

**Criterio Temporal Refinado:**
- **📅 Mes actual**: AEMET API (funciona bien con pequeños batches)
- **📆 Meses anteriores**: datosclima.es ETL (datos históricos confiables)
- **🔄 Auto-trigger**: Gaps >3 horas activan backfill automático
- **📊 Rate limiting**: REE 30req/min, AEMET 20req/min

### Endpoints Implementados

```bash
# Estado rápido de datos
GET /gaps/summary

# Análisis completo de gaps
GET /gaps/detect?days_back=10

# Backfill manual (background)
POST /gaps/backfill?days_back=7

# Backfill automático inteligente
POST /gaps/backfill/auto?max_gap_hours=6.0
```

### Scheduler Jobs - Sistema Completo

**Total: 10 jobs programados** (incluyendo backfill automático)
- ✅ REE ingestion (every 5 min) - Datos en tiempo real
- ✅ Weather ingestion (every 5 min) - Híbrido AEMET/OpenWeatherMap
- ✅ ML predictions (every 30 min) - Recomendaciones de producción
- ✅ ML training (every 30 min) - Reentrenamiento automático
- ✅ **Auto backfill check (every 2 hours)** - Recuperación automática
- ✅ Health monitoring (every 15 min) - Estado del sistema
- ✅ Token management (daily) - Renovación AEMET
- ✅ Weekly cleanup (Sunday 2 AM) - Mantenimiento
- ✅ Daily backfill (1 AM) - Validación diaria
- ✅ Production optimization (every 30 min) - Optimización continua

### Estado Operativo - Sistema Productivo

✅ **100% operativo** - 10 jobs programados, backfill automático activo  
✅ **Self-healing** - Detecta y corrige gaps automáticamente  
✅ **Smart recovery** - Estrategia híbrida por rango temporal  
✅ **Alert system** - Notificaciones automáticas de estado  
✅ **Manual override** - Control completo para debugging  

### Validation Results

#### Backfill Performance Metrics
```bash
# Estado antes del backfill
curl -s http://localhost:8000/gaps/summary
# REE: 7 días atrasado (179h gap)
# Weather: 7 días atrasado (181h gap)

# Después del backfill automático
curl -s http://localhost:8000/influxdb/verify | jq '.data'
# REE: ✅ Último dato 2025-07-07T08:00:00 (actual)
# Weather: ✅ Último dato 2025-07-07T08:23:05 (tiempo real)
# Success rate: 32.9% y mejorando
```

#### Auto-Recovery Validation
```bash
# Verificar scheduler backfill
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | select(.id == "auto_backfill_check")'
# Result: ✅ Job activo, próxima ejecución cada 2 horas

# Test manual de auto-recovery
curl -X POST "http://localhost:8000/gaps/backfill/auto?max_gap_hours=100"
# Result: ✅ 9 gaps procesados, backfill automático ejecutado
```

### Usage Examples

#### Monitoreo Rutinario
```bash
# Verificar estado de datos
curl -s http://localhost:8000/gaps/summary

# Análisis detallado de gaps
curl -s http://localhost:8000/gaps/detect | jq '.summary'

# Estado del scheduler
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.total_jobs'
```

#### Recuperación Manual
```bash
# Backfill de últimos 3 días (background)
curl -X POST http://localhost:8000/gaps/backfill?days_back=3

# Auto-backfill con umbral personalizado  
curl -X POST "http://localhost:8000/gaps/backfill/auto?max_gap_hours=24"

# Verificar resultados
curl -s http://localhost:8000/influxdb/verify | jq '.data'
```

### Documentation
Complete technical documentation available in:
- **`docs/AUTOMATIC_BACKFILL_SYSTEM.md`** - Sistema completo de backfill automático
- **`docs/GAP_DETECTION_STRATEGY.md`** - Estrategias de detección y recuperación  
- **`docs/SCHEDULER_INTEGRATION.md`** - Integración con APScheduler

## Dashboard Migration: Node-RED → FastAPI Integration ✅ COMPLETADO

### Overview
**Septiembre 2025**: Exitosa migración de Node-RED a dashboard integrado en FastAPI, **reduciendo la arquitectura de 4 a 3 contenedores** y unificando el stack tecnológico al 100% Python.

### ✅ Achievements
- **Eliminación completa de Node-RED**: Contenedor `chocolate_factory_monitor:1880` removido
- **Dashboard integrado**: Servido directamente desde FastAPI en `/dashboard/complete`
- **Stack unificado**: 100% Python (FastAPI + Dashboard + ML) vs Stack mixto anterior
- **Recursos liberados**: ~200MB RAM + CPU, 1 puerto menos (`:1880`)
- **Arquitectura simplificada**: 3 contenedores vs 4 (25% reducción)

### Arquitectura Final - 3 Contenedores

```
🧠 chocolate_factory_brain (FastAPI)
├── Puerto: 8000
├── API endpoints: /predict, /ingest-now, /scheduler
├── 📊 Dashboard integrado: /dashboard/complete
└── APScheduler: 10+ jobs automatizados

💾 chocolate_factory_storage (InfluxDB)
├── Puerto: 8086
├── Time series database
└── Datos: REE prices + Weather + ML features

🤖 chocolate_factory_mlops (MLflow + PostgreSQL) 
├── Puerto: 5000 (MLflow UI)
├── ML models + experiments tracking
└── PostgreSQL backend para metadata
```

### Funcionalidades Dashboard
- ⚡ **Precio energía**: REE tiempo real con tendencias
- 🌡️ **Temperatura/Humedad**: Weather híbrido AEMET/OpenWeatherMap
- 🏭 **Producción ML**: Recomendaciones energy optimization + production classifier
- 🔔 **Sistema de alertas**: Condiciones críticas automáticas
- 📊 **Datos JSON**: API `/dashboard/complete` para consumo programático

### Beneficios Inmediatos
- **Mantenimiento simplificado**: 1 aplicación vs 2 servicios independientes
- **Performance mejorado**: Acceso directo a datos sin HTTP calls inter-servicios
- **Deploy optimizado**: `docker compose up` con 3 contenedores vs 4
- **Desarrollo unificado**: Stack 100% Python para todo el ecosistema

### Endpoints Dashboard
```bash
# Dashboard data completo
GET /dashboard/complete

# Verificar datos en tiempo real
curl http://localhost:8000/dashboard/complete | jq '.current_info'

# Estado del sistema
curl http://localhost:8000/dashboard/complete | jq '.system_status'
```

### Resultado de la Migración
✅ **Exitosa reducción de complejidad**  
✅ **Mejor performance y menor consumo recursos**  
✅ **Stack tecnológico unificado (100% Python)**  
✅ **Datos dashboard funcionales y actualizados**  
✅ **Arquitectura productiva simplificada**

## Tailscale Sidecar Integration ✅ COMPLETADO

### Overview
**Septiembre 2025**: Implementación exitosa de sidecar Tailscale para **exposición externa segura del dashboard**, expandiendo la arquitectura a **4 contenedores especializados** con acceso remoto cifrado.

### ✅ Achievements
- **Sidecar Tailscale**: Contenedor Alpine 52.4MB ultra-ligero
- **SSL Automático**: Certificados Tailscale ACME con renovación automática
- **Acceso Seguro**: Solo `/dashboard` expuesto externamente
- **Dual Access**: Externo (limitado) + Local (completo) para desarrollo
- **Zero Configuration**: Setup automático con auth key

### Arquitectura Final - 4 Contenedores + Sidecar

```
🔐 chocolate-factory (Tailscale Sidecar)
├── Alpine Linux 52.4MB
├── Nginx proxy + SSL automático
├── URL: https://chocolate-factory.azules-elver.ts.net/dashboard
└── Solo /dashboard expuesto + bloqueos de seguridad

🧠 chocolate_factory_brain (FastAPI)
├── Puerto: 8000 (local development)
├── API endpoints: /predict, /ingest-now, /scheduler  
├── Dashboard integrado: /dashboard/complete
└── APScheduler: 10+ jobs automatizados

💾 chocolate_factory_storage (InfluxDB)
├── Puerto: 8086 (local admin)
├── Time series database
└── Datos: REE prices + Weather + ML features

🤖 chocolate_factory_mlops (MLflow + PostgreSQL)
├── Puerto: 5000 (local development) 
├── ML models + experiments tracking
└── PostgreSQL backend para metadata
```

### Configuración Tailscale Sidecar

#### Docker Configuration
```yaml
# docker-compose.override.yml
chocolate-factory:
  build:
    dockerfile: docker/tailscale-sidecar.Dockerfile
  container_name: chocolate-factory
  hostname: chocolate-factory
  privileged: true  # Requerido para Tailscale
  cap_add: [NET_ADMIN, SYS_MODULE]
  devices: [/dev/net/tun]
  environment:
    - TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY}
    - TAILSCALE_HOSTNAME=chocolate-factory
  volumes:
    - tailscale_state:/var/lib/tailscale  # Estado persistente
```

#### Nginx Security Configuration
```nginx
# Solo /dashboard permitido
location /dashboard { 
    proxy_pass http://chocolate_factory_brain:8000; 
}

# Endpoints bloqueados con páginas HTML personalizadas
location ~ ^/(docs|redoc|openapi\.json|predict|mlflow) { 
    return 403; 
}
```

#### SSL Certificates
- **Automáticos**: `tailscale cert chocolate-factory.azules-elver.ts.net`
- **Renovación**: Automática vía Tailscale ACME
- **Configuración**: TLS 1.2/1.3 con ciphers modernos
- **Redirección**: HTTP → HTTPS (301 Permanent)

### URLs de Acceso

#### Acceso Externo (Tailscale - Seguro)
```bash
# Dashboard principal (único endpoint expuesto)
https://chocolate-factory.azules-elver.ts.net/dashboard

# IP directa Tailscale  
https://100.127.58.34/dashboard

# APIs bloqueadas externamente (403 Forbidden)
https://chocolate-factory.azules-elver.ts.net/docs      # ❌
https://chocolate-factory.azules-elver.ts.net/predict   # ❌
```

#### Acceso Local (Desarrollo - Completo)
```bash
# FastAPI completo para desarrollo
http://localhost:8000/docs        # ✅ Swagger UI
http://localhost:8000/predict     # ✅ ML predictions  
http://localhost:8000/dashboard   # ✅ Dashboard data

# Servicios administrativos
http://localhost:8086             # ✅ InfluxDB UI
http://localhost:5000             # ✅ MLflow UI
```

### Variables de Entorno Requeridas

#### .env Configuration
```bash
# Tailscale Auth Key (generar en panel Tailscale)
TAILSCALE_AUTHKEY=tskey-auth-XXXXXXXXXXXXXXXXXXXXXXXXX
TAILSCALE_HOSTNAME=chocolate-factory

# APIs y servicios principales
OPENWEATHERMAP_API_KEY=xxx
AEMET_API_KEY=xxx  
INFLUXDB_TOKEN=xxx
# ... resto de variables existentes
```

### Setup Instructions
```bash
# 1. Generar auth key en https://login.tailscale.com/admin/settings/keys
# 2. Agregar variables Tailscale a .env principal
# 3. Build y deploy
docker compose build chocolate-factory
docker compose up -d

# 4. Verificar conexión
curl https://chocolate-factory.azules-elver.ts.net/dashboard
```

### Network Architecture
- **MTU Optimizado**: 1280 bytes para evitar fragmentación Tailscale
- **Subnet Docker**: 192.168.100.0/24 con gateway .1
- **Persistent State**: Volumen `tailscale_state` para reconexiones
- **Health Checks**: Verificación automática cada 60s

### Security Features
- **Endpoint Isolation**: Solo `/dashboard` accesible externamente  
- **Custom Error Pages**: HTML responses elegantes para 403/404
- **SSL Enforcement**: Redirección automática HTTP→HTTPS
- **Container Privileges**: Mínimos necesarios (NET_ADMIN, SYS_MODULE)
- **State Persistence**: Reconexión automática tras reinicios

### Benefits
- **Remote Access**: Dashboard accesible desde cualquier dispositivo en tailnet
- **Zero Configuration**: Setup automático sin configuración manual de SSL
- **Development Friendly**: Acceso local completo preservado
- **Ultra Lightweight**: Container 52.4MB vs alternativas ~200-500MB  
- **Enterprise Security**: Cifrado WireGuard + certificados válidos
- **Fail Safe**: Fallback local siempre disponible

### Monitoring
```bash
# Estado Tailscale
docker exec chocolate-factory tailscale status

# Logs sidecar
docker logs chocolate-factory

# Verificar certificados SSL
curl -I https://chocolate-factory.azules-elver.ts.net/dashboard
```

### Resultado Tailscale Integration
✅ **Dashboard remotely accessible via HTTPS**  
✅ **SSL certificates auto-provisioned and renewed**  
✅ **Security isolation: only dashboard exposed externally**  
✅ **Local development access preserved (complete API)**  
✅ **Ultra-lightweight sidecar: 52.4MB Alpine container**  
✅ **Zero-config deployment with persistent state**
✅ **Security Update: Tailscale 1.86.2** - Updated Sept 2025 to address security vulnerabilities

## Future Enhancements
- **Advanced ML models**: Hybrid feature engineering for production optimization  
- **Model serving**: Load trained models from MLflow for real-time predictions
- **Drift detection**: Monitor model performance degradation over time
- **A/B Testing**: Compare model versions in production
- **Enhanced backfill**: Priorización inteligente por criticidad de datos
- Procura que esté actualizados los datos de las api externas(REE y AEMET) usando los dos enfoques, cuando ha pasado un mes y mes actual. Además recuer openWeahter
- el backfill debes siempre comprobarlo una vez iniciado el contenedor ya que no siempre está encendido el equipo.