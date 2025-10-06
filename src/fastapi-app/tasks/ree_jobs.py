"""
REE Ingestion Jobs
==================

APScheduler jobs for REE electricity price ingestion.
"""

import logging
from datetime import date

from services.ree_service import REEService
from infrastructure.influxdb import get_influxdb_client

logger = logging.getLogger(__name__)


async def ree_ingestion_job():
    """
    Scheduled job: Ingest REE prices (runs every 5 minutes).
    """
    logger.info("🔄 Running scheduled REE ingestion")

    try:
        influx = get_influxdb_client()
        ree_service = REEService(influx)

        result = await ree_service.ingest_prices(date.today())

        logger.info(f"✅ REE ingestion completed: {result['records_written']} records")

    except Exception as e:
        logger.error(f"❌ REE ingestion failed: {e}", exc_info=True)
