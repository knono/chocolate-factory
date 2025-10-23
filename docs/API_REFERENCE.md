# API Reference - Chocolate Factory

Base URL: `http://localhost:8000`

## Core Endpoints

### GET /
System overview and available endpoints.

**Response:**
```json
{
  "service": "Chocolate Factory API",
  "version": "1.0",
  "status": "running",
  "total_endpoints": 19
}
```

### GET /health
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-23T09:00:00Z"
}
```

### GET /ready
Readiness probe for container orchestration.

**Response:**
```json
{
  "status": "ready"
}
```

### GET /version
API version information.

**Response:**
```json
{
  "version": "1.0",
  "build": "2025-10-23"
}
```

## Data Ingestion

### POST /ingest-now
Manual data ingestion (REE + weather).

**Request (optional):**
```json
{
  "source": "hybrid",
  "force": true
}
```

**Response:**
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
  "timestamp": "2025-10-23T09:00:00Z"
}
```

### GET /ree/prices
Current REE electricity prices.

**Response:**
```json
{
  "status": "success",
  "current_price": {
    "price_eur_kwh": 0.18542,
    "timestamp": "2025-10-23T09:00:00Z",
    "tariff_period": "P2"
  },
  "market_info": {
    "demand_mw": 28457,
    "renewable_percentage": 45.8
  }
}
```

### GET /weather/hybrid
Hybrid weather data (AEMET + OpenWeatherMap).

**Response:**
```json
{
  "status": "success",
  "current_weather": {
    "temperature": 28.5,
    "humidity": 62.0,
    "pressure": 1015.2,
    "timestamp": "2025-10-23T09:00:00Z",
    "source": "OpenWeatherMap",
    "station": "Linares, Jaen"
  },
  "data_strategy": {
    "hour_range": "08:00-23:00",
    "preferred_source": "OpenWeatherMap",
    "fallback_available": true
  }
}
```

## Gap Detection & Backfill

### GET /gaps/summary
Quick data status check (REE + weather gap hours).

**Response:**
```json
{
  "ree_prices": {
    "status": "Actualizado",
    "latest_data": "2025-10-23T08:00:00+00:00",
    "gap_hours": 1.2
  },
  "weather_data": {
    "status": "Actualizado",
    "latest_data": "2025-10-23T08:23:05+00:00",
    "gap_hours": 0.5
  },
  "recommendations": {
    "action_needed": false,
    "suggested_endpoint": "Sistema al dia"
  }
}
```

### GET /gaps/detect?days_back=N
Detailed gap analysis with recommended backfill strategy.

**Parameters:**
- `days_back` (int, default: 7): Days to analyze backwards

**Response:**
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
      "start_time": "2025-10-22T14:00:00+00:00",
      "end_time": "2025-10-22T16:00:00+00:00",
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

### POST /gaps/backfill?days_back=N
Manual backfill execution.

**Parameters:**
- `days_back` (int, default: 10): Days to process backwards

**Response:**
```json
{
  "status": "Executing in background",
  "days_processing": 7,
  "estimated_duration": "5-15 minutes",
  "monitoring": {
    "check_progress": "GET /gaps/summary",
    "verify_results": "GET /influxdb/verify"
  }
}
```

### POST /gaps/backfill/auto?max_gap_hours=N
Automatic intelligent backfill (only if gaps exceed threshold).

**Parameters:**
- `max_gap_hours` (float, default: 6.0): Threshold to trigger backfill

**Response (when triggered):**
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
  }
}
```

**Response (no action needed):**
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

### POST /gaps/backfill/range
Date range specific backfill with data source filter.

**Request:**
```json
{
  "start_date": "2025-10-01",
  "end_date": "2025-10-15",
  "data_source": "ree"
}
```

**Response:**
```json
{
  "status": "success",
  "records_written": 336,
  "date_range": "2025-10-01 to 2025-10-15"
}
```

## Machine Learning (sklearn)

### POST /models/train
Train ML models directly (energy optimization + production classifier).

**Response:**
```json
{
  "status": "success",
  "training_results": {
    "energy_model": {
      "r2_score": 0.8876,
      "mae": 12.45,
      "training_samples": 50
    },
    "production_model": {
      "accuracy": 0.90,
      "f1_score": 0.88,
      "training_samples": 50
    }
  },
  "timestamp": "2025-10-23T09:00:00Z"
}
```

### GET /models/status-direct
Direct ML models health and performance.

**Response:**
```json
{
  "models_health": "healthy",
  "energy_optimization_model": {
    "status": "trained",
    "performance": {
      "r2_score": 0.8876,
      "mae": 12.45
    },
    "last_training": "2025-10-23T08:00:00Z",
    "training_samples": 50
  },
  "production_classifier": {
    "status": "trained",
    "performance": {
      "accuracy": 0.90,
      "f1_score": 0.88
    },
    "last_training": "2025-10-23T08:00:00Z",
    "training_samples": 50
  }
}
```

### POST /predict/energy-optimization
Energy optimization score prediction (0-100).

**Request:**
```json
{
  "price_eur_kwh": 0.15,
  "temperature": 22.5,
  "humidity": 55.0
}
```

**Response:**
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
  "timestamp": "2025-10-23T09:00:00Z"
}
```

