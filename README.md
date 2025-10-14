# Chocolate Factory - Energy Optimization System

Containerized system for energy monitoring and production optimization with machine learning.

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?style=flat&logo=influxdb)](https://influxdata.com)
[![Tailscale](https://img.shields.io/badge/Tailscale-Zero--Trust-000000?style=flat&logo=tailscale)](https://tailscale.com)
[![ML](https://img.shields.io/badge/ML-131k_Records-10b981?style=flat)](https://github.com)

---

## Overview

Energy optimization system integrating Spanish electricity market data (REE), meteorological data (AEMET), and 25 years of historical weather records (SIAR). Provides ML-powered production recommendations.

**Features**:
- Prophet ML model for 168-hour electricity price prediction (MAE: 0.033 €/kWh)
- Hourly production planning based on energy costs and weather
- Claude Haiku chatbot for natural language queries
- 131,513 historical records for ML training
- Self-healing data pipeline with automatic gap detection
- Interactive dashboard with weekly heatmap

### Dashboard Preview

<table>
  <tr>
    <!-- Dashboard Principal -->
    <td style="text-align:center; width:50%;">
      <img src="docs/images/demo.gif"
           alt="Dashboard Principal - ML Predictions & Insights"
           style="max-width:100%; height:auto; border:1px solid #eaeaea;" />
      <p><em>Dashboard Principal - ML Predictions & Insights</em></p>
    </td>
    <!-- Chatbot BI -->
    <td style="text-align:center; width:50%;">
      <img src="docs/images/chat_Bot.gif"
           alt="Chatbot BI Conversacional - Claude Haiku"
           style="max-width:100%; height:auto; border:1px solid #eaeaea;" />
      <p><em>Chatbot BI Conversacional - Claude Haiku (Sprint 11)</em></p>
    </td>
  </tr>
</table>
---

## System Architecture

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

### Security Architecture

**Network**:
- Isolated Docker network (MTU 1280)
- No direct internet port exposure
- Tailscale sidecar as single external gateway

**Reverse Proxy (Nginx)**:
- Whitelist approach: `/dashboard` and static resources only
- Administrative endpoints blocked (`/docs`, `/predict`, `/models`, `/influxdb`)
- HTTP 403 for data modification endpoints

**Tailscale**:
- WireGuard-based encrypted tunnels
- Identity-based access
- Automatic SSL/TLS certificates

**Application**:
- Full API access restricted to localhost
- Dashboard provides read-only remote visibility

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI (Python 3.11+) | REST API + Dashboard |
| **Database** | InfluxDB 2.7 | Time series storage |
| **ML Framework** | scikit-learn, Prophet | Unified ML service (131k+ records) |
| **Chatbot** | Claude Haiku 3.5 | Conversational BI (RAG local) |
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

**Completed Sprints**: ML Evolution (06-10) + Infrastructure (11)

| Sprint | Description |
|--------|-------------|
| 06 | REE Price Forecasting (Prophet 168h) |
| 07 | SIAR Historical Analysis (88k records) |
| 08 | Hourly Optimization |
| 09 | Unified Predictive Dashboard |
| 10 | ML Consolidation & Cleanup |
| 11 | Chatbot BI (Claude Haiku API) |

**Documentation**: [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)

### Implemented Models

- **Price Forecasting**: Prophet 168h (MAE: 0.033 €/kWh, R²: 0.49)
- **Energy Optimization**: RandomForest regressor (R²: 0.89)
- **Production Recommendation**: RandomForest classifier (90% accuracy)
- **Historical Analysis**: SIAR correlations (25 years)
- **Predictive Insights**: Optimal windows, REE deviation tracking
- **Model Versioning**: 10 versions per model type

---

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- API keys:
  - AEMET: https://opendata.aemet.es/centrodedescargas/obtencionAPIKey
  - OpenWeatherMap: https://openweathermap.org/api
  - Anthropic (optional): https://console.anthropic.com/

### Project Structure

```
chocolate-factory/
├── src/fastapi-app/           # Main application
│   ├── main.py                # FastAPI entry point (3,734 lines)
│   ├── services/              # Business logic layer
│   │   ├── siar_analysis_service.py  # SIAR historical analysis
│   │   ├── dashboard.py       # Dashboard data service
│   │   ├── ree_client.py      # REE API client
│   │   ├── siar_etl.py        # SIAR ETL (88k records)
│   │   └── weather_service.py # Weather integration
│   └── pyproject.toml         # Dependencies
├── static/                    # Dashboard frontend (v0.41.0)
│   ├── index.html             # Main dashboard (432 lines)
│   ├── css/
│   │   └── dashboard.css      # Styles (826 lines)
│   └── js/
│       └── dashboard.js       # Logic + API calls (890 lines)
├── docker-compose.yml         # Main orchestration (2 containers)
├── docker-compose.override.yml # Tailscale sidecar (optional)
├── docker/                    # Container configuration
│   ├── fastapi.Dockerfile     # FastAPI image build
│   ├── tailscale-sidecar.Dockerfile # Tailscale sidecar image
│   ├── sidecar-nginx.conf     # Nginx reverse proxy config
│   ├── tailscale-start.sh     # Sidecar startup script
│   └── services/              # Persistent data
│       ├── influxdb/data/     # Time series database
│       └── fastapi/           # Application data
├── .claude/                   # Project documentation
│   ├── sprints/ml-evolution/  # Sprint 06-10 roadmap
│   ├── architecture.md        # System architecture
│   └── rules/                 # Business logic rules
└── CLAUDE.md                  # Development guide
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

#### Mode 1: Local-Only

```bash
docker compose up -d

# Access
http://localhost:8000/static/index.html  # Dashboard
http://localhost:8000/docs               # API documentation
http://localhost:8086                    # InfluxDB UI
```

#### Mode 2: Hybrid (Local + Tailscale)

```bash
# 1. Generate Tailscale auth key
# https://login.tailscale.com/admin/settings/keys

# 2. Configure credentials
cp .env.tailscale.example .env.tailscale
nano .env.tailscale
# Set TAILSCALE_AUTHKEY and TAILSCALE_DOMAIN

# 3. Deploy
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Access
# Local: http://localhost:8000/docs (full API)
# Remote: https://<hostname>.ts.net/dashboard (read-only)
```

**Remote Access (Nginx whitelist)**:
- Allowed: `/`, `/dashboard`, `/static/*`, `/dashboard/*`, `/insights/*`, `/optimize/*`, `/chat/*`
- Blocked: `/docs`, `/predict/*`, `/models/*`, `/influxdb/*`, `/gaps/*`, `/scheduler/*`, `/ree/*`, `/aemet/*`

### Data Persistence

Docker bind mounts:
- InfluxDB: `./docker/services/influxdb/data/`
- ML Models: `./models/`
- Logs: `./docker/services/fastapi/logs/`

---

## Documentation

**Technical** (`/docs/`):
- CLAUDE.md: Project reference
- architecture.md: System design
- TAILSCALE_INTEGRATION.md: Remote access
- SIAR_ETL_SOLUTION.md: Historical data

**Sprint Planning** (`.claude/sprints/`):
- ml-evolution/README.md: Roadmap
- infrastructure/README.md: Infrastructure sprints

**Business Logic** (`.claude/rules/`):
- production_rules.md
- business-logic-suggestions.md
- security-sensitive-data.md







## License

Provided as-is for educational and research purposes.

---

<div align="center">

Built with FastAPI, InfluxDB, and Machine Learning

[Documentation](CLAUDE.md) | [Architecture](.claude/architecture.md) | [Sprint Roadmap](.claude/sprints/ml-evolution/README.md)

</div>
