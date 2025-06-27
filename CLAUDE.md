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

#### Solution Strategy for MLflow Models
1. **Primary data**: AEMET observation (00:00-07:00) + AEMET hourly prediction (08:00-23:00)
2. **Secondary validation**: OpenWeatherMap integration planned for cross-validation
3. **Feature engineering**: Interpolation and gap-filling algorithms
4. **Hybrid approach**: Official AEMET data + commercial weather API for real-time validation

### Token Management
- **AEMET Token**: Auto-renewal every 6 days (permanent API key system)
- **REE**: No authentication required for public endpoints
- **Status**: ✅ Fully automated token lifecycle management

## MLflow Feature Architecture

### Recommended Feature Pipeline
```python
# Hourly features (00:00-23:00)
- ree_price_eur_kwh          # REE: complete 24h coverage
- ree_demand_mw              # REE: complete 24h coverage  
- tariff_period              # Derived: P1-P6 classification

# Weather features (hybrid approach)
- temp_observed              # AEMET: 00:00-07:00 real data
- temp_predicted             # AEMET: 08:00-23:00 prediction API
- temp_interpolated          # Derived: gap filling algorithm
- humidity_observed          # AEMET: 00:00-07:00 real data
- humidity_predicted         # AEMET: 08:00-23:00 prediction API

# Chocolate production indices
- chocolate_production_index # Derived: temp + humidity + pressure
- heat_stress_factor        # Derived: extreme weather detection
- energy_optimization_score # Derived: REE price + weather combination
```

### Data Quality Considerations
- **REE data reliability**: ⭐⭐⭐⭐⭐ (excellent real-time accuracy)
- **AEMET observation reliability**: ⭐⭐⭐ (official but limited coverage)
- **AEMET prediction reliability**: ⭐⭐⭐⭐ (good for planning, 48h horizon)
- **Temporal synchronization**: REE hourly + AEMET mixed (obs/pred)

## Future Enhancements
- **OpenWeatherMap integration**: Planned for real-time weather validation
- **Extreme weather detection**: Cross-validation between AEMET and commercial APIs
- **Production correlation analysis**: REE price patterns vs weather conditions
- **Advanced interpolation**: Machine learning-based gap filling for missing weather data