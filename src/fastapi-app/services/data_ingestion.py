"""
Data Ingestion Service for TFM Chocolate Factory
==============================================

Service for ingesting external data (REE, AEMET) into InfluxDB following
the defined schemas and data quality standards.

Handles:
- REE electricity price data ingestion
- Data validation and transformation
- InfluxDB batch writing with error handling
- Automatic retry and recovery mechanisms
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pydantic import BaseModel, Field
from loguru import logger
import os

from infrastructure.external_apis import REEAPIClient, AEMETAPIClient, OpenWeatherMapAPIClient  # Sprint 15
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# For backward compatibility with old code that uses these names
REEClient = REEAPIClient
AEMETClient = AEMETAPIClient
OpenWeatherMapClient = OpenWeatherMapAPIClient

# Import data models from infrastructure
try:
    from infrastructure.external_apis.ree_client import REEPriceData, REEDemandData
    from infrastructure.external_apis.aemet_client import AEMETWeatherData
except ImportError:
    # Fallback: define minimal data classes if imports fail
    from dataclasses import dataclass
    @dataclass
    class REEPriceData:
        pass
    @dataclass
    class REEDemandData:
        pass
    @dataclass
    class AEMETWeatherData:
        pass
from configs.influxdb_schemas import (
    EnergyPricesSchema, WeatherDataSchema, get_tariff_period,
    calculate_heat_index, calculate_chocolate_production_index, get_season_from_date
)


class InfluxDBConfig(BaseModel):
    """Configuration for InfluxDB connection"""
    url: str = Field(default_factory=lambda: os.getenv("INFLUXDB_URL", "http://localhost:8086"))
    token: str = Field(default_factory=lambda: os.getenv("INFLUXDB_TOKEN", ""))
    org: str = Field(default_factory=lambda: os.getenv("INFLUXDB_ORG", "chocolate-factory"))
    bucket: str = Field(default_factory=lambda: os.getenv("INFLUXDB_BUCKET", "energy-data"))
    timeout: int = 30000  # ms


class DataIngestionStats(BaseModel):
    """Statistics for data ingestion operations"""
    total_records: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    validation_errors: int = 0
    duplicate_records: int = 0
    processing_time_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.successful_writes / self.total_records) * 100


class DataIngestionService:
    """
    Service for ingesting external energy data into InfluxDB
    
    Provides methods for:
    - REE electricity price data ingestion
    - Data validation and transformation
    - Batch writing to InfluxDB
    - Error handling and recovery
    """
    
    def __init__(self, influx_config: Optional[InfluxDBConfig] = None):
        self.config = influx_config or InfluxDBConfig()
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        
        if not all([self.config.url, self.config.token, self.config.org, self.config.bucket]):
            logger.warning("InfluxDB configuration incomplete. Check environment variables.")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = InfluxDBClient(
            url=self.config.url,
            token=self.config.token,
            org=self.config.org,
            timeout=self.config.timeout
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
        # Test connection
        try:
            health = self.client.health()
            logger.info(f"InfluxDB connection established: {health.status}")
        except Exception as e:
            logger.error(f"InfluxDB connection failed: {e}")
            raise
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.write_api:
            self.write_api.close()
        if self.client:
            self.client.close()
    
    def _determine_season(self, timestamp: datetime) -> str:
        """Determine season based on timestamp"""
        month = timestamp.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _determine_day_type(self, timestamp: datetime) -> str:
        """Determine day type (weekday/weekend/holiday)"""
        # TODO: Integrate with Spanish holidays calendar
        if timestamp.weekday() >= 5:  # Saturday=5, Sunday=6
            return "weekend"
        else:
            return "weekday"
    
    def _transform_ree_price_to_influx_point(self, price_data: REEPriceData) -> Point:
        """Transform REE price data to InfluxDB point"""
        
        # Calculate derived values
        price_eur_kwh = price_data.price_eur_mwh / 1000
        tariff_period = get_tariff_period(
            price_data.timestamp.hour, 
            price_data.timestamp.weekday() >= 5
        )
        
        # Create tags
        tags = {
            "market_type": price_data.market_type,
            "tariff_period": tariff_period,
            "day_type": self._determine_day_type(price_data.timestamp),
            "season": self._determine_season(price_data.timestamp),
            "provider": price_data.provider
        }
        
        # Create fields
        fields = {
            "price_eur_mwh": price_data.price_eur_mwh,
            "price_eur_kwh": price_eur_kwh,
            "energy_cost": price_eur_kwh,  # Base cost without fees
            # Note: Grid fees and system charges would be added from tariff data
            "grid_fees": 0.0,  # Placeholder - would come from tariff configuration
            "system_charges": 0.0,  # Placeholder - would come from tariff configuration
        }
        
        # Create InfluxDB point
        point = Point("energy_prices")
        point.time(price_data.timestamp, WritePrecision.S)
        
        # Add tags
        for tag_key, tag_value in tags.items():
            point.tag(tag_key, tag_value)
        
        # Add fields
        for field_key, field_value in fields.items():
            point.field(field_key, field_value)
        
        return point
    
    def _validate_price_data(self, price_data: REEPriceData) -> Tuple[bool, List[str]]:
        """Validate REE price data for quality and reasonableness"""
        errors = []
        
        # Price range validation (reasonable limits for Spanish market)
        if price_data.price_eur_mwh < -100 or price_data.price_eur_mwh > 500:
            errors.append(f"Price out of reasonable range: {price_data.price_eur_mwh} €/MWh")
        
        # Timestamp validation
        now = datetime.now(timezone.utc)
        if price_data.timestamp > now + timedelta(days=1):
            errors.append(f"Future timestamp beyond reasonable forecast: {price_data.timestamp}")
        
        # Data completeness
        if price_data.price_eur_mwh is None:
            errors.append("Missing price value")
        
        return len(errors) == 0, errors
    
    async def ingest_ree_prices(self, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> DataIngestionStats:
        """
        Ingest REE electricity price data into InfluxDB
        
        Args:
            start_date: Start date for data ingestion
            end_date: End date for data ingestion
            
        Returns:
            DataIngestionStats with ingestion results
        """
        if not self.client or not self.write_api:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        start_time = datetime.now()
        stats = DataIngestionStats()
        
        try:
            range_info = f"{start_date.strftime('%Y-%m-%d %H:%M') if start_date else 'auto'} to {end_date.strftime('%Y-%m-%d %H:%M') if end_date else 'auto'}"
            logger.info(f"📊 REE Ingestion Start: {range_info}")

            # Fetch data from REE API
            async with REEClient() as ree_client:
                price_data = await ree_client.get_pvpc_prices(start_date, end_date)

            stats.total_records = len(price_data)

            if price_data:
                earliest = min(p.timestamp for p in price_data)
                latest = max(p.timestamp for p in price_data)
                logger.success(f"✅ REE Data Retrieved: {stats.total_records} records ({earliest.strftime('%Y-%m-%d %H:%M')} to {latest.strftime('%Y-%m-%d %H:%M')})")
            else:
                logger.error(f"❌ REE Data Empty: No price data retrieved from REE API for {range_info}")
                return stats
            
            # Transform and validate data
            logger.info(f"🔄 REE Processing: Transforming {stats.total_records} records to InfluxDB points")
            valid_points = []
            validation_errors_detail = []

            for price_record in price_data:
                is_valid, validation_errors = self._validate_price_data(price_record)

                if not is_valid:
                    stats.validation_errors += 1
                    error_detail = f"{price_record.timestamp}: {validation_errors}"
                    validation_errors_detail.append(error_detail)
                    logger.warning(f"⚠️ REE Validation Failed: {error_detail}")
                    continue

                try:
                    point = self._transform_ree_price_to_influx_point(price_record)
                    valid_points.append(point)
                except Exception as e:
                    logger.error(f"❌ REE Transform Error: Failed to transform {price_record.timestamp}: {e}")
                    stats.failed_writes += 1

            if validation_errors_detail:
                logger.warning(f"⚠️ REE Validation Summary: {len(validation_errors_detail)} records failed validation")

            logger.info(f"✅ REE Transform Complete: {len(valid_points)} valid points ready for InfluxDB")
            
            # Batch write to InfluxDB
            if valid_points:
                try:
                    logger.info(f"📥 REE InfluxDB Write: Starting batch write of {len(valid_points)} points")
                    logger.debug(f"🔧 InfluxDB Config: bucket={self.config.bucket}, org={self.config.org}")

                    self.write_api.write(
                        bucket=self.config.bucket,
                        org=self.config.org,
                        record=valid_points
                    )

                    stats.successful_writes = len(valid_points)

                    # Log success with data range info
                    if valid_points:
                        first_point_time = valid_points[0].time
                        last_point_time = valid_points[-1].time
                        logger.success(f"✅ REE InfluxDB Success: Wrote {stats.successful_writes} records")
                        logger.info(f"📈 REE Data Written: From {first_point_time} to {last_point_time}")

                except Exception as e:
                    logger.error(f"❌ REE InfluxDB Error: Failed to write {len(valid_points)} points: {e}")
                    logger.error(f"🔍 InfluxDB Error Details: Type={type(e).__name__}, Message={str(e)}")

                    # Log first few points for debugging
                    if valid_points:
                        logger.debug(f"🔍 Sample Point Debug: {valid_points[0]}")

                    stats.failed_writes = len(valid_points)
                    raise
            else:
                logger.warning("⚠️ REE Write Skipped: No valid points to write to InfluxDB")
            
        except Exception as e:
            logger.error(f"❌ REE Ingestion Failed: {e}")
            logger.error(f"🔍 REE Failure Details: Type={type(e).__name__}, Message={str(e)}")
            raise

        finally:
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()

            # Enhanced completion logging with alarm thresholds
            if stats.success_rate >= 90:
                logger.success(f"✅ REE Ingestion Complete: {stats.processing_time_seconds:.2f}s - Success rate: {stats.success_rate:.1f}%")
            elif stats.success_rate >= 50:
                logger.warning(f"⚠️ REE Ingestion Partial: {stats.processing_time_seconds:.2f}s - Success rate: {stats.success_rate:.1f}% (Below 90% threshold)")
            else:
                logger.error(f"🚨 REE Ingestion Critical: {stats.processing_time_seconds:.2f}s - Success rate: {stats.success_rate:.1f}% (ALARM: Below 50%)")

            # Detailed stats for monitoring
            logger.info(f"📊 REE Stats: Total={stats.total_records}, Success={stats.successful_writes}, Failed={stats.failed_writes}, ValidationErrors={stats.validation_errors}")

        return stats
    
    async def ingest_current_prices(self) -> DataIngestionStats:
        """Ingest current hour price data"""
        now = datetime.now(timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        next_hour = current_hour + timedelta(hours=1)
        
        return await self.ingest_ree_prices(current_hour, next_hour)
    
    async def ingest_daily_prices(self, target_date: Optional[datetime] = None) -> DataIngestionStats:
        """Ingest full day price data"""
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        
        start_date = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        return await self.ingest_ree_prices(start_date, end_date)
    
    async def backfill_historical_data(self, days_back: int = 7) -> DataIngestionStats:
        """
        Backfill historical price data
        
        Args:
            days_back: Number of days to backfill from today
            
        Returns:
            Aggregated statistics for all backfilled data
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Starting historical data backfill: {days_back} days")
        
        total_stats = DataIngestionStats()
        
        # Process data day by day to avoid overwhelming the APIs
        current_date = start_date
        while current_date < end_date:
            try:
                next_date = current_date + timedelta(days=1)
                daily_stats = await self.ingest_ree_prices(current_date, next_date)
                
                # Aggregate statistics
                total_stats.total_records += daily_stats.total_records
                total_stats.successful_writes += daily_stats.successful_writes
                total_stats.failed_writes += daily_stats.failed_writes
                total_stats.validation_errors += daily_stats.validation_errors
                total_stats.processing_time_seconds += daily_stats.processing_time_seconds
                
                logger.info(f"Completed backfill for {current_date.date()}: "
                           f"{daily_stats.successful_writes} records")
                
                # Rate limiting between days
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to backfill data for {current_date.date()}: {e}")
                # Continue with next day
            
            current_date = next_date
        
        logger.info(f"Historical backfill completed: {total_stats.successful_writes} total records")
        return total_stats
    
    async def ingest_ree_prices_historical(self, prices: List) -> DataIngestionStats:
        """
        Ingest historical REE price data (for initialization)
        
        Args:
            prices: List of REEPriceData objects from historical API calls
            
        Returns:
            DataIngestionStats for the ingestion operation
        """
        start_time = datetime.now()
        stats = DataIngestionStats()
        stats.total_records = len(prices)
        
        if not prices:
            logger.warning("No historical price data provided")
            return stats
        
        try:
            logger.info(f"📊 Processing {len(prices)} historical REE price records")
            
            # Transform to InfluxDB points
            valid_points = []
            for price_data in prices:
                try:
                    # Convert EUR/MWh to EUR/kWh for consistency
                    price_eur_kwh = price_data.price_eur_mwh / 1000.0
                    
                    # Basic validation
                    if not (0.001 <= price_eur_kwh <= 1.0):  # Reasonable price range
                        logger.warning(f"Price out of range: {price_eur_kwh} EUR/kWh at {price_data.timestamp}")
                        stats.validation_errors += 1
                        continue
                    
                    # Create InfluxDB point with historical tag
                    point = Point("energy_prices") \
                        .tag("source", "REE") \
                        .tag("market_type", price_data.market_type) \
                        .tag("data_source", "ree_historical") \
                        .tag("season", get_season_from_date(price_data.timestamp)) \
                        .field("price_eur_kwh", price_eur_kwh) \
                        .field("price_eur_mwh", price_data.price_eur_mwh) \
                        .time(price_data.timestamp)
                    
                    valid_points.append(point)
                    
                except Exception as e:
                    logger.warning(f"Failed to process price record {price_data.timestamp}: {e}")
                    stats.validation_errors += 1
            
            # Batch write to InfluxDB
            if valid_points:
                try:
                    logger.info(f"📥 Writing {len(valid_points)} historical points to InfluxDB")
                    self.write_api.write(
                        bucket=self.config.bucket,
                        org=self.config.org,
                        record=valid_points
                    )
                    stats.successful_writes = len(valid_points)
                    logger.info(f"✅ Successfully wrote {stats.successful_writes} historical price records")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to write historical data to InfluxDB: {e}")
                    stats.failed_writes = len(valid_points)
                    raise
            else:
                logger.warning("No valid historical price points to write")
            
        except Exception as e:
            logger.error(f"❌ Historical REE price ingestion failed: {e}")
            raise
        
        finally:
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()
            logger.info(f"Historical ingestion completed in {stats.processing_time_seconds:.2f}s - "
                       f"Success rate: {stats.success_rate:.1f}%")
        
        return stats
    
    def _transform_aemet_weather_to_influx_point(self, weather_data: Dict[str, Any]) -> Point:
        """Transform AEMET weather data (dict) to InfluxDB point"""

        # Create tags
        tags = {
            "station_id": weather_data.get("station_id", "unknown"),
            "data_source": weather_data.get("source", "aemet"),
            "data_type": "current",
            "season": get_season_from_date(weather_data.get("timestamp"))
        }

        # Add optional tags if available
        if weather_data.get("station_name"):
            tags["station_name"] = weather_data["station_name"]
        if weather_data.get("province"):
            tags["province"] = weather_data["province"]

        # Create fields with available data
        fields = {}

        # Temperature fields
        if weather_data.get("temperature") is not None:
            fields["temperature"] = weather_data["temperature"]
        if weather_data.get("temp_max") is not None:
            fields["temperature_max"] = weather_data["temp_max"]
        if weather_data.get("temp_min") is not None:
            fields["temperature_min"] = weather_data["temp_min"]

        # Humidity fields
        if weather_data.get("humidity") is not None:
            fields["humidity"] = weather_data["humidity"]
        if weather_data.get("humidity_max") is not None:
            fields["humidity_max"] = weather_data["humidity_max"]
        if weather_data.get("humidity_min") is not None:
            fields["humidity_min"] = weather_data["humidity_min"]

        # Pressure fields
        if weather_data.get("pressure") is not None:
            fields["pressure"] = weather_data["pressure"]
        if weather_data.get("pressure_max") is not None:
            fields["pressure_max"] = weather_data["pressure_max"]
        if weather_data.get("pressure_min") is not None:
            fields["pressure_min"] = weather_data["pressure_min"]

        # Wind fields
        if weather_data.get("wind_speed") is not None:
            fields["wind_speed"] = weather_data["wind_speed"]
        if weather_data.get("wind_direction") is not None:
            fields["wind_direction"] = weather_data["wind_direction"]
        if weather_data.get("wind_gust") is not None:
            fields["wind_gust"] = weather_data["wind_gust"]

        # Other meteorological fields
        if weather_data.get("precipitation") is not None:
            fields["precipitation"] = weather_data["precipitation"]
        if weather_data.get("solar_radiation") is not None:
            fields["solar_radiation"] = weather_data["solar_radiation"]
        if weather_data.get("altitude") is not None:
            fields["altitude"] = weather_data["altitude"]

        # Calculate derived fields for chocolate production
        temp = weather_data.get("temperature")
        hum = weather_data.get("humidity")
        pres = weather_data.get("pressure")

        if temp is not None and hum is not None:
            fields["heat_index"] = calculate_heat_index(temp, hum)
            fields["chocolate_production_index"] = calculate_chocolate_production_index(
                temp, hum, pres
            )

        # Create InfluxDB point
        point = Point("weather_data")
        point.time(weather_data["timestamp"], WritePrecision.S)
        
        # Add tags
        for tag_key, tag_value in tags.items():
            point.tag(tag_key, tag_value)
        
        # Add fields
        for field_key, field_value in fields.items():
            point.field(field_key, field_value)
        
        return point
    
    def _validate_weather_data(self, weather_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate AEMET weather data (dict) for quality and reasonableness"""
        errors = []

        # Temperature range validation (reasonable limits for Spain)
        temp = weather_data.get("temperature")
        if temp is not None:
            if temp < -20 or temp > 50:
                errors.append(f"Temperature out of reasonable range: {temp}°C")

        # Humidity validation
        hum = weather_data.get("humidity")
        if hum is not None:
            if not (0 <= hum <= 100):
                errors.append(f"Humidity out of range: {hum}%")

        # Pressure validation
        pres = weather_data.get("pressure")
        if pres is not None:
            if pres < 900 or pres > 1100:
                errors.append(f"Pressure out of reasonable range: {pres} hPa")

        # Wind speed validation
        wind = weather_data.get("wind_speed")
        if wind is not None:
            if wind < 0 or wind > 200:
                errors.append(f"Wind speed out of range: {wind} km/h")

        # Data completeness check
        station_id = weather_data.get("station_id")
        if not station_id or station_id == "":
            errors.append("Missing station ID")

        # Timestamp validation
        timestamp = weather_data.get("timestamp")
        if timestamp:
            now = datetime.now(timezone.utc)
            if timestamp > now + timedelta(hours=1):
                errors.append(f"Future timestamp beyond reasonable range: {timestamp}")

        return len(errors) == 0, errors
    
    async def ingest_aemet_weather(self, 
                                  station_ids: Optional[List[str]] = None,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> DataIngestionStats:
        """
        Ingest AEMET weather data into InfluxDB
        
        Args:
            station_ids: List of weather station IDs (defaults to Madrid area stations)
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            DataIngestionStats with ingestion results
        """
        if not self.client or not self.write_api:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        start_time = datetime.now()
        stats = DataIngestionStats()
        
        # Default to Jaén area stations if none specified (focused on Linares)
        if station_ids is None:
            station_ids = [
                "5279X",  # Linares, VOR - Jaén
                "5298X",  # Andújar - Jaén (backup)
            ]
        
        try:
            logger.info(f"Starting AEMET weather data ingestion for {len(station_ids)} stations")
            
            # Fetch data from AEMET API
            async with AEMETClient() as aemet_client:
                weather_data = []
                
                if start_date and end_date:
                    # Fetch historical daily data
                    for station_id in station_ids:
                        try:
                            station_data = await aemet_client.get_daily_weather(
                                start_date, end_date, station_id
                            )
                            weather_data.extend(station_data)
                        except Exception as e:
                            logger.warning(f"Failed to fetch data for station {station_id}: {e}")
                            stats.failed_writes += 1
                else:
                    # Fetch current weather data
                    for station_id in station_ids:
                        try:
                            current_weather = await aemet_client.get_current_weather(station_id)
                            if current_weather:
                                # get_current_weather returns a list, use extend not append
                                weather_data.extend(current_weather)
                        except Exception as e:
                            logger.warning(f"Failed to fetch current weather for station {station_id}: {e}")
                            stats.failed_writes += 1
            
            stats.total_records = len(weather_data)
            logger.info(f"Retrieved {stats.total_records} weather records from AEMET API")
            
            if not weather_data:
                logger.warning("No weather data retrieved from AEMET API")
                return stats
            
            # Transform and validate data
            valid_points = []
            for weather_record in weather_data:
                is_valid, validation_errors = self._validate_weather_data(weather_record)

                if not is_valid:
                    stats.validation_errors += 1
                    station_id = weather_record.get('station_id', 'unknown')
                    timestamp = weather_record.get('timestamp', 'unknown')
                    logger.warning(f"Validation failed for {station_id} at {timestamp}: {validation_errors}")
                    continue

                try:
                    point = self._transform_aemet_weather_to_influx_point(weather_record)
                    valid_points.append(point)
                except Exception as e:
                    logger.error(f"Failed to transform weather data: {e}")
                    stats.failed_writes += 1
            
            # Batch write to InfluxDB
            if valid_points:
                try:
                    logger.info(f"Writing {len(valid_points)} weather points to InfluxDB")
                    self.write_api.write(
                        bucket=self.config.bucket,
                        org=self.config.org,
                        record=valid_points
                    )
                    stats.successful_writes = len(valid_points)
                    logger.info(f"Successfully wrote {stats.successful_writes} weather records to InfluxDB")
                    
                except Exception as e:
                    logger.error(f"Failed to write weather data to InfluxDB: {e}")
                    stats.failed_writes = len(valid_points)
                    raise
            
        except Exception as e:
            logger.error(f"AEMET weather ingestion failed: {e}")
            raise
        
        finally:
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()
            logger.info(f"AEMET ingestion completed in {stats.processing_time_seconds:.2f}s - "
                       f"Success rate: {stats.success_rate:.1f}%")
        
        return stats
    
    async def ingest_openweathermap_weather(self) -> DataIngestionStats:
        """
        Ingest OpenWeatherMap weather data into InfluxDB
        
        Returns:
            DataIngestionStats with ingestion results
        """
        if not self.client or not self.write_api:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        start_time = datetime.now()
        stats = DataIngestionStats()
        
        try:
            logger.info("Starting OpenWeatherMap weather data ingestion")
            
            # Fetch data from OpenWeatherMap API
            async with OpenWeatherMapClient() as owm_client:
                current_weather = await owm_client.get_current_weather()
            
            if current_weather:
                stats.total_records = 1
                logger.info("Retrieved current weather from OpenWeatherMap")
                
                # Validate data
                is_valid, validation_errors = self._validate_weather_data(current_weather)
                
                if not is_valid:
                    stats.validation_errors += 1
                    logger.warning(f"OpenWeatherMap validation failed: {validation_errors}")
                    return stats
                
                try:
                    # Transform to InfluxDB point with OpenWeatherMap-specific tags
                    point = self._transform_aemet_weather_to_influx_point(current_weather)
                    
                    # Update tags to indicate OpenWeatherMap source
                    point = point.tag("data_source", "openweathermap")
                    point = point.tag("data_type", "current_realtime")
                    
                    # Write to InfluxDB
                    logger.info("Writing OpenWeatherMap data to InfluxDB")
                    self.write_api.write(
                        bucket=self.config.bucket,
                        org=self.config.org,
                        record=[point]
                    )
                    stats.successful_writes = 1
                    logger.info("Successfully wrote OpenWeatherMap weather record to InfluxDB")
                    
                except Exception as e:
                    logger.error(f"Failed to write OpenWeatherMap data to InfluxDB: {e}")
                    stats.failed_writes = 1
                    raise
            else:
                logger.warning("No weather data retrieved from OpenWeatherMap")
                
        except Exception as e:
            logger.error(f"OpenWeatherMap weather ingestion failed: {e}")
            raise
        
        finally:
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()
            logger.info(f"OpenWeatherMap ingestion completed in {stats.processing_time_seconds:.2f}s - "
                       f"Success rate: {stats.success_rate:.1f}%")
        
        return stats
    
    async def ingest_hybrid_weather(self, 
                                   force_openweathermap: bool = False,
                                   station_ids: Optional[List[str]] = None) -> DataIngestionStats:
        """
        Hybrid weather ingestion strategy:
        - Hours 00:00-07:00: Use AEMET (official observations)
        - Hours 08:00-23:00: Use OpenWeatherMap (real-time data)
        - Can force OpenWeatherMap for testing
        
        Args:
            force_openweathermap: Force use of OpenWeatherMap regardless of time
            station_ids: List of AEMET station IDs for fallback
            
        Returns:
            DataIngestionStats with combined results
        """
        current_hour = datetime.now(timezone.utc).hour
        
        # Determine data source based on hybrid strategy
        use_aemet = (0 <= current_hour <= 7) and not force_openweathermap
        
        if use_aemet:
            logger.info(f"Hybrid strategy: Using AEMET (hour {current_hour:02d}:xx - official observation window)")
            try:
                stats = await self.ingest_aemet_weather(station_ids=station_ids)
                if stats.successful_writes > 0:
                    return stats
                else:
                    logger.warning("AEMET ingestion failed, falling back to OpenWeatherMap")
            except Exception as e:
                logger.warning(f"AEMET ingestion error, falling back to OpenWeatherMap: {e}")
        else:
            logger.info(f"Hybrid strategy: Using OpenWeatherMap (hour {current_hour:02d}:xx - real-time data window)")
        
        # Use OpenWeatherMap (either by strategy or as fallback)
        return await self.ingest_openweathermap_weather()
    
    async def ingest_current_weather(self, station_ids: Optional[List[str]] = None) -> DataIngestionStats:
        """Ingest current weather data for specified stations"""
        return await self.ingest_aemet_weather(station_ids=station_ids)
    
    async def ingest_daily_weather(self, target_date: Optional[datetime] = None,
                                  station_ids: Optional[List[str]] = None) -> DataIngestionStats:
        """Ingest daily weather data for a specific date"""
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        
        start_date = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        return await self.ingest_aemet_weather(station_ids=station_ids, start_date=start_date, end_date=end_date)
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get status of data ingestion and InfluxDB connection"""
        if not self.client:
            return {"status": "disconnected", "error": "Client not initialized"}
        
        try:
            # Check InfluxDB health
            health = self.client.health()
            
            # Query recent data to check ingestion status
            query_api = self.client.query_api()
            
            # Check latest energy prices record
            flux_query = f'''
                from(bucket: "{self.config.bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> last()
            '''
            
            result = query_api.query(flux_query)
            
            latest_record = None
            for table in result:
                for record in table.records:
                    latest_record = {
                        "timestamp": record.get_time(),
                        "measurement": record.get_measurement(),
                        "value": record.get_value()
                    }
                    break
                if latest_record:
                    break
            
            return {
                "status": "connected",
                "influxdb_health": health.status,
                "latest_price_record": latest_record,
                "bucket": self.config.bucket,
                "org": self.config.org
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Utility functions
async def run_daily_ingestion() -> DataIngestionStats:
    """Run daily data ingestion (typically called by scheduler)"""
    async with DataIngestionService() as service:
        return await service.ingest_daily_prices()


async def run_current_ingestion() -> DataIngestionStats:
    """Run current hour data ingestion"""
    async with DataIngestionService() as service:
        return await service.ingest_current_prices()


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Test data ingestion
        async with DataIngestionService() as service:
            # Ingest current prices
            stats = await service.ingest_current_prices()
            print(f"Current ingestion: {stats.successful_writes} records, "
                  f"{stats.success_rate:.1f}% success rate")
            
            # Check status
            status = await service.get_ingestion_status()
            print(f"Service status: {status}")
    
    asyncio.run(main())