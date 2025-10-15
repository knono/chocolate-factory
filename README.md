# Chocolate Factory - Energy Optimization System

Containerized system for energy monitoring and production optimization with machine learning and automated CI/CD.

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?style=flat&logo=influxdb)](https://influxdata.com)
[![Tailscale](https://img.shields.io/badge/Tailscale-SSL-000000?style=flat&logo=tailscale)](https://tailscale.com)
[![Forgejo](https://img.shields.io/badge/Forgejo-CI%2FCD-FB923C?style=flat&logo=forgejo)](https://forgejo.org)
[![ML](https://img.shields.io/badge/ML-131k_Records-10b981?style=flat)](https://github.com)

---

## Overview

Energy optimization system with ML-powered predictions, automated CI/CD, and self-hosted infrastructure.

**Core Features**:
- Prophet ML: 168-hour electricity price forecasting (MAE: 0.033 €/kWh)
- Clean Architecture: Refactored FastAPI application (41 modules)
- CI/CD: Forgejo self-hosted + Gitea Actions dual environment
- Chatbot: Claude Haiku conversational BI with RAG
- Data: 131,513 records (REE + AEMET + SIAR 25 years)
- Self-healing: Automatic gap detection and backfill
- Security: Tailscale SSL + nginx reverse proxy

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

### Production Infrastructure (3 Tailscale Nodes)

```
┌──────────────────────────────────────────────────────────────────┐
│  TAILSCALE NETWORK (Zero-Trust VPN)                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────────┐    │
│  │  NODE 1: GIT/CI/CD     │  │  NODE 2: DEVELOPMENT       │    │
│  │  git.*.ts.net          │  │  *-dev.ts.net              │    │
│  │                        │  │                            │    │
│  │  - Forgejo 1.21        │  │  - FastAPI (dev)           │    │
│  │  - Runners (dev/prod)  │  │  - InfluxDB shared (read)  │    │
│  │  - Docker Registry     │  │  - Hot reload enabled      │    │
│  │  - Nginx SSL           │  │  - Port 8001               │    │
│  └────────────────────────┘  └────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │  NODE 3: PRODUCTION                                │         │
│  │  *.ts.net                                          │         │
│  │                                                    │         │
│  │  - FastAPI (prod)                                 │         │
│  │  - InfluxDB (data ingestion)                      │         │
│  │  - ML models                                      │         │
│  │  - APScheduler (11 jobs)                          │         │
│  │  - Port 8000                                      │         │
│  │  - Nginx SSL                                      │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

CI/CD Pipeline: develop → dev | main → prod
SSL: Automatic Tailscale ACME certificates
Secrets: SOPS encrypted (fallback .env)
```

### Application Architecture (Clean Architecture - Oct 2025)

```
src/fastapi-app/
├── main.py (76 lines)           # Entry point
├── api/                         # HTTP Interface
│   ├── routers/                 # Endpoints (health, dashboard, ree, weather,
│   │                            #   optimization, analysis, insights, gaps, chatbot)
│   └── schemas/                 # Pydantic models
├── domain/                      # Business Logic
│   ├── energy/forecaster.py    # Price forecasting
│   └── ml/model_trainer.py     # ML validation
├── services/                    # Orchestration
│   ├── ree_service.py          # REE + InfluxDB
│   ├── weather_aggregation.py  # Multi-source weather
│   ├── dashboard.py            # Data consolidation
│   ├── predictive_insights.py  # Sprint 09
│   ├── chatbot_service.py      # Claude Haiku API
│   └── backfill_service.py     # Gap recovery
├── infrastructure/              # External Systems
│   ├── influxdb/               # DB client + queries
│   └── external_apis/          # REE, AEMET, OpenWeatherMap
├── core/                        # Utilities
│   ├── config.py               # Settings
│   ├── logging_config.py       # Structured logging
│   └── exceptions.py           # Error handling
└── tasks/                       # Background Jobs
    ├── ree_jobs.py             # REE ingestion
    ├── weather_jobs.py         # Weather ingestion
    └── scheduler_config.py     # APScheduler

Refactoring: 3,838 → 76 lines main.py (98% reduction)
Architecture: Clean Architecture compliant
Modules: 41 Python files organized by layer
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
| **ML Framework** | scikit-learn, Prophet | 131k+ records ML training |
| **Chatbot** | Claude Haiku 3.5 | Conversational BI (RAG) |
| **CI/CD** | Forgejo + Gitea Actions | Self-hosted automation |
| **Registry** | Docker Registry 2.8 | Private image storage |
| **Scheduling** | APScheduler | 11 automated jobs |
| **Containerization** | Docker Compose | Orchestration |
| **Reverse Proxy** | Nginx (Alpine) | SSL + endpoint filtering |
| **VPN** | Tailscale (WireGuard) | Zero-trust mesh network |
| **Secrets** | SOPS + age | Encrypted secrets management |

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

## Implementation Status

**Completed Sprints**: ML Evolution (06-11) + Infrastructure (12 partial)

| Sprint | Status | Description |
|--------|--------|-------------|
| 06 | ✅ Complete | Prophet Price Forecasting (168h MAE 0.033) |
| 07 | ✅ Complete | SIAR Historical Analysis (88k records, 25y) |
| 08 | ✅ Complete | Hourly Production Optimization |
| 09 | ✅ Complete | Unified Predictive Dashboard |
| 10 | ✅ Complete | ML Consolidation + Clean Architecture |
| 11 | ✅ Complete | Chatbot BI (Claude Haiku + RAG) |
| 12 | 🔵 In Progress | Forgejo CI/CD (Phases 1-8 done, 9-11 pending) |
| 13 | ⏳ Planned | Tailscale MCP Server (local integration) |

**Phase 12 Status**:
- Phases 1-8: Infrastructure completed (Forgejo + runners + dual environment + SSL)
- Phases 9-11: Testing suite pending (88 tests target)
- Phase 12: SOPS secrets optional

**Documentation**:
- ML: [`.claude/sprints/ml-evolution/README.md`](.claude/sprints/ml-evolution/README.md)
- CI/CD: [`.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`](.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md)

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
├── src/fastapi-app/           # Clean Architecture (Oct 2025)
│   ├── main.py                # Entry point (76 lines)
│   ├── api/                   # HTTP Interface Layer
│   │   ├── routers/           # 9 routers (health, dashboard, ree, weather, etc.)
│   │   └── schemas/           # Pydantic models
│   ├── domain/                # Business Logic Layer
│   │   ├── energy/            # Forecasting logic
│   │   └── ml/                # Model training validation
│   ├── services/              # Application Layer
│   │   ├── ree_service.py     # REE orchestration
│   │   ├── dashboard.py       # Data consolidation
│   │   ├── chatbot_service.py # Claude Haiku integration
│   │   └── backfill_service.py # Gap recovery
│   ├── infrastructure/        # External Systems Layer
│   │   ├── influxdb/          # DB client + queries
│   │   └── external_apis/     # REE, AEMET, OpenWeatherMap
│   ├── core/                  # Utilities
│   └── tasks/                 # APScheduler jobs
├── docker/                    # Infrastructure
│   ├── docker-compose.yml     # Production (2 containers)
│   ├── docker-compose.dev.yml # Development environment
│   ├── docker-compose.prod.yml # Production environment
│   ├── forgejo-compose.yml    # Git/CI/CD node
│   ├── gitea-runners-compose.yml # CI/CD runners
│   ├── registry-compose.yml   # Docker registry
│   └── services/              # Persistent data
│       ├── influxdb/{dev,prod}-data/
│       ├── forgejo/data/      # Git repository
│       ├── gitea-runner/{dev,prod}-data/
│       └── registry/data/     # Image storage
├── .gitea/workflows/          # CI/CD Pipelines
│   ├── ci-cd-dual.yml         # Main pipeline (dual env)
│   └── quick-test.yml         # Fast PR validation
├── .claude/                   # Documentation
│   ├── sprints/
│   │   ├── ml-evolution/      # Sprints 06-11
│   │   └── infrastructure/    # Sprints 12-13
│   ├── architecture.md        # System design
│   └── rules/                 # Business logic
├── docs/                      # Technical docs
│   ├── CI_CD_PIPELINE.md      # Pipeline documentation
│   ├── GITFLOW_CICD_WORKFLOW.md # Git workflow
│   └── DUAL_ENVIRONMENT_SETUP.md # Environment setup
└── CLAUDE.md                  # Development guide
```

### Running Tests

**⚠️ Note**: Testing suite implementation pending (Sprint 12 Phase 9-11).

Planned test structure:
```bash
# Unit tests (25 tests target)
pytest src/fastapi-app/tests/unit/ -v --cov

# Integration tests (19 tests target)
pytest src/fastapi-app/tests/integration/ -v

# ML regression tests (24 tests target)
pytest src/fastapi-app/tests/ml/ -v

# Full suite (88 tests target, coverage >85%)
pytest src/fastapi-app/tests/ -v --cov --cov-report=term-missing
```

Current test files:
- `test_foundation.py`: Architecture validation
- `test_architecture.py`: Clean Architecture compliance
- `test_infrastructure.py`: Infrastructure layer validation

### Development Workflow (Git Flow + CI/CD)

1. Feature development:
   ```bash
   git checkout develop
   git flow feature start my-feature
   # ... make changes ...
   git flow feature finish my-feature
   git push origin develop  # → Triggers CI/CD → Deploys to dev
   ```

2. Release to production:
   ```bash
   git flow release start 0.63.0
   # ... version bump, CHANGELOG update ...
   git flow release finish 0.63.0
   git checkout main
   git push origin main --follow-tags  # → Triggers CI/CD → Deploys to prod
   git checkout develop
   git push origin develop
   ```

3. CI/CD pipeline validates:
   - Tests pass (when implemented)
   - Docker image builds
   - Deployment succeeds
   - Health check passes

See: [`docs/GITFLOW_CICD_WORKFLOW.md`](docs/GITFLOW_CICD_WORKFLOW.md)

---

## Production Deployment

### Infrastructure Requirements

**Three-Node Setup (Recommended)**:

| Node | CPU | RAM | Storage | Purpose |
|------|-----|-----|---------|---------|
| Git/CI/CD | 2 cores | 2 GB | 10 GB | Forgejo + runners + registry |
| Development | 2 cores | 2 GB | 10 GB | Testing environment |
| Production | 4 cores | 4 GB | 20 GB SSD | Main application + InfluxDB |

**Single-Node Setup (Development)**:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Storage | 10 GB | 20 GB SSD |

### Deployment Options

#### Option 1: Production (3 Nodes + CI/CD)

Full production setup with automated deployments:

```bash
# Node 1: Git/CI/CD
cd docker
docker compose -f forgejo-compose.yml up -d
docker compose -f gitea-runners-compose.yml up -d
docker compose -f registry-compose.yml up -d

# Node 2: Development
docker compose -f docker-compose.dev.yml up -d

# Node 3: Production
docker compose -f docker-compose.prod.yml up -d

# Tailscale sidecars (each node)
docker compose -f docker-compose.override.yml up -d
```

Access:
- Git: `https://git.your-tailnet.ts.net`
- Dev: `https://dev.your-tailnet.ts.net` (port 8001)
- Prod: `https://your-tailnet.ts.net` (port 8000)

#### Option 2: Local Development

Single-node development without CI/CD:

```bash
docker compose up -d

# Access
http://localhost:8000/docs               # Full API
http://localhost:8000/dashboard          # Dashboard
http://localhost:8086                    # InfluxDB UI
```

#### Option 3: Local + Remote Access

Single-node with Tailscale sidecar:

```bash
# Configure Tailscale
cp .env.example .env
# Set TAILSCALE_AUTHKEY and TAILSCALE_DOMAIN

# Deploy
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Access
# Local: http://localhost:8000/docs (full API)
# Remote: https://<hostname>.ts.net/dashboard (filtered)
```

### CI/CD Pipeline

Automated deployments via Forgejo:

- `git push origin develop` → Build → Test → Deploy to development
- `git push origin main` → Build → Test → Deploy to production
- SOPS-encrypted secrets
- Automatic health checks
- Rollback on failure (planned)

### Data Persistence

Docker bind mounts:
- InfluxDB: `./docker/services/influxdb/data/`
- ML Models: `./models/`
- Logs: `./docker/services/fastapi/logs/`

---

## Documentation

**Development** (`/`):
- `CLAUDE.md`: Complete project reference
- `.claude/architecture.md`: System design

**Sprint Documentation** (`.claude/sprints/`):
- `ml-evolution/README.md`: Sprints 06-11 (ML features)
- `infrastructure/SPRINT_12_FORGEJO_CICD.md`: CI/CD implementation
- `infrastructure/README.md`: Infrastructure roadmap

**Technical Guides** (`/docs/`):
- `CI_CD_PIPELINE.md`: Pipeline architecture and troubleshooting
- `GITFLOW_CICD_WORKFLOW.md`: Git workflow with CI/CD
- `DUAL_ENVIRONMENT_SETUP.md`: Dev/prod environment configuration
- `CLEAN_ARCHITECTURE_REFACTORING.md`: Architecture migration guide
- `API_REFERENCE.md`: Complete API documentation
- `AUTOMATIC_BACKFILL_SYSTEM.md`: Gap detection and recovery
- `SOPS_SECRETS_MANAGEMENT.md`: Secrets encryption

**Business Rules** (`.claude/rules/`):
- `production_rules.md`: Production optimization logic
- `business-logic-suggestions.md`: ML recommendations
- `security-sensitive-data.md`: Data protection guidelines







## License

Provided as-is for educational and research purposes.

---

## Quick Links

| Resource | Description |
|----------|-------------|
| [Development Guide](CLAUDE.md) | Complete project reference |
| [Architecture](.claude/architecture.md) | System design and Clean Architecture |
| [ML Sprints](.claude/sprints/ml-evolution/README.md) | Sprints 06-11 roadmap |
| [CI/CD Sprint](.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md) | Sprint 12 implementation |
| [API Docs](docs/API_REFERENCE.md) | Complete API reference |
| [Git Workflow](docs/GITFLOW_CICD_WORKFLOW.md) | Git Flow + CI/CD guide |

---

<div align="center">

Built with FastAPI, InfluxDB, Prophet ML, Forgejo CI/CD, and Tailscale

**Status**: Sprint 12 in progress (CI/CD complete, testing pending) | Sprint 13 planned (Tailscale MCP)

</div>
