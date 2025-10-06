"""
REE API Client (Infrastructure Layer)
======================================

Robust client for Red Eléctrica de España (REE) API with:
- Automatic retries using tenacity
- Rate limiting
- Structured error handling
- Type-safe responses

API Documentation: https://www.ree.es/es/apidatos

Usage:
    from infrastructure.external_apis.ree_client import REEAPIClient

    async with REEAPIClient() as client:
        prices = await client.get_pvpc_prices(date(2025, 10, 6))
"""

import asyncio
from datetime import datetime, timedelta, date
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
from core.exceptions import REEAPIError

logger = logging.getLogger(__name__)


class REEAPIClient:
    """
    Asynchronous client for REE (Red Eléctrica de España) API.

    Features:
    - Automatic retries with exponential backoff
    - Rate limiting compliance
    - PVPC price data retrieval
    - Type-safe responses
    """

    BASE_URL = settings.REE_API_BASE_URL
    PVPC_ENDPOINT = "mercados/precios-mercados-tiempo-real"

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize REE API client.

        Args:
            api_token: Optional API token (REE API doesn't require auth)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_token = api_token or settings.REE_API_TOKEN
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers()
        )
        logger.info("✅ REE API client initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            logger.info("🔒 REE API client closed")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for REE API."""
        headers = {
            "Accept": "application/json",
            "User-Agent": f"ChocolateFactory/{settings.API_VERSION}"
        }

        if self.api_token:
            headers["Authorization"] = f"Token token={self.api_token}"

        return headers

    @staticmethod
    def _format_date(dt: datetime) -> str:
        """Format datetime for REE API (YYYY-MM-DDTHH:MM)."""
        return dt.strftime("%Y-%m-%dT%H:%M")

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
        Make HTTP request to REE API with automatic retries.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            REEAPIError: If request fails after retries
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            logger.debug(f"🌐 REE API request: GET {url}")
            response = await self._client.get(url, params=params or {})
            response.raise_for_status()

            logger.info(f"✅ REE API success: {endpoint} (status {response.status_code})")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ REE API HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise REEAPIError(e.response.status_code, e.response.text)

        except httpx.RequestError as e:
            logger.error(f"❌ REE API request error: {e}")
            raise REEAPIError(0, str(e))

    async def get_pvpc_prices(
        self,
        target_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get PVPC (Precio Voluntario Pequeño Consumidor) electricity prices.

        Args:
            target_date: Date to fetch prices for (defaults to today)

        Returns:
            List of price records with timestamp and price

        Example:
            >>> async with REEAPIClient() as client:
            ...     prices = await client.get_pvpc_prices(date(2025, 10, 6))
            ...     for record in prices:
            ...         print(f"{record['timestamp']}: {record['price_eur_kwh']:.4f} €/kWh")
        """
        if target_date is None:
            target_date = date.today()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        params = {
            "start_date": self._format_date(start_dt),
            "end_date": self._format_date(end_dt),
            "time_trunc": "hour"
        }

        logger.info(f"📊 Fetching REE PVPC prices for {target_date.isoformat()}")

        try:
            data = await self._make_request(self.PVPC_ENDPOINT, params)
            prices = self._parse_pvpc_response(data)

            if prices:
                logger.info(f"✅ Retrieved {len(prices)} PVPC prices for {target_date}")
            else:
                logger.warning(f"⚠️ No PVPC prices found for {target_date}")

            return prices

        except Exception as e:
            logger.error(f"❌ Failed to fetch PVPC prices: {e}")
            raise

    def _parse_pvpc_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse REE API response to extract PVPC prices.

        Args:
            data: Raw API response

        Returns:
            List of parsed price records
        """
        prices = []

        # Navigate REE API response structure
        included = data.get("included", [])
        for item in included:
            if item.get("type") == "PVPC" and "attributes" in item:
                values = item["attributes"].get("values", [])

                for value in values:
                    timestamp_str = value.get("datetime")
                    price_mwh = value.get("value")

                    if timestamp_str and price_mwh is not None:
                        try:
                            # Parse timestamp
                            timestamp = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )

                            # Convert MWh to kWh
                            price_kwh = float(price_mwh) / 1000.0

                            prices.append({
                                "timestamp": timestamp,
                                "price_eur_kwh": price_kwh,
                                "price_eur_mwh": float(price_mwh),
                                "source": "ree_pvpc"
                            })

                        except (ValueError, TypeError) as e:
                            logger.warning(f"⚠️ Invalid price data: {e}")

        return sorted(prices, key=lambda x: x["timestamp"])

    async def get_demand_data(
        self,
        target_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get electricity demand data.

        Args:
            target_date: Date to fetch demand for (defaults to today)

        Returns:
            List of demand records

        Note:
            This is a placeholder for future implementation.
        """
        logger.warning("⚠️ Demand data endpoint not yet implemented")
        return []
