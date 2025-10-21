"""
Tailscale Analytics Service

Observabilidad Tailscale usando HTTP proxy para monitoring autónomo 24/7.
Clasifica nodos (propios/compartidos/externos) y rastrea uso de cuota.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx
from influxdb_client import Point
from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TailscalePeer:
    """Representa un peer en la Tailnet con clasificación."""
    hostname: str
    ip: str
    user_id: int
    user_email: str
    os: str
    online: bool
    last_seen: Optional[str]
    node_type: str  # own_node, shared_node, external_user
    sharee_node: bool
    exit_node: bool


class TailscaleAnalyticsService:
    """
    Servicio de analytics Tailscale usando subprocess CLI.

    Features:
    - Clasificación automática de nodos (own/shared/external)
    - Tracking uso de cuota (3 usuarios free tier)
    - Parsing nginx logs con correlación Tailscale
    - Almacenamiento histórico en InfluxDB
    """

    def __init__(self, influx_client=None, tailscale_proxy_url="http://chocolate-factory:8765"):
        """
        Initialize Tailscale Analytics Service.

        Args:
            influx_client: InfluxDB client for storing analytics
            tailscale_proxy_url: Base URL for Tailscale HTTP proxy in sidecar (port 8765 socat server)
        """
        self.influx_client = influx_client
        self.tailscale_proxy_url = tailscale_proxy_url
        self._self_user_id: Optional[int] = None
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

    def _get_tailscale_whois_http(self, ip: str) -> str:
        """
        Get tailscale whois via HTTP proxy.

        Args:
            ip: Tailscale IP address

        Returns:
            Whois output as text

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.tailscale_proxy_url}/whois/{ip}"
        logger.debug(f"Fetching Tailscale whois for {ip} from: {url}")

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

            # Cache self user ID for comparisons
            if "Self" in status:
                self._self_user_id = status["Self"].get("UserID")

            return status

        except httpx.HTTPError as e:
            logger.error(f"Tailscale status HTTP request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tailscale status JSON: {e}")
            raise

    def get_self_user_id(self) -> int:
        """Get current user ID (cached)."""
        if self._self_user_id is None:
            status = self.get_tailscale_status()
            self._self_user_id = status["Self"]["UserID"]
        return self._self_user_id

    def classify_peer(self, peer: Dict) -> str:
        """
        Classify peer as own_node, shared_node, or external_user.

        Args:
            peer: Peer dict from tailscale status

        Returns:
            Classification: 'own_node', 'shared_node', 'external_user'
        """
        self_user_id = self.get_self_user_id()
        peer_user_id = peer.get("UserID")
        is_sharee = peer.get("ShareeNode", False)

        if peer_user_id == self_user_id:
            return "own_node"  # Your own device
        elif is_sharee:
            return "shared_node"  # Shared with you (doesn't count toward quota)
        else:
            return "external_user"  # Different user (COUNTS toward quota)

    async def get_active_devices(self) -> List[TailscalePeer]:
        """
        List active devices in Tailnet with classification.

        Returns:
            List of TailscalePeer objects
        """
        status = self.get_tailscale_status()
        peers_data = status.get("Peer", {})

        devices = []

        for peer_id, peer in peers_data.items():
            if not peer.get("Online", False):
                continue  # Skip offline peers

            # Classify peer
            node_type = self.classify_peer(peer)

            # Get first Tailscale IP
            tailscale_ips = peer.get("TailscaleIPs", [])
            ip = tailscale_ips[0] if tailscale_ips else "unknown"

            # Get user info via whois
            user_info = await self.whois_ip(ip)

            peer_obj = TailscalePeer(
                hostname=peer.get("HostName", "unknown"),
                ip=ip,
                user_id=peer.get("UserID", 0),
                user_email=user_info.get("user", "unknown"),
                os=peer.get("OS", "unknown"),
                online=peer.get("Online", False),
                last_seen=peer.get("LastSeen"),
                node_type=node_type,
                sharee_node=peer.get("ShareeNode", False),
                exit_node=peer.get("ExitNode", False)
            )

            devices.append(peer_obj)

        logger.info(f"Found {len(devices)} active Tailscale devices")
        return devices

    async def whois_ip(self, ip: str) -> Dict[str, Any]:
        """
        Identify user/device by Tailscale IP via HTTP proxy.

        Args:
            ip: Tailscale IP address (100.x.x.x)

        Returns:
            Dict with hostname, user, user_id
        """
        try:
            output = self._get_tailscale_whois_http(ip)

            # Parse whois output
            # Format:
            # Machine:
            #   Name:           hostname.tailnet.ts.net
            #   ID:             nodeXXXX
            # User:
            #   Name:     user@example.com
            #   ID:       1234567890

            hostname = "unknown"
            user = "unknown"
            user_id = None

            # Extract hostname
            hostname_match = re.search(r'Name:\s+(.+?)\.', output)
            if hostname_match:
                hostname = hostname_match.group(1)

            # Extract user email
            user_match = re.search(r'User:\s+Name:\s+(.+)', output)
            if user_match:
                user = user_match.group(1).strip()

            # Extract user ID
            user_id_match = re.search(r'User:\s+.*?ID:\s+(\d+)', output, re.DOTALL)
            if user_id_match:
                user_id = int(user_id_match.group(1))

            return {
                "hostname": hostname,
                "user": user,
                "user_id": user_id,
                "ip": ip
            }

        except httpx.HTTPError as e:
            logger.warning(f"whois HTTP request failed for {ip}: {e}")
            return {
                "hostname": "unknown",
                "user": "unknown",
                "user_id": None,
                "ip": ip
            }

    async def get_quota_usage(self) -> Dict[str, Any]:
        """
        Calculate Tailscale quota usage (3 users free tier).

        Returns:
            Dict with quota_limit, users_count, quota_available, alert, external_users
        """
        status = self.get_tailscale_status()
        peers = status.get("Peer", {})

        # Track unique external user IDs
        external_user_ids = set()
        external_users_details = []

        for peer in peers.values():
            classification = self.classify_peer(peer)

            if classification == "external_user":
                user_id = peer.get("UserID")
                if user_id:
                    external_user_ids.add(user_id)

                    # Get user details
                    ip = peer.get("TailscaleIPs", ["unknown"])[0]
                    user_info = await self.whois_ip(ip)

                    external_users_details.append({
                        "user_id": user_id,
                        "email": user_info.get("user", "unknown"),
                        "hostname": peer.get("HostName", "unknown"),
                        "online": peer.get("Online", False)
                    })

        users_count = len(external_user_ids)
        quota_limit = 3  # Tailscale free tier

        return {
            "quota_limit": quota_limit,
            "users_count": users_count,
            "quota_available": max(0, quota_limit - users_count),
            "quota_percentage": (users_count / quota_limit) * 100,
            "alert": users_count >= quota_limit,
            "warning": users_count >= (quota_limit - 1),  # Alert at 2/3 users
            "external_users": external_users_details
        }

    async def parse_nginx_logs(
        self,
        hours: int = 24,
        log_path: str = "./logs/sidecar/nginx/access.log"
    ) -> List[Dict]:
        """
        Parse nginx access logs from Tailscale sidecar.

        Args:
            hours: Hours back to parse
            log_path: Path to nginx access.log

        Returns:
            List of enriched log entries with user/device info
        """
        log_file = Path(log_path)

        if not log_file.exists():
            logger.warning(f"Nginx log file not found: {log_path}")
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        access_logs = []

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    parsed = self._parse_nginx_line(line)

                    if not parsed:
                        continue

                    if parsed["timestamp"] < cutoff:
                        continue

                    # Enrich with Tailscale whois data
                    user_info = await self.whois_ip(parsed["ip"])
                    parsed["user"] = user_info.get("user")
                    parsed["device"] = user_info.get("hostname")
                    parsed["user_id"] = user_info.get("user_id")

                    access_logs.append(parsed)

            logger.info(f"Parsed {len(access_logs)} nginx log entries (last {hours}h)")
            return access_logs

        except Exception as e:
            logger.error(f"Failed to parse nginx logs: {e}")
            return []

    def _parse_nginx_line(self, line: str) -> Optional[Dict]:
        """
        Parse single nginx log line.

        Expected format:
        100.x.x.x - - [21/Oct/2025:14:32:15 +0000] "GET /dashboard HTTP/1.1" 200 1234 "-" "Mozilla/5.0..."

        Returns:
            Dict with ip, timestamp, method, endpoint, status or None
        """
        # Regex pattern for nginx combined log format
        pattern = r'(\d+\.\d+\.\d+\.\d+) .* \[(.+?)\] "(\w+) (.+?) HTTP.*?" (\d+)'
        match = re.match(pattern, line)

        if not match:
            return None

        ip, timestamp_str, method, endpoint, status = match.groups()

        try:
            # Parse timestamp: 21/Oct/2025:14:32:15 +0000
            timestamp = datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S %z")
            # Convert to naive datetime (remove timezone for comparison)
            timestamp = timestamp.replace(tzinfo=None)

            return {
                "ip": ip,
                "timestamp": timestamp,
                "method": method,
                "endpoint": endpoint,
                "status": int(status)
            }
        except ValueError as e:
            logger.debug(f"Failed to parse timestamp: {timestamp_str}, error: {e}")
            return None

    async def store_analytics(self, log: Dict):
        """
        Store analytics entry in InfluxDB.

        Args:
            log: Log dict with user, device, endpoint, status, timestamp
        """
        if not self.influx_client:
            logger.warning("InfluxDB client not configured, skipping storage")
            return

        try:
            point = (
                Point("tailscale_access")
                .tag("user", log.get("user", "unknown"))
                .tag("device", log.get("device", "unknown"))
                .tag("endpoint", log.get("endpoint", "unknown"))
                .tag("method", log.get("method", "GET"))
                .field("status", log.get("status", 0))
                .field("user_id", log.get("user_id", 0))
                .time(log.get("timestamp", datetime.now()))
            )

            # Write to InfluxDB (assumes async write_api)
            await self.influx_client.write(point)
            logger.debug(f"Stored analytics: {log['user']} → {log['endpoint']}")

        except Exception as e:
            logger.error(f"Failed to store analytics in InfluxDB: {e}")

    async def get_devices_summary(self) -> Dict[str, Any]:
        """
        Get summary of devices grouped by type.

        Returns:
            Dict with counts and lists for own_nodes, shared_nodes, external_users
        """
        devices = await self.get_active_devices()

        own_nodes = [d for d in devices if d.node_type == "own_node"]
        shared_nodes = [d for d in devices if d.node_type == "shared_node"]
        external_users = [d for d in devices if d.node_type == "external_user"]

        return {
            "total_devices": len(devices),
            "own_nodes": {
                "count": len(own_nodes),
                "devices": [
                    {
                        "hostname": d.hostname,
                        "ip": d.ip,
                        "os": d.os,
                        "online": d.online
                    }
                    for d in own_nodes
                ]
            },
            "shared_nodes": {
                "count": len(shared_nodes),
                "devices": [
                    {
                        "hostname": d.hostname,
                        "ip": d.ip,
                        "user": d.user_email,
                        "os": d.os,
                        "online": d.online
                    }
                    for d in shared_nodes
                ]
            },
            "external_users": {
                "count": len(external_users),
                "devices": [
                    {
                        "hostname": d.hostname,
                        "ip": d.ip,
                        "user": d.user_email,
                        "os": d.os,
                        "online": d.online
                    }
                    for d in external_users
                ]
            }
        }
