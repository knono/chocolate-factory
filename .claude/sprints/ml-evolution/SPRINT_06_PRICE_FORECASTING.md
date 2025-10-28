# SPRINT 06: Price Forecasting (Prophet ML)

**Status**: COMPLETED
**Date**: 2025-10-03
**Time**: ~8 hours

---

## Objective

Implement Prophet model for REE price forecasting (168-hour horizon) to replace static heatmap with real predictions.

---

## Technical Implementation

### Model: Prophet 1.1.7

**File**: `src/fastapi-app/services/price_forecasting_service.py` (450 lines)

**Training Data**: 1,844 REE records (1,475 train / 369 test)

**Performance Metrics**:
- MAE: 0.0325 €/kWh (target: <0.02)
- RMSE: 0.0396 €/kWh (target: <0.03)
- R²: 0.489 (target: >0.85)
- Coverage 95%: 88.3% (target: >90%)

**Configuration**:
```python
from prophet import Prophet

model = Prophet(
    changepoint_prior_scale=0.05,
    seasonality_prior_scale=10.0,
    holidays_prior_scale=10.0,
    seasonality_mode='multiplicative',
    interval_width=0.95
)

# Hourly seasonality
model.add_seasonality(name='hourly', period=1, fourier_order=3)

# Daily seasonality
model.add_seasonality(name='daily', period=1, fourier_order=8)

# Weekly seasonality
model.add_seasonality(name='weekly', period=7, fourier_order=3)
```

---

## API Endpoints

### Prediction Endpoints

**`GET /predict/prices/weekly`**
- Returns: 168-hour forecast with confidence intervals
- Response: `[{timestamp, predicted_price, confidence_lower, confidence_upper}]`

**`GET /predict/prices/hourly?hours=N`**
- Configurable forecast horizon (1-168 hours)
- Default: 24 hours

**`GET /models/price-forecast/status`**
- Model metrics: MAE, RMSE, R², coverage, last training timestamp
- Training data summary

**`POST /models/price-forecast/train`**
- Manual retraining trigger
- Fetches latest REE data from InfluxDB

---

## Dashboard Integration

**Heatmap Updates**:
- Removed static `_generate_weekly_heatmap()` method
- Prophet predictions populate 7-day heatmap grid
- Real-time forecasts replace historical data

**Color Coding**:
- Green: ≤ 0.10 €/kWh (LOW)
- Yellow: 0.10-0.20 €/kWh (MEDIUM)
- Red: > 0.20 €/kWh (HIGH)

**Tooltip Implementation**:
- CSS `data-tooltip` attribute (Safari/Chrome/Brave compatible)
- Displays: Price, timestamp, confidence interval

**Model Info Display**:
- MAE, RMSE, R² visible in dashboard
- Last training timestamp
- Forecast generation time

**Nginx Configuration**:
- `/dashboard/heatmap` endpoint allowed in Tailscale sidecar
- HTTPS access via Tailscale domain

---

## Data Storage

**InfluxDB Measurement**: `price_predictions`

**Bucket**: `energy_data`

**Schema**:
```
Fields:
  - predicted_price (float)
  - confidence_lower (float)
  - confidence_upper (float)

Tags:
  - model_type: "prophet"
  - model_version: "1.1.7"
  - forecast_horizon: "168h"
```

---

## Automation

**APScheduler Job**: `price_forecasting_update`

**Frequency**: Hourly (cron: `minute=30`)

**Actions**:
1. Fetch latest REE data from InfluxDB
2. Generate 168-hour forecast
3. Store predictions in InfluxDB
4. Alert if any price > 0.35 €/kWh

**Configuration**:
```python
scheduler.add_job(
    update_price_forecasts,
    trigger="cron",
    minute=30,
    id="price_forecasting_update",
    name="Price Forecasting Update (hourly)"
)
```

---

## Key Decisions

