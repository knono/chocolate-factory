"""
Health Monitoring APScheduler Jobs

Jobs periódicos para monitorear salud de nodos Tailscale.
Recopila métricas útiles: uptime, disponibilidad, latencia.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict

from services.tailscale_health_service import TailscaleHealthService
from infrastructure.influxdb.client import get_influxdb_client
from dependencies import get_telegram_alert_service
from core.logging_config import get_logger

logger = get_logger(__name__)

# Track offline duration for alerting (node_id -> first_offline_time)
_offline_tracking: Dict[str, datetime] = {}


async def collect_health_metrics():
    """
    Recolecta métricas de salud de todos los nodos y las almacena en InfluxDB.

    Ejecuta cada 5 minutos para tracking continuo de uptime.
    """
    try:
        logger.info("🏥 Starting health metrics collection...")

        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)

        # Get current health status
        nodes = await service.get_nodes_health()

        if not nodes:
            logger.warning("No nodes found during health check")
            return

        # Store metrics in InfluxDB
        await service.store_health_metrics(nodes)

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


async def log_health_status():
    """
    Logging periódico del estado de salud general.

    Ejecuta cada hora para tener registro de estado del sistema.
    """
    try:
        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)

        summary = await service.get_health_summary()

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


async def check_critical_nodes():
    """
    Verifica específicamente nodos críticos y genera alertas si están caídos.

    Ejecuta cada 5 minutos para detección rápida de caídas.
    Envía alerta Telegram si nodo crítico offline >5 minutos.
    """
    global _offline_tracking

    try:
        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)
        telegram_service = get_telegram_alert_service()

        nodes = await service.get_nodes_health()
        critical_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]

        offline_critical = [n for n in critical_nodes if not n.online]
        now = datetime.utcnow()

        if offline_critical:
            for node in offline_critical:
                severity = "🚨 CRITICAL" if node.node_type == "production" else "⚠️  WARNING"
                logger.error(
                    f"{severity}: Node '{node.hostname}' ({node.node_type}) is OFFLINE! "
                    f"Last seen: {node.last_seen}"
                )

                # Track offline duration
                node_id = node.hostname
                if node_id not in _offline_tracking:
                    # First time seeing node offline
                    _offline_tracking[node_id] = now
                    logger.info(f"Started tracking offline duration for {node_id}")
                else:
                    # Check if offline > 5 minutes
                    offline_since = _offline_tracking[node_id]
                    offline_duration = now - offline_since

                    if offline_duration > timedelta(minutes=5):
                        # Send Telegram alert
                        if telegram_service:
                            try:
                                from services.telegram_alert_service import AlertSeverity

                                await telegram_service.send_alert(
                                    message=f"Critical node '{node.hostname}' ({node.node_type}) "
                                            f"offline for {offline_duration.total_seconds()/60:.1f} minutes",
                                    severity=AlertSeverity.CRITICAL,
                                    topic=f"health_monitoring_{node_id}"
                                )

                                logger.info(f"📱 Telegram alert sent for offline node {node_id}")

                            except Exception as alert_error:
                                logger.error(f"Failed to send Telegram alert: {alert_error}")

        else:
            # All critical nodes online - clear tracking
            if _offline_tracking:
                logger.info(f"All critical nodes back online, clearing offline tracking")
                _offline_tracking.clear()

            logger.debug(f"✅ All critical nodes online ({len(critical_nodes)} nodes)")

    except Exception as e:
        logger.error(f"Failed to check critical nodes: {e}", exc_info=True)


async def collect_connection_metrics():
    """
    Recolecta métricas detalladas de conexión (latency, traffic, relay) para nodos críticos.

    Ejecuta cada 5 minutos para obtener histórico de:
    - Latencia (min/max/avg)
    - Packet loss
    - Connection type (direct vs relay)
    - Traffic stats (RxBytes/TxBytes)

    Envía alertas Telegram si:
    - Latency >100ms
    - Connection usando relay (no direct)
    """
    try:
        logger.info("🌐 Starting connection metrics collection...")

        influx_client = get_influxdb_client()
        service = TailscaleHealthService(influx_client=influx_client)
        telegram_service = get_telegram_alert_service()

        # Critical nodes to monitor
        critical_hostnames = ["git", "chocolate-factory-dev"]

        for hostname in critical_hostnames:
            try:
                logger.debug(f"Collecting metrics for {hostname}...")

                # Ping peer for latency
                ping_stats = await service.ping_peer(hostname, count=5)

                # Get connection stats
                conn_stats = await service.get_connection_stats(hostname)

                # Store metrics in InfluxDB
                await service.store_connection_metrics(hostname, ping_stats, conn_stats)

                # Check for alerts
                latency_avg = ping_stats.get("avg")
                connection_type = conn_stats.get("connection_type")

                # Alert: High latency (>100ms)
                if latency_avg and latency_avg > 100:
                    logger.warning(f"⚠️  High latency to {hostname}: {latency_avg}ms")

                    if telegram_service:
                        try:
                            from services.telegram_alert_service import AlertSeverity

                            await telegram_service.send_alert(
                                message=f"High latency to {hostname}: {latency_avg:.1f}ms (threshold 100ms)",
                                severity=AlertSeverity.WARNING,
                                topic=f"latency_{hostname}"
                            )

                        except Exception as alert_error:
                            logger.error(f"Failed to send latency alert: {alert_error}")

                # Alert: Using relay (not direct connection)
                if connection_type == "relay":
                    relay_node = conn_stats.get("relay_node", "unknown")
                    logger.warning(f"⚠️  {hostname} using DERP relay: {relay_node}")

                    if telegram_service:
                        try:
                            from services.telegram_alert_service import AlertSeverity

                            await telegram_service.send_alert(
                                message=f"{hostname} using DERP relay ({relay_node}) - direct connection unavailable",
                                severity=AlertSeverity.WARNING,
                                topic=f"relay_{hostname}"
                            )

                        except Exception as alert_error:
                            logger.error(f"Failed to send relay alert: {alert_error}")

                logger.debug(
                    f"✅ Metrics collected for {hostname}: "
                    f"latency={latency_avg}ms, type={connection_type}"
                )

            except Exception as node_error:
                logger.error(f"Failed to collect metrics for {hostname}: {node_error}")
                continue

        logger.info("✅ Connection metrics collection completed")

    except Exception as e:
        logger.error(f"Failed to collect connection metrics: {e}", exc_info=True)
