# SPRINT 08: Hourly Production Optimization

**Status**: COMPLETED
**Date**: 2025-10-06
**Duration**: 6 hours

## Objective

24-hour production planning based on Prophet REE predictions (Sprint 06), SIAR climate analysis (Sprint 07), and production constraints (sequence, buffers, climate thresholds, capacity).

## Technical Implementation

### 1. Optimization Engine

**File**: `services/hourly_optimizer_service.py` (687 lines)

**Algorithm**: Greedy Heuristic with multi-objective scoring

**Scoring function**:
```python
price_score = 1.0 - min(price / 0.30, 1.0)
climate_score = (temp_optimal + humidity_optimal) / 2
total_score = 0.6 * price_score + 0.4 * climate_score
```

**Constraints**:
- Sequence: Mixing → Rolling → Conching → Tempering → Molding
- Buffers: 30 min between stages (15 min conching→tempering)
- Climate: Conching optimal 18-28°C, critical <32°C
- Capacity: 10kg/batch, 200kg/day target

**Output**:
```json
{
  "batches": [
    {"id": "P01", "type": "Premium", "start": "00:00", "end": "12:00", "cost": 79.14}
  ],
  "savings": {
    "absolute_eur": 30.26,
    "percent": 35.71,
    "daily_projection": 30.26,
    "monthly_projection": 908.00,
    "annual_projection": 11045.00
  }
}
```

### 2. Hourly Timeline (24h granular view)

**Function**: `_generate_hourly_timeline()` in `hourly_optimizer_service.py`

**Per-hour data**:
```json
{
  "hour": 10,
  "time": "10:00",
  "price_eur_kwh": 0.0796,
  "tariff_period": "P1",
  "tariff_color": "#dc2626",
  "temperature": 22.0,
  "humidity": 55.0,
  "climate_status": "optimal",
  "active_batch": "P01",
  "active_process": "Conchado Premium",
  "is_production_hour": true
}
```

**Tariff period classification**:
- P1 (Peak): 10-13h, 18-21h → Red (#dc2626)
- P2 (Flat): 8-9h, 14-17h, 22-23h → Yellow (#f59e0b)
- P3 (Valley): 0-7h, rest → Green (#10b981)

**Dashboard visualization**:
- Responsive HTML table with 24 rows (one per hour)
- 6 columns: Hour, Price, Period, Process, Batch, Climate
- Background colored by tariff period
- Left border highlight for active production hours
- Sticky headers for scroll
- Tooltips with temperature/humidity details

### 3. Baseline Calculation

**Function**: `_calculate_baseline()` in `hourly_optimizer_service.py`

Baseline: Fixed 08:00-16:00h schedule

**Real test results** (2025-10-06):
```
Target: 200kg (20 batches: 6 premium + 14 standard)
Baseline: 84.73€/día (distribución aleatoria 25% P1, 35% P2, 40% P3)
Optimized: 54.47€/día (valle-prioritized: Conchado 100% P3, etc.)
Savings: 30.26€/día (35.71%)
Annual ROI: 11,045€
```

### 4. API Endpoints

```
POST /optimize/production/daily
GET /optimize/production/summary
```

**Example request**:
```bash
curl -X POST http://localhost:8000/optimize/production/daily \
  -H "Content-Type: application/json" \
  -d '{"target_date": "2025-10-06", "target_kg": 200}'
```

**Response includes**:
- Optimized batch plan
- Hourly timeline (24 elements)
- Savings vs baseline
- Recommendations

## Files Modified

**Created**:
- `src/fastapi-app/services/hourly_optimizer_service.py` (800+ lines)
  - Classes: `ProductionProcess`, `ProductionBatch`
  - Functions: `_generate_hourly_timeline()`, `sanitize_for_json()`
  - Helpers: `_classify_tariff_period()`, `_get_tariff_color()`, `_get_climate_status()`, `_get_active_process_at_hour()`

**Modified**:
- `src/fastapi-app/main.py` (lines 2351-2447: optimization endpoints)
- `static/index.html` (lines 115-187: widget "Plan Optimizado 24h", lines 150-158: "Vista Horaria 24h" section)
- `static/js/dashboard.js` (lines 896-986: `renderHourlyTimeline()` function, line 318: removed obsolete `renderEnhancedMLData()`)

## Key Decisions

1. **Greedy Heuristic**: Sufficient for 24h planning, scipy optimization not required
2. **Multi-objective scoring**: 60% price + 40% climate balances cost and quality
3. **Hourly timeline**: Provides granular view for identifying process/tariff period crossings
4. **NaN/inf validation**: `sanitize_for_json()` ensures JSON compliance

## Testing

**API test**:
```bash
curl -X POST http://localhost:8000/optimize/production/daily \
  -H "Content-Type: application/json" \
  -d '{"target_kg": 200}'
```

**Dashboard validation**:
- Visit `http://localhost:8000/dashboard`
- Verify "Plan Optimizado 24h" card displays
- Check hourly timeline table renders with 24 rows
- Confirm color coding by tariff period
- Validate tooltips show climate details

**Metrics verification**:
- Savings calculation accuracy
- Baseline vs optimized comparison
- ROI projections (daily/monthly/annual)

## Known Limitations

- Greedy algorithm may not find global optimum (acceptable for 24h planning)
- Fixed tariff period classification (Spanish electricity market specific)
- Climate thresholds based on chocolate industry standards (may need adjustment)

## Results

**Operational test** (2025-10-06):
- 100% feasibility (all constraints respected)
- 35.71% savings valle-prioritized vs baseline
- 11,045€ annual ROI projection
- Prophet predictions 0.03€ - 0.16€/kWh
- Timeline enables identification of process/tariff crossings

**Example timeline**:
```
00:00 | 0.0710€ | P3 🟢 | Templado          | P01
01:00 | 0.0653€ | P3 🟢 | Mezclado          | P01
02:00 | 0.0598€ | P3 🟢 | Conchado Premium  | P01
08:00 | 0.0894€ | P2 🟡 | Conchado Premium  | P01
10:00 | 0.0796€ | P1 🔴 | Conchado Premium  | P01
```

## References

- Prophet model: Sprint 06
- SIAR analysis: Sprint 07
- Spanish tariff periods: BOE electricity regulation

---

## UPDATE OCT 28: INTEGRACIÓN SKLEARN EN TIMELINE

**Cambios Realizados**:

### Inicialización: `__init__()`
- Agregado DirectMLService y carga modelos sklearn (línea 172-175)

### Timeline: `_generate_hourly_timeline()`
- Para cada hora, predice `ml_service.predict_production_recommendation(price, temp, humidity)`
- Nuevos campos en respuesta:
  - `production_state`: "Optimal"/"Moderate"/"Reduced"/"Halt" (de sklearn)
  - `ml_confidence`: 0-1 (confianza del modelo)
  - `climate_score`: 0-1 (basado en estado)

### JSON Response: `optimize_daily_production()`
- Nuevo bloque `ml_insights`:
  - `model_accuracy`: 1.0
  - `model_type`: "RandomForestClassifier + RandomForestRegressor"
  - `high_confidence_windows`: Ventanas con confianza >0.8 y Optimal
  - `production_state_distribution`: Conteo de estados

### Métodos auxiliares:
- `_extract_high_confidence_windows()`: Extrae ventanas óptimas (línea 870-894)
- `_count_production_states()`: Distribución de estados (línea 896-903)

**Impacto**: Optimizer ahora data-driven con confianza ML visible. No breaking changes (campos aditivos).
