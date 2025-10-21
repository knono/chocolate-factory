"""
Analytics Jobs

APScheduler background jobs para recolección automática de analytics Tailscale.
"""

from datetime import datetime
from services.tailscale_analytics_service import TailscaleAnalyticsService
from core.logging_config import get_logger

logger = get_logger(__name__)


async def collect_analytics():
    """
    Job APScheduler: Recolectar analytics Tailscale cada 15 minutos.

    Process:
    1. Parse nginx logs última hora
    2. Enrich con tailscale whois (IP → usuario/dispositivo)
    3. Store en InfluxDB para históricos
    4. Log quota warnings si se acerca límite

    Frequency: Every 15 minutes (configurable en scheduler_config.py)
    """
    try:
        logger.info("Starting Tailscale analytics collection...")

        service = TailscaleAnalyticsService()

        # Parse nginx logs última hora (evitar duplicados)
        logs = await service.parse_nginx_logs(hours=1)

        if not logs:
            logger.info("No new nginx logs to process")
            return

        # Store cada log en InfluxDB
        stored_count = 0
        for log in logs:
            try:
                await service.store_analytics(log)
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store log entry: {e}")
                continue

        logger.info(
            f"Analytics collection completed: {stored_count}/{len(logs)} entries stored"
        )

        # Check quota status and log warnings
        quota = await service.get_quota_usage()

        if quota["alert"]:
            logger.error(
                f"⚠️  TAILSCALE QUOTA EXCEEDED: "
                f"{quota['users_count']}/{quota['quota_limit']} users "
                f"(external users: {len(quota['external_users'])})"
            )
        elif quota["warning"]:
            logger.warning(
                f"⚠️  Tailscale quota warning: "
                f"{quota['users_count']}/{quota['quota_limit']} users "
                f"({quota['quota_available']} remaining)"
            )

    except Exception as e:
        logger.error(f"Analytics collection job failed: {e}", exc_info=True)


async def log_tailscale_status():
    """
    Job APScheduler: Log resumen estado Tailscale cada hora.

    Útil para debugging y monitoreo general del estado de la Tailnet.

    Frequency: Every hour (configurable en scheduler_config.py)
    """
    try:
        service = TailscaleAnalyticsService()

        # Get devices summary
        summary = await service.get_devices_summary()

        logger.info(
            f"📊 Tailscale Status: "
            f"{summary['total_devices']} devices "
            f"({summary['own_nodes']['count']} own, "
            f"{summary['shared_nodes']['count']} shared, "
            f"{summary['external_users']['count']} external)"
        )

        # Get quota status
        quota = await service.get_quota_usage()

        logger.info(
            f"📊 Quota: {quota['users_count']}/{quota['quota_limit']} users "
            f"({quota['quota_percentage']:.1f}%)"
        )

    except Exception as e:
        logger.error(f"Tailscale status logging failed: {e}", exc_info=True)