**Why Prophet over LSTM?**
- Automatic seasonality handling
- Robust with missing data
- Native confidence intervals
- Fewer hyperparameters
- Faster training (2-3 minutes vs 15-20 minutes)

**Seasonality Strategy**:
- Hourly: Fourier order 3 (intraday patterns)
- Daily: Fourier order 8 (daily cycles)
- Weekly: Fourier order 3 (weekend/weekday patterns)

**Performance Trade-offs**:
- MAE 0.0325 acceptable for MVP (3.25 cents error)
- R² 0.489 indicates room for improvement
- Coverage 88.3% close to target 90%

---

## UPDATE OCT 28: VARIABLES EXÓGENAS AGREGADAS

**Cambios Realizados**:

### Nuevo método: `_add_prophet_features()`
- Holidays españoles fijos (Año Nuevo, Reyes, Asunción, etc.)
- `is_peak_hour`: 1 si 10-13 o 18-21 (demanda máxima)
- `is_weekend`: 1 si sábado/domingo
- `is_holiday`: 1 si festividad española

### Modificación: `train_model()`
- Integrado `model.add_country_holidays('ES')`
- Agregados regressores: `is_peak_hour`, `is_weekend`, `is_holiday`
- Prior scales: 0.1, 0.05, 0.1

### Modificación: `predict_weekly()`
- Ahora agrega features antes de predecir
- Captura holidays en rango de predicción

**Impacto Esperado**: R² 0.489 → 0.55-0.65, MAE 0.0325 → 0.027-0.030

---

## Files Modified

**Core Implementation**:
- `src/fastapi-app/services/price_forecasting_service.py` (NEW - 450 lines)
- `src/fastapi-app/api/routers/ml.py` (UPDATED - 4 new endpoints)
- `src/fastapi-app/tasks/scheduler_config.py` (UPDATED - new job)

**Dashboard**:
- `static/js/dashboard.js` (UPDATED - Prophet integration)
- `static/css/dashboard.css` (UPDATED - tooltip styles)
- `docker/nginx.conf` (UPDATED - heatmap endpoint)

**Database**:
- InfluxDB schema: `price_predictions` measurement created

---

## Testing

**Manual Tests**:
```bash
# Generate forecast
curl -X POST http://localhost:8000/models/price-forecast/train

# Get weekly predictions
curl http://localhost:8000/predict/prices/weekly

# Check model status
curl http://localhost:8000/models/price-forecast/status

# Verify dashboard
curl http://localhost:8000/dashboard/heatmap
```

**Results**:
- Training completes in ~2 minutes
- 168 predictions generated successfully
- InfluxDB stores all predictions
- Dashboard renders heatmap correctly
- Tooltips work in Safari/Chrome/Brave

---

## Known Limitations

**Model Performance**:
- R² 0.489 suggests simple linear patterns captured
- Complex price spikes not well predicted
- Improvement requires: feature engineering, external data (weather, demand)

**Data Quality**:
- Only 1,844 training records (ideally 10,000+)
- Missing data handled by Prophet but reduces accuracy
- No exogenous variables (temperature, holidays, demand)

**Forecast Accuracy**:
- Short-term (24h): More reliable
- Long-term (168h): Confidence intervals widen
- Weekend predictions less accurate (less training data)

---

## Future Improvements

**Model Enhancements**:
- Add exogenous regressors (temperature, day type)
- Incorporate Spanish holidays calendar
- Ensemble with LSTM for complex patterns

**Data Augmentation**:
- Fetch 5+ years historical REE data (ESIOS API)
- Add weather correlation features
- Include electricity demand data

**Performance Optimization**:
- Cache predictions in Redis
- Incremental training (update vs full retrain)
- Model versioning and A/B testing

---

## References

- Prophet Documentation: https://facebook.github.io/prophet/
- REE API: https://www.ree.es/es/apidatos
- Implementation: `src/fastapi-app/services/price_forecasting_service.py:1-450`
- Dashboard: `static/js/dashboard.js:fetchWeeklyHeatmap()`
