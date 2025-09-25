# Infraestructura del Sistema - Chocolate Factory

> **IMPORTANTE PARA CLAUDE**: Este documento define la arquitectura REAL del sistema. No asumas otras tecnologías. Usa SIEMPRE esta referencia.

## 🚀 Quick Reference para Claude Code

### Stack Confirmado (NO CAMBIAR)
- **Backend**: FastAPI (Python 3.11+) - NO Express, NO Django
- **Frontend**: HTML + JavaScript Vanilla - NO React, NO Vue, NO Angular
- **Database**: InfluxDB 2.7 - NO PostgreSQL, NO MongoDB
- **Proxy**: Nginx - NO Apache, NO Traefik
- **Container**: Docker Compose - NO Kubernetes, NO Swarm

### Rutas y Endpoints Principales
```python
# Dashboard
GET /dashboard → HTMLResponse (HTML embebido)
GET /dashboard/complete → JSON data
GET /dashboard/alerts → JSON alerts
GET /dashboard/recommendations → JSON recommendations

# APIs
POST /predict/* → ML predictions
GET /models/* → Model status
GET /gaps/* → Data gaps detection
GET /scheduler/* → Scheduler status
```

### Estructura de Archivos REAL
```
src/
├── fastapi-app/
│   ├── main.py                 # FastAPI app principal
│   ├── services/
│   │   ├── energy_service.py   # REE API
│   │   ├── weather_service.py  # AEMET/OpenWeather
│   │   ├── ml_service.py       # Modelos ML
│   │   └── influx_service.py   # InfluxDB client
│   └── routers/
│       ├── dashboard.py        # Dashboard routes
│       └── api.py              # API routes
├── models/                      # Pickled ML models
└── configs/                     # Configuraciones
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

#### 1. **chocolate_factory_brain** - FastAPI App
```yaml
Imagen: Custom (docker/fastapi.Dockerfile)
Puerto: 8000
Volúmenes:
  - ./src/fastapi-app/services:/app/services
  - ./models:/app/models
  - ./docker/services/fastapi/logs:/app/logs
Red: backend (192.168.100.0/24)
Función: API + Dashboard + ML + Scheduler
```

#### 2. **chocolate_factory_storage** - InfluxDB
```yaml
Imagen: influxdb:2.7
Puerto: 8086
Volúmenes:
  - ./docker/services/influxdb/data:/var/lib/influxdb2
  - ./docker/services/influxdb/config:/etc/influxdb2
Red: backend
Función: Time series data storage
```

#### 3. **chocolate-factory** - Tailscale Sidecar (Opcional)
```yaml
Imagen: Alpine + Tailscale
Puerto: 443 (HTTPS)
Función: Acceso remoto seguro vía Tailnet
Expone: Solo /dashboard (limitado)
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

### Endpoints de Dashboard

- **Local**: http://localhost:8000/dashboard
- **Nginx**: http://localhost/dashboard
- **Tailscale**: https://[machine-name].tailnet/dashboard

## Acceso por Rutas

### 1. Dashboard Principal
- **Ruta**: GET /dashboard
- **Tipo**: HTMLResponse (HTML + CSS + JS embebido)
- **Función**: Dashboard visual interactivo
- **Auto-refresh**: 30 segundos vía JavaScript

### 2. APIs de Datos
- **Base**: /dashboard/*
- **Formato**: JSON
- **Endpoints**:
  - `/dashboard/complete` - Dashboard completo
  - `/dashboard/alerts` - Alertas activas
  - `/dashboard/recommendations` - Recomendaciones
  - `/dashboard/heatmap` - Pronóstico semanal

### 3. APIs Operacionales
- `/predict/*` - Predicciones ML
- `/models/*` - Estado y entrenamiento ML
- `/gaps/*` - Detección y backfill de gaps
- `/scheduler/*` - Estado APScheduler

## Frontend: HTML + JavaScript

### Tecnología Confirmada
- **Framework**: Ninguno (Vanilla JS)
- **Renderizado**: Server-side (FastAPI HTMLResponse)
- **Datos**: Fetch API → JSON endpoints
- **Styling**: CSS3 con variables custom
- **Interactividad**: JavaScript ES6+

### Estructura Frontend
```
GET /dashboard → HTMLResponse
├── HTML Base (estructura)
├── CSS Embebido (estilos + responsive)
├── JavaScript Embebido (lógica + auto-refresh)
└── Fetch → /dashboard/complete (datos JSON)
```

### Auto-refresh Pattern
```javascript
// Pattern actual confirmado
setInterval(async () => {
    const response = await fetch('/dashboard/complete');
    const data = await response.json();
    updateDashboardElements(data);
}, 30000); // 30 segundos
```

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