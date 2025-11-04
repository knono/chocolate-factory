"""
Health Monitoring Router

Endpoints para monitoreo de salud de nodos Tailscale.
Enfoque en métricas útiles: uptime, disponibilidad, latencia.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from datetime import datetime

from services.tailscale_health_service import TailscaleHealthService
from services.health_logs_service import HealthLogsService
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
    project_only: bool = True,
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get detailed status of all monitored nodes.

    Args:
        project_only: If True, show only project nodes (production/development/git).
                     If False, show all Tailnet nodes. Default: True.

    Returns list of nodes with:
        - Hostname, IP, OS
        - Online status
        - Node type (production/development/git)
        - Last seen timestamp
    """
    try:
        all_nodes = service.get_nodes_health()

        # Filter project nodes if requested (default)
        if project_only:
            nodes = [n for n in all_nodes if n.node_type in ["production", "development", "git"]]
            logger.info(f"Filtered to project nodes: {len(nodes)}/{len(all_nodes)}")
        else:
            nodes = all_nodes

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": len(nodes),
            "project_only": project_only,
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


@router.get("/logs")
async def get_health_logs(
    page: int = 1,
    page_size: int = 50,
    hours: int = 48,
    severity: str = None,
    event_type: str = None,
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get paginated health monitoring event logs.

    Generates logs based on current node states and historical patterns.

    Args:
        page: Page number (1-indexed, default 1)
        page_size: Entries per page (default 50)
        hours: Hours to look back for historical events (default 48 = 2 days)
        severity: Filter by severity (ok, warning, critical)
        event_type: Filter by event type (node_online, node_offline, health_check, alert)

    Returns:
        Paginated logs with metadata and summary
    """
    try:
        logs_service = HealthLogsService(health_service=service)
        result = logs_service.get_logs_paginated(
            page=page,
            page_size=page_size,
            hours=hours,
            severity=severity,
            event_type=event_type
        )

        logger.info(
            f"Health logs retrieved: page {page}/{result['pagination']['total_pages']}, "
            f"{len(result['logs'])} entries, "
            f"severity={severity or 'all'}, event_type={event_type or 'all'}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to get health logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")


@router.get("/connection-stats/{hostname}")
async def get_connection_stats(
    hostname: str,
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get detailed connection statistics for a specific node.

    Returns:
        - Connection type (direct vs relay)
        - Relay node if applicable
        - Current latency stats (min/max/avg)
        - Traffic stats (RxBytes/TxBytes)
        - Endpoint information

    Args:
        hostname: Target hostname (e.g., "git", "chocolate-factory-dev")
    """
    try:
        logger.info(f"Fetching connection stats for {hostname}...")

        # Get connection stats
        conn_stats = service.get_connection_stats(hostname)

        if "error" in conn_stats:
            raise HTTPException(status_code=404, detail=conn_stats["error"])

        # Get current ping stats
        ping_stats = service.ping_peer(hostname, count=5)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": hostname,
            "connection": conn_stats,
            "latency": ping_stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connection stats for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve connection stats: {str(e)}")


@router.get("/latency-history/{hostname}")
async def get_latency_history(
    hostname: str,
    hours: int = 24,
    service: TailscaleHealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get latency history from InfluxDB for a specific node.

    Returns time series data for:
        - Latency avg/min/max
        - Packet loss
        - Connection type changes
        - Traffic stats

    Args:
        hostname: Target hostname
        hours: Time window in hours (default 24)
    """
    try:
        logger.info(f"Fetching latency history for {hostname} ({hours}h)...")

        influx_client = get_influxdb_client()
        if not influx_client:
            raise HTTPException(status_code=503, detail="InfluxDB not available")

        query_api = influx_client.query_api()

        # Query latency data
        query = f'''
            from(bucket: "analytics")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r["_measurement"] == "tailscale_connections")
                |> filter(fn: (r) => r["hostname"] == "{hostname}")
                |> filter(fn: (r) => r["_field"] == "latency_avg" or r["_field"] == "latency_min" or r["_field"] == "latency_max" or r["_field"] == "packet_loss")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''

        result = query_api.query(query=query)

        # Parse result
        history = []
        for table in result:
            for record in table.records:
                history.append({
                    "timestamp": record.get_time().isoformat(),
                    "latency_avg": record.values.get("latency_avg"),
                    "latency_min": record.values.get("latency_min"),
                    "latency_max": record.values.get("latency_max"),
                    "packet_loss": record.values.get("packet_loss"),
                    "connection_type": record.values.get("connection_type", "unknown")
                })

        # Calculate stats
        if history:
            latencies = [h["latency_avg"] for h in history if h["latency_avg"]]
            stats = {
                "mean": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "min": round(min(latencies), 2) if latencies else None,
                "max": round(max(latencies), 2) if latencies else None,
                "points": len(history)
            }
        else:
            stats = {
                "mean": None,
                "min": None,
                "max": None,
                "points": 0
            }

        return {
            "hostname": hostname,
            "time_window_hours": hours,
            "data_points": len(history),
            "stats": stats,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latency history for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")
