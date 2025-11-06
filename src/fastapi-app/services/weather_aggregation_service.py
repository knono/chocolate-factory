"""
Weather Aggregation Service (Application Layer)
================================================

Aggregates weather data from multiple sources (AEMET + OpenWeatherMap).

Responsibilities:
- Provide unified weather interface
- Aggregate data from AEMET (primary) and OpenWeatherMap (fallback)
- Handle 24/7 coverage (AEMET 00:00-07:00, OpenWeatherMap 08:00-23:00)
- Return best available data

Usage:
    from services.weather_aggregation_service import WeatherAggregationService

    weather_service = WeatherAggregationService(influx, aemet_service, owm_service)
    current = await weather_service.get_current_weather()
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from infrastructure.influxdb import InfluxDBClientWrapper
from infrastructure.external_apis import OpenWeatherMapAPIClient
from services.aemet_service import AEMETService
from core.config import settings

logger = logging.getLogger(__name__)


class WeatherAggregationService:
    """
    Multi-source weather aggregation service.

    Strategy:
    1. Try AEMET first (official Spanish weather service)
    2. Fall back to OpenWeatherMap if AEMET unavailable
    3. Use time-based routing: AEMET (00-07h), OpenWeatherMap (08-23h)
    """

    def __init__(
        self,
        influxdb_client: InfluxDBClientWrapper,
        aemet_service: AEMETService
    ):
        """
        Initialize weather aggregation service.

        Args:
            influxdb_client: InfluxDB client instance
            aemet_service: AEMET service instance
        """
        self.influxdb = influxdb_client
        self.aemet_service = aemet_service

    async def get_current_weather(
        self,
        prefer_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current weather from best available source.

        Args:
            prefer_source: Preferred source ("aemet" or "openweathermap")

        Returns:
            Weather data with source information

        Example:
            >>> weather = await weather_service.get_current_weather()
            >>> print(f"{weather['temperature']}°C from {weather['source']}")
        """
        # Determine source based on time of day (Spanish timezone)
        current_hour = datetime.now(timezone.utc).hour

        # Strategy: AEMET for 00-07h, OpenWeatherMap for 08-23h
        if prefer_source:
            primary_source = prefer_source
        elif 0 <= current_hour < 8:
            primary_source = "aemet"
        else:
            primary_source = "openweathermap"

        logger.info(f"🌤️ Fetching weather from {primary_source} (hour: {current_hour})")

        # Try primary source
        if primary_source == "aemet":
            weather = await self._get_aemet_weather()
            if weather:
                return weather

            # Fallback to OpenWeatherMap
            logger.warning("⚠️ AEMET unavailable, falling back to OpenWeatherMap")
            weather = await self._get_openweathermap_weather()
            if weather:
                return weather

        else:
            # Primary: OpenWeatherMap
            weather = await self._get_openweathermap_weather()
            if weather:
                return weather

            # Fallback to AEMET
            logger.warning("⚠️ OpenWeatherMap unavailable, falling back to AEMET")
            weather = await self._get_aemet_weather()
            if weather:
                return weather

        # No data available from any source
        logger.error("❌ No weather data available from any source")
        return {
            "error": "No weather data available",
            "source": "none",
            "timestamp": datetime.now(timezone.utc)
        }

    async def _get_aemet_weather(self) -> Optional[Dict[str, Any]]:
        """Get latest weather from AEMET."""
        try:
            weather = await self.aemet_service.get_latest_weather(
                station_id=settings.AEMET_DEFAULT_STATION
            )
            if weather:
                logger.info(f"✅ Got AEMET weather: {weather['temperature']}°C")
            return weather
        except Exception as e:
            logger.error(f"❌ Failed to get AEMET weather: {e}")
            return None

    async def _get_openweathermap_weather(self) -> Optional[Dict[str, Any]]:
        """Get current weather from OpenWeatherMap."""
        try:
            async with OpenWeatherMapAPIClient() as owm_client:
                weather = await owm_client.get_current_weather()

            if weather:
                logger.info(f"✅ Got OpenWeatherMap weather: {weather['temperature']}°C")

                # Transform to InfluxDB and persist
                await self._persist_openweathermap(weather)

            return weather

        except Exception as e:
            logger.error(f"❌ Failed to get OpenWeatherMap weather: {e}")
            return None

    async def _persist_openweathermap(self, weather: Dict[str, Any]):
        """Persist OpenWeatherMap data to InfluxDB."""
        try:
            from influxdb_client import Point, WritePrecision

            point = Point("weather_data") \
                .tag("source", "openweathermap") \
                .tag("station_id", weather.get("station_id", "owm_default"))

            if weather.get("temperature") is not None:
                point.field("temperature", float(weather["temperature"]))
            if weather.get("humidity") is not None:
                point.field("humidity", float(weather["humidity"]))
            if weather.get("pressure") is not None:
                point.field("pressure", float(weather["pressure"]))
            if weather.get("wind_speed") is not None:
                point.field("wind_speed", float(weather["wind_speed"]))

            point.time(weather["timestamp"], WritePrecision.NS)

            self.influxdb.write_points([point])
            logger.info("✅ Persisted OpenWeatherMap data to InfluxDB")

        except Exception as e:
            logger.warning(f"⚠️ Failed to persist OpenWeatherMap data: {e}")

    async def ingest_weather_hybrid(self) -> Dict[str, Any]:
        """
        Ingest weather from both sources and return summary.

        Returns:
            Summary of ingestion from both sources
        """
        results = {
            "aemet": None,
            "openweathermap": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Ingest AEMET
        try:
            aemet_result = await self.aemet_service.ingest_weather()
            results["aemet"] = {
                "success": True,
                "records_written": aemet_result.get("records_written", 0),
                "temperature": aemet_result.get("latest_temperature")
            }
        except Exception as e:
            logger.error(f"❌ AEMET ingestion failed: {e}")
            results["aemet"] = {"success": False, "error": str(e)}

        # Ingest OpenWeatherMap
        try:
            weather = await self._get_openweathermap_weather()
            if weather:
                results["openweathermap"] = {
                    "success": True,
                    "temperature": weather.get("temperature")
                }
        except Exception as e:
            logger.error(f"❌ OpenWeatherMap ingestion failed: {e}")
            results["openweathermap"] = {"success": False, "error": str(e)}

        return results
