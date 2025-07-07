# API Reference - TFM Chocolate Factory

## Índice
1. [Overview](#overview)
2. [Core Endpoints](#core-endpoints)
3. [Gap Detection & Backfill](#gap-detection--backfill)
4. [Machine Learning](#machine-learning)
5. [Data Ingestion](#data-ingestion)
6. [System Management](#system-management)
7. [Monitoring & Health](#monitoring--health)

## Overview

El sistema TFM Chocolate Factory expone **19 endpoints funcionales** distribuidos en diferentes categorías para manejo completo de la infraestructura de datos y ML.

**Base URL**: `http://localhost:8000`

### Arquitectura de Endpoints

```
🏠 Root & Status
├── GET  /                          # Sistema overview y endpoints
├── GET  /health                    # Health check básico

📊 Data Ingestion  
├── POST /ingest-now                # Ingesta manual inmediata
├── GET  /ree/prices               # REE current prices
├── GET  /weather/hybrid           # Weather data híbrido

🔍 Gap Detection & Backfill
├── GET  /gaps/summary             # Estado rápido de datos
├── GET  /gaps/detect              # Análisis completo de gaps
├── POST /gaps/backfill            # Backfill manual
├── POST /gaps/backfill/auto       # Backfill automático

🤖 Machine Learning
├── GET  /mlflow/status            # MLflow connectivity
├── GET  /models/status            # Models performance
├── POST /predict/energy-optimization
├── POST /predict/production-recommendation

⚙️  System Management
├── GET  /scheduler/status         # APScheduler estado
├── GET  /influxdb/verify          # InfluxDB connectivity
└── POST /init/status              # System initialization
```

## Core Endpoints

### Root Information
#### `GET /`
**Descripción**: Overview del sistema y lista de endpoints disponibles
**Respuesta**:
```json
{
  "service": "TFM Chocolate Factory API",
  "version": "1.0",
  "status": "running",
  "total_endpoints": 19,
  "endpoints": {
    "gaps_summary": "GET /gaps/summary",
    "gaps_detect": "GET /gaps/detect",
    "gaps_backfill": "POST /gaps/backfill", 
    "gaps_auto_backfill": "POST /gaps/backfill/auto",
    "predict_energy": "POST /predict/energy-optimization",
    "predict_production": "POST /predict/production-recommendation"
  }
}
```

#### `GET /health`
**Descripción**: Health check básico del servicio
**Respuesta**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-07T09:00:00Z"
}
```

## Gap Detection & Backfill

### Gap Summary
#### `GET /gaps/summary`
**Descripción**: Estado rápido de datos actuales y recomendaciones
**Parámetros**: Ninguno
**Respuesta**:
```json
{
  "ree_prices": {
    "status": "🚨 7d atrasado",
    "latest_data": "2025-06-29T21:00:00+00:00",
    "gap_hours": 179.3
  },
  "weather_data": {
    "status": "✅ Actualizado",
    "latest_data": "2025-07-07T08:23:05+00:00", 
    "gap_hours": 0.5
  },
  "recommendations": {
    "action_needed": false,
    "suggested_endpoint": "Sistema al día"
  }
}
```

### Gap Detection
#### `GET /gaps/detect?days_back=10`
**Descripción**: Análisis completo de gaps en rango temporal
**Parámetros**:
- `days_back` (int, opcional): Días hacia atrás para analizar (default: 7)

**Respuesta**:
```json
{
  "summary": {
    "total_gaps": 3,
    "ree_gaps": 1,
    "weather_gaps": 2,
    "estimated_backfill_time": "~15 minutos"
  },
  "ree_data_gaps": [
    {
      "measurement": "energy_prices",
      "start_time": "2025-07-06T14:00:00+00:00",
      "end_time": "2025-07-06T16:00:00+00:00",
      "duration_hours": 2.0,
      "missing_records": 2,
      "severity": "moderate"
    }
  ],
  "weather_data_gaps": [],
  "recommended_strategy": {
    "approach": "intelligent_progressive",
    "ree_strategy": {
      "api": "REE_historical",
      "method": "daily_chunks"
    },
    "weather_strategy": {
      "primary_api": "AEMET_current_month",
      "fallback_api": "datosclima_etl"
    }
  }
}
```

### Manual Backfill
#### `POST /gaps/backfill?days_back=7`
**Descripción**: Backfill manual ejecutado en background
**Parámetros**:
- `days_back` (int, opcional): Días hacia atrás para procesar (default: 10)

**Respuesta**:
```json
{
  "status": "🚀 Executing in background",
  "days_processing": 7,
  "estimated_duration": "5-15 minutes",
  "monitoring": {
    "check_progress": "GET /gaps/summary",
    "verify_results": "GET /influxdb/verify"
  }
}
```

### Automatic Backfill
#### `POST /gaps/backfill/auto?max_gap_hours=6.0`
**Descripción**: Backfill automático inteligente (solo si hay gaps significativos)
**Parámetros**:
- `max_gap_hours` (float, opcional): Umbral en horas para activar backfill (default: 6.0)

**Respuesta** (cuando se activa):
```json
{
  "status": "partial",
  "trigger": "automatic",
  "summary": {
    "total_gaps_processed": 9,
    "ree_gaps": 3,
    "weather_gaps": 6,
    "total_duration_seconds": 14.7,
    "overall_success_rate": 32.9
  },
  "records": {
    "total_requested": 387,
    "total_obtained": 127,
    "total_written": 127,
    "ree_records_written": 72,
    "weather_records_written": 55
  },
  "detected_gaps": {
    "ree_hours": 179.3,
    "weather_hours": 181.7
  }
}
```

**Respuesta** (cuando no se requiere acción):
```json
{
  "status": "no_action_needed",
  "message": "Data is up to date",
  "gaps": {
    "ree_hours": 1.2,
    "weather_hours": 0.8,
    "threshold_hours": 6.0
  }
}
```

## Machine Learning

### MLflow Status
#### `GET /mlflow/status`
**Descripción**: Estado de conectividad MLflow y experimentos
**Respuesta**:
```json
{
  "mlflow_status": "connected",
  "tracking_uri": "http://mlflow-server:5000",
  "experiments": {
    "total_experiments": 2,
    "chocolate_factory_experiment": {
      "name": "chocolate-factory-optimization",
      "runs": 15,
      "latest_run": "2025-07-07T08:30:00Z"
    }
  }
}
```

### Models Status  
#### `GET /models/status`
**Descripción**: Estado de rendimiento y salud de modelos ML
**Respuesta**:
```json
{
  "models_health": "healthy",
  "energy_optimization_model": {
    "status": "trained",
    "performance": {
      "r2_score": 0.8876,
      "mae": 12.45
    },
    "last_training": "2025-07-07T08:00:00Z",
    "training_samples": 50
  },
  "production_classifier": {
    "status": "trained", 
    "performance": {
      "accuracy": 0.90,
      "f1_score": 0.88
    },
    "last_training": "2025-07-07T08:00:00Z",
    "training_samples": 50
  }
}
```

### Energy Optimization Prediction
#### `POST /predict/energy-optimization`
**Descripción**: Predicción de score de optimización energética
**Body**:
```json
{
  "price_eur_kwh": 0.15,
  "temperature": 22.5,
  "humidity": 55.0
}
```

**Respuesta**:
```json
{
  "energy_optimization_score": 78.5,
  "prediction_confidence": 0.92,
  "features_used": {
    "energy_cost_index": 34.2,
    "temperature_comfort_index": 85.0,
    "price_eur_kwh": 0.15,
    "temperature": 22.5,
    "humidity": 55.0
  },
  "recommendation": "optimal_conditions",
  "timestamp": "2025-07-07T09:00:00Z"
}
```

### Production Recommendation
#### `POST /predict/production-recommendation`
**Descripción**: Predicción de recomendación de producción
**Body**:
```json
{
  "price_eur_kwh": 0.30,
  "temperature": 35.0,
  "humidity": 80.0
}
```

**Respuesta**:
```json
{
  "recommendation": "Reduced_Production",
  "confidence": 0.85,
  "chocolate_production_index": 45.2,
  "reasoning": {
    "energy_cost": "high",
    "temperature_stress": "high", 
    "humidity_stress": "moderate"
  },
  "urgency": "medium",
  "features_used": {
    "energy_cost_index": 85.7,
    "temperature_comfort_index": 15.0,
    "humidity_stress_factor": 45.4
  },
  "timestamp": "2025-07-07T09:00:00Z"
}
```

## Data Ingestion

### Manual Ingestion
#### `POST /ingest-now`
**Descripción**: Ingesta manual inmediata de datos
**Body** (opcional):
```json
{
  "source": "hybrid",
  "force": true
}
```

**Respuesta**:
```json
{
  "status": "success",
  "ingestion_results": {
    "ree_prices": {
      "records_written": 1,
      "success_rate": 100.0
    },
    "weather_data": {
      "records_written": 1,
      "success_rate": 100.0,
      "source_used": "OpenWeatherMap"
    }
  },
  "timestamp": "2025-07-07T09:00:00Z"
}
```

### REE Prices
#### `GET /ree/prices`
**Descripción**: Precios actuales de REE
**Respuesta**:
```json
{
  "status": "success",
  "current_price": {
    "price_eur_kwh": 0.18542,
    "timestamp": "2025-07-07T09:00:00Z",
    "tariff_period": "P2"
  },
  "market_info": {
    "demand_mw": 28457,
    "renewable_percentage": 45.8
  }
}
```

### Hybrid Weather
#### `GET /weather/hybrid`
**Descripción**: Datos climáticos híbridos (AEMET + OpenWeatherMap)
**Respuesta**:
```json
{
  "status": "success",
  "current_weather": {
    "temperature": 28.5,
    "humidity": 62.0,
    "pressure": 1015.2,
    "timestamp": "2025-07-07T09:00:00Z",
    "source": "OpenWeatherMap",
    "station": "Linares, Jaén"
  },
  "data_strategy": {
    "hour_range": "08:00-23:00",
    "preferred_source": "OpenWeatherMap",
    "fallback_available": true
  }
}
```

## System Management

### Scheduler Status
#### `GET /scheduler/status`
**Descripción**: Estado completo del APScheduler y jobs programados
**Respuesta**:
```json
{
  "scheduler": {
    "status": "running",
    "total_jobs": 10,
    "running_since": "2025-07-07T07:00:00Z"
  },
  "jobs": [
    {
      "id": "ree_price_ingestion",
      "name": "REE Price Data Ingestion (ACCELERATED)",
      "next_run": "2025-07-07T09:05:00Z",
      "trigger": "interval[0:05:00]",
      "stats": {
        "run_count": 145,
        "success_count": 142,
        "error_count": 3,
        "last_run": "2025-07-07T09:00:00Z"
      }
    },
    {
      "id": "auto_backfill_check",
      "name": "Auto Backfill Detection", 
      "next_run": "2025-07-07T11:00:00Z",
      "trigger": "interval[2:00:00]",
      "stats": {
        "run_count": 12,
        "success_count": 11,
        "error_count": 1,
        "last_run": "2025-07-07T09:00:00Z"
      }
    }
  ]
}
```

### InfluxDB Verification
#### `GET /influxdb/verify`
**Descripción**: Verificación de conectividad y estado de datos en InfluxDB
**Respuesta**:
```json
{
  "connection": {
    "status": "connected",
    "ping_response_ms": 15.2
  },
  "data": {
    "total_records": 2847,
    "ree_records": 1423,
    "weather_records": 1424,
    "latest_ree": "2025-07-07T08:00:00+00:00",
    "latest_weather": "2025-07-07T08:23:05+00:00",
    "data_freshness": "current"
  },
  "bucket_info": {
    "name": "chocolate_factory_data",
    "retention_policy": "30d",
    "size_mb": 32.4
  }
}
```

### System Initialization Status
#### `GET /init/status`
**Descripción**: Estado de inicialización del sistema
**Respuesta**:
```json
{
  "system_status": "initialized",
  "initialization_timestamp": "2025-07-07T07:00:00Z",
  "status": {
    "ree_records": 1423,
    "weather_records": 1424,
    "historical_weather_records": 1095,
    "mlflow_experiments": 2,
    "scheduler_jobs": 10
  },
  "recommendations": {
    "data_sufficient": true,
    "mlflow_ready": true,
    "production_ready": true
  }
}
```

## Monitoring & Health

### System Health Patterns

#### Success Response Pattern
```json
{
  "status": "success",
  "timestamp": "2025-07-07T09:00:00Z",
  "data": { /* specific endpoint data */ }
}
```

#### Error Response Pattern
```json
{
  "status": "error", 
  "error": "Error description",
  "timestamp": "2025-07-07T09:00:00Z",
  "details": { /* error context */ }
}
```

### Rate Limits

| API Source | Límite | Aplicación |
|------------|--------|------------|
| REE | 30 req/min | Backfill automático |
| AEMET | 20 req/min | Weather histórico |
| OpenWeatherMap | 60 req/min | Weather tiempo real |
| Internal APIs | Sin límite | Todas las operaciones |

### Authentication

- **REE API**: Sin autenticación requerida
- **AEMET API**: Token automático (renovación cada 6 días)
- **OpenWeatherMap**: API key configurada en variables de entorno
- **Internal APIs**: Sin autenticación (desarrollo)

### Error Handling

#### Common Error Codes
- `400`: Bad Request - Parámetros inválidos
- `500`: Internal Server Error - Error del sistema
- `503`: Service Unavailable - APIs externas no disponibles
- `429`: Too Many Requests - Rate limit excedido

#### Retry Policies
- **Gap Detection**: 3 reintentos con backoff exponencial
- **Backfill Operations**: 2 reintentos para gaps moderados, 3 para críticos
- **Real-time Ingestion**: 1 reintento inmediato

---

**Documentación actualizada**: 2025-07-07  
**Versión API**: v1.0  
**Estado**: ✅ Sistema Productivo con 19 Endpoints Funcionales