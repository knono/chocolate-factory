# Node-RED Dashboard Setup Guide
**TFM Chocolate Factory - El Monitor (Dashboard Read-Only)**

## 📋 Resumen

Esta guía describe la configuración completa del dashboard Node-RED para monitoreo en tiempo real de la fábrica de chocolate, incluyendo métricas energéticas, datos climáticos, predicciones ML y alertas de producción.

## 🏗️ Arquitectura del Dashboard

### Componentes Principales
```
🍫 Chocolate Factory Dashboard
├── 📊 Real-time Metrics    (Gauges: Precio, Temperatura, Humedad)
├── 📈 Historical Trends    (Charts: Tendencias 24h)
├── 🤖 ML Predictions      (Status: Modelos + Predicciones)
└── 🚨 Production Alerts   (Alertas: Recomendaciones + Urgencia)
```

### Fuentes de Datos
- **InfluxDB**: Datos históricos (precios REE + clima)
- **FastAPI**: APIs de modelos ML y predicciones
- **MLflow**: Estado de experimentos y modelos

## 🚀 Configuración Paso a Paso

### 1. Acceso a Node-RED
```bash
# Node-RED está disponible en:
http://localhost:1880

# Dashboard se mostrará en:
http://localhost:1880/ui
```

### 2. Instalación de Nodos Requeridos

#### a) Nodos de Dashboard
```
node-red-dashboard          # UI elements (gauges, charts, etc.)
node-red-contrib-influxdb   # InfluxDB integration
```

#### b) Instalación via Node-RED Interface
1. **Menu → Manage palette → Install**
2. **Buscar e instalar:**
   - `node-red-dashboard`
   - `node-red-contrib-influxdb`

#### c) Instalación via Docker (Alternativo)
```bash
# Si necesitas instalar vía docker exec:
docker exec -it chocolate_factory_monitor npm install node-red-dashboard node-red-contrib-influxdb
```

### 3. Configuración de InfluxDB Connection

#### Configuración del Nodo InfluxDB
```json
{
  "hostname": "influxdb",
  "port": "8086", 
  "protocol": "http",
  "database": "chocolate_factory",
  "version": "2.0",
  "url": "http://influxdb:8086",
  "organization": "chocolate_factory_org",
  "token": "[INFLUXDB_TOKEN from .env]"
}
```

#### Variables de Entorno Disponibles
```bash
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=[token]
INFLUXDB_ORG=chocolate_factory_org  
INFLUXDB_BUCKET=chocolate_factory
```

### 4. Importación del Flow

#### Opción A: Import via JSON File
1. **Copy content** from `docker/services/nodered/flows/chocolate_factory_dashboard.json`
2. **Node-RED Menu → Import → Clipboard**
3. **Paste JSON** and confirm import

#### Opción B: Manual Flow Creation
Follow the flow structure described in this document to create manually.

## 📊 Componentes del Dashboard

### 1. Real-time Metrics (Gauges)

#### a) Energy Price Gauge
```javascript
// Query para último precio REE
from(bucket: "chocolate_factory")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> filter(fn: (r) => r._field == "price_eur_kwh")
  |> last()
```

**Configuración:**
- **Rango**: 0 - 0.4 €/kWh
- **Colores**: Verde (< 0.15), Amarillo (0.15-0.25), Rojo (> 0.25)
- **Actualización**: Cada 5 minutos

#### b) Temperature Gauge
```javascript
// Query para temperatura actual
from(bucket: "chocolate_factory")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r._field == "temperature")
  |> last()
```

**Configuración:**
- **Rango**: 0 - 45°C
- **Colores**: Verde (18-24°C), Amarillo (24-30°C), Rojo (>30°C)
- **Actualización**: Cada 5 minutos

#### c) Humidity Gauge
```javascript
// Query para humedad actual
from(bucket: "chocolate_factory")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r._field == "humidity")
  |> last()
```

**Configuración:**
- **Rango**: 0 - 100%
- **Colores**: Rojo (<40%), Verde (40-70%), Rojo (>70%)
- **Actualización**: Cada 5 minutos

### 2. Historical Trends (Charts)

