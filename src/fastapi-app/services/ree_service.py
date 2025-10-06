"""
REE Service (Application Layer)
================================

Orchestrates REE API client and InfluxDB for electricity price data.

Responsibilities:
- Fetch prices from REE API (via infrastructure layer)
- Validate and transform data
- Persist to InfluxDB
- Query historical prices
- Detect data gaps

Usage:
    from services.ree_service import REEService
    from dependencies import get_influxdb_client

    influx = get_influxdb_client()
    ree_service = REEService(influx)

    await ree_service.ingest_prices(date(2025, 10, 6))
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from influxdb_client import Point, WritePrecision

from infrastructure.influxdb import InfluxDBClientWrapper
from infrastructure.external_apis import REEAPIClient
from core.config import settings
from core.exceptions import (
    REEDataError,
    InfluxDBWriteError,
    DataGapError
)

logger = logging.getLogger(__name__)


class REEService:
    """
    REE data orchestration service.

    Handles the complete lifecycle of REE electricity price data:
    1. Fetch from REE API
    2. Transform and validate
    3. Persist to InfluxDB
    4. Query and analyze
    """

    MEASUREMENT = "energy_prices"
    BUCKET = settings.INFLUXDB_BUCKET

    def __init__(self, influxdb_client: InfluxDBClientWrapper):
        """
        Initialize REE service.

        Args:
            influxdb_client: InfluxDB client instance
        """
        self.influxdb = influxdb_client

    async def ingest_prices(
        self,
        target_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest REE electricity prices for a specific date.

        Args:
            target_date: Date to ingest (defaults to today)
            force_refresh: If True, overwrites existing data

        Returns:
            Ingestion result with metadata

        Raises:
            REEDataError: If ingestion fails

        Example:
            >>> result = await ree_service.ingest_prices(date(2025, 10, 6))
            >>> print(f"Ingested {result['records_written']} prices")
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"📊 Ingesting REE prices for {target_date}")

        # Check if data already exists
        if not force_refresh:
            existing = await self._check_existing_data(target_date)
            if existing:
                logger.info(f"⚠️ Data for {target_date} already exists (use force_refresh=True to overwrite)")
                return {
                    "date": target_date.isoformat(),
                    "records_written": 0,
                    "already_exists": True,
                    "message": "Data already exists"
                }

        # Fetch from REE API
        try:
            async with REEAPIClient() as ree_client:
                prices = await ree_client.get_pvpc_prices(target_date)

            if not prices:
                raise REEDataError(f"No prices returned from REE API for {target_date}")

            logger.info(f"✅ Fetched {len(prices)} prices from REE API")

        except Exception as e:
            logger.error(f"❌ Failed to fetch REE prices: {e}")
            raise REEDataError(f"Failed to fetch REE prices: {e}")

        # Transform to InfluxDB points
        points = self._transform_to_points(prices)

        # Write to InfluxDB
        try:
            records_written = self.influxdb.write_points(points, bucket=self.BUCKET)
            logger.info(f"✅ Wrote {records_written} REE prices to InfluxDB")

        except Exception as e:
            logger.error(f"❌ Failed to write REE prices to InfluxDB: {e}")
            raise InfluxDBWriteError(self.MEASUREMENT, str(e))

        return {
            "date": target_date.isoformat(),
            "records_written": records_written,
            "price_range": {
                "min": min(p["price_eur_kwh"] for p in prices),
                "max": max(p["price_eur_kwh"] for p in prices),
                "avg": sum(p["price_eur_kwh"] for p in prices) / len(prices)
            },
            "source": "ree_pvpc"
        }

    def _transform_to_points(self, prices: List[Dict[str, Any]]) -> List[Point]:
        """
        Transform REE price data to InfluxDB points.

        Args:
            prices: List of price dictionaries from REE API

        Returns:
            List of InfluxDB Point objects
        """
        points = []

        for price_data in prices:
            point = Point(self.MEASUREMENT) \
                .tag("source", price_data.get("source", "ree_pvpc")) \
                .field("price_eur_kwh", float(price_data["price_eur_kwh"])) \
                .field("price_eur_mwh", float(price_data["price_eur_mwh"])) \
                .time(price_data["timestamp"], WritePrecision.NS)

            points.append(point)

        return points

    async def _check_existing_data(self, target_date: date) -> bool:
        """
        Check if data already exists for a given date.

        Args:
            target_date: Date to check

        Returns:
            True if data exists, False otherwise
        """
        start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        flux_query = f'''
from(bucket: "{self.BUCKET}")
  |> range(start: {start_dt.isoformat()}, stop: {end_dt.isoformat()})
  |> filter(fn: (r) => r["_measurement"] == "{self.MEASUREMENT}")
  |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
  |> count()
'''

        try:
            results = self.influxdb.query(flux_query)
            return len(results) > 0
        except Exception as e:
            logger.warning(f"⚠️ Failed to check existing data: {e}")
            return False

    async def get_prices(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical REE prices from InfluxDB.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date + 1 day)
            limit: Maximum number of records to return

        Returns:
            List of price records

        Example:
            >>> prices = await ree_service.get_prices(
            ...     start_date=date(2025, 10, 1),
            ...     end_date=date(2025, 10, 7)
            ... )
        """
        if end_date is None:
            end_date = start_date + timedelta(days=1)

        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)

        flux_query = f'''
from(bucket: "{self.BUCKET}")
  |> range(start: {start_dt.isoformat()}, stop: {end_dt.isoformat()})
  |> filter(fn: (r) => r["_measurement"] == "{self.MEASUREMENT}")
  |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
  |> sort(columns: ["_time"], desc: false)
'''

        if limit:
            flux_query += f'\n  |> limit(n: {limit})'

        try:
            results = self.influxdb.query(flux_query)

            prices = [
                {
                    "timestamp": record["time"],
                    "price_eur_kwh": record["value"],
                    "source": record.get("source", "unknown")
                }
                for record in results
            ]

            logger.info(f"📊 Retrieved {len(prices)} REE prices from InfluxDB")
            return prices

        except Exception as e:
            logger.error(f"❌ Failed to query REE prices: {e}")
            raise

    async def get_latest_price(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent electricity price.

        Returns:
            Latest price record or None if no data

        Example:
            >>> latest = await ree_service.get_latest_price()
            >>> print(f"Current price: {latest['price_eur_kwh']} €/kWh")
        """
        flux_query = f'''
from(bucket: "{self.BUCKET}")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "{self.MEASUREMENT}")
  |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
'''

        try:
            results = self.influxdb.query(flux_query)

            if results:
                record = results[0]
                return {
                    "timestamp": record["time"],
                    "price_eur_kwh": record["value"],
                    "source": record.get("source", "unknown")
                }

            return None

        except Exception as e:
            logger.error(f"❌ Failed to get latest price: {e}")
            return None

    async def get_price_stats(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get price statistics for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            Dictionary with min, max, avg, median prices

        Example:
            >>> stats = await ree_service.get_price_stats(date(2025, 10, 1))
            >>> print(f"Average price: {stats['avg']:.4f} €/kWh")
        """
        if end_date is None:
            end_date = date.today()

        prices = await self.get_prices(start_date, end_date)

        if not prices:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "median": None
            }

        price_values = [p["price_eur_kwh"] for p in prices]
        sorted_prices = sorted(price_values)

        return {
            "count": len(price_values),
            "min": min(price_values),
            "max": max(price_values),
            "avg": sum(price_values) / len(price_values),
            "median": sorted_prices[len(sorted_prices) // 2],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    async def detect_gaps(
        self,
        start_date: date,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in REE price data.

        Args:
            start_date: Start date to check
            end_date: End date to check (defaults to today)

        Returns:
            List of detected gaps with start/end times

        Example:
            >>> gaps = await ree_service.detect_gaps(date(2025, 10, 1))
            >>> for gap in gaps:
            ...     print(f"Gap: {gap['start']} to {gap['end']}")
        """
        if end_date is None:
            end_date = date.today()

        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)

        # Get all timestamps
        prices = await self.get_prices(start_date, end_date)

        if not prices:
            return [{
                "start": start_dt,
                "end": end_dt,
                "hours": (end_dt - start_dt).total_seconds() / 3600,
                "type": "complete_gap"
            }]

        # Detect gaps (prices should be hourly)
        gaps = []
        for i in range(len(prices) - 1):
            current_time = prices[i]["timestamp"]
            next_time = prices[i + 1]["timestamp"]

            expected_next = current_time + timedelta(hours=1)
            if next_time > expected_next:
                gap_hours = (next_time - expected_next).total_seconds() / 3600
                gaps.append({
                    "start": expected_next,
                    "end": next_time,
                    "hours": gap_hours,
                    "type": "data_gap"
                })

        logger.info(f"📊 Detected {len(gaps)} gaps in REE data")
        return gaps
