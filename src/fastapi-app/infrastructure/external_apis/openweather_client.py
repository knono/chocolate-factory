"""
OpenWeatherMap API Client (Infrastructure Layer)
=================================================

Robust client for OpenWeatherMap API v2.5 (free tier) with:
- Automatic retries using tenacity
- Rate limiting compliance (60 calls/min free tier)
- Current weather and forecast support
- Compatible data structure with AEMET

API Documentation: https://openweathermap.org/current

Usage:
    from infrastructure.external_apis.openweather_client import OpenWeatherMapAPIClient

    async with OpenWeatherMapAPIClient() as client:
        weather = await client.get_current_weather()
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from core.config import settings
from core.exceptions import OpenWeatherMapError

logger = logging.getLogger(__name__)


class OpenWeatherMapAPIClient:
    """
    Asynchronous client for OpenWeatherMap API v2.5 (free tier).

    Features:
    - Current weather conditions
    - 5-day/3-hour forecast
    - Automatic retries with exponential backoff
    - Rate limiting compliance
    - Compatible output with AEMET client
    """

    BASE_URL = settings.OPENWEATHERMAP_API_BASE_URL
    CURRENT_ENDPOINT = "/weather"
    FORECAST_ENDPOINT = "/forecast"

    # Linares, Jaén coordinates (Chocolate Factory location)
    DEFAULT_LAT = 38.151107
    DEFAULT_LON = -3.629453

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize OpenWeatherMap API client.

        Args:
            api_key: OpenWeatherMap API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or settings.OPENWEATHERMAP_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            raise ValueError("OPENWEATHERMAP_API_KEY is required")

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        logger.info("✅ OpenWeatherMap API client initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            logger.info("🔒 OpenWeatherMap API client closed")

    def _get_params(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get API request parameters."""
        return {
            "lat": lat or self.DEFAULT_LAT,
            "lon": lon or self.DEFAULT_LON,
            "appid": self.api_key,
            "units": "metric"  # Celsius, km/h
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OpenWeatherMap API with automatic retries.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response

        Raises:
            OpenWeatherMapError: If request fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized")

        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.debug(f"🌐 OpenWeatherMap API request: GET {url}")
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            logger.info(f"✅ OpenWeatherMap API success: {endpoint}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("❌ OpenWeatherMap API: Invalid API key")
                raise OpenWeatherMapError(401, "Invalid API key")
            elif e.response.status_code == 429:
                logger.error("❌ OpenWeatherMap API: Rate limit exceeded")
                raise OpenWeatherMapError(429, "Rate limit exceeded (60 calls/min)")
            else:
                logger.error(f"❌ OpenWeatherMap HTTP error: {e.response.status_code}")
                raise OpenWeatherMapError(e.response.status_code, e.response.text)

        except httpx.RequestError as e:
            logger.error(f"❌ OpenWeatherMap request error: {e}")
            raise OpenWeatherMapError(0, str(e))

    async def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get current weather conditions.

        Args:
            lat: Latitude (defaults to Linares, Jaén)
            lon: Longitude (defaults to Linares, Jaén)

        Returns:
            Weather data dictionary

        Example:
            >>> async with OpenWeatherMapAPIClient() as client:
            ...     weather = await client.get_current_weather()
            ...     print(f"Temperature: {weather['temperature']}°C")
        """
        params = self._get_params(lat, lon)

        logger.info(f"📊 Fetching OpenWeatherMap current weather for ({params['lat']}, {params['lon']})")

        try:
            data = await self._make_request(self.CURRENT_ENDPOINT, params)
            weather = self._parse_current_weather(data)

            logger.info(f"✅ Retrieved OpenWeatherMap current weather: {weather['temperature']}°C")
            return weather

        except Exception as e:
            logger.error(f"❌ Failed to fetch current weather: {e}")
            raise

    def _parse_current_weather(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse current weather response.

        Args:
            data: Raw API response

        Returns:
            Parsed weather data (compatible with AEMET format)
        """
        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})

        # Parse timestamp
        dt = data.get("dt")
        timestamp = datetime.fromtimestamp(dt, tz=timezone.utc) if dt else datetime.now(timezone.utc)

        return {
            "timestamp": timestamp,
            "station_id": f"openweathermap_{data.get('id', 'unknown')}",
            "temperature": main.get("temp"),
            "temperature_min": main.get("temp_min"),
            "temperature_max": main.get("temp_max"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"),
            "wind_direction": wind.get("deg"),
            "precipitation": rain.get("1h", 0.0),  # Precipitation last 1 hour
            "weather_description": data.get("weather", [{}])[0].get("description"),
            "cloudiness": data.get("clouds", {}).get("all"),
            "source": "openweathermap"
        }

    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get weather forecast (5-day/3-hour).

        Args:
            lat: Latitude
            lon: Longitude
            hours: Number of hours to forecast (max 120)

        Returns:
            List of forecast records

        Example:
            >>> async with OpenWeatherMapAPIClient() as client:
            ...     forecast = await client.get_forecast(hours=24)
            ...     for record in forecast:
            ...         print(f"{record['timestamp']}: {record['temperature']}°C")
        """
        params = self._get_params(lat, lon)

        logger.info(f"📊 Fetching OpenWeatherMap forecast for {hours}h")

        try:
            data = await self._make_request(self.FORECAST_ENDPOINT, params)
            forecast = self._parse_forecast(data, hours)

            logger.info(f"✅ Retrieved {len(forecast)} OpenWeatherMap forecast records")
            return forecast

        except Exception as e:
            logger.error(f"❌ Failed to fetch forecast: {e}")
            raise

    def _parse_forecast(
        self,
        data: Dict[str, Any],
        hours: int
    ) -> List[Dict[str, Any]]:
        """
        Parse forecast response.

        Args:
            data: Raw API response
            hours: Number of hours to return

        Returns:
            List of parsed forecast records
        """
        records = []
        forecast_list = data.get("list", [])

        # Limit to requested hours (forecast is every 3 hours)
        max_records = hours // 3

        for item in forecast_list[:max_records]:
            main = item.get("main", {})
            wind = item.get("wind", {})
            rain = item.get("rain", {})

            # Parse timestamp
            dt = item.get("dt")
            timestamp = datetime.fromtimestamp(dt, tz=timezone.utc) if dt else datetime.now(timezone.utc)

            record = {
                "timestamp": timestamp,
                "temperature": main.get("temp"),
                "temperature_min": main.get("temp_min"),
                "temperature_max": main.get("temp_max"),
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "wind_speed": wind.get("speed"),
                "wind_direction": wind.get("deg"),
                "precipitation": rain.get("3h", 0.0),  # Precipitation last 3 hours
                "weather_description": item.get("weather", [{}])[0].get("description"),
                "cloudiness": item.get("clouds", {}).get("all"),
                "source": "openweathermap"
            }

            records.append(record)

        return records

    async def get_air_quality(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get air quality data (requires paid subscription).

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Air quality data or None if not available

        Note:
            Air Quality API requires a paid subscription.
        """
        logger.warning("⚠️ Air quality endpoint requires paid subscription")
        return None
