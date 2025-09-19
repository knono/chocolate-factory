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

```
├── src/fastapi-app/            # Main FastAPI application
│   ├── main.py                # FastAPI entry point
│   ├── pyproject.toml         # Python dependencies
│   └── services/              # Service layer modules
│       ├── direct_ml.py       # Direct ML training (sklearn)
│       ├── dashboard.py       # Integrated dashboard
│       ├── siar_etl.py       # SIAR weather data ETL
│       ├── ree_client.py      # REE electricity API
│       └── [backfill, gaps, weather APIs]
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
- **Direct Training**: sklearn + pickle storage (no external ML services)
- **Real-time Predictions**: Energy optimization + production recommendations
- **Automated ML**: Model retraining and predictions (every 30 min)

### Operations
- **APScheduler**: 10+ automated jobs (ingestion, ML, backfill, health)
- **Integrated Dashboard**: `/dashboard/complete` (replaces Node-RED)
- **Visual Dashboard**: `/dashboard` with real-time heatmap and interactive widgets
- **Weekly Forecast**: 7-day heatmap with price zones and weather integration
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

### Data Ingestion
- `POST /ingest-now` - Manual data ingestion
- `GET /weather/hybrid` - Hybrid weather data
- `GET /ree/prices` - Current electricity prices

### ML Operations  
- `POST /models/train` - Train ML models directly
- `GET /models/status-direct` - Model health and performance
- `POST /predict/energy-optimization` - Energy optimization predictions
- `POST /predict/production-recommendation` - Production recommendations

### Dashboard & Monitoring
- `GET /dashboard` - Visual dashboard with interactive heatmap
- `GET /dashboard/complete` - Integrated dashboard JSON data
- `GET /scheduler/status` - APScheduler job status
- `GET /gaps/summary` - Data gap detection  
- `POST /gaps/backfill/auto` - Automatic backfill recovery

### Weekly Forecast System
- **7-day heatmap**: Color-coded price zones with weather overlay
- **Interactive tooltips**: Hover details for each day (price, weather, recommendations)
- **Real-time data**: REE prices + AEMET/OpenWeatherMap weather integration
- **Production guidance**: Daily recommendations (Optimal/Moderate/Reduced/Halt)
- **Responsive design**: CSS Grid layout with dynamic color coding

## System Automation

### APScheduler Jobs (10+ automated)
- **REE ingestion**: Every 5 minutes
- **Weather ingestion**: Every 5 minutes (hybrid AEMET/OpenWeatherMap)
- **ML training**: Every 30 minutes (direct sklearn)
- **ML predictions**: Every 30 minutes
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
- **Ultra-lightweight**: 52.4MB Alpine container
- **SSL Automatic**: Tailscale ACME certificates with auto-renewal
- **Security isolation**: Only `/dashboard` exposed externally
- **Dual access**: External (limited) + Local (complete) for development

### Setup
```bash
# 1. Generate auth key at https://login.tailscale.com/admin/settings/keys
# 2. Add TAILSCALE_AUTHKEY to .env
# 3. Deploy sidecar
docker compose up -d chocolate-factory
```

### Access URLs
- **External dashboard**: `https://chocolate-factory.azules-elver.ts.net/dashboard`
- **Local dashboard**: `http://localhost:8000/dashboard` (with weekly heatmap)
- **Local dev API**: `http://localhost:8000/docs` (complete API access)
- **JSON data**: `http://localhost:8000/dashboard/complete`


## Important Instructions

- **Placeholder usage**: Keep placeholders in mind to avoid false positives
- **Data freshness**: Always check backfill status when container starts (system not always running)
- **Gap recovery**: Use backfill when necessary to maintain data currency
- **API updates**: Ensure REE and AEMET data stays current (remember OpenWeather for 08:00-23:00)
- **Monthly strategy**: Use current month (AEMET) vs historical (SIAR system) approaches

## Recent System Updates

### 🔧 **AEMET Integration Fix (Sept 19, 2025)**
- **Issue**: System was only using OpenWeatherMap, AEMET integration broken
- **Root cause**: Import errors (`DatosClimaETL` class didn't exist) + silent error handling
- **Solution**: Fixed imports to `SiarETL` + enhanced logging + proper error handling
- **Result**: ✅ AEMET official data restored, hybrid system fully operational
- **Status**: Weather gaps closed (0.0 hours), project value restored with official Spanish data