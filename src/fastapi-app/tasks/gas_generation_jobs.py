"""
Gas Generation Ingestion Jobs
==============================

APScheduler job for daily gas generation data ingestion from REE API.

Runs daily at 11:00 AM to fetch yesterday's Ciclo Combinado (gas) data.

Usage:
    This job is registered in scheduler.py and runs automatically.
"""

import asyncio
import logging
from datetime import date, timedelta

from services.gas_generation_service import GasGenerationService
from dependencies import get_telegram_alert_service

logger = logging.getLogger(__name__)


async def gas_ingestion_job():
    """
    Daily job to ingest gas generation data.
    
    Runs at 11:00 AM to fetch yesterday's data.
    Also checks for gaps in recent data and fills them.
    """
    logger.info("🔄 Starting gas generation ingestion job")
    
    try:
        service = GasGenerationService()
        telegram = get_telegram_alert_service()
        
        # Ingest yesterday's data
        yesterday = date.today() - timedelta(days=1)
        result = await service.ingest_gas_data(yesterday)
        
        if result["success"]:
            if result.get("action") == "ingested":
                logger.info(f"✅ Gas ingestion completed: {result['value_mwh']:,.0f} MWh")
            else:
                logger.info(f"⏭️ Gas ingestion skipped: {result.get('reason', 'unknown')}")
        else:
            error_msg = f"Gas ingestion failed: {result.get('error', 'unknown')}"
            logger.error(f"❌ {error_msg}")
            
            # Alert on failure
            if telegram:
                await telegram.send_alert(
                    title="⚠️ Gas Ingestion Failed",
                    message=error_msg,
                    level="warning"
                )
        
        # Check for gaps in last 7 days and fill them
        gaps = await service.detect_gaps(days_back=7)
        
        if gaps:
            logger.info(f"📥 Filling {len(gaps)} gaps in gas data")
            for gap_date in gaps:
                gap_result = await service.ingest_gas_data(gap_date)
                if gap_result["success"]:
                    logger.info(f"   ✅ Filled gap for {gap_date}")
                else:
                    logger.warning(f"   ⚠️ Could not fill gap for {gap_date}")
        
    except Exception as e:
        logger.error(f"❌ Gas ingestion job failed: {e}", exc_info=True)
        
        try:
            telegram = get_telegram_alert_service()
            if telegram:
                await telegram.send_alert(
                    title="❌ Gas Ingestion Job Error",
                    message=str(e),
                    level="error"
                )
        except Exception:
            pass
