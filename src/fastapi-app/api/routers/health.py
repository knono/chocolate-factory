"""
Health Check Router
===================

Health and readiness endpoints for Kubernetes/monitoring.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime

from infrastructure.influxdb import get_influxdb_client
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
