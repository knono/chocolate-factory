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
This project is in the initial setup phase. The directory structure is prepared, but most implementation files are not yet created:
- Docker containers and orchestration are planned but not implemented
- FastAPI dependencies not yet defined in pyproject.toml
- MLOps infrastructure (MLflow, InfluxDB) not yet configured

## Key Design Principles

- **Autonomous Operation**: The FastAPI container runs independently with APScheduler handling all automation
- **Read-Only Dashboard**: Node-RED only visualizes data, never executes actions
- **Separation of Concerns**: Each container has a specific role in the data pipeline
- **Time Series Focus**: InfluxDB chosen specifically for time series data management