#### a) Energy Price Trend (24h)
```javascript
// Query para tendencia precio 24h
from(bucket: "chocolate_factory")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> filter(fn: (r) => r._field == "price_eur_kwh")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
```

#### b) Temperature & Humidity Trends
```javascript
// Query combinada para clima 24h
from(bucket: "chocolate_factory")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
```

### 3. ML Predictions Status

#### a) Models Status API Call
```javascript
// HTTP Request to FastAPI
GET http://fastapi-app:8000/models/status

// Response processing
{
  "models": {
    "energy_optimization": {
      "status": "trained",
      "last_r2_score": "0.8876"
    },
    "production_classifier": {
      "status": "trained", 
      "last_accuracy": "0.9000"
    }
  }
}
```

#### b) Real-time Predictions
```javascript
// HTTP Request for prediction
POST http://fastapi-app:8000/predict/production-recommendation
{
  "price_eur_kwh": current_price,
  "temperature": current_temp,
  "humidity": current_humidity
}

// Response shows:
{
  "prediction": {
    "production_recommendation": "Optimal_Production",
    "chocolate_production_index": 75.2,
    "urgency": "low"
  }
}
```

### 4. Production Alerts

#### Alert Levels & Colors
```javascript
// Alert color mapping
const alertColors = {
  "low": "green",        // Optimal_Production
  "medium": "yellow",    // Moderate_Production  
  "high": "orange",      // Reduced_Production
  "critical": "red"      // Halt_Production
};
```

#### Alert Messages
- **🟢 Optimal**: "Condiciones óptimas para producción máxima"
- **🟡 Moderate**: "Condiciones aceptables, producción reducida recomendada"
- **🟠 Reduced**: "Condiciones subóptimas, considerar reducir producción"
- **🔴 Halt**: "Condiciones críticas, detener producción temporalmente"

## ⏰ Scheduling & Updates

### Timers Configuration
```javascript
// Data refresh intervals
Real-time metrics: 5 minutes    // InfluxDB queries
ML predictions: 30 seconds      // FastAPI calls
Charts: 5 minutes              // Historical data
Alerts: 30 seconds             // Production recommendations
```

### Update Logic
1. **Timer triggers** → Query execution
2. **Data processing** → Format for dashboard
3. **UI update** → Display new values
4. **Error handling** → Fallback to last known values

## 🔧 Troubleshooting

### Common Issues

#### 1. InfluxDB Connection Failed
```bash
# Check InfluxDB container
docker logs chocolate_factory_storage

# Verify token in Node-RED config
# Should match INFLUXDB_TOKEN from .env
```

#### 2. FastAPI Endpoints Not Responding
```bash
# Check FastAPI container
docker logs chocolate_factory_brain

# Test endpoints manually
curl http://localhost:8000/models/status
curl http://localhost:8000/health
```

#### 3. Dashboard Not Loading
```bash
# Check Node-RED container
docker logs chocolate_factory_monitor

# Verify dashboard nodes installed
# Menu → Manage palette → Installed
```

#### 4. No Data in Charts
- **Verify InfluxDB has data**: `curl http://localhost:8000/influxdb/verify`
- **Check query syntax**: Ensure Flux queries are correct
- **Confirm time ranges**: Data may be outside query window

### Debug Queries

#### Test InfluxDB Connection
```javascript
// Simple test query
from(bucket: "chocolate_factory")
  |> range(start: -1h)
  |> limit(n: 1)
```

#### Test FastAPI Connection
```javascript
// Node-RED HTTP request node
GET http://fastapi-app:8000/health
// Should return: {"status":"healthy"}
```

## 📱 Dashboard Layout

