"""
APScheduler Configuration
==========================

Registers all scheduled jobs for the Chocolate Factory system.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import settings
from .ree_jobs import ree_ingestion_job
from .weather_jobs import weather_ingestion_job
from .ml_jobs import ensure_prophet_model_job
from .analytics_jobs import collect_analytics, log_tailscale_status  # Sprint 13

logger = logging.getLogger(__name__)


async def register_all_jobs(scheduler: AsyncIOScheduler):
    """
    Register all APScheduler jobs.

    Args:
        scheduler: AsyncIOScheduler instance
    """
    logger.info("📋 Registering APScheduler jobs...")

    # REE price ingestion (every 5 minutes)
    scheduler.add_job(
        func=ree_ingestion_job,
        trigger="interval",
        minutes=settings.REE_INGESTION_INTERVAL,
        id="ree_ingestion",
        name="REE Price Ingestion",
        replace_existing=True
    )
    logger.info(f"   ✅ REE ingestion: every {settings.REE_INGESTION_INTERVAL} minutes")

    # Weather data ingestion (every 5 minutes)
    scheduler.add_job(
        func=weather_ingestion_job,
        trigger="interval",
        minutes=settings.WEATHER_INGESTION_INTERVAL,
        id="weather_ingestion",
        name="Weather Data Ingestion",
        replace_existing=True
    )
    logger.info(f"   ✅ Weather ingestion: every {settings.WEATHER_INGESTION_INTERVAL} minutes")

    # Prophet model auto-training (run at startup + daily)
    from datetime import datetime as dt
    scheduler.add_job(
        func=ensure_prophet_model_job,
        trigger="interval",
        hours=24,
        id="ensure_prophet_model",
        name="Ensure Prophet Model Exists",
        replace_existing=True,
        next_run_time=dt.now()  # Execute immediately
    )
    logger.info("   ✅ Prophet model check: at startup + every 24 hours")

    # Tailscale analytics collection (every 15 minutes) - Sprint 13
    scheduler.add_job(
        func=collect_analytics,
        trigger="interval",
        minutes=15,
        id="tailscale_analytics_collection",
        name="Tailscale Analytics Collection",
        replace_existing=True
    )
    logger.info("   ✅ Tailscale analytics: every 15 minutes")

    # Tailscale status logging (every hour) - Sprint 13
    scheduler.add_job(
        func=log_tailscale_status,
        trigger="interval",
        hours=1,
        id="tailscale_status_log",
        name="Tailscale Status Logging",
        replace_existing=True
    )
    logger.info("   ✅ Tailscale status log: every hour")

    logger.info(f"✅ Registered {len(scheduler.get_jobs())} jobs")
