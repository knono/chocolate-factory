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
│       ├── datosclima_etl.py # Weather data ETL
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
- **Historical Data**: 1,095+ weather records via datosclima.es ETL
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
- **Historical**: datosclima.es ETL (1,095+ records)
- **Status**: ✅ 24/7 coverage achieved

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

### Historical Data
- **datosclima.es ETL**: 1,095+ weather records via `POST /init/datosclima/etl`
- **REE Historical**: Limited reliability for >1 year data
- **Backfill system**: Auto-detects and recovers gaps every 2 hours


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
- **Smart strategy**: Current month (AEMET API) vs historical (datosclima.es ETL)
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
- **Monthly strategy**: Use current month (AEMET) vs historical (datosclima.es) approaches