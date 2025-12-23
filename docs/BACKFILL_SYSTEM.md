# Backfill System - Chocolate Factory

## Overview

Automatic gap detection and recovery system for time series data. Ensures data continuity when system has been offline for extended periods.

**Core capabilities:**
- Automatic gap detection in REE and weather data
- Intelligent backfill with source-specific strategies
- Auto-recovery scheduled every 2 hours
- Automatic success/failure alerts

---

## Architecture

### Components

**Gap Detection Service** (`services/gap_detector.py`):
- Analyzes InfluxDB for missing time ranges
- Calculates severity (minor, moderate, critical)
- Estimates recovery time
- Generates backfill strategies

**Backfill Service** (`services/backfill_service.py`):
- Executes intelligent data recovery
- REE backfill with daily chunks
- Weather backfill with temporal hybrid strategy
- Automatic rate limiting and error handling

### Key Methods

```python
# Gap Detection
async def detect_all_gaps(days_back: int) -> GapAnalysis
async def get_latest_timestamps() -> Dict[str, Optional[datetime]]

# Backfill Execution
async def execute_intelligent_backfill(days_back: int) -> Dict[str, Any]
async def check_and_execute_auto_backfill(max_gap_hours: float) -> Dict[str, Any]
```

---

## Gap Detection Algorithm

### Detection Logic

```python
def _find_time_gaps(expected_times, existing_times, measurement, interval):
    """
    1. Identify missing timestamps
    2. Group consecutive missing times into gaps
    3. Calculate gap metrics
    """
    existing_set = set(existing_times)
    missing_times = [t for t in expected_times if t not in existing_set]

    # Group consecutive missing times
    gaps = []
    current_gap_start = missing_times[0]
    current_gap_end = missing_times[0]

    for i in range(1, len(missing_times)):
        time_diff = missing_times[i] - current_gap_end

        if time_diff <= interval * 1.5:  # 50% tolerance
            current_gap_end = missing_times[i]
        else:
            gaps.append(create_gap(current_gap_start, current_gap_end))
            current_gap_start = missing_times[i]
            current_gap_end = missing_times[i]

    return gaps
```

### Gap Classification

**Minor Gaps** (≤2 hours):
- Impact: Minimal
- Priority: Low
- Strategy: Automatic backfill in next cycle

**Moderate Gaps** (2-12 hours):
- Impact: Affects dashboard and some predictions
- Priority: Medium
- Strategy: Immediate backfill with alerts

**Critical Gaps** (>12 hours):
- Impact: Compromises ML models and dashboard
- Priority: High
- Strategy: Aggressive backfill with multiple retries

---

## Backfill Strategies

### REE Data Backfill

**Strategy**: Daily chunks with historical API

```python
async def _backfill_ree_gaps(gaps):
    for gap in gaps:
        current_date = gap.start_time.date()
        end_date = gap.end_time.date()

        while current_date <= end_date:
            # Daily chunk to avoid timeouts
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1) - timedelta(minutes=1)

            # REE historical API
            daily_data = await ree_client.get_pvpc_prices(
                start_date=day_start,
                end_date=day_end
            )

            await ingestion_service.ingest_ree_prices_historical(daily_data)

            # Rate limiting: 30 req/min
            await asyncio.sleep(2)
            current_date += timedelta(days=1)
```

### Weather Data Backfill

**Adaptive strategy based on gap age (optimizado Dec 2025):**

#### Estrategia de 48h con Predicción Horaria por Municipio

```python
# Calcular posición temporal del gap
gap_age_hours = (now - gap.start_time).total_seconds() / 3600
hours_until_gap_end = (gap.end_time - now).total_seconds() / 3600

# Estrategia optimizada para reducir tiempo de equipo encendido
if hours_until_gap_end > 0 and hours_until_gap_end <= 48:
    # Gap que incluye futuro cercano: predicción horaria AEMET (48h forecast)
    # Endpoint: /prediccion/especifica/municipio/horaria/23055 (Linares)
    result = await self._backfill_weather_aemet_forecast(gap)
elif gap_age_hours < 48 and gap.gap_duration_hours <= 48:
    # Gap muy reciente: también usar predicción
    result = await self._backfill_weather_aemet_forecast(gap)
elif gap_age_hours >= 72 or gap.gap_duration_hours >= 72:
    # Gap antiguo: usar valores climatológicos diarios
    result = await self._backfill_weather_aemet(gap)
else:
    # Gap intermedio (48-72h): observaciones horarias de estación
    result = await self._backfill_weather_aemet_hourly(gap)
```

**Beneficio clave:** Con el equipo encendido solo por las tardes, se recuperan hasta 48h de datos weather usando la predicción horaria por municipio.