### Responsive Design
```
Desktop (1920px):
┌─────────────────────────────────────┐
│ 📊 Real-time Metrics               │
│ [Price] [Temp] [Humidity]          │
├─────────────────────────────────────┤
│ 📈 Historical Trends               │
│ [24h Price Chart - Full Width]     │
├─────────────────────────────────────┤
│ 🤖 ML Predictions                  │
│ [Energy] [Classifier] [MLflow]     │
├─────────────────────────────────────┤
│ 🚨 Production Alerts               │
│ [Recommendation] [Alert Level]     │
└─────────────────────────────────────┘

Mobile (768px):
┌─────────────────┐
│ 📊 Metrics     │
│ [Price]        │
│ [Temp]         │
│ [Humidity]     │
├─────────────────┤
│ 📈 Trends      │
│ [Chart]        │
├─────────────────┤
│ 🤖 ML Status   │
│ [Models]       │
├─────────────────┤
│ 🚨 Alerts      │
│ [Production]   │
└─────────────────┘
```

## 🎨 Visual Customization

### Color Schemes
```css
/* Energy Price Colors */
Optimal (< 0.15): #00b04f    /* Green */
Warning (0.15-0.25): #e6e600 /* Yellow */
Critical (> 0.25): #ca3838   /* Red */

/* Temperature Colors */
Optimal (18-24°C): #00b04f   /* Green */
Warm (24-30°C): #e6e600      /* Yellow */
Hot (> 30°C): #ca3838        /* Red */

/* Production Alert Colors */
Optimal: #00b04f             /* Green */
Moderate: #e6e600            /* Yellow */
Reduced: #ff8c00             /* Orange */
Halt: #ca3838                /* Red */
```

### Dashboard Themes
Node-RED Dashboard supports multiple themes:
- **Light Theme** (default)
- **Dark Theme** (recommended for monitoring)
- **Custom CSS** for brand colors

## 🔒 Security Considerations

### Read-Only Access
- **Dashboard is read-only** - no control actions
- **No write operations** to databases
- **Monitoring only** - pure visualization

### Network Security
- **Internal Docker network** only
- **No external API calls** from dashboard
- **Secure container communication**

### Data Privacy
- **No sensitive data** in dashboard
- **Aggregated metrics** only
- **No personal information** displayed

## 📈 Performance Optimization

### Query Optimization
```javascript
// Efficient InfluxDB queries
- Use aggregateWindow() for historical data
- Limit data ranges appropriately
- Cache frequently accessed data
- Use specific field filters
```

### Update Frequency
```javascript
// Balanced refresh rates
Real-time data: 5 minutes     // Not too frequent
ML predictions: 30 seconds    // Quick updates for alerts
Charts: 5 minutes            // Historical doesn't change fast
```

### Resource Usage
- **Minimize concurrent queries**
- **Use efficient data processing**
- **Limit chart data points**
- **Cache static content**

## 🚀 Advanced Features

### Custom Widgets
```javascript
// Custom gauge colors based on chocolate production zones
Temperature zones:
- Cooling: 15-18°C (Blue)
- Optimal: 18-24°C (Green) 
- Warning: 24-30°C (Yellow)
- Critical: >30°C (Red)

Production zones:
- Peak efficiency: Score > 75 (Green)
- Good efficiency: Score 50-75 (Yellow)
- Low efficiency: Score 25-50 (Orange)
- Production halt: Score < 25 (Red)
```

### Alert System
```javascript
// Production alert thresholds
Critical alerts:
- Temperature > 35°C
- Humidity > 85%
- Energy price > 0.30€/kWh
- Production index < 25

Warning alerts:
- Temperature 30-35°C
- Humidity 75-85%
- Energy price 0.25-0.30€/kWh
- Production index 25-50
```

### Data Export
```javascript
// Optional: Export dashboard data
- CSV export for historical analysis
- JSON export for external systems
- PDF reports for management
```

## 📚 Additional Resources

### Node-RED Documentation
- **Official Docs**: https://nodered.org/docs/
- **Dashboard Guide**: https://flows.nodered.org/node/node-red-dashboard
- **InfluxDB Node**: https://flows.nodered.org/node/node-red-contrib-influxdb

### Flow Examples
- **Basic Dashboard**: https://flows.nodered.org/flow/dashboard-example
- **Industrial Monitoring**: Similar patterns for SCADA systems
- **Time Series Visualization**: InfluxDB + Node-RED examples

---

**Author**: Claude Code  
**Date**: 2025-06-30  
**Version**: 1.0  
**Status**: ✅ Ready for Implementation