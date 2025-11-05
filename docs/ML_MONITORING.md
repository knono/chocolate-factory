# Model Monitoring - Sprint 20

Sistema de tracking de métricas ML para detección de degradación de modelos.

## Arquitectura

### ModelMetricsTracker

Clase para tracking CSV de métricas ML.

**Ubicación**: `domain/ml/model_metrics_tracker.py`

**Funciones**:
- Log metrics to CSV (append-only)
- Baseline calculation (median over window)
- Degradation detection (threshold-based)
- Metrics history retrieval

### CSV Storage

**Path**: `/app/models/metrics_history.csv`

**Columns**:
- `timestamp`: ISO 8601 format
- `model_name`: Model identifier (e.g., "prophet_price_forecast")
- `mae`: Mean Absolute Error
- `rmse`: Root Mean Squared Error
- `r2`: R² score
- `samples`: Training samples count
- `duration_seconds`: Training duration
- `notes`: Free text (e.g., "manual_train", "scheduled_retrain")

**Formato**:
```csv
timestamp,model_name,mae,rmse,r2,samples,duration_seconds,notes
2025-11-05T10:30:00,prophet_price_forecast,0.033,0.048,0.49,12493,45.2,manual_train
```

## Integration

### Prophet Training

**Service**: `services/price_forecasting_service.py`

Metrics logged automatically after training:

```python
self.metrics_tracker.log_metrics(
    model_name="prophet_price_forecast",
    metrics={
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "samples": len(df_train),
        "duration_seconds": training_duration
    },
    notes="scheduled_retrain" if hasattr(self, '_scheduled_run') else "manual_train"
)
```

### Degradation Detection

**Job**: `tasks/ml_jobs.py:ensure_prophet_model_job()`

Ejecuta después de cada training:

```python
degradation = forecast_service.metrics_tracker.detect_degradation(
    model_name="prophet_price_forecast",
    current_metrics=current_metrics,
    threshold_multiplier=2.0
)
```

**Thresholds**:
- MAE >2x baseline → WARNING alert
- R² <50% baseline → WARNING alert

### Telegram Alerts

**Topic**: `prophet_model_degradation`
**Severity**: `WARNING`
**Rate limit**: 15 minutes

Alert message format:
```
⚠️ Prophet model degradation detected:
MAE degradation: 0.0700 vs baseline 0.0350 (2.0x higher)
```

## API Endpoints

### GET /models/metrics-history

Retrieve metrics history with filters.

**Query parameters**:
- `model_name`: Optional filter (e.g., "prophet_price_forecast")
- `limit`: Max entries (1-1000, default 100)

**Response**:
```json
{
  "model_name": "prophet_price_forecast",
  "total_entries": 45,
  "entries": [
    {
      "timestamp": "2025-11-05T10:30:00",
      "model_name": "prophet_price_forecast",
      "mae": 0.033,
      "rmse": 0.048,
      "r2": 0.49,
      "samples": 12493,
      "duration_seconds": 45.2,
      "notes": "scheduled_retrain"
    }
  ],
  "baseline_metrics": {
    "mae": 0.035,
    "rmse": 0.050,
    "r2": 0.48
  }
}
```

**Usage**:
```bash
# All models
curl http://localhost:8000/models/metrics-history?limit=50

# Specific model
curl http://localhost:8000/models/metrics-history?model_name=prophet_price_forecast&limit=100
```

## Baseline Calculation

**Method**: Median of recent entries
**Window**: 30 entries (configurable)
**Minimum entries**: 3 (returns None if insufficient)

```python
baseline_mae = tracker.get_baseline("prophet_price_forecast", "mae", window_entries=30)
```

## Degradation Detection

Compares current metrics against baseline.

**Thresholds**:
- MAE: Alert if `current_mae > baseline_mae * 2.0`
- R²: Alert if `current_r2 < baseline_r2 * 0.5`

**Returns**:
```python
{
    "degradation_detected": True,
    "model_name": "prophet_price_forecast",
    "current_metrics": {"mae": 0.070, "rmse": 0.095, "r2": 0.30},
    "baseline_metrics": {"mae": 0.035, "rmse": 0.050, "r2": 0.48},
    "alerts": [
        {
            "metric": "mae",
            "current": 0.070,
            "baseline": 0.035,
            "ratio": 2.0,
            "message": "MAE degradation: 0.0700 vs baseline 0.0350 (2.0x higher)"
        }
    ]
}
```

## Testing

**Test file**: `tests/unit/test_model_metrics.py`
**Coverage**: 18 tests (100% passing)

**Test classes**:
- `TestModelMetricsTrackerInitialization` (2 tests)
- `TestMetricsLogging` (3 tests)
- `TestBaselineCalculation` (4 tests)
- `TestDegradationDetection` (4 tests)
- `TestMetricsHistoryRetrieval` (5 tests)

**Run tests**:
```bash
pytest tests/unit/test_model_metrics.py -v
```

## Verification

### Manual Prophet Training

Trigger training to generate CSV:

```bash
# API call
curl -X POST http://localhost:8000/models/price-forecast/train

# Check CSV created
ls -lh /app/models/metrics_history.csv

# View contents
cat /app/models/metrics_history.csv
```

### Metrics History API

```bash
# Check metrics logged
curl http://localhost:8000/models/metrics-history?model_name=prophet_price_forecast

# Should return entries with timestamps
```

### Degradation Detection Test

Simulate degradation by training with degraded data:

1. Train model with good data
2. Train model with reduced/noisy data
3. Check Telegram for degradation alert
4. Verify API shows baseline comparison

## Limitations

- **CSV only**: No database storage, append-only file
- **No rotation**: CSV grows indefinitely (manual cleanup required)
- **Single file**: All models share same CSV (filtered by model_name)
- **No versioning**: No tracking of model file versions
- **Baseline window**: Fixed at 30 entries (not time-based)
- **Thresholds**: Hardcoded (2x MAE, 0.5x R²), not configurable per model
- **No drift detection**: Only sudden degradation, not gradual drift
- **Manual cleanup**: No automatic CSV archival or compression

## Maintenance

### CSV Cleanup

Manual rotation recommended after ~1000 entries:

```bash
# Backup current CSV
cp /app/models/metrics_history.csv /app/models/metrics_history_$(date +%Y%m%d).csv

# Keep last 100 entries
tail -n 100 /app/models/metrics_history.csv > /app/models/metrics_history_new.csv
mv /app/models/metrics_history_new.csv /app/models/metrics_history.csv
```

### Baseline Adjustment

If model changes significantly (new features, data sources):

1. Archive old CSV
2. Create new CSV (automatic on first training)
3. Accumulate 30+ entries before degradation detection becomes reliable

## Future Improvements

Potential enhancements (not implemented):

- Database storage (InfluxDB measurement)
- Time-based baseline windows (e.g., last 7 days)
- Configurable thresholds per model
- Model version tracking
- Automatic CSV rotation
- Drift detection (gradual degradation)
- Dashboard visualization (metrics over time)
- Model comparison (A/B testing)