#### Legacy 72-Hour Strategy (referencia)

```python
GAP_AGE_THRESHOLD_HOURS = 72

gap_age_hours = (datetime.now(timezone.utc) - gap.end_time).total_seconds() / 3600

if gap_age_hours < 72:
    # Recent gap: AEMET hourly observations
    # Endpoint: /observacion/convencional/datos/estacion/{idema}
    result = await self._backfill_weather_aemet_hourly(gap)
else:
    # Historical gap: AEMET daily climatological values
    # Endpoint: /valores/climatologicos/diarios/datos/fechaini/.../fechafin/.../estacion/{idema}
    result = await self._backfill_weather_aemet(gap)
```

**Why 72 hours?**
- AEMET `/valores/climatologicos/diarios` requires ~3 days processing delay
- API returns 404 "No hay datos que satisfagan esos criterios" for recent dates
- `/observacion/convencional` provides last 24h observations immediately
- OpenWeatherMap Free tier does NOT support historical data (current only)

#### Current Month vs Historical Strategy

```python
current_month = datetime.now().month
current_year = datetime.now().year

gap_month = gap.start_time.month
gap_year = gap.start_time.year

is_current_month = (gap_year == current_year and gap_month == current_month)

if is_current_month:
    # Use AEMET API (small batches, recent data)
    result = await self._backfill_weather_aemet(gap)
else:
    # Use SIAR ETL (historical CSV processing)
    result = await self._backfill_weather_siar(gap)
```

**AEMET Hourly Observations (<72h):**
```python
async def _backfill_weather_aemet_hourly(gap):
    # Uses current weather endpoint (last 24h available)
    write_result = await ingestion_service.ingest_aemet_weather(
        station_ids=["5279X"],  # Linares, Jaén
        start_date=None,  # None = current observations mode
        end_date=None
    )
    return write_result
```

**AEMET Daily Values (≥72h):**
```python
async def _backfill_weather_aemet(gap):
    # Uses climatological values endpoint (requires 3-day delay)
    write_result = await ingestion_service.ingest_aemet_weather(
        station_ids=["5279X"],  # Linares, Jaén
        start_date=gap.start_time,
        end_date=gap.end_time
    )
    return write_result
```

**SIAR Historical:**
```python
async def _backfill_weather_siar(gap):
    years_needed = [gap.start_time.year]
    etl_service = SiarETL()

    for year in years_needed:
        etl_result = await etl_service.process_station_data(
            station_id="5279X",
            years=1,
            target_year=year
        )
    return etl_result
```

### OpenWeatherMap Limitations

**Free Tier Capabilities:**
- ✅ Current weather data
- ✅ 5-day forecast (3h intervals)
- ❌ Historical data (requires paid tier)

**Practical Result:**
- Gaps <48h: OWM provides 1 current record (better than nothing)
- Gaps ≥48h: AEMET provides complete backfill

---

## API Reference

### Gap Detection Endpoints

#### `GET /gaps/summary`
Quick data status (REE + Weather gap hours)
```json
{
  "ree_data": {"status": "ok", "gap_hours": 0.0},
  "weather_data": {"status": "⚠️ 14h atrasado", "gap_hours": 14.9}
}
```

#### `GET /gaps/detect?days_back=N`
Detailed gap analysis with recommended strategy
```json
{
  "ree_gaps": [{"start": "...", "end": "...", "severity": "critical"}],
  "weather_gaps": [{"start": "...", "end": "...", "severity": "moderate"}],
  "recommendation": "Execute backfill immediately"
}
```

### Backfill Execution Endpoints

#### `POST /gaps/backfill?days_back=N`
Manual backfill execution (default: 10 days)
```bash
curl -X POST "http://localhost:8000/gaps/backfill?days_back=7"
```

#### `POST /gaps/backfill/auto?max_gap_hours=N`
Automatic intelligent backfill (default: 48h threshold with AEMET forecast)
```bash
curl -X POST "http://localhost:8000/gaps/backfill/auto?max_gap_hours=48"
```

**Threshold Configuration:**
- Current: 48 hours (optimizado con predicción AEMET por municipio)
- Location: `.claude/hooks/backfill.sh:121`
- Rationale: Permite recuperar hasta 48h de datos weather con el equipo encendido solo por las tardes
- Datos marcados con `data_type=forecast` para diferenciar de observaciones

#### `POST /gaps/backfill/range`
Date range specific backfill with data_source filter
```bash
curl -X POST "http://localhost:8000/gaps/backfill/range" \
  -d '{"start_date": "2025-10-01", "end_date": "2025-10-07", "data_source": "weather"}'
```

---

## Scheduler Integration

### Auto-Recovery Job

