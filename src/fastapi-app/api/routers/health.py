"""
Health Check Router
===================

Health and readiness endpoints for Kubernetes/monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime

from infrastructure.influxdb import get_influxdb_client
from dependencies import get_telegram_alert_service
from core.config import settings

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check (includes InfluxDB connectivity).

    Returns:
        Readiness status
    """
    influx = get_influxdb_client()

    try:
        health = influx.health_check()
        influx_status = health.get("status", "unknown")
    except Exception as e:
        influx_status = f"error: {str(e)}"

    is_ready = influx_status == "pass"

    return {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "influxdb": influx_status
        }
    }


@router.get("/version")
async def version_info() -> Dict[str, str]:
    """
    API version information.

    Returns:
        Version details
    """
    return {
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": "3.11+"
    }


@router.post("/test-telegram")
async def test_telegram_alert() -> Dict[str, Any]:
    """
    Test endpoint to verify Telegram alerts are working.

    Sends a test alert to the configured Telegram chat.

    **Sprint 18 - Testing only**
    """
    telegram_service = get_telegram_alert_service()

    if not telegram_service:
        raise HTTPException(
            status_code=503,
            detail="Telegram alerts are disabled. Set TELEGRAM_ALERTS_ENABLED=true in .env"
        )

    try:
        from services.telegram_alert_service import AlertSeverity

        success = await telegram_service.send_alert(
            message="🧪 TEST ALERT\n\n"
                    "This is a test message from Chocolate Factory.\n"
                    "If you received this, Telegram alerts are working correctly!\n\n"
                    f"Timestamp: {datetime.utcnow().isoformat()}",
            severity=AlertSeverity.INFO,
            topic="test_alert"
        )

        if success:
            return {
                "status": "success",
                "message": "Test alert sent successfully",
                "telegram_enabled": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send Telegram alert. Check logs for details."
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test alert: {str(e)}"
        )
