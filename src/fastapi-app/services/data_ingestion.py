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

from .ree_client import REEClient, REEPriceData, REEDemandData
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configs.influxdb_schemas import EnergyPricesSchema, get_tariff_period


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
            logger.info("Starting REE price data ingestion")
            
            # Fetch data from REE API
            async with REEClient() as ree_client:
                price_data = await ree_client.get_pvpc_prices(start_date, end_date)
            
            stats.total_records = len(price_data)
            logger.info(f"Retrieved {stats.total_records} price records from REE API")
            
            if not price_data:
                logger.warning("No price data retrieved from REE API")
                return stats
            
            # Transform and validate data
            valid_points = []
            for price_record in price_data:
                is_valid, validation_errors = self._validate_price_data(price_record)
                
                if not is_valid:
                    stats.validation_errors += 1
                    logger.warning(f"Validation failed for {price_record.timestamp}: {validation_errors}")
                    continue
                
                try:
                    point = self._transform_ree_price_to_influx_point(price_record)
                    valid_points.append(point)
                except Exception as e:
                    logger.error(f"Failed to transform price data: {e}")
                    stats.failed_writes += 1
            
            # Batch write to InfluxDB
            if valid_points:
                try:
                    logger.info(f"Writing {len(valid_points)} points to InfluxDB")
                    self.write_api.write(
                        bucket=self.config.bucket,
                        org=self.config.org,
                        record=valid_points
                    )
                    stats.successful_writes = len(valid_points)
                    logger.info(f"Successfully wrote {stats.successful_writes} price records to InfluxDB")
                    
                except Exception as e:
                    logger.error(f"Failed to write to InfluxDB: {e}")
                    stats.failed_writes = len(valid_points)
                    raise
            
        except Exception as e:
            logger.error(f"REE price ingestion failed: {e}")
            raise
        
        finally:
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()
            logger.info(f"REE ingestion completed in {stats.processing_time_seconds:.2f}s - "
                       f"Success rate: {stats.success_rate:.1f}%")
        
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