```python
# Registered in tasks/scheduler_config.py
scheduler.add_job(
    auto_backfill_job,
    trigger="interval",
    hours=2,
    id="auto_backfill",
    name="Auto Backfill (every 2 hours)"
)

async def auto_backfill_job():
    async with BackfillService() as service:
        result = await service.check_and_execute_auto_backfill(
            max_gap_hours=6.0
        )
        logger.info(f"Auto backfill: {result}")
```

---

## Monitoring & Troubleshooting

### Check System Status

```bash
# Quick gap check
curl http://localhost:8000/gaps/summary

# Detailed analysis
curl "http://localhost:8000/gaps/detect?days_back=7"

# Verify data freshness
curl http://localhost:8000/influxdb/verify
```

### Common Issues

**Gap persists after backfill:**
```bash
# Check backfill logs
docker logs chocolate_factory_brain | grep -i "backfill\|gap"

# Verify API connectivity
curl -I "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

# Manual re-execution
curl -X POST "http://localhost:8000/gaps/backfill?days_back=3"
```

**AEMET API failures:**
```bash
# Check gap age
curl http://localhost:8000/gaps/summary | jq '.weather_data.gap_hours'

# If gap <72h: uses hourly observations (immediate)
# If gap ≥72h: uses daily climatological values (3-day delay)

# Test AEMET endpoints directly:
# Hourly observations (last 24h):
docker compose exec fastapi-app curl -s \
  "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/5279X?api_key=${AEMET_API_KEY}"

# Daily values (requires 3-day delay):
docker compose exec fastapi-app curl -s \
  "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/2025-10-01T00:00:00UTC/fechafin/2025-10-02T00:00:00UTC/estacion/5279X?api_key=${AEMET_API_KEY}"
```

**Rate limiting errors:**
- REE: 30 requests/min (2s delay between calls)
- AEMET: 20 requests/min (3s delay)
- Automatic retry with exponential backoff implemented

---

## Performance Metrics

### Expected Results

**Successful Backfill:**
```json
{
  "status": "completed",
  "ree_records_recovered": 168,
  "weather_records_recovered": 156,
  "duration_seconds": 45,
  "gaps_resolved": 2
}
```

**Failure Indicators:**
- 0 records recovered after multiple attempts
- Timeout errors (increase chunk size)
- HTTP 429 errors (adjust rate limiting)

### Optimization Tips

**REE Backfill:**
- Use daily chunks (24h) for gaps >7 days
- Hourly chunks for gaps <24h
- Rate limit: 2s between requests

**Weather Backfill:**
- Use 72h strategy: hourly observations (<72h), daily values (≥72h)
- SIAR ETL for historical gaps (>current month)
- AEMET for current month gaps (respecting 3-day delay)

---

## Preventive Strategy

### Recommended Setup (Production)

**Current Implementation** (Default)
- ✅ AEMET hourly observations for gaps <72h (immediate availability)
- ✅ AEMET daily climatological for gaps ≥72h (3-day delay)
- ✅ Official quality data, consistent source
- ✅ Automatic switching based on gap age

**Gap Behavior:**
- System offline <24h: Backfill retrieves last 24h AEMET observations
- System offline >72h: Backfill uses daily climatological values
- Gap window: ~2h typical (last observation to current time)

---

## AEMET OpenData API

### Endpoints Used

**Hourly Observations** (immediate availability):
```
GET /observacion/convencional/datos/estacion/{idema}
```
- Returns: Last 24h observations from station
- Fields: ta (temp), hr (humidity), pres (pressure), vv (wind speed), prec (precipitation)
- Update frequency: Hourly
- Station 5279X: Linares VOR, Jaén

**Daily Climatological Values** (3-day processing delay):
```
GET /valores/climatologicos/diarios/datos/fechaini/{fecha_ini}/fechafin/{fecha_fin}/estacion/{idema}
```
- Returns: Daily aggregated values for date range
- Fields: tmed, tmax, tmin, hrMedia, presMax, velmedia, prec
- Date format: YYYY-MM-DDTHH:MM:SSUTC
- Limitation: Data available ~72h after observation date

### Response Format

Both endpoints return metadata first:
```json
{
  "descripcion": "exito",
  "estado": 200,
  "datos": "https://opendata.aemet.es/opendata/sh/{hash}",
  "metadatos": "https://opendata.aemet.es/opendata/sh/{hash}"
}
```

Then fetch actual data from `datos` URL (list of observations/values).

### Error Responses

**404 - No data available**:
```json
{
  "descripcion": "No hay datos que satisfagan esos criterios",
  "estado": 404
}
```
Common cause: Requesting daily values for dates <72h old.

**401 - Invalid API key**:
```json
{
  "descripcion": "API key invalido",
  "estado": 401
}
```

### Implementation

