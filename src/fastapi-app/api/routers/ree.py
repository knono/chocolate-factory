"""
REE (Electricity Prices) Router
================================

Endpoints for Spanish electricity price data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import logging

from services.ree_service import REEService
from infrastructure.influxdb import get_influxdb_client
from dependencies import get_telegram_alert_service
from core.exceptions import REEDataError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ree", tags=["REE - Electricity Prices"])


def get_ree_service() -> REEService:
    """Dependency injection for REE service."""
    influx = get_influxdb_client()
    telegram = get_telegram_alert_service()
    return REEService(influx, telegram_service=telegram)


@router.post("/ingest")
async def ingest_ree_prices(
    target_date: Optional[date] = Query(None, description="Date to ingest (defaults to today)"),
    force_refresh: bool = Query(False, description="Overwrite existing data"),
    service: REEService = Depends(get_ree_service)
) -> Dict[str, Any]:
    """
    Ingest REE electricity prices for a specific date.

    - **target_date**: Date to ingest (YYYY-MM-DD format)
    - **force_refresh**: If true, overwrites existing data
    """
    try:
        result = await service.ingest_prices(target_date, force_refresh)
        return result
    except REEDataError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_ree_prices(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to start_date + 1 day)"),
    limit: Optional[int] = Query(None, description="Maximum records to return"),
    service: REEService = Depends(get_ree_service)
) -> List[Dict[str, Any]]:
    """
    Get historical REE electricity prices.

    Returns hourly prices for the specified date range.
    """
    try:
        prices = await service.get_prices(start_date, end_date, limit)
        return prices
    except Exception as e:
        logger.error(f"Failed to get REE prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/latest")
async def get_latest_price(
    service: REEService = Depends(get_ree_service)
) -> Dict[str, Any]:
    """
    Get the most recent electricity price.
    """
    latest = await service.get_latest_price()
    if not latest:
        raise HTTPException(status_code=404, detail="No recent price data available")
    return latest


@router.get("/prices/stats")
async def get_price_stats(
    start_date: date = Query(..., description="Start date"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    service: REEService = Depends(get_ree_service)
) -> Dict[str, Any]:
    """
    Get price statistics for a date range.

    Returns min, max, avg, median prices.
    """
    try:
        stats = await service.get_price_stats(start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"Failed to get price stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