### POST /predict/production-recommendation
Production recommendation based on conditions.

**Request:**
```json
{
  "price_eur_kwh": 0.30,
  "temperature": 35.0,
  "humidity": 80.0
}
```

**Response:**
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
  "timestamp": "2025-10-23T09:00:00Z"
}
```

## Price Forecasting (Prophet)

### GET /predict/prices/weekly
168-hour (7-day) price forecast using Prophet model.

**Response:**
```json
{
  "status": "success",
  "forecast_horizon": "168 hours (7 days)",
  "model_type": "Prophet",
  "predictions_count": 168,
  "predictions": [
    {
      "timestamp": "2025-10-23T17:00:00",
      "predicted_price": 0.2397,
      "confidence_lower": 0.1823,
      "confidence_upper": 0.2971
    }
  ],
  "model_metrics": {
    "mae": 0.0325,
    "rmse": 0.0396,
    "r2": 0.489,
    "coverage_95": 0.883,
    "train_samples": 1475,
    "test_samples": 369
  },
  "last_training": "2025-10-23T17:41:39.781906",
  "timestamp": "2025-10-23T17:52:09.730934"
}
```

### GET /predict/prices/hourly?hours=N
Configurable hourly forecast (1-168 hours).

**Parameters:**
- `hours` (int, default: 24, max: 168): Number of hours to forecast

**Response:**
Same structure as weekly, limited to N predictions.

### POST /models/price-forecast/train
Train Prophet model with historical REE data.

**Parameters:**
- `months_back` (int, default: 12): Months of historical data to use

**Response:**
```json
{
  "status": "success",
  "training_result": {
    "success": true,
    "metrics": {
      "mae": 0.0325,
      "rmse": 0.0396,
      "r2": 0.489,
      "coverage_95": 0.883,
      "train_samples": 1475,
      "test_samples": 369
    },
    "last_training": "2025-10-23T17:41:39.781906",
    "model_file": "/app/models/forecasting/prophet_latest.pkl"
  }
}
```

### GET /models/price-forecast/status
Prophet model status and metrics.

**Response:**
```json
{
  "status": "available",
  "model_info": {
    "type": "Prophet",
    "version": "1.1.7",
    "last_training": "2025-10-23T17:41:39.781906"
  },
  "metrics": {
    "mae": 0.0325,
    "rmse": 0.0396,
    "r2": 0.489,
    "coverage_95": 0.883
  }
}
```

## SIAR Historical Analysis

### GET /analysis/weather-correlation
Weather correlation analysis (temperature, humidity vs efficiency).

**Response:**
```json
{
  "status": "success",
  "correlations": {
    "temperature_r2": 0.049,
    "humidity_r2": 0.057
  },
  "data_source": "SIAR historical (88,935 records, 2000-2025)"
}
```

### GET /analysis/seasonal-patterns
Seasonal patterns from 25 years of SIAR data.

**Response:**
```json
{
  "status": "success",
  "best_months": ["January", "February", "December"],
  "worst_months": ["July", "August"],
  "analysis_period": "2000-2025",
  "records_analyzed": 88935
}
```

### GET /analysis/critical-thresholds
Critical thresholds based on historical percentiles.

**Response:**
```json
{
  "status": "success",
  "thresholds": {
    "temperature_p90": 32.5,
    "temperature_p95": 35.0,
    "temperature_p99": 38.2,
    "humidity_p90": 75.0,
    "humidity_p95": 82.0,
    "humidity_p99": 88.5
  }
}
```

### GET /analysis/siar-summary
Executive summary of SIAR historical analysis.

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_records": 88935,
    "date_range": "2000-2025",
    "stations": ["J09_Linares", "J17_Linares"],
    "key_insights": [
      "R2=0.049 (temp), R2=0.057 (humidity)",
      "Best production months: Jan, Feb, Dec",
      "Critical temp threshold: 35C (P95)"
    ]
  }
}
```

### POST /analysis/forecast/aemet-contextualized
AEMET predictions with SIAR historical context.

**Request:**
```json
{
  "days_ahead": 7
}
```

**Response:**
```json
{
  "status": "success",
  "forecast": [
    {
      "date": "2025-10-24",
      "temperature": 24.5,
      "humidity": 58.0,
      "historical_context": "Normal for October",
      "production_suitability": "optimal"
    }
  ]
}
```