- Client: `src/fastapi-app/infrastructure/external_apis/aemet_client.py`
  - `get_current_weather()`: Hourly observations endpoint
  - `get_daily_weather()`: Daily climatological endpoint
- Token caching: 6-day validity, disk persistence
- Rate limiting: 20 req/min (3s delay)

### Technical Robustness & Edge Cases

- **Encoding Fallback**: AEMET API responses can sometimes be encoded in ISO-8859-1 (Latin-1) instead of UTF-8, especially in fields with Spanish accents. The client implements an automatic fallback to decode these correctly.
- **Timestamp Formatting**: The `/prediccion/...` endpoints return base dates in different formats (sometimes `YYYY-MM-DD`, sometimes `YYYY-MM-DDTHH:MM:SS`). The parser handles both by extracting only the date part before appending hourly offsets, avoiding "double T" ISO format errors.
- **Validation Script**: Use `scripts/test_aemet_parsing.py` to verify the JSON structure and parsing without requiring a full system rebuild.

### Documentation

- API Spec: https://opendata.aemet.es/AEMET_OpenData_specification.json
- Portal: https://opendata.aemet.es/dist/index.html

---

## Limitaciones y Estrategias

### Estrategia Actual: Predicción Horaria por Municipio (48h)

Con la predicción horaria AEMET por municipio (endpoint `/prediccion/especifica/municipio/horaria/23055`), se recuperan hasta **48 horas** de datos weather con el equipo apagado.

**Beneficio:** Encender el equipo solo por las tardes es suficiente para mantener datos completos.

**Pérdida de datos por apagado (con predicción AEMET):**

| Apagado | Gap | Fuente backfill | Pérdida |
|---------|-----|-----------------|---------|
| 12h     | 12h | Predicción 48h  | 0h      |
| 24h     | 24h | Predicción 48h  | 0h      |
| 48h     | 48h | Predicción 48h  | 0h      |
| 72h     | 72h | Observaciones   | ~60h    |

**Configuración actual:**
- Threshold: 48h (`.claude/hooks/backfill.sh:121`)
- Gaps <48h: 100% recuperación con predicción horaria
- Gaps ≥48h: recuperación parcial con observaciones (limitada a últimas 12h)

### AEMET: Fuentes de Datos

| Endpoint | Datos | Disponibilidad | Limitación |
|----------|-------|----------------|------------|
| `/prediccion/especifica/municipio/horaria/{municipio}` | Predicción 48h | Inmediata | Es PREDICCIÓN, no observación real |
| `/observacion/convencional/datos/estacion/{idema}` | Últimas 12h | Inmediata | Solo 12 registros |
| `/valores/climatologicos/diarios/...` | Históricos | 72h delay | Requiere 3 días procesamiento |

---

## Solución Futura: OpenWeatherMap One Call API 3.0

**Capacidades:**
- Históricos desde 1979 (45+ años)
- 1000 calls/día gratis
- 100% recuperación gaps hasta 5 días

**Caveats:**
- Requiere tarjeta crédito (no se cobra si <1000 calls/día)
- Configurar hard limit 1000 calls en dashboard para evitar cargos
- Requiere atribución "Powered by OpenWeather"
- Licencia: Open Database License (ODbL)

**Uso estimado:**
- Apagado 8h: 8 calls
- Weekend 48h: 48 calls
- Budget: 1000 calls/día suficiente

**Implementación:** Sprint pendiente (ver `.claude/sprints/infrastructure/SPRINT_XX_OWM_ONECALL_3.md`)

---

## References

- Gap Detection: `src/fastapi-app/services/gap_detector.py`
- Backfill Engine: `src/fastapi-app/services/backfill_service.py`
  - `_backfill_weather_aemet_forecast()`: Predicción horaria por municipio (gaps <48h)
  - `_backfill_weather_aemet_hourly()`: Observaciones de estación (gaps 48-72h)
  - `_backfill_weather_aemet()`: Valores climatológicos diarios (gaps ≥72h)
- AEMET Client: `src/fastapi-app/infrastructure/external_apis/aemet_client.py`
  - `get_hourly_forecast_municipality()`: Predicción horaria por municipio (48h)
  - `get_current_weather()`: Observaciones horarias de estación
  - `get_daily_weather()`: Valores climatológicos diarios
- Data Ingestion: `src/fastapi-app/services/data_ingestion.py`
  - `ingest_weather_forecast()`: Ingesta datos de predicción (tag `data_type=forecast`)
- Scheduler Jobs: `src/fastapi-app/tasks/scheduler_config.py`, `gap_detection_jobs.py`
- Router: `src/fastapi-app/api/routers/gaps.py`
- Hook: `.claude/hooks/backfill.sh` (max_gap_hours=48)
