"""
TFM Chocolate Factory - Historical Data Ingestion
================================================

Carga de datos históricos REE post-COVID (2022-2024).
~17,520 registros de precios eléctricos con patrones estabilizados.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..ree_client import REEClient
from ..aemet_client import AEMETClient, AEMETWeatherData
from ..data_ingestion import DataIngestionService, DataIngestionStats

logger = logging.getLogger(__name__)

@dataclass
class HistoricalDataStats:
    """Statistics from historical data loading"""
    total_records_requested: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    api_calls_made: int = 0
    duration_seconds: float = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class HistoricalDataIngestion:
    """
    Servicio para carga masiva de datos históricos REE
    """
    
    def __init__(self):
        self.data_service: Optional[DataIngestionService] = None
        self.ree_client: Optional[REEClient] = None
        self.aemet_client: Optional[AEMETClient] = None
        
    async def __aenter__(self):
        self.data_service = DataIngestionService()
        await self.data_service.__aenter__()
        self.ree_client = REEClient()
        await self.ree_client.__aenter__()
        self.aemet_client = AEMETClient()
        await self.aemet_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.aemet_client:
            await self.aemet_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.ree_client:
            await self.ree_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_service:
            await self.data_service.__aexit__(exc_type, exc_val, exc_tb)
    
    async def load_post_covid_data(self) -> HistoricalDataStats:
        """
        Cargar datos históricos post-COVID (2022-2024)
        
        Estrategia:
        - 2022-01-01 hasta 2024-12-31 
        - Datos horarios (~17,520 registros)
        - Patrones de mercado estabilizados post-COVID
        """
        start_time = datetime.now(timezone.utc)
        stats = HistoricalDataStats()
        
        # Define date range: Post-COVID stable period
        start_date = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        stats.date_range_start = start_date.isoformat()
        stats.date_range_end = end_date.isoformat()
        
        logger.info(f"📊 Starting historical REE data ingestion")
        logger.info(f"📅 Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"⏳ Expected records: ~{(end_date - start_date).days * 24}")
        
        try:
            # Load data in monthly chunks to avoid API timeouts
            current_date = start_date
            total_successful = 0
            total_api_calls = 0
            
            while current_date < end_date:
                # Process one month at a time
                chunk_end = min(
                    current_date + timedelta(days=30),  # ~30 days chunks
                    end_date
                )
                
                logger.info(f"📥 Processing chunk: {current_date.date()} to {chunk_end.date()}")
                
                try:
                    chunk_stats = await self._load_ree_chunk(current_date, chunk_end)
                    total_successful += chunk_stats.successful_writes
                    total_api_calls += 1
                    
                    logger.info(f"✅ Chunk completed: {chunk_stats.successful_writes} records")
                    
                    # Brief pause to be respectful to REE API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Failed to load chunk {current_date.date()}: {e}"
                    stats.errors.append(error_msg)
                    logger.error(error_msg)
                
                current_date = chunk_end
            
            stats.successful_writes = total_successful
            stats.api_calls_made = total_api_calls
            stats.total_records_requested = int((end_date - start_date).total_seconds() / 3600)  # Hourly
            
            end_time = datetime.now(timezone.utc)
            stats.duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"🎉 Historical data ingestion completed!")
            logger.info(f"📊 Records written: {stats.successful_writes}")
            logger.info(f"🔧 API calls made: {stats.api_calls_made}")
            logger.info(f"⏱️ Duration: {stats.duration_seconds:.1f}s")
            
            if stats.errors:
                logger.warning(f"⚠️ {len(stats.errors)} errors occurred during ingestion")
            
            return stats
            
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ Historical data ingestion failed: {e}")
            raise
    
    async def _load_ree_chunk(self, start_date: datetime, end_date: datetime) -> DataIngestionStats:
        """
        Cargar un chunk de datos REE para un rango específico
        """
        try:
            # Use REE client to get historical prices
            # REE API supports date ranges for historical data
            prices = await self.ree_client.get_price_range(
                start_date=start_date,
                end_date=end_date
            )
            
            if not prices:
                logger.warning(f"No REE data received for {start_date.date()} to {end_date.date()}")
                return DataIngestionStats()
            
            # Use existing data ingestion service to write to InfluxDB
            # But with historical data instead of current
            stats = await self.data_service.ingest_ree_prices_historical(prices)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to load REE chunk {start_date} to {end_date}: {e}")
            raise
    
    async def check_existing_historical_data(self) -> Dict[str, Any]:
        """
        Verificar qué datos históricos ya existen en la base de datos
        """
        if not self.data_service:
            raise RuntimeError("DataIngestionService not initialized")
        
        query_api = self.data_service.client.query_api()
        
        # Query for historical data presence
        query = f'''
            from(bucket: "{self.data_service.config.bucket}")
            |> range(start: 2022-01-01T00:00:00Z, stop: 2025-01-01T00:00:00Z)
            |> filter(fn: (r) => r._measurement == "energy_prices")
            |> filter(fn: (r) => r._field == "price_eur_kwh")
            |> group(columns: ["_time"])
            |> count()
        '''
        
        try:
            results = query_api.query(query)
            
            total_records = 0
            earliest_date = None
            latest_date = None
            
            for table in results:
                for record in table.records:
                    total_records += record.get_value()
                    record_time = record.get_time()
                    
                    if earliest_date is None or record_time < earliest_date:
                        earliest_date = record_time
                    if latest_date is None or record_time > latest_date:
                        latest_date = record_time
            
            return {
                "total_historical_records": total_records,
                "earliest_date": earliest_date.isoformat() if earliest_date else None,
                "latest_date": latest_date.isoformat() if latest_date else None,
                "expected_records_2022_2024": 26280,  # 3 years * 365 days * 24 hours
                "completion_percentage": (total_records / 26280 * 100) if total_records > 0 else 0,
                "needs_historical_load": total_records < 1000  # Threshold for "needs loading"
            }
            
        except Exception as e:
            logger.error(f"Failed to check existing historical data: {e}")
            return {
                "error": str(e),
                "needs_historical_load": True
            }
    
    async def load_aemet_historical_data(self, years_back: int = 3) -> HistoricalDataStats:
        """
        Cargar datos históricos meteorológicos de AEMET
        
        Args:
            years_back: Número de años hacia atrás desde hoy (default: 3)
            
        Returns:
            HistoricalDataStats con el resultado de la carga
        """
        start_time = datetime.now(timezone.utc)
        stats = HistoricalDataStats()
        
        # Calculate date range (years_back from today)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=years_back * 365)
        
        stats.date_range_start = start_date.isoformat()
        stats.date_range_end = end_date.isoformat()
        
        logger.info(f"🌤️ Starting AEMET historical weather data ingestion")
        logger.info(f"📅 Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"📍 Station: 5279X (Linares, Jaén)")
        logger.info(f"⏳ Expected records: ~{years_back * 365} daily records")
        
        if not self.aemet_client:
            raise RuntimeError("AEMET client not initialized")
        
        try:
            # Use chunked method to handle AEMET API limitations (max 5 years)
            weather_data = await self.aemet_client.get_historical_weather_chunked(
                start_date=start_date,
                end_date=end_date,
                station_id="5279X",  # Linares, Jaén
                chunk_years=3  # 3-year chunks for safety
            )
            
            if weather_data:
                # Store weather data in InfluxDB
                stats.successful_writes = await self._store_aemet_historical_data(weather_data)
                stats.total_records_requested = len(weather_data)
                logger.info(f"✅ Stored {stats.successful_writes} AEMET historical records")
            else:
                logger.warning("No AEMET historical data received")
                stats.errors.append("No data received from AEMET API")
            
            stats.api_calls_made = len(weather_data) // 1000 + 1  # Estimate API calls
            
            end_time = datetime.now(timezone.utc)
            stats.duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"🎉 AEMET historical data ingestion completed!")
            logger.info(f"📊 Records written: {stats.successful_writes}")
            logger.info(f"⏱️ Duration: {stats.duration_seconds:.1f}s")
            
            return stats
            
        except Exception as e:
            error_msg = f"AEMET historical data ingestion failed: {e}"
            stats.errors.append(error_msg)  
            logger.error(f"❌ {error_msg}")
            raise
    
    async def _store_aemet_historical_data(self, weather_data: List[AEMETWeatherData]) -> int:
        """
        Almacenar datos históricos de AEMET en InfluxDB
        
        Args:
            weather_data: Lista de datos meteorológicos de AEMET
            
        Returns:
            Número de registros almacenados exitosamente
        """
        if not self.data_service:
            raise RuntimeError("DataIngestionService not initialized")
        
        write_api = self.data_service.client.write_api()
        successful_writes = 0
        
        try:
            for weather in weather_data:
                # Convert AEMET data to InfluxDB point using correct method
                point = self.data_service._transform_aemet_weather_to_influx_point(weather)
                
                # Write individual point
                write_api.write(
                    bucket=self.data_service.config.bucket,
                    org=self.data_service.config.org,
                    record=point
                )
                successful_writes += 1
                
                # Batch write every 100 records for efficiency
                if successful_writes % 100 == 0:
                    logger.debug(f"Wrote {successful_writes} AEMET historical records...")
            
            # Ensure all data is written
            write_api.flush()
            logger.info(f"Successfully stored {successful_writes} AEMET historical weather records")
            
            return successful_writes
            
        except Exception as e:
            logger.error(f"Failed to store AEMET historical data: {e}")
            raise
    
    async def check_existing_weather_data(self) -> Dict[str, Any]:
        """
        Verificar qué datos meteorológicos históricos ya existen
        """
        if not self.data_service:
            raise RuntimeError("DataIngestionService not initialized")
        
        query_api = self.data_service.client.query_api()
        
        # Query for historical weather data from AEMET
        query = f'''
            from(bucket: "{self.data_service.config.bucket}")
            |> range(start: 2022-01-01T00:00:00Z, stop: now())
            |> filter(fn: (r) => r._measurement == "weather_data")
            |> filter(fn: (r) => r._field == "temperature")
            |> filter(fn: (r) => r.source == "aemet_historical")
            |> group(columns: ["_time"])
            |> count()
            |> sort(columns: ["_time"])
        '''
        
        try:
            results = query_api.query(query)
            
            total_records = 0
            earliest_date = None
            latest_date = None
            
            for table in results:
                for record in table.records:
                    total_records += record.get_value()
                    record_time = record.get_time()
                    
                    if earliest_date is None or record_time < earliest_date:
                        earliest_date = record_time
                    if latest_date is None or record_time > latest_date:
                        latest_date = record_time
            
            # Expected records: ~3 years * 365 days = ~1095 daily records
            expected_records = 1095
            
            return {
                "total_weather_records": total_records,
                "earliest_weather_date": earliest_date.isoformat() if earliest_date else None,
                "latest_weather_date": latest_date.isoformat() if latest_date else None,
                "expected_weather_records": expected_records,
                "weather_completion_percentage": (total_records / expected_records * 100) if total_records > 0 else 0,
                "needs_weather_historical_load": total_records < 100  # Threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to check existing weather data: {e}")
            return {
                "error": str(e),
                "needs_weather_historical_load": True
            }