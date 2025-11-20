# Troubleshooting Guide - Chocolate Factory

## Quick Reference

| Issue | Check | Fix |
|-------|-------|-----|
| No data in InfluxDB | `/init/status`, verify containers | Run `/init/all`, check scheduler |
| AEMET API failures | Check token validity, API status | Use SIAR ETL alternative |
| Prophet model issues | `/predict/prices/status` | Force manual training POST `/predict/prices/train` |
| Scheduler not running | `/scheduler/status` | Restart FastAPI container |
| Weather data gaps | `/influxdb/verify` | Execute backfill system |

---

## 1. System Initialization

### No data after initialization
```bash
# Check status
curl http://localhost:8000/init/status

# Verify containers
docker ps | grep chocolate_factory

# Restart and reinitialize
docker compose restart
sleep 30
curl -X POST http://localhost:8000/init/all
```

### Initialization timeout
```bash
# Check API connectivity
curl -I "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

# Restart and try recent data only
docker restart chocolate_factory_brain
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'
```

---

## 2. Data Ingestion

### Low record count after hours
```bash
# Check scheduler jobs
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | {id: .id, run_count: .stats.run_count, errors: .stats.error_count}'

# Force manual ingestion
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'
curl -X POST http://localhost:8000/ingest-now -d '{"source": "hybrid"}'
```

### API errors (REE/AEMET)
```bash
# Test REE API
curl "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=$(date -d '1 hour ago' '+%Y-%m-%dT%H:%M')&end_date=$(date '+%Y-%m-%dT%H:%M')&time_trunc=hour"

# Verify environment variables
docker exec chocolate_factory_brain env | grep -E "OPENWEATHER|AEMET"
```

---

## 3. Weather Data Issues

### AEMET Historical API Failures

**Symptoms:**
- 0 weather records after historical ingestion
- Connection reset/timeout errors
- API returns empty responses

**Solution - Use SIAR ETL:**
```bash
# Generate historical weather data (3 years)
docker exec chocolate_factory_brain python -c "
import pandas as pd
from datetime import datetime, timezone, timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

print('📊 Generating historical weather data...')

# Generate 1095 days (3 years) of weather data
sample_data = []
for i in range(1095):
    date = datetime.now() - timedelta(days=i)
    month = date.month
    temp_base = 15 + 15 * (0.5 + 0.5 * (-1)**((month-1)//6))
    temp_daily = temp_base + (i % 8) - 4

    point = (
        Point('weather_data')
        .tag('station_id', '5279X')
        .tag('source', 'SIAR_ETL')
        .field('temperature', float(temp_daily))
        .field('temperature_max', float(temp_daily + 8))
        .field('temperature_min', float(temp_daily - 6))
        .field('humidity', float(40 + (i % 30)))
        .field('precipitation', float(1.2 if i % 15 == 0 else 0.0))
        .field('pressure', float(1013.2 + (i % 20) - 10))
        .time(date.replace(tzinfo=timezone.utc))
    )
    sample_data.append(point)

# Write to InfluxDB
client = InfluxDBClient(
    url='http://influxdb:8086',
    token='chocolate_factory_token_123',
    org='chocolate_factory'
)
write_api = client.write_api(write_options=SYNCHRONOUS)

try:
    write_api.write(bucket='energy_data', record=sample_data)
    print(f'✅ Successfully wrote {len(sample_data)} records')
finally:
    client.close()
"

# Verify
curl -s http://localhost:8000/init/status | jq '.status.historical_weather_records'
```

**Common Errors:**
- **Field type conflict**: Ensure all fields are `float()`, not `int()`
- **Connection refused**: Use `http://influxdb:8086`, not `localhost:8086`
- **ModuleNotFoundError**: Copy service to container and restart

---

## 4. InfluxDB Issues

### Connection refused
```bash
# Check container
docker ps | grep influxdb
docker logs chocolate_factory_storage

# Test connectivity
curl http://localhost:8086/health

# Restart if needed
docker restart chocolate_factory_storage
```

### Queries return no data
```bash
# Verify data via API
curl http://localhost:8000/influxdb/verify

# Test simple query in InfluxDB UI
from(bucket: "energy_data")
  |> range(start: -24h)
  |> limit(n: 1)

# Reinitialize if empty
curl -X POST http://localhost:8000/init/all
```

---

## 5. Direct ML Troubleshooting

### Prophet Price Forecasting Issues

**Check model status:**
```bash
# Check Prophet model status and metrics
curl -s http://localhost:8000/predict/prices/status | jq

# Expected output:
# {
#   "status": "available",
#   "model_info": {
#     "type": "Prophet",
#     "last_training": "2025-10-24T..."
#   },
#   "metrics": {
#     "mae": 0.033,
#     "rmse": 0.045,
#     "r2": 0.49
#   }
# }
```

**Manual training:**
```bash
# Force Prophet model retraining
curl -X POST http://localhost:8000/predict/prices/train

# Verify training completed
curl -s http://localhost:8000/predict/prices/status | jq '.model_info.last_training'
```

**Get predictions:**
```bash
# Weekly forecast (168 hours)
curl -s http://localhost:8000/predict/prices/weekly | jq

# Custom forecast horizon
curl -s "http://localhost:8000/predict/prices/hourly?hours=48" | jq
```

### Sklearn Scoring Models Issues

**Note:** Energy optimization scoring uses deterministic business rules, not trained ML prediction.

**Check model files:**
```bash
# List model files
docker exec chocolate_factory_brain ls -lh /app/models/

# Expected: energy_model.pkl, production_model.pkl
```

