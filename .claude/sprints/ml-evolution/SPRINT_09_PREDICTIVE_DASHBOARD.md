# SPRINT 09: Predictive Dashboard

**Status**: COMPLETED
**Date**: 2025-10-07
**Duration**: 8 hours

## Objective

Unified predictive dashboard with optimal production windows (7 days), REE D-1 deviation analysis, predictive alerts, and savings tracking.

## Technical Implementation

### 1. Predictive Insights Service

**File**: `services/predictive_insights_service.py`

**Methods**:
- `get_optimal_windows()`: 7-day Prophet forecast with production recommendations
- `get_ree_deviation()`: D-1 vs real price comparison (last 24h)
- `get_predictive_alerts()`: Threshold-based alerts (price spikes, climate extremes)
- `get_savings_tracking()`: ROI tracking with baseline comparison

### 2. API Endpoints

**Router**: `api/routers/insights.py`

```
GET /insights/optimal-windows
GET /insights/ree-deviation
GET /insights/alerts
GET /insights/savings-tracking
```

**Example responses**:

**Optimal windows**:
```json
{
  "windows": [
    {
      "date": "2025-10-08",
      "period": "00:00-06:00",
      "avg_price": 0.08,
      "quality": "excellent",
      "recommended_kg": 80,
      "savings_vs_peak": 12.00
    }
  ]
}
```

**Savings tracking**:
```json
{
  "daily_saving": 30.26,
  "weekly_saving": 211.82,
  "monthly_saving": 908.00,
  "annual_projection": 11045.00,
  "comparison": {
    "optimized_cost": 54.47,
    "baseline_cost": 84.73,
    "percent_saving": 35.71
  }
}
```

### 3. Dashboard Integration

**Cards added to dashboard**:
1. "Optimal Production Windows (7 days)"
2. "REE D-1 Deviation Analysis"
3. "Predictive Alerts"
4. "Savings Tracking"

**JavaScript rendering**:
- `static/js/dashboard.js`: Functions for each card
- Real-time updates every 30 seconds
- Color-coded indicators (green/yellow/red)

### 4. BusinessLogicService Integration

**Location**: `services/business_logic_service.py` (implemented Sprint 05)

Humanized recommendations integrated into optimal windows widget:
- Current energy moment analysis
- Savings opportunity vs average
- Process-specific recommendations (Conching/Rolling/Tempering)
- Spanish business context

### 5. ROI Tracking

**Trazability**:
```
Frontend Dashboard
  ↓
GET /insights/savings-tracking (routers/insights.py:259)
  ↓
PredictiveInsightsService.get_savings_tracking() (line 333)
  ↓
ROI calculations:
  - Daily: 30.26€ savings/day (54.47€ optimized vs 84.73€ baseline)
  - Weekly: 211.82€/week
  - Monthly: 908€/month
  - Annual: 11,045€/year
```

**Dashboard card**:
- Current savings (daily/weekly/monthly/annual)
- Progress vs monthly target (908€/month)
- Comparison optimized vs baseline (35.7% savings valle-prioritized)
- ROI description: "11k€/year estimated"

## Files Modified

**Created**:
- `src/fastapi-app/services/predictive_insights_service.py`
- `src/fastapi-app/api/routers/insights.py`

**Modified**:
- `src/fastapi-app/main.py` (register insights router)
- `src/fastapi-app/services/dashboard.py` (integrate predictive data)
- `static/index.html` (4 new dashboard cards)
- `static/js/dashboard.js` (rendering functions for insights)
- `static/css/dashboard.css` (styling for new cards)

## Key Decisions

1. **Rescate funcionalidad Sprint 08**: Card "Análisis REE" removed (redundant with Hourly Timeline), functionality integrated into unified widgets
2. **BusinessLogicService maintained**: Implemented Sprint 05, humanized recommendations integrated into optimal windows (not separate card)
3. **ROI tracking already implemented**: Sprint 09 completed tracking, verified in Sprint 10
4. **7-day forecast scope**: Balance between accuracy (Prophet) and planning horizon

## Testing

**API endpoint tests**:
```bash
curl http://localhost:8000/insights/optimal-windows
curl http://localhost:8000/insights/ree-deviation
curl http://localhost:8000/insights/alerts
curl http://localhost:8000/insights/savings-tracking
```

**Dashboard validation**:
- Visit `http://localhost:8000/dashboard`
- Verify 4 new cards render correctly
- Check real-time updates (30s refresh)
- Validate savings calculations against baseline

**Prophet integration**:
- Verify 168h forecast availability
- Check confidence intervals
- Validate price range (0.03€ - 0.16€/kWh)

## Known Limitations

- REE D-1 deviation only last 24h (limited historical comparison)
- Prophet accuracy varies by market volatility (MAE 0.033 €/kWh from Sprint 06)
- Alerts threshold-based (no ML classification)
- Savings tracking assumes consistent production patterns

## Results

**Metrics**:
- 11,045€/year energy savings (ROI tracking active)
- 35.7% savings vs baseline (valle-prioritized strategy)
- 7-day optimal window recommendations
- Real-time predictive alerts

**Dashboard completion**:
- 4 new cards operational
- Integration with Sprints 06-08 (Prophet, SIAR, Optimization)
- Unified view: predictions + historical + current + recommendations

## References

- Prophet forecasting: Sprint 06
- SIAR analysis: Sprint 07
- Hourly optimization: Sprint 08
- BusinessLogicService: Sprint 05
