# Chocolate Factory - Industrial Energy Optimization System

**Autonomous energy monitoring and production optimization system with machine learning and historical data analysis**

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?style=flat&logo=influxdb)](https://influxdata.com)
[![Tailscale](https://img.shields.io/badge/Tailscale-Zero--Trust-000000?style=flat&logo=tailscale)](https://tailscale.com)
[![ML](https://img.shields.io/badge/ML-131k_Records-10b981?style=flat)](https://github.com)

---

## Overview

Industrial-grade system for energy cost optimization and production planning. Integrates real-time Spanish electricity market data (REE), official meteorological data (AEMET), and 25+ years of historical weather records (SIAR) to provide ML-powered production recommendations.

### Core Capabilities

- **Energy Price Forecasting**: LSTM/Prophet models for 168-hour electricity price prediction
- **Production Optimization**: Hourly production planning based on energy costs and weather conditions
- **Historical Analysis**: 131,513+ records (88,935 SIAR + 42,578 REE) for robust ML training
- **Autonomous Operation**: Self-healing data pipeline with automatic gap detection and recovery
- **Real-time Dashboard**: Interactive weekly heatmap with production recommendations

---

## System Architecture

### Deployment Philosophy: On-Premise with Secure Remote Access

The system implements a **hybrid architecture** combining complete on-premise data sovereignty with zero-trust remote access capabilities. This design ensures:

- **Data Sovereignty**: All data processing, storage, and ML training occurs on local infrastructure
- **Zero Cloud Dependencies**: No reliance on third-party cloud services for core operations
- **Selective Exposure**: Only read-only dashboard accessible remotely; administrative APIs remain local-only
- **Cost Efficiency**: Eliminates recurring cloud service costs while maintaining secure remote monitoring

### Infrastructure (2-Container + Optional Sidecar)

```
┌─────────────────────────────────────────────────────────────┐
│  LOCAL INFRASTRUCTURE (On-Premise)                          │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │  FastAPI Application (Port 8000)    │ ◄─── Local Admin  │
│  │  ├── RESTful API (full access)      │      Access       │
│  │  ├── Integrated Dashboard           │      (localhost)  │
│  │  ├── ML Training & Prediction       │                   │
│  │  └── APScheduler (10+ jobs)         │                   │
│  └─────────────────────────────────────┘                   │
│                ↓                                            │
│  ┌─────────────────────────────────────┐                   │
│  │  InfluxDB 2.7 (Port 8086)           │ ◄─── Local Admin  │
│  │  ├── Time series database           │      Access       │
│  │  ├── REE prices (42,578 records)    │                   │
│  │  ├── Real-time weather data         │                   │
│  │  └── SIAR historical (88,935)       │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                       ↑
                       │ Docker Internal Network (192.168.100.0/24)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  OPTIONAL: TAILSCALE SIDECAR (Secure Remote Access)        │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │  Nginx Reverse Proxy (Alpine 52MB)  │                   │
│  │  ├── SSL/TLS Termination            │                   │
│  │  ├── Endpoint Filtering (whitelist) │                   │
│  │  └── /dashboard ONLY (read-only)    │                   │
│  └─────────────────────────────────────┘                   │
│                ↑                                            │
│                │ Tailscale Zero-Trust Network              │
│                ↓                                            │
│  [ Remote Access: https://<hostname>.ts.net ]              │
│    ✓ Dashboard monitoring (read-only)                      │
│    ✗ Admin APIs (blocked by Nginx)                         │
│    ✗ ML training endpoints (blocked)                       │
│    ✗ Data modification (blocked)                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Security Architecture: Defense in Depth

**Layer 1: Network Isolation**
- Local infrastructure operates on isolated Docker network (MTU 1280 for Tailscale compatibility)
- No direct port exposure to internet
- Tailscale sidecar acts as sole external gateway

**Layer 2: Reverse Proxy Filtering (Nginx)**
- Whitelist-only approach: Only `/dashboard` and static resources permitted
- All administrative endpoints explicitly blocked (`/docs`, `/predict`, `/models`, `/influxdb`, etc.)
- API endpoints for data modification return HTTP 403
- Custom 403 pages prevent information disclosure

**Layer 3: Zero-Trust Networking (Tailscale)**
- WireGuard-based encrypted tunnels
- Identity-based access (not IP-based)
- Automatic SSL/TLS certificate management
- No VPN configuration or firewall rules required

**Layer 4: Application-Level Access Control**
- Full API access restricted to localhost (development/maintenance)
- Dashboard provides read-only operational visibility
- No sensitive credentials exposed through remote interface

### Operational Benefits

**On-Premise Data Control**
- Complete data sovereignty: No third-party cloud access to operational or historical data
- GDPR/Privacy compliance: Data never leaves local infrastructure
- Offline capability: System operates independently of internet connectivity
- Customization freedom: No cloud service limitations or API constraints

**Cost Structure**
- Zero recurring cloud costs (no AWS/Azure/GCP bills)
- Free-tier external APIs (REE, AEMET, OpenWeatherMap) for data acquisition
- Hardware amortization: One-time investment in local server/NUC
- Tailscale: Free for personal use (up to 100 devices)

**Security Posture**
- Minimal attack surface: Only dashboard exposed remotely (read-only)
- Defense in depth: 4 security layers (network, proxy, zero-trust, application)
- No credential exposure: Admin credentials never traverse remote connections
- Audit trail: Local logs for all administrative actions

**Operational Flexibility**
- Local development: Full API access on `localhost:8000` for testing/debugging
- Selective remote access: Dashboard monitoring from anywhere via Tailscale
- Easy maintenance: Direct access to InfluxDB and logs on local network
- No vendor lock-in: Standard Docker containers, portable to any infrastructure

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI (Python 3.11+) | REST API + Dashboard |
| **Database** | InfluxDB 2.7 | Time series storage |
| **ML Framework** | scikit-learn, Prophet/LSTM | Predictive models |
| **Scheduling** | APScheduler | Automated data ingestion |
| **Containerization** | Docker Compose | Orchestration |
| **Reverse Proxy** | Nginx (Alpine) | Endpoint filtering |
| **Remote Access** | Tailscale (WireGuard) | Zero-trust networking |

---

## Data Sources

### Real-time Integration

1. **REE (Red Eléctrica de España)**
   - Spanish electricity market prices (PVPC)
   - Hourly updates
   - 42,578 historical records (2022-2025)

2. **AEMET (Spanish State Meteorological Agency)**
   - Official weather observations (Station 5279X - Linares)
   - Active hours: 00:00-07:00 UTC
   - Temperature, humidity, pressure

3. **OpenWeatherMap**
   - Complementary weather data (08:00-23:00 UTC)
   - 24/7 coverage when combined with AEMET

### Historical Data

**SIAR (Agricultural Climate Information System)**
- 88,935 weather records (2000-2025)
- 25+ years historical coverage
- 10 meteorological variables
- 2 stations: J09 (2000-2017) + J17 (2018-2025)

---

## Machine Learning System

### Current Status: Sprint 06 (Price Forecasting)

The ML system is undergoing evolution from synthetic models to real time series predictions.

**Sprint Progress**: 6/10 (60% infrastructure, 0% ML evolution)

### Planned ML Architecture (Sprint 06-10)

| Sprint | Component | Status | ETA |
|--------|-----------|--------|-----|
| **06** | REE Price Forecasting (LSTM/Prophet) | 🟡 Active | 8-10h |
| **07** | SIAR Time Series Integration | 🔴 Pending | 6-8h |
| **08** | Hourly Production Optimization | 🔴 Pending | 8-10h |
| **09** | Predictive Dashboard Enhancement | 🔴 Pending | 6-8h |
| **10** | ML Consolidation & Cleanup | 🔴 Pending | 6-8h |

**Full roadmap**: [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)

### Current ML Capabilities (Legacy)

- **Direct ML Service**: sklearn-based models with pickle storage
- **Energy Optimization**: RandomForest regressor (R² = 0.89)
- **Production Classification**: RandomForest classifier (90% accuracy)
- **Feature Engineering**: 13 engineered features from raw data

---

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- API keys (free tier sufficient):
  - REE: Public access (no key required)
  - AEMET: https://opendata.aemet.es/centrodedescargas/obtencionAPIKey
  - OpenWeatherMap: https://openweathermap.org/api

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/chocolate-factory.git
cd chocolate-factory

# Configure environment
cp .env.example .env
nano .env  # Add API keys

# Launch system
docker compose up -d

# Verify deployment
docker compose ps
docker compose logs -f chocolate_factory_brain
```

### Access Points

```bash
# Local dashboard (visual interface)
http://localhost:8000/dashboard

# API documentation (Swagger)
http://localhost:8000/docs

# InfluxDB admin
http://localhost:8086
```

---

## API Reference

### Data Ingestion

```bash
# Manual data ingestion
POST /ingest-now

# Hybrid weather data
GET /weather/hybrid

# Current REE prices
GET /ree/prices
```

### ML Operations

```bash
# Train models
POST /models/train

# Model status
GET /models/status-direct

# Predictions
POST /predict/energy-optimization
POST /predict/production-recommendation
```

### System Monitoring

```bash
# Scheduler status
GET /scheduler/status

# Data gaps detection
GET /gaps/summary

# Automatic backfill
POST /gaps/backfill/auto?max_gap_hours=6.0
```

### Dashboard Data

```bash
# Complete dashboard JSON
GET /dashboard/complete

# Weekly heatmap data
GET /dashboard/heatmap

# System alerts
GET /dashboard/alerts
```

---

## Development

### Project Structure

```
chocolate-factory/
├── src/fastapi-app/           # Main application
│   ├── main.py                # FastAPI entry point
│   ├── services/              # Business logic layer
│   │   ├── direct_ml.py       # ML training (legacy)
│   │   ├── dashboard.py       # Dashboard service
│   │   ├── ree_client.py      # REE API client
│   │   ├── siar_etl.py        # SIAR data ETL
│   │   └── weather_service.py # Weather integration
│   └── pyproject.toml         # Dependencies
├── docker/                    # Container infrastructure
│   ├── docker-compose.yml     # Main orchestration
│   ├── fastapi.Dockerfile     # Application container
│   └── services/              # Persistent data
│       ├── influxdb/data/     # Time series database
│       └── fastapi/models/    # ML model storage
├── models/                    # Trained ML models
├── .claude/                   # Project documentation
│   ├── sprints/ml-evolution/  # Sprint planning
│   ├── architecture.md        # System architecture
│   └── rules/                 # Business logic rules
└── CLAUDE.md                  # Main documentation
```

### Running Tests

```bash
# Unit tests
docker compose exec chocolate_factory_brain pytest tests/

# Integration tests
docker compose exec chocolate_factory_brain pytest tests/integration/

# ML model backtesting
curl -X POST http://localhost:8000/models/validate
```

### Development Workflow

1. Read current sprint: `.claude/sprints/ml-evolution/README.md`
2. Check active tasks in sprint document
3. Implement changes incrementally
4. Update sprint checklist (`- [ ]` → `- [x]`)
5. Commit with descriptive message
6. Deploy and verify

---

## Production Deployment

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Storage | 10 GB | 20 GB SSD |
| Network | Broadband | Ethernet |

### Deployment Modes

#### Mode 1: Local-Only (On-Premise)

Recommended for development and when remote access is not required.

```bash
# Standard deployment (no remote access)
docker compose up -d

# Access points (local network only)
http://localhost:8000/dashboard      # Dashboard
http://localhost:8000/docs           # Full API documentation
http://localhost:8086                # InfluxDB admin UI
```

**Characteristics**:
- ✓ Full API access on localhost
- ✓ Direct InfluxDB access
- ✓ No external network exposure
- ✓ Simplest configuration

#### Mode 2: Hybrid (On-Premise + Tailscale)

Recommended for production monitoring with secure remote access.

```bash
# 1. Generate Tailscale auth key
# Visit: https://login.tailscale.com/admin/settings/keys
# Create reusable key with tag 'chocolate-factory'

# 2. Configure Tailscale credentials
cp .env.tailscale.example .env.tailscale
nano .env.tailscale
# Set: TAILSCALE_AUTHKEY=<your-tailscale-authkey>
# Set: TAILSCALE_DOMAIN=<your-hostname> (auto-registered in Tailscale)

# 3. Deploy with Tailscale sidecar
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 4. Verify Tailscale registration
docker logs chocolate-factory | grep "Tailscale started"

# Access points
# Local (full access):
http://localhost:8000/docs           # Full API + admin
# Remote (read-only):
https://<your-tailscale-hostname>.ts.net/dashboard  # Dashboard only
```

**Characteristics**:
- ✓ Local: Full API access on localhost
- ✓ Remote: Dashboard monitoring via Tailscale
- ✓ Automatic SSL/TLS certificates
- ✓ Zero firewall configuration
- ✗ Admin APIs blocked remotely (security by design)

**Nginx Filtering** (Sidecar):
```nginx
# Allowed remotely
✓ /dashboard              # Main dashboard
✓ /dashboard/complete     # Dashboard data API
✓ /static/*               # Static resources

# Blocked remotely (403 Forbidden)
✗ /docs                   # API documentation
✗ /predict/*              # ML predictions
✗ /models/*               # Model management
✗ /influxdb/*             # Database access
✗ /gaps/*                 # Data backfill
✗ /scheduler/*            # Job management
```

### Data Persistence

All data persists through Docker bind mounts:
- **InfluxDB**: `./docker/services/influxdb/data/`
- **ML Models**: `./models/`
- **Logs**: `./docker/services/fastapi/logs/`

Backup strategy: Snapshot these directories regularly.

---

## Performance Metrics

### System Statistics

- **Total Records**: 131,513 (REE + Weather + SIAR historical)
- **Historical Coverage**: 25+ years (2000-2025)
- **API Response Time**: <100ms (local), <500ms (remote via Tailscale)
- **Dashboard Refresh**: 30 seconds (auto-refresh)
- **Uptime**: 99.5% (with auto-recovery)

### ML Model Performance (Legacy)

- **Energy Optimization**: R² = 0.89, MAE = 0.02 €/kWh
- **Production Classifier**: 90% accuracy (4-class classification)
- **Training Time**: ~15 seconds (with 42,578 samples)
- **Prediction Latency**: <50ms per request

---

## Documentation

Comprehensive documentation available in `/docs/` and `.claude/`:

### Technical Documentation
- **CLAUDE.md**: Complete project reference for AI assistance
- **architecture.md**: System architecture and design decisions
- **SYSTEM_ARCHITECTURE.md**: Detailed infrastructure documentation
- **TAILSCALE_INTEGRATION.md**: Remote access setup guide
- **SIAR_ETL_SOLUTION.md**: Historical data ingestion process

### Sprint Planning
- **ML Evolution Roadmap**: `.claude/sprints/ml-evolution/README.md`
- **Active Sprint**: `.claude/sprints/ml-evolution/SPRINT_06_PRICE_FORECASTING.md`
- **Future Sprints**: Sprint 07-10 documentation

### Business Logic
- **Production Rules**: `.claude/rules/production_rules.md`
- **Business Suggestions**: `.claude/rules/business-logic-suggestions.md`
- **Security Guidelines**: `.claude/rules/security-sensitive-data.md`

---

## Milestones

### ✅ Completed

- **Sprint 01-02**: Monolithic to microservices migration (Sept 2025)
- **Sprint 03**: Service layer architecture implementation
- **Sprint 04**: SIAR ETL - 88,935 historical records ingested
- **Sprint 05**: Unified dashboard + BusinessLogicService
- **Dashboard**: Weekly heatmap with interactive tooltips
- **Weather Integration**: Hybrid AEMET + OpenWeatherMap (24/7 coverage)
- **Backfill System**: Automatic gap detection and recovery

### 🟡 In Progress

- **Sprint 06**: REE price forecasting with LSTM/Prophet models
- **Heatmap Enhancement**: Real predictions vs historical data

### 🔴 Planned

- **Sprint 07-10**: Complete ML evolution (time series, optimization, consolidation)
- **Mobile Dashboard**: Responsive design for mobile devices
- **Extended Forecasts**: 14-day price predictions
- **Export Functionality**: PDF/CSV production planning reports

---

## Contributing

This is a reference implementation for industrial energy optimization. Contributions welcome:

- **Bug Reports**: Open issue with reproduction steps
- **Feature Requests**: Describe use case and expected behavior
- **Pull Requests**: Follow existing code structure and documentation standards

### Development Guidelines

1. Read `.claude/sprints/ml-evolution/README.md` for current priorities
2. Follow sprint-based development workflow
3. Update documentation alongside code changes
4. Maintain backward compatibility with existing APIs
5. Add tests for new functionality

---

## License

This project is provided as-is for educational and research purposes. Not intended for commercial production use without proper adaptation and validation.

---

## Support

- **Documentation**: Read `CLAUDE.md` and `.claude/` directory
- **Issues**: GitHub issue tracker
- **Architecture**: See `.claude/architecture.md`
- **Sprint Planning**: `.claude/sprints/ml-evolution/`

---

<div align="center">

**Industrial Energy Optimization System**

Built with FastAPI, InfluxDB, and Machine Learning

[📊 Documentation](CLAUDE.md) | [🏗️ Architecture](.claude/architecture.md) | [🚀 Sprint Roadmap](.claude/sprints/ml-evolution/README.md)

</div>
