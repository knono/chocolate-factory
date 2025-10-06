"""
APScheduler Configuration Module
=================================

Registers all scheduled jobs for the Chocolate Factory system.

Jobs include:
- REE data ingestion (every 5 minutes)
- Weather data ingestion (every 5 minutes)
- ML training (every 30 minutes)
- ML predictions (every 30 minutes)
- Prophet forecasting (every hour)
- Backfill detection (every 2 hours)
- Health checks (every 15 minutes)

Note: This is a placeholder for Phase 7.
Full job registration will be implemented when migrating APScheduler jobs.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import settings

logger = logging.getLogger(__name__)


async def register_all_jobs(scheduler: AsyncIOScheduler):
    """
    Register all APScheduler jobs.

    This function will be fully implemented in Phase 7.
    For now, it's a placeholder to complete the foundation setup.

    Args:
        scheduler: AsyncIOScheduler instance
    """
    logger.info("📋 Job registration placeholder (Phase 7 pending)")
    logger.info(f"   Scheduler timezone: {settings.SCHEDULER_TIMEZONE}")
    logger.info(f"   REE ingestion interval: {settings.REE_INGESTION_INTERVAL}min")
    logger.info(f"   Weather ingestion interval: {settings.WEATHER_INGESTION_INTERVAL}min")
    logger.info(f"   ML training interval: {settings.ML_TRAINING_INTERVAL}min")
    logger.info(f"   Prophet forecast interval: {settings.PROPHET_FORECAST_INTERVAL}min")
    logger.info(f"   Backfill interval: {settings.BACKFILL_INTERVAL}min")

    # Jobs will be registered here in Phase 7
    # Example structure:
    # scheduler.add_job(
    #     func=ree_ingestion_job,
    #     trigger="interval",
    #     minutes=settings.REE_INGESTION_INTERVAL,
    #     id="ree_ingestion",
    #     name="REE Data Ingestion",
    #     replace_existing=True
    # )

    logger.info("✅ Scheduler configuration ready for Phase 7 job registration")
