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


@router.get("/logs/search")
async def search_logs(
    level: str = None,
    hours: int = 24,
    limit: int = 100,
    module: str = None
) -> Dict[str, Any]:
    """
    Search application logs (JSON structured logs only).

    **Sprint 20 Fase 2 - JSON Log Search**

    Args:
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        hours: Time window in hours (default 24)
        limit: Maximum number of log entries to return (default 100)
        module: Filter by module name (e.g., "services.ree_service")

    Returns:
        Filtered log entries with metadata

    Note: Only works with JSON-formatted logs (LOG_FORMAT_JSON=true).
          For development colored logs, this endpoint will return empty.
    """
    import json
    from pathlib import Path
    from datetime import timedelta

    log_file = Path("/app/logs/fastapi.log")

    if not log_file.exists():
        return {
            "status": "no_logs",
            "message": "Log file not found. File logging may be disabled.",
            "logs": [],
            "count": 0
        }

    # Calculate time threshold
    now = datetime.utcnow()
    threshold = now - timedelta(hours=hours)

    logs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Skip empty lines
                if not line.strip():
                    continue

                try:
                    # Parse JSON log entry
                    log_entry = json.loads(line)

                    # Parse timestamp
                    timestamp_str = log_entry.get("timestamp", "").rstrip("Z")
                    log_time = datetime.fromisoformat(timestamp_str)

                    # Filter by time window
                    if log_time < threshold:
                        continue

                    # Filter by level
                    if level and log_entry.get("level") != level.upper():
                        continue

                    # Filter by module
                    if module and module not in log_entry.get("logger", ""):
                        continue

                    logs.append(log_entry)

                    # Stop if limit reached
                    if len(logs) >= limit:
                        break

                except (json.JSONDecodeError, ValueError):
                    # Skip non-JSON lines (e.g., colored logs from development)
                    continue

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading log file: {str(e)}"
        )

    return {
        "status": "success",
        "filters": {
            "level": level or "all",
            "hours": hours,
            "module": module or "all",
            "limit": limit
        },
        "count": len(logs),
        "logs": logs
    }