## Hourly Production Optimization

### POST /optimize/production/daily
Daily production plan with hourly timeline.

**Request:**
```json
{
  "target_date": "2025-10-24",
  "target_kg": 200
}
```

**Response:**
```json
{
  "status": "success",
  "plan": {
    "batches": [
      {
        "batch_id": "P01",
        "process": "Conchado Premium",
        "start_hour": 2,
        "end_hour": 10,
        "kg": 100
      }
    ],
    "hourly_timeline": [
      {
        "hour": 2,
        "time": "02:00",
        "price_eur_kwh": 0.0796,
        "tariff_period": "P3",
        "tariff_color": "#10b981",
        "temperature": 18.0,
        "humidity": 60.0,
        "climate_status": "optimal",
        "active_batch": "P01",
        "active_process": "Conchado Premium",
        "is_production_hour": true
      }
    ],
    "savings_vs_baseline": 0.43
  }
}
```

### GET /optimize/production/summary
Optimization metrics summary.

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_plans_generated": 142,
    "average_savings": 0.38,
    "optimal_period": "P3 (Valle)"
  }
}
```

## Predictive Insights

### GET /insights/energy
Energy price insights and recommendations.

**Response:**
```json
{
  "status": "success",
  "current_price": 0.15,
  "forecast_24h": [0.14, 0.16, 0.18],
  "recommendation": "Producir en proximas 3 horas"
}
```

### GET /insights/production
Production optimization insights.

**Response:**
```json
{
  "status": "success",
  "current_conditions": "optimal",
  "next_optimal_window": "2025-10-24T02:00:00",
  "expected_savings": 0.42
}
```

### GET /insights/weather
Weather impact analysis.

**Response:**
```json
{
  "status": "success",
  "current_impact": "favorable",
  "next_24h_forecast": "stable",
  "production_suitability": "high"
}
```

### GET /insights/summary
Unified predictive dashboard summary.

**Response:**
```json
{
  "status": "success",
  "roi_tracking": {
    "annual_savings_eur": 1661,
    "monthly_average": 138.4
  },
  "recommendations": [
    "Maximizar produccion entre 02:00-06:00",
    "Clima optimo para calidad premium"
  ]
}
```

## Chatbot BI

### POST /chat/ask
Conversational BI chatbot endpoint.

**Request:**
```json
{
  "question": "Cuando debo producir hoy?"
}
```

**Response:**
```json
{
  "answer": "Segun las condiciones actuales...",
  "tokens": {
    "input": 234,
    "output": 156
  },
  "latency_ms": 10234,
  "cost_usd": 0.00045
}
```

### GET /chat/stats
Chatbot usage statistics.

**Response:**
```json
{
  "total_questions": 142,
  "total_tokens": 45623,
  "total_cost_usd": 0.52,
  "average_latency_ms": 11234
}
```

### GET /chat/health
Chatbot service health check.

**Response:**
```json
{
  "status": "healthy",
  "claude_api": "connected",
  "rate_limit": "20/min"
}
```

## Health Monitoring

### GET /health-monitoring/summary
VPN and system health summary.

**Response:**
```json
{
  "status": "success",
  "tailscale_status": "connected",
  "critical_nodes": {
    "production": "healthy",
    "development": "healthy",
    "git": "healthy"
  },
  "uptime_percentage": 99.8
}
```

### GET /health-monitoring/critical
Critical nodes monitoring.

**Response:**
```json
{
  "status": "success",
  "critical_nodes": [
    {
      "hostname": "production",
      "status": "healthy",
      "last_seen": "2025-10-23T09:00:00Z"
    }
  ]
}
```

### GET /health-monitoring/alerts
Active health alerts.

**Response:**
```json
{
  "status": "success",
  "active_alerts": [],
  "resolved_alerts": 5
}
```

### GET /health-monitoring/nodes
All Tailscale nodes status.

**Response:**
```json
{
  "status": "success",
  "total_nodes": 12,
  "project_nodes": 3,
  "nodes": [
    {
      "hostname": "production",
      "online": true,
      "ip": "100.x.x.x"
    }
  ]
}
```

### GET /health-monitoring/uptime
Uptime tracking for critical nodes.

**Response:**
```json
{
  "status": "success",
  "uptime_stats": [
    {
      "hostname": "production",
      "uptime_percentage": 99.9,
      "total_checks": 1440,
      "failures": 2
    }
  ]
}
```

### GET /health-monitoring/logs
Event logs with pagination and filters.

**Parameters:**
- `page` (int, default: 1): Page number
- `severity` (str, optional): Filter by severity (info, warning, error, critical)
- `event_type` (str, optional): Filter by event type
- `project_only` (bool, default: false): Show only project nodes

**Response:**
```json
{
  "status": "success",
  "logs": [
    {
      "timestamp": "2025-10-23T09:00:00Z",
      "hostname": "production",
      "severity": "info",
      "event_type": "node_online",
      "message": "Node came online"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_logs": 92
  }
}
```

## Dashboard & Monitoring

### GET /dashboard
Visual dashboard HTML interface.

**Response:**
HTML page with interactive charts and real-time data.

### GET /dashboard/complete
Complete dashboard JSON data.

**Response:**
```json
{
  "service": "Chocolate Factory",
  "timestamp": "2025-10-23T09:00:00Z",
  "current_data": {
    "ree_price": 0.15,
    "temperature": 22.5,
    "humidity": 55.0
  },
  "predictions": {
    "energy_score": 78.5,
    "production_recommendation": "Optimal_Production",
    "prophet_forecast_24h": []
  },
  "siar_analysis": {
    "correlations": {},
    "seasonal_patterns": {}
  },
  "optimization": {
    "daily_plan": {},
    "hourly_timeline": []
  },
  "chatbot_stats": {},
  "health_monitoring": {},
  "system_status": {
    "scheduler_jobs": 11,
    "influxdb_records": 42578
  }
}
```

### GET /dashboard/summary
Quick summary for visualization.

**Response:**
```json
{
  "status": "healthy",
  "data_freshness": "current",
  "active_alerts": 0,
  "recommendations_count": 3
}
```

### GET /dashboard/alerts
Active system alerts.

**Response:**
```json
{
  "alerts": [
    {
      "severity": "warning",
      "message": "Price spike detected",
      "timestamp": "2025-10-23T08:45:00Z"
    }
  ]
}
```

## System Management

### GET /scheduler/status
APScheduler job status and statistics.

**Response:**
```json
{
  "scheduler": {
    "status": "running",
    "total_jobs": 11,
    "running_since": "2025-10-23T07:00:00Z"
  },
  "jobs": [
    {
      "id": "ree_price_ingestion",
      "name": "REE Price Data Ingestion",
      "next_run": "2025-10-23T09:05:00Z",
      "trigger": "interval[0:05:00]",
      "stats": {
        "run_count": 145,
        "success_count": 142,
        "error_count": 3,
        "last_run": "2025-10-23T09:00:00Z"
      }
    }
  ]
}
```

### GET /influxdb/verify
InfluxDB connectivity and data status.

**Response:**
```json
{
  "connection": {
    "status": "connected",
    "ping_response_ms": 15.2
  },
  "data": {
    "total_records": 42578,
    "ree_records": 21289,
    "weather_records": 21289,
    "latest_ree": "2025-10-23T08:00:00+00:00",
    "latest_weather": "2025-10-23T08:23:05+00:00",
    "data_freshness": "current"
  },
  "bucket_info": {
    "name": "chocolate_factory_data",
    "retention_policy": "30d",
    "size_mb": 32.4
  }
}
```

### GET /init/status
System initialization status.

**Response:**
```json
{
  "system_status": "initialized",
  "initialization_timestamp": "2025-10-23T07:00:00Z",
  "status": {
    "ree_records": 42578,
    "weather_records": 21289,
    "historical_weather_records": 88935,
    "scheduler_jobs": 11
  },
  "recommendations": {
    "data_sufficient": true,
    "production_ready": true
  }
}
```

## Response Patterns

### Success Response
```json
{
  "status": "success",
  "timestamp": "2025-10-23T09:00:00Z",
  "data": {}
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Error description",
  "timestamp": "2025-10-23T09:00:00Z",
  "details": {}
}
```

## Rate Limits

| API Source | Limit | Application |
|------------|-------|-------------|
| REE | 30 req/min | Backfill automatic |
| AEMET | 20 req/min | Weather historical |
| OpenWeatherMap | 60 req/min | Weather real-time |
| Claude Haiku | 20 req/min | Chatbot |
| Internal APIs | No limit | All operations |

## Authentication

- REE API: No authentication required
- AEMET API: Token auto-renewal every 6 days
- OpenWeatherMap: API key in environment variables
- Claude API: API key in environment variables
- Internal APIs: No authentication (development)

## Error Codes

- `400`: Bad Request - Invalid parameters
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - System error
- `503`: Service Unavailable - External APIs unavailable

## Retry Policies

- Gap Detection: 3 retries with exponential backoff
- Backfill Operations: 2 retries for moderate gaps, 3 for critical
- Real-time Ingestion: 1 immediate retry
- ML Predictions: No retry (fail fast)

---

Last Updated: 2025-10-23
API Version: v1.0
Status: Production Ready
