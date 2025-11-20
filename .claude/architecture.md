# Infraestructura del Sistema - Chocolate Factory

> **IMPORTANTE PARA CLAUDE**: Este documento define la arquitectura REAL del sistema. No asumas otras tecnologías. Usa SIEMPRE esta referencia.

## 🚀 Quick Reference para Claude Code

### Stack Confirmado (NO CAMBIAR)
- **Backend**: FastAPI (Python 3.11+) - NO Express, NO Django
- **Frontend**: HTML + JavaScript Vanilla - NO React, NO Vue, NO Angular
- **Database**: InfluxDB 2.7 - NO PostgreSQL, NO MongoDB
- **Proxy**: Nginx - NO Apache, NO Traefik
- **Container**: Docker Compose - NO Kubernetes, NO Swarm

### Routers y Endpoints
```python
# Health
GET /health, /ready, /version

# Data APIs
GET /ree/prices
GET /weather/hybrid

# ML Predictions
POST /predict/energy-optimization
POST /predict/production-recommendation
POST /predict/train, /predict/train/hybrid

# Price Forecasting
GET /predict/prices/weekly, /hourly
POST /models/price-forecast/train
GET /models/price-forecast/status

# Analysis
GET /analysis/weather-correlation, /seasonal-patterns, /critical-thresholds, /siar-summary
POST /analysis/forecast/aemet-contextualized

# Production Optimization
POST /optimize/production/daily
GET /optimize/production/summary

# Insights
GET /insights/optimal-windows, /ree-deviation, /alerts, /savings-tracking

# Gaps & Backfill
GET /gaps/summary, /gaps/detect
POST /gaps/backfill, /gaps/backfill/auto, /gaps/backfill/range

# Chatbot
POST /chat/ask
GET /chat/stats, /chat/health

# Dashboard
GET /dashboard, /dashboard/complete, /dashboard/summary, /dashboard/alerts

# Health Monitoring
GET /health-monitoring/summary, /critical, /alerts, /nodes, /uptime/{hostname}, /logs
```

### Estructura de Archivos Real
```
src/fastapi-app/
├── main.py                     # Entry point
├── api/routers/               # 12 routers
│   ├── health.py, ree.py, weather.py, dashboard.py
│   ├── price_forecast.py, ml_predictions.py
│   ├── optimization.py, analysis.py
│   ├── gaps.py, insights.py, chatbot.py
│   └── health_monitoring.py
├── services/                   # 30+ application services
├── domain/                     # Business logic
├── infrastructure/             # External API clients
├── core/                       # Config, logging, exceptions
├── tasks/                      # APScheduler jobs
├── models/                     # Pickled ML models
└── tests/                      # 102 tests
```

---

## Arquitectura General

### Stack Tecnológico ✅ CONFIRMADO
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: HTML5 + JavaScript Vanilla + CSS3
- **Base de Datos**: InfluxDB 2.7 (Time Series)
- **Proxy**: Nginx (reverse proxy + SSL termination)
- **Orquestación**: Docker Compose
- **Acceso Remoto**: Tailscale (opcional)

### Contenedores en Producción

#### 1. **chocolate_factory_brain** - FastAPI
```yaml
Imagen: docker/fastapi.Dockerfile
Puerto: 8000
Volúmenes: Services, models, logs, static files, .claude rules
Red: backend (192.168.100.0/24)
Función: API + Dashboard + ML + APScheduler
```

#### 2. **chocolate_factory_storage** - InfluxDB
```yaml
Imagen: influxdb:2.7
Puerto: 8086
Volúmenes: Data, config
Red: backend
Función: Time series database
```

#### 3. **chocolate-factory** - Tailscale Sidecar (Opcional)
```yaml
Imagen: Alpine + Tailscale
Puerto: 443 (HTTPS)
Función: Remote access via Tailnet
Expone: /dashboard, /static, limited API
```

## Arquitectura de Red

### Routing y Proxy

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Tailscale     │    │      Nginx      │    │    FastAPI      │
│   (Opcional)    │───▶│  Reverse Proxy  │───▶│   Port 8000     │
│   Port 443      │    │   Port 80/443   │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    InfluxDB     │
                        │   Port 8086     │
                        └─────────────────┘
