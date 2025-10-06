"""
Dashboard Router
================

RESTful endpoints for dashboard data and visualizations.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from services.dashboard import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service() -> DashboardService:
    """
    Dependency injection for DashboardService.

    Returns:
        DashboardService: Dashboard service instance
    """
    try:
        return DashboardService()
    except Exception as e:
        logger.error(f"Failed to initialize DashboardService: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard service initialization failed: {str(e)}")


@router.get("/complete")
async def get_complete_dashboard(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    🎯 Complete dashboard with information, predictions, and recommendations.

    Returns comprehensive dashboard data including:
    - Current energy prices and weather
    - ML predictions (energy optimization, production recommendations)
    - Weekly forecast heatmap with Prophet predictions
    - Historical analytics (SIAR 88k + REE 42k records)
    - System alerts and recommendations

    Returns:
        Dict[str, Any]: Complete dashboard data
    """
    try:
        dashboard_data = await service.get_complete_dashboard_data()

        # Add weekly heatmap with Prophet predictions
        try:
            weekly_heatmap = await service._get_weekly_forecast_heatmap()
            dashboard_data["weekly_forecast"] = weekly_heatmap
        except Exception as e:
            logger.warning(f"Failed to add weekly heatmap: {e}")
            dashboard_data["weekly_forecast"] = {
                "status": "error",
                "message": f"Heatmap generation failed: {str(e)}"
            }

        # Add historical analytics
        try:
            from services.historical_analytics import HistoricalAnalyticsService
            analytics_service = HistoricalAnalyticsService()
            historical_analytics = await analytics_service.get_historical_analytics()
            dashboard_data["historical_analytics"] = historical_analytics.model_dump()
        except Exception as e:
            logger.warning(f"Failed to add historical analytics: {e}")
            dashboard_data["historical_analytics"] = {
                "status": "error",
                "message": f"Historical analytics failed: {str(e)}"
            }

        return dashboard_data

    except Exception as e:
        logger.error(f"Complete dashboard failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.get("/summary")
async def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    📊 Quick summary for dashboard.

    Returns essential metrics:
    - Current energy price, temperature, humidity
    - Production status
    - ML predictions (energy score, production class)
    - Active alerts count

    Returns:
        Dict[str, Any]: Dashboard summary
    """
    try:
        full_data = await service.get_complete_dashboard_data()

        # Extract essential information
        current_info = full_data.get("current_info", {})
        predictions = full_data.get("predictions", {})

        from datetime import datetime

        summary = {
            "🏢": "Chocolate Factory - Dashboard Summary",
            "current": {
                "energy_price": current_info.get("energy", {}).get("price_eur_kwh", 0) if current_info.get("energy") else 0,
                "temperature": current_info.get("weather", {}).get("temperature", 0) if current_info.get("weather") else 0,
                "humidity": current_info.get("weather", {}).get("humidity", 0) if current_info.get("weather") else 0,
                "production_status": current_info.get("production_status", "🔄 Cargando...")
            },
            "predictions": {
                "energy_score": predictions.get("energy_optimization", {}).get("score", 0),
                "production_class": predictions.get("production_recommendation", {}).get("class", "Unknown")
            },
            "alerts_count": len(full_data.get("alerts", [])),
            "status": full_data.get("system_status", {}).get("status", "🔄 Cargando..."),
            "timestamp": full_data.get("timestamp", datetime.now().isoformat())
        }

        return summary

    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard summary error: {str(e)}")


@router.get("/alerts")
async def get_dashboard_alerts(
    service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    🚨 Active system alerts.

    Returns:
        Dict[str, Any]: Active alerts with counts by severity
    """
    try:
        full_data = await service.get_complete_dashboard_data()

        alerts = full_data.get("alerts", [])

        return {
            "🏢": "Chocolate Factory - Alertas Activas",
            "alerts": alerts,
            "alert_counts": {
                "critical": len([a for a in alerts if a.get("level") == "critical"]),
                "warning": len([a for a in alerts if a.get("level") == "warning"]),
                "high": len([a for a in alerts if a.get("level") == "high"]),
                "info": len([a for a in alerts if a.get("level") == "info"])
            },
            "timestamp": full_data.get("timestamp")
        }

    except Exception as e:
        logger.error(f"Dashboard alerts failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard alerts error: {str(e)}")
