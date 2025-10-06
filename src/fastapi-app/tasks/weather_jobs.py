"""
Weather Ingestion Jobs
=======================

APScheduler jobs for weather data ingestion.
"""

import logging

from services.aemet_service import AEMETService
from services.weather_aggregation_service import WeatherAggregationService
from infrastructure.influxdb import get_influxdb_client

logger = logging.getLogger(__name__)


async def weather_ingestion_job():
    """
    Scheduled job: Ingest weather data (runs every 5 minutes).
    """
    logger.info("🔄 Running scheduled weather ingestion")

    try:
        influx = get_influxdb_client()
        aemet_service = AEMETService(influx)
        weather_service = WeatherAggregationService(influx, aemet_service)

        result = await weather_service.ingest_weather_hybrid()

        logger.info(f"✅ Weather ingestion completed: {result}")

    except Exception as e:
        logger.error(f"❌ Weather ingestion failed: {e}", exc_info=True)