```

### Access Points

- **Local**: http://localhost:8000/dashboard
- **API Dev**: http://localhost:8000/docs
- **Tailscale**: https://<your-tailnet-host>/dashboard (via Tailnet)

## API Endpoints

### Dashboard
- **GET /dashboard** - HTMLResponse with embedded static files
- **GET /dashboard/complete** - Full JSON dashboard data
- **GET /dashboard/summary** - Quick summary
- **GET /dashboard/alerts** - System alerts

### Data Ingestion
- **GET /ree/prices** - Current electricity prices
- **GET /weather/hybrid** - Current weather (AEMET/OpenWeather)
- **POST /ingest-now** - Manual ingestion trigger

### ML Operations
- **POST /predict/energy-optimization** - Energy score (0-100)
- **POST /predict/production-recommendation** - Production class (scoring determinístico)
- **POST /predict/train** - Train sklearn scoring systems (90 días REE)
- **POST /predict/train/hybrid** - SIAR + REE hybrid training (deprecated)

### Price Forecasting
- **GET /predict/prices/weekly** - 7-day Prophet forecast
- **GET /predict/prices/hourly** - Configurable horizon (1-168h)
- **POST /models/price-forecast/train** - Train Prophet
- **GET /models/price-forecast/status** - Model metrics

### Analysis & Optimization
- **GET /analysis/*/** - SIAR historical analysis
- **POST /optimize/production/daily** - 24h production plan
- **GET /optimize/production/summary** - Optimization metrics

### Insights & Alerts
- **GET /insights/optimal-windows** - Next 7 days windows
- **GET /insights/ree-deviation** - D-1 vs Real analysis
- **GET /insights/alerts** - Predictive alerts (24-48h)
- **GET /insights/savings-tracking** - Real savings tracking

### Gap Management
- **GET /gaps/summary** - Data status overview
- **GET /gaps/detect** - Detailed gap analysis
- **POST /gaps/backfill** - Manual backfill
- **POST /gaps/backfill/auto** - Auto intelligent backfill

### Chatbot
- **POST /chat/ask** - Question submission
- **GET /chat/stats** - Usage statistics
- **GET /chat/health** - Service health

### Health Monitoring
- **GET /health-monitoring/summary** - System health overview
- **GET /health-monitoring/critical** - Critical nodes
- **GET /health-monitoring/nodes** - Detailed node info
- **GET /health-monitoring/logs** - Event logs (paginated)

## Frontend Architecture

### Technology Stack
- **Framework**: Vanilla JavaScript (no dependencies)
- **Styling**: CSS3 with custom properties
- **Build**: Static files (no bundler)
- **Data**: Fetch API to JSON endpoints

### Directory Structure
```
static/
├── index.html              # Main dashboard
├── vpn.html                # Tailscale-only dashboard
├── css/
│   └── dashboard.css       # Styles
├── js/
│   └── dashboard.js        # Logic + API calls
├── assets/                 # Images, icons
└── README.md
```

### Data Flow
1. Browser loads `GET /dashboard` → static files served
2. JavaScript calls `GET /dashboard/complete` for JSON
3. Auto-refresh every 30s via `setInterval`
4. Real-time updates without page reload

### Static Files Strategy
- Served directly from FastAPI `/static` directory
- No HTML/CSS/JS embedded in Python
- Reduces main.py maintainability
- Clear separation of concerns

## Datos y Persistencia

### InfluxDB Structure
```
Bucket: energy_data
├── Measurement: energy_prices
│   ├── Field: price_eur_kwh
│   └── Tags: source=REE, region=spain
├── Measurement: weather_data  
│   ├── Fields: temperature, humidity, pressure
│   └── Tags: source=AEMET|OpenWeatherMap
└── Measurement: predictions
    ├── Fields: energy_score, production_class
    └── Tags: model_version, confidence
