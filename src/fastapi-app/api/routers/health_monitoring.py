"""
Health Monitoring Router

Endpoints para monitoreo de salud de nodos Tailscale.
Enfoque en métricas útiles: uptime, disponibilidad, latencia.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime

from services.tailscale_health_service import TailscaleHealthService
from infrastructure.influxdb.client import get_influxdb_client
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health-monitoring", tags=["Health Monitoring"])


def get_health_service():
    """Dependency injection for TailscaleHealthService."""
    influx_client = get_influxdb_client()
    return TailscaleHealthService(influx_client=influx_client)


@router.get("/summary")
async def get_health_summary(
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get overall health summary of Tailscale network.

    Returns:
        - Total nodes count
        - Online/offline counts
        - Critical nodes health percentage
        - Individual node status
    """
    try:
        summary = service.get_health_summary()
        logger.info(
            f"Health summary: {summary['online_nodes']}/{summary['total_nodes']} nodes online, "
            f"Critical: {summary['critical_nodes']['health_percentage']}%"
        )
        return summary

    except Exception as e:
        logger.error(f"Failed to get health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/nodes")
async def get_nodes_status(
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get detailed status of all monitored nodes.

    Returns list of nodes with:
        - Hostname, IP, OS
        - Online status
        - Node type (production/development/git)
        - Last seen timestamp
    """
    try:
        nodes = service.get_nodes_health()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": len(nodes),
            "nodes": [
                {
                    "hostname": node.hostname,
                    "ip": node.ip,
                    "online": node.online,
                    "node_type": node.node_type,
                    "os": node.os,
                    "last_seen": node.last_seen,
                    "uptime_24h": node.uptime_24h,
                    "latency_ms": node.latency_ms
                }
                for node in nodes
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get nodes status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve nodes: {str(e)}")


@router.get("/uptime/{hostname}")
async def get_node_uptime(
    hostname: str,
    hours: int = 24,
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get uptime percentage for a specific node.

    Args:
        hostname: Node hostname
        hours: Time window (default 24h)

    Returns:
        Uptime percentage and timestamp
    """
    try:
        uptime = service.calculate_uptime(hostname, hours)

        if uptime is None:
            return {
                "hostname": hostname,
                "uptime_percentage": None,
                "hours": hours,
                "message": "No data available yet. Metrics will be available after first collection cycle."
            }

        return {
            "hostname": hostname,
            "uptime_percentage": uptime,
            "hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to calculate uptime for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Uptime calculation failed: {str(e)}")


@router.get("/critical")
async def get_critical_nodes_status(
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get status of critical nodes only (production, development, git).

    Returns:
        Filtered list with only critical infrastructure nodes
    """
    try:
        all_nodes = service.get_nodes_health()
        critical_nodes = [n for n in all_nodes if n.node_type in ["production", "development", "git"]]

        online_critical = sum(1 for n in critical_nodes if n.online)
        health_percentage = round((online_critical / len(critical_nodes) * 100), 2) if critical_nodes else 100

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_critical": len(critical_nodes),
            "online": online_critical,
            "offline": len(critical_nodes) - online_critical,
            "health_percentage": health_percentage,
            "status": "healthy" if health_percentage == 100 else "degraded" if health_percentage >= 66 else "critical",
            "nodes": [
                {
                    "hostname": node.hostname,
                    "ip": node.ip,
                    "online": node.online,
                    "node_type": node.node_type,
                    "last_seen": node.last_seen
                }
                for node in critical_nodes
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get critical nodes status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve critical nodes: {str(e)}")


@router.get("/alerts")
async def get_health_alerts(
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get active health alerts (offline nodes, degraded services).

    Returns:
        List of alerts with severity and recommended actions
    """
    try:
        nodes = service.get_nodes_health()
        alerts = []

        # Check for offline critical nodes
        for node in nodes:
            if node.node_type in ["production", "development", "git"] and not node.online:
                alerts.append({
                    "severity": "critical" if node.node_type == "production" else "warning",
                    "type": "node_offline",
                    "hostname": node.hostname,
                    "node_type": node.node_type,
                    "message": f"Critical node '{node.hostname}' ({node.node_type}) is offline",
                    "action": "Check Tailscale connection and restart services if needed",
                    "last_seen": node.last_seen
                })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_alerts": len(alerts),
            "active_alerts": alerts,
            "status": "ok" if len(alerts) == 0 else "alerts_present"
        }

    except Exception as e:
        logger.error(f"Failed to get health alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")
