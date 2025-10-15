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

    logger.info(f"✅ Registered {len(scheduler.get_jobs())} jobs")
