"""
Analytics Router

Endpoints para observabilidad Tailscale con clasificación de nodos
y tracking de cuota de usuarios.
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any
from pathlib import Path

from services.tailscale_analytics_service import TailscaleAnalyticsService
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/devices")
async def get_active_devices():
    """
    Lista dispositivos activos en Tailnet con clasificación.

    Clasifica cada dispositivo en:
    - own_node: Tu propio dispositivo
    - shared_node: Compartido contigo (no cuenta hacia cuota)
    - external_user: Usuario diferente (CUENTA hacia cuota 3 usuarios)

    Returns:
        {
            "total_devices": 5,
            "own_nodes": {
                "count": 3,
                "devices": [...]
            },
            "shared_nodes": {
                "count": 1,
                "devices": [...]
            },
            "external_users": {
                "count": 1,
                "devices": [...]
            }
        }
    """
    try:
        service = TailscaleAnalyticsService()
        summary = await service.get_devices_summary()

        logger.info(
            f"Devices summary: {summary['total_devices']} total "
            f"({summary['own_nodes']['count']} own, "
            f"{summary['shared_nodes']['count']} shared, "
            f"{summary['external_users']['count']} external)"
        )

        return summary

    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve devices: {str(e)}")


@router.get("/quota-status")
async def get_quota_status():
    """
    Estado de cuota de usuarios Tailscale (free tier: 3 usuarios).

    Cuenta solo usuarios externos (external_user), NO cuenta:
    - Tus propios nodos (own_node)
    - Nodos compartidos contigo (shared_node)

    Returns:
        {
            "quota_limit": 3,
            "users_count": 1,
            "quota_available": 2,
            "quota_percentage": 33.33,
            "alert": false,
            "warning": false,
            "external_users": [
                {
                    "user_id": 123456,
                    "email": "user@example.com",
                    "hostname": "laptop",
                    "online": true
                }
            ]
        }
    """
    try:
        service = TailscaleAnalyticsService()
        quota = await service.get_quota_usage()

        # Log warning if quota is being reached
        if quota["warning"]:
            logger.warning(
                f"Tailscale quota warning: {quota['users_count']}/{quota['quota_limit']} users"
            )

        if quota["alert"]:
            logger.error(
                f"Tailscale quota EXCEEDED: {quota['users_count']}/{quota['quota_limit']} users"
            )

        return quota

    except Exception as e:
        logger.error(f"Failed to get quota status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve quota: {str(e)}")


@router.get("/access-logs")
async def get_access_logs(hours: int = Query(default=24, ge=1, le=168)):
    """
    Access logs de nginx con identificación de usuario Tailscale.

    Parsea logs del sidecar nginx y correlaciona IPs Tailscale con usuarios
    usando `tailscale whois`.

    Args:
        hours: Horas hacia atrás (1-168, default 24)

    Returns:
        {
            "logs": [
                {
                    "ip": "100.x.x.x",
                    "timestamp": "2025-10-21T14:32:15",
                    "method": "GET",
                    "endpoint": "/dashboard",
                    "status": 200,
                    "user": "user@example.com",
                    "device": "laptop",
                    "user_id": 123456
                }
            ],
            "summary": {
                "total_requests": 150,
                "unique_users": 3,
                "unique_devices": 5,
                "period_hours": 24
            }
        }
    """
    try:
        service = TailscaleAnalyticsService()
        logs = await service.parse_nginx_logs(hours=hours)

        # Calculate summary
        unique_users = len(set(log["user"] for log in logs if log.get("user")))
        unique_devices = len(set(log["device"] for log in logs if log.get("device")))

        summary = {
            "total_requests": len(logs),
            "unique_users": unique_users,
            "unique_devices": unique_devices,
            "period_hours": hours
        }

        logger.info(
            f"Access logs: {summary['total_requests']} requests "
            f"from {summary['unique_users']} users "
            f"({summary['unique_devices']} devices) "
            f"in last {hours}h"
        )

        return {
            "logs": logs,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Failed to get access logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse logs: {str(e)}")


@router.get("/dashboard-usage")
async def get_dashboard_usage(days: int = Query(default=7, ge=1, le=30)):
    """
    Métricas de uso del dashboard desde InfluxDB.

    Requiere que el APScheduler job `collect_analytics` esté activo
    y haya almacenado datos en InfluxDB.

    Args:
        days: Días hacia atrás (1-30, default 7)

    Returns:
        {
            "most_viewed_endpoints": [
                {"endpoint": "/dashboard", "count": 450},
                {"endpoint": "/analytics/devices", "count": 120}
            ],
            "peak_hours": [
                {"hour": 10, "count": 85},
                {"hour": 15, "count": 72}
            ],
            "active_users": [
                {"user": "user@example.com", "accesses": 234}
            ],
            "period_days": 7
        }
    """
    try:
        # TODO: Implementar query InfluxDB cuando APScheduler job esté activo
        # Por ahora retornamos placeholder

        logger.info(f"Dashboard usage requested for last {days} days")

        return {
            "most_viewed_endpoints": [],
            "peak_hours": [],
            "active_users": [],
            "period_days": days,
            "note": "Analytics collection via APScheduler not yet active. Run `collect_analytics` job first."
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve usage data: {str(e)}")
