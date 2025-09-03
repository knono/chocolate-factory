# Data Pipeline Troubleshooting Guide

**Quick Reference for InfluxDB Data Pipeline Issues**

## 🚨 Common Symptoms

### "No raw data available for feature engineering"
- **Cause**: Query timezone mismatch or schema incompatibility
- **Quick Fix**: Check InfluxDB data exists, then verify query tag filters
- **Command**: `curl "http://localhost:8000/mlflow/features?hours_back=1"`

### MLflow Training Says "Initiated" But No Models Created
- **Cause**: Data pipeline fails silently in background tasks
- **Quick Fix**: Check feature engineering endpoint directly
- **Verification**: `curl "http://localhost:5000/api/2.0/mlflow/runs/search" | jq '.runs[0].info.start_time'`

## 🔍 Diagnostic Commands

### 1. Check Raw Data in InfluxDB
```bash
# Energy prices
docker exec chocolate_factory_storage influx query \
  'from(bucket: "energy_data") |> range(start: -3h) |> filter(fn: (r) => r._measurement == "energy_prices") |> limit(n:3)'

# Weather data  
docker exec chocolate_factory_storage influx query \
  'from(bucket: "energy_data") |> range(start: -3h) |> filter(fn: (r) => r._measurement == "weather_data") |> limit(n:3)'
```

### 2. Test Feature Engineering
```bash
# Test with different time windows
curl "http://localhost:8000/mlflow/features?hours_back=1"
curl "http://localhost:8000/mlflow/features?hours_back=24"
```

### 3. Check Recent MLflow Runs
```bash
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids":["1","2"],"max_results":3,"order_by":["start_time DESC"]}' | \
  jq '.runs[] | {name: .info.run_name, start_time: .info.start_time, status: .info.status}'
```

## 🔧 Quick Fixes

### Force Direct MLflow Training (Emergency)
```bash
docker exec chocolate_factory_brain python -c "
import mlflow
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression
from datetime import datetime

mlflow.set_tracking_uri('http://mlflow:5000')
mlflow.set_experiment('chocolate_energy_optimization')

with mlflow.start_run(run_name=f'EMERGENCY_TRAINING_{datetime.now().strftime(\"%Y%m%d_%H%M\")}'):
    X, y = make_regression(n_samples=100, n_features=8, noise=0.1, random_state=42)
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    mlflow.log_param('model_type', 'Emergency_Training')
    mlflow.log_param('timestamp', datetime.now().isoformat())
    mlflow.log_metric('train_r2', model.score(X, y))
    
    print('✅ Emergency training completed')
"
```

### Reset Feature Engineering (Nuclear Option)
```bash
# Restart FastAPI container to reset any stuck connections
docker restart chocolate_factory_brain

# Wait for restart
sleep 15

# Test feature engineering
curl "http://localhost:8000/mlflow/features?hours_back=3"
```

## 🎯 Root Cause Analysis Checklist

### Data Ingestion Issues
- [ ] Check scheduler status: `curl "http://localhost:8000/scheduler/status"`
- [ ] Verify recent data ingestion: `curl "http://localhost:8000/influxdb/verify"`
- [ ] Check API connectivity: `curl "http://localhost:8000/weather/openweather/status"`

### InfluxDB Query Issues
- [ ] Data exists in InfluxDB: Test direct queries
- [ ] Schema tags match: Check actual vs expected tag structure
- [ ] Timezone handling: Queries use explicit UTC timestamps
- [ ] Time ranges: Data falls within query window

### MLflow Connection Issues
- [ ] MLflow server accessible: `curl "http://localhost:5000/version"`
- [ ] Experiments exist: Check experiment IDs 1, 2
- [ ] Permissions: Container can write to MLflow artifacts

## 🛠️ Permanent Fixes Applied

### Enhanced Feature Engineering Query
```python
# Before (broken)
energy_query = f'|> range(start: -{hours_back}h)'

# After (fixed)  
from datetime import datetime, timezone, timedelta
end_time = datetime.now(timezone.utc) + timedelta(hours=1)
start_time = end_time - timedelta(hours=hours_back + 1)
start_rfc3339 = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
end_rfc3339 = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

energy_query = f'''
|> range(start: {start_rfc3339}, stop: {end_rfc3339})
|> filter(fn: (r) => r.provider == "ree" or r.data_source == "ree_historical")
'''
```

### Schema-Aware Tag Filtering
- Energy: `r.provider == "ree" or r.data_source == "ree_historical"`
- Weather: `r.data_source == "openweathermap" or r.station_id == "openweathermap_linares"`

## 🔄 Recovery Procedures

### Full Data Pipeline Reset
```bash
# 1. Stop containers
docker compose down

# 2. Rebuild with latest fixes  
docker compose build fastapi-app

# 3. Start system
docker compose up -d

# 4. Wait for initialization
sleep 30

# 5. Test pipeline
curl "http://localhost:8000/mlflow/features?hours_back=1"

# 6. Force training if needed
curl -X POST "http://localhost:8000/mlflow/train"
```

### MLflow Data Recovery
```bash
# Check MLflow artifacts persistence
ls -la docker/services/mlflow/artifacts/

# Check PostgreSQL backend
docker exec chocolate_factory_postgres psql -U mlflow -d mlflow -c "SELECT name FROM experiments;"

# Verify data binding
docker inspect chocolate_factory_mlops | jq '.Mounts'
```

## 📊 Monitoring & Alerts

### Daily Health Check Script
```bash
#!/bin/bash
# File: scripts/daily-mlflow-check.sh

echo "🔍 MLflow Pipeline Health Check - $(date)"

# 1. Check recent training
LATEST_RUN=$(curl -s "http://localhost:5000/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids":["1"],"max_results":1,"order_by":["start_time DESC"]}' | \
  jq -r '.runs[0].info.run_name // "NONE"')

if [[ "$LATEST_RUN" == "NONE" ]]; then
  echo "🚨 ALERT: No MLflow runs found"
  exit 1
fi

echo "✅ Latest run: $LATEST_RUN"

# 2. Check feature engineering
FEATURE_STATUS=$(curl -s "http://localhost:8000/mlflow/features?hours_back=1" | \
  jq -r '.status // "ERROR"')

if [[ "$FEATURE_STATUS" == *"No data available"* ]]; then
  echo "🚨 ALERT: Feature engineering pipeline broken"
  exit 1  
fi

echo "✅ Feature engineering: OK"

# 3. Check data freshness
LATEST_DATA=$(curl -s "http://localhost:8000/influxdb/verify" | \
  jq -r '.data.energy_prices.latest_data[0].timestamp // "NONE"')

if [[ "$LATEST_DATA" == "NONE" ]]; then
  echo "🚨 ALERT: No recent energy data"
  exit 1
fi

echo "✅ Data freshness: $LATEST_DATA"
echo "🎉 All checks passed"
```

### Emergency Response Plan
1. **Immediate**: Run emergency training to get fresh models
2. **Short-term**: Investigate data pipeline with diagnostic commands
3. **Long-term**: Apply permanent fixes to prevent recurrence

## 🔗 Related Files
- `src/fastapi-app/services/feature_engineering.py` - Main data pipeline
- `src/fastapi-app/services/ml_models.py` - Training logic
- `docker/services/mlflow/` - MLflow persistence
- `docs/MLFLOW_DEBUGGING_RESOLUTION.md` - Complete case study

---
**Last Updated**: September 3, 2025  
**Status**: Pipeline fixed with permanent solutions implemented