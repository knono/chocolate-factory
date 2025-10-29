"""
Insights Router - Sprint 09
============================

RESTful endpoints for predictive insights and dashboard widgets.

Endpoints:
- GET /insights/optimal-windows - Next 7 days optimal production windows
- GET /insights/ree-deviation - REE D-1 vs Real analysis (last 24h)
- GET /insights/alerts - Predictive alerts (price spikes, weather)
- GET /insights/savings-tracking - Real savings vs baseline
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query

from services.predictive_insights_service import PredictiveInsightsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Predictive Insights"])


def get_insights_service() -> PredictiveInsightsService:
    """
    Dependency injection for PredictiveInsightsService.

    Returns:
        PredictiveInsightsService: Insights service instance
    """
    try:
        return PredictiveInsightsService()
    except Exception as e:
        logger.error(f"Failed to initialize PredictiveInsightsService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Insights service initialization failed: {str(e)}"
        )


@router.get("/optimal-windows")
async def get_optimal_windows(
    days: int = Query(default=7, ge=1, le=14, description="Number of days to forecast"),
    service: PredictiveInsightsService = Depends(get_insights_service)
) -> Dict[str, Any]:
    """
    🟢 Get optimal production windows for next N days.

    Uses Prophet price forecasts + tariff period classification to identify
    best time slots for production:
    - Valle (P3): 00-07h + rest hours (<0.10 €/kWh typically)
    - Llano (P2): 08-09h, 14-17h, 22-23h (0.10-0.20 €/kWh)
    - Avoid Punta (P1): 10-13h, 18-21h (>0.20 €/kWh)

    **Widget Integration**: Powers "Próximas Ventanas Óptimas" dashboard card.

    Args:
        days: Number of days to forecast (1-14, default 7)

    Returns:
        Dict with:
        - optimal_windows: List of recommended production windows
        - avoid_windows: List of windows to avoid (high prices)
        - summary: Totals and statistics

    Example Response:
    ```json
    {
        "status": "success",
        "optimal_windows": [
            {
                "datetime": "2025-10-08T02:00:00",
                "hours": "02-05h",
                "duration_hours": 3,
                "avg_price_eur_kwh": 0.0654,
                "tariff_period": "P3",
                "quality": "EXCELLENT",
                "icon": "🟢",
                "recommended_process": "Conchado intensivo 80kg",
                "estimated_savings_eur": 18.45,
                "recommendation": "EXCELLENT (0.07€/kWh) - Conchado intensivo"
            }
        ],
        "avoid_windows": [
            {
                "datetime": "2025-10-08T19:00:00",
                "hours": "19-21h",
                "avg_price": 0.3234,
                "tariff_period": "P1",
                "recommendation": "⚠️ EVITAR - Solo completar lotes en curso"
            }
        ],
        "summary": {
            "total_optimal_hours": 42,
            "total_avoid_hours": 21,
            "best_price": 0.0621,
            "worst_price": 0.3456
        }
    }
    ```
    """
    try:
        result = await service.get_optimal_windows(days=days)

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimal windows endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get optimal windows: {str(e)}")


@router.get("/ree-deviation")
async def get_ree_deviation(
    service: PredictiveInsightsService = Depends(get_insights_service)
) -> Dict[str, Any]:
    """
    📊 Analyze REE D-1 predictions vs real prices (last 24h).

    REE publishes day-ahead (D-1) prices at 20:15 for next day.
    This endpoint compares Prophet forecasts with actual prices to measure
    prediction reliability.

    **Widget Integration**: Powers "REE D-1 vs REAL" dashboard card.

    Returns:
        Dict with:
        - deviation_summary: Average, max, accuracy metrics
        - reliability_by_period: Valle vs Punta reliability
        - worst_deviation: Hour with largest error
        - hourly_deviations: Detailed hourly comparison

    Example Response:
    ```json
    {
        "status": "success",
        "deviation_summary": {
            "avg_deviation_eur_kwh": 0.0183,
            "max_deviation_eur_kwh": 0.0421,
            "accuracy_score_pct": 87.5,
            "trend": "STABLE"
        },
        "reliability_by_period": {
            "valle_p3": {
                "avg_deviation": 0.0121,
                "reliability": "✅ Más confiable"
            },
            "punta_p1": {
                "avg_deviation": 0.0287,
                "reliability": "⚠️ Mayor desviación"
            }
        },
        "worst_deviation": {
            "hour": "19:00",
            "predicted": 0.2847,
            "actual": 0.3268,
            "deviation": 0.0421
        }
    }
    ```
    """
    try:
        result = await service.get_ree_deviation_analysis()

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"REE deviation endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze REE deviation: {str(e)}")


@router.get("/alerts")
async def get_predictive_alerts(
    service: PredictiveInsightsService = Depends(get_insights_service)
) -> Dict[str, Any]:
    """
    ⚠️ Get predictive alerts for next 24-48h.

    Alert types:
    - ⚠️ **Price spike**: >0.30 €/kWh predicted (avoid production)
    - 🌡️ **Heat wave**: >28.8°C next 3 days (SIAR P90 threshold)
    - 💰 **Optimal window**: Next 6h in valle (<0.10 €/kWh)
    - ❄️ **Production boost**: Exceptional conditions detected

    **Widget Integration**: Powers "Alertas Predictivas" dashboard section.

    Returns:
        Dict with:
        - alerts: List of active alerts with severity and recommendations
        - active_count: Total number of alerts
        - high_severity_count: Critical alerts requiring immediate action

    Example Response:
    ```json
    {
        "status": "success",
        "alerts": [
            {
                "type": "price_spike",
                "severity": "high",
                "icon": "⚠️",
                "message": "Pico precio inminente: 19h hoy (0.34€/kWh predicho)",
                "recommendation": "Evitar producción intensiva durante esta ventana",
                "datetime": "2025-10-08T19:00:00"
            },
            {
                "type": "optimal_window",
                "severity": "info",
                "icon": "💰",
                "message": "Ventana óptima abierta: Próximas 4h precios valle",
                "recommendation": "Oportunidad para producción intensiva",
                "datetime": "2025-10-08T02:00:00"
            }
        ],
        "active_count": 2,
        "high_severity_count": 1
    }
    ```
    """
    try:
        result = await service.get_predictive_alerts()

        if result.get("status") == "error":
            logger.warning(f"Predictive alerts returned error: {result.get('message')}")
            # Return empty alerts instead of raising exception (non-critical)
            return {
                "status": "success",
                "alerts": [],
                "active_count": 0,
                "high_severity_count": 0,
                "message": result.get("message")
            }

        return result

    except Exception as e:
        logger.error(f"Predictive alerts endpoint failed: {e}", exc_info=True)
        # Return empty alerts instead of failing (non-critical feature)
        return {
            "status": "error",
            "alerts": [],
            "active_count": 0,
            "high_severity_count": 0,
            "message": f"Alert generation failed: {str(e)}"
        }


@router.get("/savings-tracking")
async def get_savings_tracking(
    service: PredictiveInsightsService = Depends(get_insights_service)
) -> Dict[str, Any]:
    """
    💰 Track theoretical energy savings vs baseline.

    ⚠️ **IMPORTANT DISCLAIMER**:
    Returns THEORETICAL ESTIMATES based on machine specs and simulation.
    NOT real measurements from production (no smart meters installed).

    Compares:
    - **Optimized plan**: Hourly optimizer (Sprint 08) with Prophet predictions (theoretical)
    - **Baseline plan**: Fixed schedule 08-16h (theoretical)
    - **Real consumption**: NOT AVAILABLE (no measurement infrastructure)

    **Widget Integration**: Powers "Ahorro Energético" dashboard card.
    **Future Work**: Replace with real measurements when smart meters available.

    Returns:
        Dict with:
        - disclaimer: Warning about theoretical nature
        - data_source: Origin of estimates
        - daily_savings: Theoretical comparison
        - weekly_projection: Theoretical forecast
        - monthly_tracking: Theoretical progress
        - annual_projection: Theoretical ROI (baseline_theoretical_savings_eur, actual_measured_savings_eur: None)

    Example Response:
    ```json
    {
        "status": "success",
        "disclaimer": "⚠️ Theoretical estimates - NOT real measurements from production",
        "data_source": "Sprint 08 simulation using machine specs (no smart meters)",
        "daily_savings": {
            "optimized_cost_eur": 26.47,
            "baseline_cost_eur": 31.02,
            "savings_eur": 4.55,
            "savings_pct": 14.7
        },
        "annual_projection": {
            "baseline_theoretical_savings_eur": 1661,
            "actual_measured_savings_eur": null,
            "confidence": "low - theoretical only",
            "roi_description": "ROI teórico: 1.7k€/año (no medido)"
        }
    }
    ```
    """
    try:
        result = await service.get_savings_tracking()

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Savings tracking endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to track savings: {str(e)}")