```

### Modelos ML (Pickle Storage)
```
./models/
├── latest/
│   ├── energy_optimization.pkl → ../energy_optimization_20250925_143022.pkl
│   └── production_classifier.pkl → ../production_classifier_20250925_143022.pkl
├── energy_optimization_20250925_143022.pkl
├── production_classifier_20250925_143022.pkl
└── model_registry.json
```

## Seguridad y Acceso

### Niveles de Acceso

#### 1. Local Development (Sin restricciones)
- **URL**: http://localhost:8000/*
- **Acceso**: API completa + Dashboard
- **Auth**: Ninguna
- **Uso**: Desarrollo y testing

#### 2. Nginx Proxy (Producción local)
- **URL**: http://localhost/*
- **Acceso**: Dashboard + APIs filtradas
- **Auth**: Básica (opcional)
- **Uso**: Operaciones locales

#### 3. Tailscale Remote (Acceso remoto)
- **URL**: https://[machine].tailnet/*
- **Acceso**: Solo /dashboard (limitado)
- **Auth**: Tailscale SSO
- **Uso**: Monitoreo remoto

### Variables de Entorno Sensibles
```bash
# APIs Externas
AEMET_API_KEY=xxxxx
OPENWEATHERMAP_API_KEY=xxxxx
REE_API_TOKEN=xxxxx (no requerido)

# InfluxDB
INFLUXDB_TOKEN=xxxxx
INFLUXDB_ADMIN_PASSWORD=xxxxx

# Tailscale (opcional)
TAILSCALE_AUTHKEY=xxxxx
TAILSCALE_DOMAIN=machine-name.tailnet
```

## Logging y Monitoreo

### Estructura de Logs
```
./docker/services/fastapi/logs/
├── application.log (FastAPI + servicios)
├── scheduler.log (APScheduler jobs)
├── ml_training.log (Entrenamiento modelos) 
└── data_ingestion.log (Ingestión datos)
```

### Monitoreo Automático
- **Health checks**: /health endpoint
- **Scheduler status**: /scheduler/status
- **Data gaps**: /gaps/summary
- **Model performance**: /models/status-direct

## Despliegue y DevOps

### Docker Compose Profiles
```bash
# Desarrollo (2 containers)
docker compose up -d

# Producción + Tailscale (3 containers)  
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Solo servicios core
docker compose up -d fastapi-app influxdb
```

### Persistence Strategy
- **Data**: Bind mounts (no volumes)
- **Modelos**: Bind mount ./models
- **Configuración**: Bind mount ./src/configs
- **Logs**: Bind mount para debugging

### Backup Considerations
```bash
# Críticos para backup
./docker/services/influxdb/data/  # Base de datos
./models/                          # Modelos ML entrenados
./.env                            # Variables de entorno
./docker-compose.yml              # Configuración orquestación
```

## Notas de Implementación

### Decisiones de Arquitectura
1. **HTML+JS Vanilla**: Simplicidad, velocidad, sin dependencias frontend
2. **Server-side Templates**: HTMLResponse de FastAPI (no JSX/Vue/React)
3. **JSON APIs**: Separación clara datos/presentación
4. **Nginx Optional**: Para SSL y filtrado en producción
5. **Tailscale Sidecar**: Acceso remoto sin VPN tradicional

### Performance Optimizations
- **Auto-refresh inteligente**: Solo si hay cambios
- **API caching**: Cache en memoria para datos frecuentes
- **Lazy loading**: Dashboard carga incremental
- **Compression**: Gzip en Nginx para assets

### Limitaciones Conocidas
- **Frontend básico**: Sin framework moderno (por diseño)
- **Auth básica**: Sin sistema complejo de usuarios
- **Monitoreo simple**: Sin Prometheus/Grafana integrados
- **Clustering**: Diseño single-node (escalable si necesario)

---

## Reglas para Claude Code

⚠️ **IMPORTANTE**: 
- **NO** sugieras cambiar el stack tecnológico
- **NO** propongas React, Vue, Angular o similares
- **NO** recomiendes PostgreSQL o MongoDB
- **USA** exactamente las rutas y endpoints documentados
- **RESPETA** la estructura de archivos existente
- **MANTÉN** el patrón HTML + JS Vanilla para el frontend