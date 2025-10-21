"""
Tailscale Health Monitoring Service

Sistema de monitoreo de salud para nodos Tailscale con métricas útiles.
Enfoque: uptime, disponibilidad, latencia y health checks distribuidos.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx
from influxdb_client import Point
from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class NodeHealth:
    """Representa el estado de salud de un nodo Tailscale."""
    hostname: str
    ip: str
    online: bool
    last_seen: Optional[str]
    os: str
    node_type: str  # production, development, git
    uptime_24h: Optional[float] = None  # % uptime últimas 24h
    latency_ms: Optional[float] = None  # latencia promedio


class TailscaleHealthService:
    """
    Servicio de health monitoring para nodos Tailscale.

    Features:
    - Status en tiempo real de nodos críticos
    - Health checks distribuidos (ping, service availability)
    - Uptime tracking con métricas en InfluxDB
    - Alertas proactivas cuando un nodo cae
    """

    # Nodos críticos a monitorear
    CRITICAL_NODES = {
        "git": {"hostname": "git", "services": ["forgejo", "registry"]},
        "dev": {"hostname": "chocolate-factory-dev", "services": ["fastapi"]},
        "prod": {"hostname": "chocolate-factory", "services": ["fastapi", "influxdb"]},
    }

    def __init__(self, influx_client=None, tailscale_proxy_url="http://chocolate-factory:8765"):
        """
        Initialize Tailscale Health Service.

        Args:
            influx_client: InfluxDB client for storing health metrics
            tailscale_proxy_url: Base URL for Tailscale HTTP proxy in sidecar
        """
        self.influx_client = influx_client
        self.tailscale_proxy_url = tailscale_proxy_url
        self._http_client = httpx.Client(timeout=10.0, follow_redirects=False)

    def _get_tailscale_status_http(self) -> str:
        """
        Get tailscale status via HTTP proxy.

        Returns:
            JSON string with status

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.tailscale_proxy_url}/status"
        logger.debug(f"Fetching Tailscale status from: {url}")

        try:
            response = self._http_client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP request to Tailscale proxy failed: {e}")
            raise

    def get_tailscale_status(self) -> Dict[str, Any]:
        """
        Get full Tailscale status as JSON via HTTP proxy.

        Returns:
            Dict with Self, Peer, CurrentTailnet, etc.
        """
        try:
            status_json = self._get_tailscale_status_http()
            status = json.loads(status_json)
            return status

        except httpx.HTTPError as e:
            logger.error(f"Tailscale status HTTP request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tailscale status JSON: {e}")
            raise

    def get_nodes_health(self) -> List[NodeHealth]:
        """
        Get health status for all critical nodes.

        Returns:
            List of NodeHealth objects with current status
        """
        try:
            status = self.get_tailscale_status()
            nodes_health = []

            # Process self node
            self_data = status.get("Self", {})
            if self_data:
                nodes_health.append(NodeHealth(
                    hostname=self_data.get("HostName", "unknown"),
                    ip=self_data.get("TailscaleIPs", ["unknown"])[0],
                    online=True,
                    last_seen=datetime.utcnow().isoformat(),
                    os=self_data.get("OS", "unknown"),
                    node_type=self._classify_node_type(self_data.get("HostName", ""))
                ))

            # Process peers
            peers = status.get("Peer", {})
            for peer_key, peer_data in peers.items():
                nodes_health.append(NodeHealth(
                    hostname=peer_data.get("HostName", "unknown"),
                    ip=peer_data.get("TailscaleIPs", ["unknown"])[0],
                    online=peer_data.get("Online", False),
                    last_seen=peer_data.get("LastSeen"),
                    os=peer_data.get("OS", "unknown"),
                    node_type=self._classify_node_type(peer_data.get("HostName", ""))
                ))

            logger.info(f"Health check: {len(nodes_health)} nodes monitored")
            return nodes_health

        except Exception as e:
            logger.error(f"Failed to get nodes health: {e}")
            return []

    def _classify_node_type(self, hostname: str) -> str:
        """
        Classify node type based on hostname.

        Args:
            hostname: Node hostname

        Returns:
            Node type (production, development, git, other)
        """
        hostname_lower = hostname.lower()

        if "git" in hostname_lower:
            return "git"
        elif "dev" in hostname_lower:
            return "development"
        elif "chocolate-factory" in hostname_lower and "dev" not in hostname_lower:
            return "production"
        else:
            return "other"

    async def check_node_reachability(self, ip: str, timeout: float = 2.0) -> Dict[str, Any]:
        """
        Check if a node is reachable via simple HTTP ping.

        Args:
            ip: Tailscale IP address
            timeout: Timeout in seconds

        Returns:
            Dict with reachable status and latency
        """
        try:
            start_time = datetime.utcnow()

            # Try to connect to common health endpoint
            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    response = await client.get(f"http://{ip}:8000/health")
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                    return {
                        "reachable": response.status_code == 200,
                        "latency_ms": round(latency_ms, 2),
                        "status_code": response.status_code
                    }
                except httpx.HTTPError:
                    # Try alternative port
                    response = await client.get(f"http://{ip}:80/health")
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                    return {
                        "reachable": response.status_code == 200,
                        "latency_ms": round(latency_ms, 2),
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.debug(f"Node {ip} unreachable: {e}")
            return {
                "reachable": False,
                "latency_ms": None,
                "error": str(e)
            }

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of Tailscale network health.

        Returns:
            Dict with overall health metrics
        """
        nodes = self.get_nodes_health()

        total_nodes = len(nodes)
        online_nodes = sum(1 for n in nodes if n.online)
        critical_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]
        critical_online = sum(1 for n in critical_nodes if n.online)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": total_nodes - online_nodes,
            "critical_nodes": {
                "total": len(critical_nodes),
                "online": critical_online,
                "offline": len(critical_nodes) - critical_online,
                "health_percentage": round((critical_online / len(critical_nodes) * 100), 2) if critical_nodes else 100
            },
            "nodes": [
                {
                    "hostname": n.hostname,
                    "ip": n.ip,
                    "online": n.online,
                    "node_type": n.node_type,
                    "last_seen": n.last_seen
                }
                for n in nodes
            ]
        }

    async def store_health_metrics(self, nodes: List[NodeHealth]) -> None:
        """
        Store health metrics in InfluxDB for historical tracking.

        Args:
            nodes: List of NodeHealth objects
        """
        if not self.influx_client:
            logger.warning("InfluxDB client not configured, skipping metrics storage")
            return

        try:
            write_api = self.influx_client.write_api()

            for node in nodes:
                point = Point("tailscale_health") \
                    .tag("hostname", node.hostname) \
                    .tag("node_type", node.node_type) \
                    .tag("os", node.os) \
                    .field("online", 1 if node.online else 0) \
                    .field("ip", node.ip)

                if node.latency_ms is not None:
                    point = point.field("latency_ms", node.latency_ms)

                write_api.write(bucket="analytics", record=point)

            logger.debug(f"Stored health metrics for {len(nodes)} nodes in InfluxDB")

        except Exception as e:
            logger.error(f"Failed to store health metrics: {e}")

    def calculate_uptime(self, hostname: str, hours: int = 24) -> Optional[float]:
        """
        Calculate uptime percentage for a node from InfluxDB data.

        Args:
            hostname: Node hostname
            hours: Time window in hours

        Returns:
            Uptime percentage (0-100) or None if no data
        """
        if not self.influx_client:
            return None

        try:
            query_api = self.influx_client.query_api()

            query = f'''
                from(bucket: "analytics")
                    |> range(start: -{hours}h)
                    |> filter(fn: (r) => r["_measurement"] == "tailscale_health")
                    |> filter(fn: (r) => r["hostname"] == "{hostname}")
                    |> filter(fn: (r) => r["_field"] == "online")
                    |> mean()
            '''

            result = query_api.query(query=query)

            if result and len(result) > 0 and len(result[0].records) > 0:
                uptime_fraction = result[0].records[0].get_value()
                return round(uptime_fraction * 100, 2)

            return None

        except Exception as e:
            logger.error(f"Failed to calculate uptime for {hostname}: {e}")
            return None