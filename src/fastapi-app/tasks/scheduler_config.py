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
from .sklearn_jobs import sklearn_training_job  # sklearn training
from .health_monitoring_jobs import (  # Sprint 13 (pivoted)
    collect_health_metrics,
    log_health_status,
    check_critical_nodes
)

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

    # sklearn model training (every 30 minutes)
    scheduler.add_job(
        func=sklearn_training_job,
        trigger="interval",
        minutes=30,
        id="sklearn_training",
        name="sklearn Model Training",
        replace_existing=True
    )
    logger.info("   ✅ sklearn training: every 30 minutes")

    # Health monitoring metrics collection (every 5 minutes) - Sprint 13 (pivoted)
    scheduler.add_job(
        func=collect_health_metrics,
        trigger="interval",
        minutes=5,
        id="health_metrics_collection",
        name="Health Metrics Collection",
        replace_existing=True
    )
    logger.info("   ✅ Health metrics: every 5 minutes")

    # Health status logging (every hour) - Sprint 13 (pivoted)
    scheduler.add_job(
        func=log_health_status,
        trigger="interval",
        hours=1,
        id="health_status_log",
        name="Health Status Logging",
        replace_existing=True
    )
    logger.info("   ✅ Health status log: every hour")

    # Critical nodes check (every 2 minutes) - Sprint 13 (pivoted)
    scheduler.add_job(
        func=check_critical_nodes,
        trigger="interval",
        minutes=2,
        id="critical_nodes_check",
        name="Critical Nodes Health Check",
        replace_existing=True
    )
    logger.info("   ✅ Critical nodes check: every 2 minutes")

    logger.info(f"✅ Registered {len(scheduler.get_jobs())} jobs")
