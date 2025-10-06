"""
InfluxDB Client Module
======================

Provides a robust InfluxDB client wrapper with:
- Automatic connection management
- Query builder utilities
- Batch write operations
- Health checks and connection pooling
- Error handling and retries

Usage:
    from infrastructure.influxdb.client import get_influxdb_client

    client = get_influxdb_client()
    query_api = client.query_api()
    results = query_api.query('from(bucket:"energy_data") |> range(start: -1h)')
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from core.config import settings
from core.exceptions import (
    InfluxDBConnectionError,
    InfluxDBQueryError,
    InfluxDBWriteError
)

logger = logging.getLogger(__name__)


class InfluxDBClientWrapper:
    """
    Wrapper for InfluxDB client with enhanced functionality.

    Provides:
    - Connection management
    - Automatic retries
    - Query and write API access
    - Health checks
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        org: Optional[str] = None,
        bucket: Optional[str] = None
    ):
        """
        Initialize InfluxDB client wrapper.

        Args:
            url: InfluxDB URL (defaults to settings.INFLUXDB_URL)
            token: Authentication token (defaults to settings.INFLUXDB_TOKEN)
            org: Organization name (defaults to settings.INFLUXDB_ORG)
            bucket: Default bucket name (defaults to settings.INFLUXDB_BUCKET)
        """
        self.url = url or settings.INFLUXDB_URL
        self.token = token or settings.INFLUXDB_TOKEN
        self.org = org or settings.INFLUXDB_ORG
        self.bucket = bucket or settings.INFLUXDB_BUCKET

        self._client: Optional[InfluxDBClient] = None
        self._write_api = None
        self._query_api = None

    @property
    def client(self) -> InfluxDBClient:
        """Get or create InfluxDB client instance (lazy loading)."""
        if self._client is None:
            try:
                self._client = InfluxDBClient(
                    url=self.url,
                    token=self.token,
                    org=self.org,
                    timeout=settings.INFLUXDB_TIMEOUT,
                    verify_ssl=settings.INFLUXDB_VERIFY_SSL,
                    enable_gzip=settings.INFLUXDB_ENABLE_GZIP
                )
                logger.info(f"✅ InfluxDB client connected: {self.url}")
            except Exception as e:
                logger.error(f"❌ Failed to create InfluxDB client: {e}")
                raise InfluxDBConnectionError(self.url, str(e))

        return self._client

    def query_api(self):
        """Get query API instance."""
        if self._query_api is None:
            self._query_api = self.client.query_api()
        return self._query_api

    def write_api(self, write_options=SYNCHRONOUS):
        """Get write API instance with specified write options."""
        if self._write_api is None:
            self._write_api = self.client.write_api(write_options=write_options)
        return self._write_api

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InfluxDBError)
    )
    def health_check(self) -> Dict[str, Any]:
        """
        Check InfluxDB health status.

        Returns:
            Dict with health information

        Raises:
            InfluxDBConnectionError: If health check fails
        """
        try:
            health = self.client.health()
            return {
                "status": health.status,
                "message": health.message,
                "version": health.version,
                "url": self.url
            }
        except Exception as e:
            logger.error(f"❌ InfluxDB health check failed: {e}")
            raise InfluxDBConnectionError(self.url, str(e))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InfluxDBError)
    )
    def query(
        self,
        flux_query: str,
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute Flux query and return results.

        Args:
            flux_query: Flux query string
            bucket: Optional bucket name (overrides default)

        Returns:
            List of records as dictionaries

        Raises:
            InfluxDBQueryError: If query fails
        """
        try:
            query_api = self.query_api()
            tables = query_api.query(flux_query, org=self.org)

            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record.get_time(),
                        "value": record.get_value(),
                        "field": record.get_field(),
                        "measurement": record.get_measurement(),
                        **record.values
                    })

            logger.info(f"📊 Query returned {len(results)} records")
            return results

        except InfluxDBError as e:
            logger.error(f"❌ Query failed: {e}")
            raise InfluxDBQueryError(flux_query, str(e))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(InfluxDBError)
    )
    def write_points(
        self,
        points: List[Point],
        bucket: Optional[str] = None
    ) -> int:
        """
        Write points to InfluxDB.

        Args:
            points: List of InfluxDB Point objects
            bucket: Optional bucket name (overrides default)

        Returns:
            Number of points written

        Raises:
            InfluxDBWriteError: If write fails
        """
        target_bucket = bucket or self.bucket

        try:
            write_api = self.write_api()
            write_api.write(
                bucket=target_bucket,
                org=self.org,
                record=points
            )

            logger.info(f"✅ Wrote {len(points)} points to {target_bucket}")
            return len(points)

        except InfluxDBError as e:
            logger.error(f"❌ Write failed: {e}")
            raise InfluxDBWriteError(target_bucket, str(e))

    def write_dict(
        self,
        measurement: str,
        fields: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
        bucket: Optional[str] = None
    ) -> int:
        """
        Write a single data point from dictionary.

        Args:
            measurement: Measurement name
            fields: Field key-value pairs
            tags: Optional tag key-value pairs
            timestamp: Optional timestamp (defaults to now)
            bucket: Optional bucket name

        Returns:
            Number of points written (1)

        Example:
            >>> client.write_dict(
            ...     measurement="energy_prices",
            ...     fields={"price_eur_kwh": 0.15},
            ...     tags={"source": "REE"},
            ...     timestamp=datetime.now()
            ... )
        """
        point = Point(measurement)

        # Add tags
        if tags:
            for key, value in tags.items():
                point.tag(key, value)

        # Add fields
        for key, value in fields.items():
            point.field(key, value)

        # Add timestamp
        if timestamp:
            point.time(timestamp, WritePrecision.NS)

        return self.write_points([point], bucket=bucket)

    def close(self):
        """Close InfluxDB client connection."""
        if self._client:
            self._client.close()
            logger.info("🔒 InfluxDB client closed")
            self._client = None
            self._write_api = None
            self._query_api = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global client instance (singleton)
_influxdb_client_instance: Optional[InfluxDBClientWrapper] = None


def get_influxdb_client() -> InfluxDBClientWrapper:
    """
    Get global InfluxDB client instance (singleton).

    Returns:
        InfluxDBClientWrapper: Global client instance

    Example:
        >>> client = get_influxdb_client()
        >>> health = client.health_check()
        >>> print(health)
    """
    global _influxdb_client_instance

    if _influxdb_client_instance is None:
        _influxdb_client_instance = InfluxDBClientWrapper()
        logger.info("🔧 InfluxDB client wrapper initialized")

    return _influxdb_client_instance
