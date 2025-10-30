"""
AEMET API Client (Infrastructure Layer)
========================================

Robust client for AEMET (Agencia Estatal de Meteorología) with:
- Automatic token renewal every 6 days
- Retry logic using tenacity
- Multi-station support
- Historical data retrieval

API Documentation: https://opendata.aemet.es/centrodedescargas/inicio

Usage:
    from infrastructure.external_apis.aemet_client import AEMETAPIClient

    async with AEMETAPIClient() as client:
        weather = await client.get_current_weather(station_id="3195")
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import hashlib

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from core.config import settings
from core.exceptions import AEMETAPIError

logger = logging.getLogger(__name__)


class AEMETAPIClient:
    """
    Asynchronous client for AEMET (Spanish Weather Service) API.

    Features:
    - Automatic token renewal (tokens expire every 6 days)
    - Token caching to disk
    - Retry logic with exponential backoff
    - Multi-station weather data
    """

    BASE_URL = settings.AEMET_API_BASE_URL
    TOKEN_CACHE_PATH = Path("/app/data/aemet_token_cache.json")
    TOKEN_VALIDITY_DAYS = 6

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize AEMET API client.

        Args:
            api_key: AEMET API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or settings.AEMET_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

        if not self.api_key:
            raise ValueError("AEMET_API_KEY is required")

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        await self._ensure_token()
        logger.info("✅ AEMET API client initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            logger.info("🔒 AEMET API client closed")

    async def _ensure_token(self):
        """Ensure we have a valid token (load from cache or fetch new)."""
        # Try loading cached token
        cached_token = self._load_cached_token()

        if cached_token and self._is_token_valid(cached_token):
            self._token = cached_token["token"]
            logger.info("✅ Using cached AEMET token")
        else:
            # Token expired or missing, fetch new one
            logger.info("🔄 Fetching new AEMET token")
            await self._fetch_new_token()

    def _load_cached_token(self) -> Optional[Dict[str, Any]]:
        """Load token from cache file."""
        try:
            if self.TOKEN_CACHE_PATH.exists():
                with open(self.TOKEN_CACHE_PATH, "r") as f:
                    data = json.load(f)
                    logger.debug(f"📄 Loaded AEMET token from cache: {self.TOKEN_CACHE_PATH}")
                    return data
        except Exception as e:
            logger.warning(f"⚠️ Failed to load AEMET token cache: {e}")

        return None

    def _is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """Check if cached token is still valid."""
        try:
            # Check API key hash
            current_hash = hashlib.md5(self.api_key.encode()).hexdigest()
            if token_data.get("api_key_hash") != current_hash:
                logger.info("🔄 API key changed, need new token")
                return False

            # Check expiration
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(timezone.utc) >= expires_at:
                logger.info("⏰ AEMET token expired")
                return False

            logger.debug(f"✅ AEMET token valid until {expires_at}")
            return True

        except (KeyError, ValueError) as e:
            logger.warning(f"⚠️ Invalid token data: {e}")
            return False

    def _save_token(self, token: str):
        """Save token to cache file."""
        try:
            # Ensure cache directory exists with proper permissions
            self.TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o777)

            token_data = {
                "token": token,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=self.TOKEN_VALIDITY_DAYS)
                ).isoformat(),
                "api_key_hash": hashlib.md5(self.api_key.encode()).hexdigest()
            }

            with open(self.TOKEN_CACHE_PATH, "w") as f:
                json.dump(token_data, f, indent=2)

            logger.info(f"💾 AEMET token saved to cache: {self.TOKEN_CACHE_PATH}")

        except (OSError, PermissionError) as e:
            # Non-critical: token will work without caching
            logger.debug(f"⚠️ Could not save AEMET token cache (non-critical): {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save AEMET token: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _fetch_new_token(self):
        """Fetch new token from AEMET API."""
        if not self._client:
            raise RuntimeError("Client not initialized")

        # AEMET uses API key as the token directly
        # No separate token endpoint needed
        self._token = self.api_key
        self._save_token(self._token)
        logger.info("✅ AEMET token refreshed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to AEMET API with automatic retries.

        AEMET API returns a metadata URL first, then actual data URL.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response data

        Raises:
            AEMETAPIError: If request fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized")

        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"api_key": self._token}

        try:
            # Step 1: Get metadata URL
            logger.debug(f"🌐 AEMET API request: GET {url}")
            response = await self._client.get(url, params=params or {}, headers=headers)
            response.raise_for_status()

            metadata = response.json()

            # Step 2: Get actual data from datos URL
            data_url = metadata.get("datos")
            if not data_url:
                raise AEMETAPIError(500, "No datos URL in AEMET response")

            logger.debug(f"📊 Fetching AEMET data from: {data_url}")
            data_response = await self._client.get(data_url)
            data_response.raise_for_status()

            logger.info(f"✅ AEMET API success: {endpoint}")
            return data_response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AEMET API HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise AEMETAPIError(e.response.status_code, e.response.text)

        except httpx.RequestError as e:
            logger.error(f"❌ AEMET API request error: {e}")
            raise AEMETAPIError(0, str(e))

    async def get_current_weather(
        self,
        station_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get current weather observations from AEMET station.

        Args:
            station_id: Weather station ID (defaults to Madrid-Retiro: 3195)

        Returns:
            List of weather observations

        Example:
            >>> async with AEMETAPIClient() as client:
            ...     weather = await client.get_current_weather(station_id="3195")
            ...     print(weather[0]["ta"])  # Temperature
        """
        station = station_id or settings.AEMET_DEFAULT_STATION
        endpoint = f"observacion/convencional/datos/estacion/{station}"

        logger.info(f"📊 Fetching AEMET weather for station {station}")

        try:
            data = await self._make_request(endpoint)
            weather_records = self._parse_weather_response(data, station)

            if weather_records:
                logger.info(f"✅ Retrieved {len(weather_records)} AEMET weather records")
            else:
                logger.warning(f"⚠️ No weather data found for station {station}")

            return weather_records

        except Exception as e:
            logger.error(f"❌ Failed to fetch AEMET weather: {e}")
            raise

    def _parse_weather_response(
        self,
        data: Any,
        station_id: str
    ) -> List[Dict[str, Any]]:
        """
        Parse AEMET API weather response.

        Args:
            data: Raw API response (list or dict)
            station_id: Station ID

        Returns:
            List of parsed weather records
        """
        records = []

        # AEMET returns list of observations
        if not isinstance(data, list):
            data = [data]

        for item in data:
            try:
                # Parse timestamp
                timestamp_str = item.get("fint")  # Fecha/hora de observación
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(timezone.utc)

                # Extract weather variables
                record = {
                    "timestamp": timestamp,
                    "station_id": station_id,
                    "temperature": self._safe_float(item.get("ta")),  # Temperatura (°C)
                    "humidity": self._safe_float(item.get("hr")),  # Humedad relativa (%)
                    "pressure": self._safe_float(item.get("pres")),  # Presión (hPa)
                    "wind_speed": self._safe_float(item.get("vv")),  # Velocidad viento (km/h)
                    "wind_direction": self._safe_float(item.get("dv")),  # Dirección viento (grados)
                    "precipitation": self._safe_float(item.get("prec")),  # Precipitación (mm)
                    "source": "aemet"
                }

                records.append(record)

            except Exception as e:
                logger.warning(f"⚠️ Failed to parse weather record: {e}")

        return records

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def get_daily_weather(
        self,
        start_date: datetime,
        end_date: datetime,
        station_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily historical weather data (valores climatológicos diarios).

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            station_id: Weather station ID (defaults to Linares, Jaén)

        Returns:
            List of daily weather records

        API Endpoint:
            /api/valores/climatologicos/diarios/datos/fechaini/{fechaIniStr}/fechafin/{fechaFinStr}/estacion/{idema}

        Format dates: YYYY-MM-DDTHH:MM:SSUTC (e.g., 2025-10-29T00:00:00UTC)
        """
        station = station_id or settings.AEMET_DEFAULT_STATION

        # Format dates as required by AEMET API
        fecha_ini = start_date.strftime("%Y-%m-%dT%H:%M:%SUTC")
        fecha_fin = end_date.strftime("%Y-%m-%dT%H:%M:%SUTC")

        endpoint = f"valores/climatologicos/diarios/datos/fechaini/{fecha_ini}/fechafin/{fecha_fin}/estacion/{station}"

        logger.info(f"📊 Fetching AEMET daily weather: {station} from {fecha_ini} to {fecha_fin}")

        try:
            data = await self._make_request(endpoint)
            weather_records = self._parse_daily_weather_response(data, station)

            if weather_records:
                logger.info(f"✅ Retrieved {len(weather_records)} AEMET daily weather records")
            else:
                logger.warning(f"⚠️ No daily weather data found for station {station} in range {fecha_ini} - {fecha_fin}")

            return weather_records

        except Exception as e:
            logger.error(f"❌ Failed to fetch AEMET daily weather: {e}")
            raise

    def _parse_daily_weather_response(
        self,
        data: Any,
        station_id: str
    ) -> List[Dict[str, Any]]:
        """
        Parse AEMET API daily weather response (valores climatológicos diarios).

        Args:
            data: Raw API response (list of daily records)
            station_id: Station ID

        Returns:
            List of parsed daily weather records
        """
        records = []

        # AEMET returns list of daily observations
        if not isinstance(data, list):
            data = [data]

        for item in data:
            try:
                # Parse date (fecha is the observation date)
                fecha_str = item.get("fecha")  # Format: YYYY-MM-DD
                if fecha_str:
                    # Use noon (12:00) as representative time for daily values
                    timestamp = datetime.fromisoformat(f"{fecha_str}T12:00:00+00:00")
                else:
                    continue  # Skip records without date

                # Extract daily weather variables
                record = {
                    "timestamp": timestamp,
                    "station_id": station_id,
                    "temperature": self._safe_float(item.get("tmed")),  # Temperatura media (°C)
                    "temp_max": self._safe_float(item.get("tmax")),  # Temperatura máxima (°C)
                    "temp_min": self._safe_float(item.get("tmin")),  # Temperatura mínima (°C)
                    "humidity": self._safe_float(item.get("hrMedia")),  # Humedad relativa media (%)
                    "pressure": self._safe_float(item.get("presMax")),  # Presión máxima (hPa)
                    "wind_speed": self._safe_float(item.get("velmedia")),  # Velocidad media viento (km/h)
                    "wind_direction": self._safe_float(item.get("dir")),  # Dirección viento (grados)
                    "precipitation": self._safe_float(item.get("prec")),  # Precipitación (mm)
                    "source": "aemet_daily"
                }

                records.append(record)

            except Exception as e:
                logger.warning(f"⚠️ Failed to parse daily weather record: {e}")

        return records

    async def get_historical_weather(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get historical weather data (alias for get_daily_weather).

        Args:
            station_id: Weather station ID
            start_date: Start date
            end_date: End date

        Returns:
            List of historical weather records
        """
        return await self.get_daily_weather(start_date, end_date, station_id)
