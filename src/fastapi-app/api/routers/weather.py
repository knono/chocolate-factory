"""
Weather Router
==============

Endpoints for weather data (AEMET + OpenWeatherMap aggregation).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from services.aemet_service import AEMETService
from services.weather_aggregation_service import WeatherAggregationService
from infrastructure.influxdb import get_influxdb_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather"])


def get_weather_service() -> WeatherAggregationService:
    """Dependency injection for weather service."""
    influx = get_influxdb_client()
    aemet_service = AEMETService(influx)
    return WeatherAggregationService(influx, aemet_service)


@router.get("/current")
async def get_current_weather(
    service: WeatherAggregationService = Depends(get_weather_service)
) -> Dict[str, Any]:
    """
    Get current weather from best available source.

    Automatically selects between AEMET and OpenWeatherMap.
    """
    try:
        weather = await service.get_current_weather()
        return weather
    except Exception as e:
        logger.error(f"Failed to get current weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_weather(
    service: WeatherAggregationService = Depends(get_weather_service)
) -> Dict[str, Any]:
    """
    Ingest weather from all sources (AEMET + OpenWeatherMap).

    Returns summary of ingestion results.
    """
    try:
        results = await service.ingest_weather_hybrid()
        return results
    except Exception as e:
        logger.error(f"Failed to ingest weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))
