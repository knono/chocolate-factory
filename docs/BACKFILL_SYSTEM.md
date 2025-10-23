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

**Dual strategy based on gap age:**

#### 48-Hour Strategy (Intelligent Temporal Decision)

```python
RECENT_GAP_THRESHOLD_HOURS = 48

hours_since_gap_end = (datetime.now(timezone.utc) - gap.end_time).total_seconds() / 3600

if hours_since_gap_end < 48:
    # Recent gap: Use OpenWeatherMap current data
    # AEMET needs 24-48h to consolidate official data
    result = await self._backfill_weather_openweather(gap)
else:
    # Historical gap: Use AEMET consolidated data
    result = await self._backfill_weather_aemet(gap)
```

**Why 48 hours?**
- AEMET API requires 24-48h to consolidate daily official data
- Attempts to fetch data <48h from AEMET result in connection errors
- OpenWeatherMap provides current data but NOT historical (free tier)

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

**AEMET Current Month:**
```python
async def _backfill_weather_aemet(gap):
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
Automatic intelligent backfill (default: 6.0h threshold)
```bash
curl -X POST "http://localhost:8000/gaps/backfill/auto?max_gap_hours=12"
```

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
# Check if gap is <48h (AEMET limitation)
curl http://localhost:8000/gaps/summary | jq '.weather_data.gap_hours'

# If <48h, wait for AEMET consolidation or use preventive OWM ingestion
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
- Use 48h strategy for recent gaps
- SIAR ETL for historical gaps (>current month)
- AEMET for current month gaps

---

## Preventive Strategy

### Recommended Setup (Production)

**Option 1: Accept 48h AEMET Gap** (Default)
- ✅ Official quality data
- ✅ No additional cost
- ✅ Consistent data source
- ⏳ Temporary 48h gap

**Option 2: Preventive OWM Ingestion** (Recommended)
```python
# Add to scheduler_config.py
scheduler.add_job(
    ingest_current_weather_preventive,
    trigger="interval",
    hours=1,
    id="openweather_preventive",
    name="OpenWeather Preventive Ingestion (hourly)"
)

async def ingest_current_weather_preventive():
    async with DataIngestionService() as service:
        result = await service.ingest_openweathermap_weather()
        logger.info(f"Preventive OWM: {result.successful_writes} records")
```

**Result:** Gap reduced from 48h to 1-2h maximum

---

## References

- Gap Detection: `src/fastapi-app/services/gap_detector.py`
- Backfill Engine: `src/fastapi-app/services/backfill_service.py`
- Scheduler Jobs: `src/fastapi-app/tasks/scheduler_config.py`
- Router: `src/fastapi-app/api/routers/gaps.py`
