# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a TFM (Master's Thesis) project for a chocolate factory simulation and monitoring system. The project implements a containerized architecture with 4 main production containers working together for automated data ingestion, ML prediction, and monitoring.

## Architecture

The system follows a 4-container production architecture:

1. **API Unificada** ("El Cerebro Autónomo") - FastAPI with APScheduler for automation
2. **Almacén de Series** ("El Almacén Principal") - InfluxDB for time series storage  
3. **Unidad MLOps** ("Cuartel General ML") - MLflow Server + PostgreSQL
4. **Dashboard** ("El Monitor") - Node-RED for read-only visualization

The main FastAPI application (`src/fastapi-app/`) acts as the autonomous brain, handling:
- `/predict` and `/ingest-now` endpoints
- APScheduler-managed automation for periodic ingestion and predictions
- SimPy/SciPy simulation logic

## Project Structure

```
├── src/fastapi-app/        # Main FastAPI application
├── docker/                 # Docker configuration files (to be implemented)
├── src/configs/           # Configuration files
├── data/raw/              # Raw data storage
├── data/processed/        # Processed data storage
├── notebooks/             # Jupyter notebooks for analysis
└── docs/                  # Project documentation
```

## Development Setup

The project uses Python 3.11+ with the main application in `src/fastapi-app/`.

### FastAPI Application
- Entry point: `src/fastapi-app/main.py`
- Project configuration: `src/fastapi-app/pyproject.toml`
- Currently in early development stage with basic skeleton

### Development Status
The project has evolved beyond the initial setup phase with significant infrastructure completed:
- ✅ Docker containers fully operational (FastAPI, InfluxDB, MLflow, PostgreSQL)
- ✅ REE API integration with real Spanish electricity prices (every hour)
- ✅ AEMET API integration with Spanish weather data (Linares, Jaén)
- ✅ APScheduler automation (7 scheduled jobs)
- ✅ InfluxDB schemas and data ingestion pipelines
- 🚧 MLflow models pending implementation
- 🚧 Node-RED dashboard pending setup

## Key Design Principles

- **Autonomous Operation**: The FastAPI container runs independently with APScheduler handling all automation
- **Read-Only Dashboard**: Node-RED only visualizes data, never executes actions
- **Separation of Concerns**: Each container has a specific role in the data pipeline
- **Time Series Focus**: InfluxDB chosen specifically for time series data management

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

## Future Enhancements
- **Advanced ML models**: Hybrid feature engineering for production optimization  
- **Extreme weather alerts**: Automated chocolate production adjustments
- **Energy correlation analysis**: REE price patterns vs weather-optimized production
- **Quality validation**: Continuous cross-validation between AEMET and OpenWeatherMap
- **datosclima.es integration**: Automated CSV download and processing pipeline