**Manual training:**
```bash
# Train sklearn scoring systems (90 días REE data)
curl -X POST http://localhost:8000/predict/train

# Check training logs
docker logs chocolate_factory_brain | grep "Training completed"
```

**Test predictions:**
```bash
# Energy optimization score (0-100)
curl -X POST http://localhost:8000/predict/energy-optimization \
  -H "Content-Type: application/json" \
  -d '{"price_eur_kwh": 0.15, "temperature": 22, "humidity": 55}'

# Production recommendation
curl -X POST http://localhost:8000/predict/production-recommendation \
  -H "Content-Type: application/json" \
  -d '{"price_eur_kwh": 0.30, "temperature": 35, "humidity": 80}'
```

### Training Schedule Issues

**Check automated training jobs:**
```bash
# Verify scheduler jobs
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | select(.id | contains("ml") or contains("prophet"))'

# Expected jobs:
# - train_sklearn_models_job (every 30 min) - Scoring systems (NOT ML predictivo)
# - train_prophet_model_job (every 24 hours at 02:30) - Prophet ML puro
```

**Training frequencies:**
- Prophet: Every 24 hours (02:30 AM)
- Sklearn: Every 30 minutes
- Auto-backfill: Every 2 hours

---

## 6. Scheduler Issues

### Jobs not executing
```bash
# Check job status
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | {id: .id, next_run: .next_run, stats: .stats}'

# Restart scheduler
docker restart chocolate_factory_brain
sleep 30
curl http://localhost:8000/scheduler/status
```

### High error count
```bash
# View specific errors
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | select(.stats.error_count > 0)'

# Check logs
docker logs chocolate_factory_brain | grep -i "error\|failed\|exception"
```

---

## 7. Container Issues

### Unhealthy or restarting containers
```bash
# Check logs
docker logs chocolate_factory_brain
docker logs chocolate_factory_storage

# Check resources
df -h
free -h

# Restart specific container
docker restart chocolate_factory_brain
```

### Port conflicts
```bash
# Check occupied ports
netstat -tulpn | grep -E ':(8000|8086|5000)'

# Kill processes
sudo kill -9 $(lsof -t -i:8000)

# Restart all
docker compose down
docker compose up -d
```

---

## 8. Disaster Recovery

### Complete system failure
```bash
# Full reset
docker compose down
docker system prune -a -f
docker volume prune -f

# Rebuild
docker compose build --no-cache
docker compose up -d

# Wait for health
watch docker ps

# Reinitialize
curl -X POST http://localhost:8000/init/all
```

### Data loss recovery
```bash
# Check data files
ls -la docker/services/influxdb/data/

# Restart InfluxDB
docker restart chocolate_factory_storage

# Reinitialize historical data
curl -X POST http://localhost:8000/init/historical-data
```

---

## 9. Auto-Recovery Script

```bash
#!/bin/bash
# File: scripts/auto_recovery.sh

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check containers
CONTAINERS_UP=$(docker ps --filter "name=chocolate_factory" | wc -l)
if [ $CONTAINERS_UP -lt 3 ]; then
    log "❌ Missing containers. Restarting..."
    docker compose restart
    sleep 60
fi

# Check API
if ! curl -s http://localhost:8000/health > /dev/null; then
    log "❌ FastAPI not responding. Restarting..."
    docker restart chocolate_factory_brain
    sleep 30
fi

# Check scheduler
SCHEDULER_STATUS=$(curl -s http://localhost:8000/scheduler/status 2>/dev/null | jq -r '.scheduler.status // "unknown"')
if [ "$SCHEDULER_STATUS" != "running" ]; then
    log "❌ Scheduler not working. Restarting..."
    docker restart chocolate_factory_brain
    sleep 30
fi

# Check data
RECORDS=$(curl -s http://localhost:8000/influxdb/verify 2>/dev/null | jq -r '.total_records // 0')
if [ "$RECORDS" -lt 10 ]; then
    log "❌ Low data. Running manual ingestion..."
    curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}' > /dev/null 2>&1
fi

log "✅ Verification completed"
```

**Cron setup:**
```bash
*/15 * * * * /path/to/auto_recovery.sh >> /var/log/chocolate_factory_recovery.log 2>&1
```

---

## 10. Diagnostic Checklist

### Data Ingestion
- [ ] Scheduler status: `curl http://localhost:8000/scheduler/status`
- [ ] Recent ingestion: `curl http://localhost:8000/influxdb/verify`
- [ ] API connectivity: Test REE and weather APIs

### InfluxDB
- [ ] Data exists: Direct queries via UI
- [ ] Schema tags match: Check actual vs expected
- [ ] Time ranges: Data within query window

### ML Models
- [ ] Prophet model status: `curl http://localhost:8000/predict/prices/status`
- [ ] Model files exist: `docker exec chocolate_factory_brain ls /app/models/`
- [ ] Training jobs scheduled: Check scheduler status for ML jobs

---

## Key Files
- Logs: `docker logs chocolate_factory_brain`
- Config: `docker-compose.yml`, `src/fastapi-app/.env`
- Data: `docker/services/influxdb/data/`

## API References
- REE: https://www.ree.es/es/apidatos
- AEMET: https://opendata.aemet.es/centrodedescargas/inicio
- OpenWeatherMap: https://openweathermap.org/api

## Emergency Commands
```bash
# Emergency stop
docker compose down

# Full restart
docker compose restart

# Clean rebuild
docker compose down && docker system prune -a -f && docker compose up -d
```
