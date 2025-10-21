"""
Health Monitoring APScheduler Jobs

Jobs periódicos para monitorear salud de nodos Tailscale.
Recopila métricas útiles: uptime, disponibilidad, latencia.
"""

import asyncio
from datetime import datetime

from services.tailscale_health_service import TailscaleHealthService
from infrastructure.influxdb.client import get_influxdb_client
from core.logging_config import get_logger

logger = get_logger(__name__)


def collect_health_metrics():
    """
    Recolecta métricas de salud de todos los nodos y las almacena en InfluxDB.

    Ejecuta cada 5 minutos para tracking continuo de uptime.
    """
    try:
        logger.info("🏥 Starting health metrics collection...")

        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)

        # Get current health status
        nodes = service.get_nodes_health()

        if not nodes:
            logger.warning("No nodes found during health check")
            return

        # Store metrics in InfluxDB
        asyncio.run(service.store_health_metrics(nodes))

        # Log summary
        online_count = sum(1 for n in nodes if n.online)
        critical_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]
        critical_online = sum(1 for n in critical_nodes if n.online)

        logger.info(
            f"✅ Health metrics collected: {online_count}/{len(nodes)} nodes online, "
            f"Critical: {critical_online}/{len(critical_nodes)}"
        )

        # Log any offline critical nodes
        for node in critical_nodes:
            if not node.online:
                logger.warning(
                    f"🔴 ALERT: Critical node '{node.hostname}' ({node.node_type}) is OFFLINE. "
                    f"Last seen: {node.last_seen}"
                )

    except Exception as e:
        logger.error(f"Failed to collect health metrics: {e}", exc_info=True)


def log_health_status():
    """
    Logging periódico del estado de salud general.

    Ejecuta cada hora para tener registro de estado del sistema.
    """
    try:
        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)

        summary = service.get_health_summary()

        logger.info(
            f"📊 Health Status Report: "
            f"{summary['online_nodes']}/{summary['total_nodes']} nodes online | "
            f"Critical nodes: {summary['critical_nodes']['health_percentage']}% healthy"
        )

        # Log individual critical nodes status
        critical_nodes = [
            n for n in summary['nodes']
            if n.get('node_type') in ["production", "development", "git"]
        ]

        for node in critical_nodes:
            status_emoji = "🟢" if node['online'] else "🔴"
            logger.info(
                f"{status_emoji} {node['hostname']} ({node['node_type']}): "
                f"{'Online' if node['online'] else 'OFFLINE'}"
            )

    except Exception as e:
        logger.error(f"Failed to log health status: {e}", exc_info=True)


def check_critical_nodes():
    """
    Verifica específicamente nodos críticos y genera alertas si están caídos.

    Ejecuta cada 2 minutos para detección rápida de caídas.
    """
    try:
        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)

        nodes = service.get_nodes_health()
        critical_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]

        offline_critical = [n for n in critical_nodes if not n.online]

        if offline_critical:
            for node in offline_critical:
                severity = "🚨 CRITICAL" if node.node_type == "production" else "⚠️  WARNING"
                logger.error(
                    f"{severity}: Node '{node.hostname}' ({node.node_type}) is OFFLINE! "
                    f"Last seen: {node.last_seen}"
                )
        else:
            logger.debug(f"✅ All critical nodes online ({len(critical_nodes)} nodes)")

    except Exception as e:
        logger.error(f"Failed to check critical nodes: {e}", exc_info=True)
