"""
AEMET Service (Application Layer)
==================================

Orchestrates AEMET API client and InfluxDB for weather data.

Responsibilities:
- Fetch weather observations from AEMET stations
- Validate and transform meteorological data
- Persist to InfluxDB
- Query historical weather
- Detect data gaps

Usage:
    from services.aemet_service import AEMETService
    from dependencies import get_influxdb_client

    influx = get_influxdb_client()
    aemet_service = AEMETService(influx)

    await aemet_service.ingest_weather(station_id="3195")
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from influxdb_client import Point, WritePrecision

from infrastructure.influxdb import InfluxDBClientWrapper
from infrastructure.external_apis import AEMETAPIClient
from core.config import settings
from core.exceptions import (
    AEMETDataError,
    InfluxDBWriteError,
    WeatherDataError
)

logger = logging.getLogger(__name__)


class AEMETService:
    """
    AEMET weather data orchestration service.

    Handles the complete lifecycle of AEMET meteorological data:
    1. Fetch from AEMET API
    2. Transform and validate
    3. Persist to InfluxDB
    4. Query and analyze
    """

    MEASUREMENT = "weather"
    BUCKET = settings.INFLUXDB_BUCKET

    def __init__(self, influxdb_client: InfluxDBClientWrapper):
        """
        Initialize AEMET service.

        Args:
            influxdb_client: InfluxDB client instance
        """
        self.influxdb = influxdb_client

    async def ingest_weather(
        self,
        station_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest current weather observations from AEMET station.

        Args:
            station_id: Weather station ID (defaults to Madrid-Retiro: 3195)
            force_refresh: If True, overwrites recent data

        Returns:
            Ingestion result with metadata

        Raises:
            AEMETDataError: If ingestion fails

        Example:
            >>> result = await aemet_service.ingest_weather(station_id="3195")
            >>> print(f"Temperature: {result['latest_temperature']}°C")
        """
        station = station_id or settings.AEMET_DEFAULT_STATION

        logger.info(f"🌤️ Ingesting AEMET weather for station {station}")

        # Fetch from AEMET API
        try:
            async with AEMETAPIClient() as aemet_client:
                weather_records = await aemet_client.get_current_weather(station)

            if not weather_records:
                raise AEMETDataError(f"No weather data returned from AEMET for station {station}")

            logger.info(f"✅ Fetched {len(weather_records)} weather observations from AEMET")

        except Exception as e:
            logger.error(f"❌ Failed to fetch AEMET weather: {e}")
            raise AEMETDataError(f"Failed to fetch AEMET weather: {e}")

        # Transform to InfluxDB points
        points = self._transform_to_points(weather_records)

        # Write to InfluxDB
        try:
            records_written = self.influxdb.write_points(points, bucket=self.BUCKET)
            logger.info(f"✅ Wrote {records_written} AEMET weather records to InfluxDB")

        except Exception as e:
            logger.error(f"❌ Failed to write AEMET weather to InfluxDB: {e}")
            raise InfluxDBWriteError(self.MEASUREMENT, str(e))

        # Extract latest values
        latest = weather_records[-1] if weather_records else {}

        return {
            "station_id": station,
            "records_written": records_written,
            "latest_temperature": latest.get("temperature"),
            "latest_humidity": latest.get("humidity"),
            "latest_pressure": latest.get("pressure"),
            "timestamp": latest.get("timestamp"),
            "source": "aemet"
        }

    def _transform_to_points(self, weather_records: List[Dict[str, Any]]) -> List[Point]:
        """
        Transform AEMET weather data to InfluxDB points.

        Args:
            weather_records: List of weather dictionaries from AEMET API

        Returns:
            List of InfluxDB Point objects
        """
        points = []

        for record in weather_records:
            point = Point(self.MEASUREMENT) \
                .tag("source", record.get("source", "aemet")) \
                .tag("station_id", record.get("station_id", "unknown"))

            # Add fields (only if not None)
            if record.get("temperature") is not None:
                point.field("temperature", float(record["temperature"]))

            if record.get("humidity") is not None:
                point.field("humidity", float(record["humidity"]))

            if record.get("pressure") is not None:
                point.field("pressure", float(record["pressure"]))

            if record.get("wind_speed") is not None:
                point.field("wind_speed", float(record["wind_speed"]))

            if record.get("wind_direction") is not None:
                point.field("wind_direction", float(record["wind_direction"]))

            if record.get("precipitation") is not None:
                point.field("precipitation", float(record["precipitation"]))

            # Add timestamp
            point.time(record["timestamp"], WritePrecision.NS)

            points.append(point)

        return points

    async def get_weather(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        station_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical AEMET weather data from InfluxDB.

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date + 1 day)
            station_id: Optional station filter

        Returns:
            List of weather records

        Example:
            >>> weather = await aemet_service.get_weather(
            ...     start_date=date(2025, 10, 1),
            ...     station_id="3195"
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
  |> filter(fn: (r) => r["source"] == "aemet")
'''

        if station_id:
            flux_query += f'\n  |> filter(fn: (r) => r["station_id"] == "{station_id}")'

        flux_query += '\n  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

        try:
            results = self.influxdb.query(flux_query)

            weather_records = []
            for record in results:
                weather_records.append({
                    "timestamp": record.get("time"),
                    "station_id": record.get("station_id"),
                    "temperature": record.get("temperature"),
                    "humidity": record.get("humidity"),
                    "pressure": record.get("pressure"),
                    "wind_speed": record.get("wind_speed"),
                    "wind_direction": record.get("wind_direction"),
                    "precipitation": record.get("precipitation"),
                    "source": "aemet"
                })

            logger.info(f"📊 Retrieved {len(weather_records)} AEMET weather records from InfluxDB")
            return weather_records

        except Exception as e:
            logger.error(f"❌ Failed to query AEMET weather: {e}")
            raise

    async def get_latest_weather(
        self,
        station_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent weather observation.

        Args:
            station_id: Optional station filter

        Returns:
            Latest weather record or None if no data

        Example:
            >>> latest = await aemet_service.get_latest_weather(station_id="3195")
            >>> print(f"Temperature: {latest['temperature']}°C")
        """
        flux_query = f'''
from(bucket: "{self.BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "{self.MEASUREMENT}")
  |> filter(fn: (r) => r["source"] == "aemet")
'''

        if station_id:
            flux_query += f'\n  |> filter(fn: (r) => r["station_id"] == "{station_id}")'

        flux_query += '''
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
'''

        try:
            results = self.influxdb.query(flux_query)

            if results:
                record = results[0]
                return {
                    "timestamp": record.get("time"),
                    "station_id": record.get("station_id"),
                    "temperature": record.get("temperature"),
                    "humidity": record.get("humidity"),
                    "pressure": record.get("pressure"),
                    "wind_speed": record.get("wind_speed"),
                    "wind_direction": record.get("wind_direction"),
                    "precipitation": record.get("precipitation"),
                    "source": "aemet"
                }

            return None

        except Exception as e:
            logger.error(f"❌ Failed to get latest AEMET weather: {e}")
            return None

    async def get_weather_stats(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        station_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get weather statistics for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)
            station_id: Optional station filter

        Returns:
            Dictionary with temperature, humidity, pressure stats

        Example:
            >>> stats = await aemet_service.get_weather_stats(date(2025, 10, 1))
            >>> print(f"Average temperature: {stats['temperature']['avg']:.1f}°C")
        """
        if end_date is None:
            end_date = date.today()

        weather = await self.get_weather(start_date, end_date, station_id)

        if not weather:
            return {
                "count": 0,
                "temperature": None,
                "humidity": None,
                "pressure": None
            }

        # Calculate temperature stats
        temps = [w["temperature"] for w in weather if w.get("temperature") is not None]
        humid = [w["humidity"] for w in weather if w.get("humidity") is not None]
        press = [w["pressure"] for w in weather if w.get("pressure") is not None]

        stats = {
            "count": len(weather),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

        if temps:
            stats["temperature"] = {
                "min": min(temps),
                "max": max(temps),
                "avg": sum(temps) / len(temps)
            }

        if humid:
            stats["humidity"] = {
                "min": min(humid),
                "max": max(humid),
                "avg": sum(humid) / len(humid)
            }

        if press:
            stats["pressure"] = {
                "min": min(press),
                "max": max(press),
                "avg": sum(press) / len(press)
            }

        return stats

    async def detect_gaps(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        station_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect gaps in AEMET weather data.

        Args:
            start_date: Start date to check
            end_date: End date to check (defaults to today)
            station_id: Optional station filter

        Returns:
            List of detected gaps

        Example:
            >>> gaps = await aemet_service.detect_gaps(date(2025, 10, 1))
            >>> print(f"Found {len(gaps)} gaps")
        """
        if end_date is None:
            end_date = date.today()

        weather = await self.get_weather(start_date, end_date, station_id)

        if not weather:
            start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            return [{
                "start": start_dt,
                "end": end_dt,
                "hours": (end_dt - start_dt).total_seconds() / 3600,
                "type": "complete_gap"
            }]

        # Detect gaps (AEMET provides observations irregularly, check for >6h gaps)
        gaps = []
        for i in range(len(weather) - 1):
            current_time = weather[i]["timestamp"]
            next_time = weather[i + 1]["timestamp"]

            gap_hours = (next_time - current_time).total_seconds() / 3600
            if gap_hours > 6:  # More than 6 hours
                gaps.append({
                    "start": current_time,
                    "end": next_time,
                    "hours": gap_hours,
                    "type": "data_gap"
                })

        logger.info(f"📊 Detected {len(gaps)} gaps in AEMET data")
        return gaps
