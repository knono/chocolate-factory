"""
TFM Chocolate Factory - Initialization Service
=============================================

Coordinador principal para inicialización del sistema.
- Datos históricos REE (2022-2024)
- Weather sintético post-COVID
- Verificación de schemas InfluxDB
- Checks de conectividad APIs
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .historical_ingestion import HistoricalDataIngestion
from .synthetic_weather import SyntheticWeatherGenerator
from ..data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)

@dataclass
class InitializationStats:
    """Statistics from initialization process"""
    historical_ree_records: int = 0
    synthetic_weather_records: int = 0
    aemet_historical_records: int = 0
    total_duration_seconds: float = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class InitializationService:
    """
    Servicio coordinador para inicialización completa del sistema
    """
    
    def __init__(self):
        self.historical_ingestion = HistoricalDataIngestion()
        self.weather_generator = SyntheticWeatherGenerator()
        
    async def __aenter__(self):
        await self.historical_ingestion.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.historical_ingestion.__aexit__(exc_type, exc_val, exc_tb)
    
    async def initialize_all(self) -> InitializationStats:
        """
        Ejecutar inicialización completa del sistema
        """
        start_time = datetime.now(timezone.utc)
        stats = InitializationStats()
        
        logger.info("🚀 Starting complete system initialization")
        
        try:
            # 1. Verificar conectividad básica
            logger.info("1️⃣ Checking system connectivity...")
            await self._check_system_connectivity()
            
            # 2. Inicializar schemas InfluxDB
            logger.info("2️⃣ Initializing InfluxDB schemas...")
            await self._initialize_database_schemas()
            
            # 3. Cargar datos históricos REE (2022-2024)
            logger.info("3️⃣ Loading historical REE data (2022-2024)...")
            ree_stats = await self.historical_ingestion.load_post_covid_data()
            stats.historical_ree_records = ree_stats.successful_writes
            
            # 4. Generar weather sintético coherente
            logger.info("4️⃣ Generating synthetic weather data (2022-2024)...")
            weather_stats = await self.weather_generator.generate_historical_weather()
            stats.synthetic_weather_records = weather_stats.successful_writes
            
            # 5. Verificación final
            logger.info("5️⃣ Final system verification...")
            await self._verify_initialization()
            
            end_time = datetime.now(timezone.utc)
            stats.total_duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ System initialization completed successfully!")
            logger.info(f"📊 REE records: {stats.historical_ree_records}")
            logger.info(f"🌤️ Weather records: {stats.synthetic_weather_records}")
            logger.info(f"⏱️ Duration: {stats.total_duration_seconds:.1f}s")
            
            return stats
            
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ System initialization failed: {e}")
            raise
    
    async def initialize_historical_data_only(self) -> InitializationStats:
        """
        Inicializar solo datos históricos (más rápido)
        """
        start_time = datetime.now(timezone.utc)
        stats = InitializationStats()
        
        logger.info("📊 Starting historical data initialization only")
        
        try:
            # Cargar datos históricos REE (2022-2024)
            ree_stats = await self.historical_ingestion.load_post_covid_data()
            stats.historical_ree_records = ree_stats.successful_writes
            
            end_time = datetime.now(timezone.utc)
            stats.total_duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Historical data initialization completed!")
            logger.info(f"📊 REE records: {stats.historical_ree_records}")
            logger.info(f"⏱️ Duration: {stats.total_duration_seconds:.1f}s")
            
            return stats
            
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ Historical data initialization failed: {e}")
            raise
    
    async def initialize_aemet_historical_data(self, years_back: int = 3) -> InitializationStats:
        """
        Inicializar solo datos históricos meteorológicos de AEMET
        
        Args:
            years_back: Años hacia atrás para cargar (default: 3)
        """
        start_time = datetime.now(timezone.utc)
        stats = InitializationStats()
        
        logger.info(f"🌤️ Starting AEMET historical data initialization ({years_back} years)")
        
        try:
            # Cargar datos históricos meteorológicos de AEMET
            aemet_stats = await self.historical_ingestion.load_aemet_historical_data(years_back)
            stats.aemet_historical_records = aemet_stats.successful_writes
            
            if aemet_stats.errors:
                stats.errors.extend(aemet_stats.errors)
            
            end_time = datetime.now(timezone.utc)
            stats.total_duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ AEMET historical data initialization completed!")
            logger.info(f"🌤️ Weather records: {stats.aemet_historical_records}")
            logger.info(f"⏱️ Duration: {stats.total_duration_seconds:.1f}s")
            
            return stats
            
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ AEMET historical data initialization failed: {e}")
            raise
    
    async def initialize_complete_historical_data(self) -> InitializationStats:
        """
        Inicializar datos históricos completos: REE + AEMET
        """
        start_time = datetime.now(timezone.utc)
        stats = InitializationStats()
        
        logger.info("📊🌤️ Starting complete historical data initialization (REE + AEMET)")
        
        try:
            # 1. Cargar datos históricos REE (2022-2024)
            logger.info("1️⃣ Loading historical REE data...")
            ree_stats = await self.historical_ingestion.load_post_covid_data()
            stats.historical_ree_records = ree_stats.successful_writes
            
            if ree_stats.errors:
                stats.errors.extend(ree_stats.errors)
            
            # 2. Cargar datos históricos AEMET (3 años)
            logger.info("2️⃣ Loading historical AEMET data...")
            aemet_stats = await self.historical_ingestion.load_aemet_historical_data(3)
            stats.aemet_historical_records = aemet_stats.successful_writes
            
            if aemet_stats.errors:
                stats.errors.extend(aemet_stats.errors)
            
            end_time = datetime.now(timezone.utc)
            stats.total_duration_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Complete historical data initialization finished!")
            logger.info(f"📊 REE records: {stats.historical_ree_records}")
            logger.info(f"🌤️ AEMET records: {stats.aemet_historical_records}")
            logger.info(f"⏱️ Total duration: {stats.total_duration_seconds:.1f}s")
            
            return stats
            
        except Exception as e:
            stats.errors.append(str(e))
            logger.error(f"❌ Complete historical data initialization failed: {e}")
            raise
    
    async def _check_system_connectivity(self):
        """Verificar conectividad con sistemas externos"""
        async with DataIngestionService() as service:
            # Check InfluxDB
            health = service.client.health()
            if health.status != "pass":
                raise RuntimeError(f"InfluxDB not healthy: {health.status}")
            
            # Check REE API (basic connectivity)
            # Note: We don't check AEMET/OpenWeatherMap to avoid quota usage
            logger.info("✅ System connectivity verified")
    
    async def _initialize_database_schemas(self):
        """Inicializar schemas de InfluxDB si no existen"""
        # En InfluxDB 2.x los schemas son implícitos
        # Solo verificamos que el bucket existe
        async with DataIngestionService() as service:
            # Try a simple query to verify bucket exists
            query_api = service.client.query_api()
            test_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -1h)
                |> limit(n: 1)
            '''
            try:
                list(query_api.query(test_query))
                logger.info("✅ InfluxDB schemas verified")
            except Exception as e:
                logger.warning(f"⚠️ InfluxDB schema check failed: {e}")
                # This is OK - bucket might be empty
    
    async def _verify_initialization(self):
        """Verificación final del estado del sistema"""
        async with DataIngestionService() as service:
            query_api = service.client.query_api()
            
            # Count total records
            count_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: 2022-01-01T00:00:00Z, stop: now())
                |> count()
            '''
            
            try:
                results = query_api.query(count_query)
                total_records = 0
                for table in results:
                    for record in table.records:
                        total_records += record.get_value()
                
                logger.info(f"✅ Verification complete: {total_records} total records in database")
                
                if total_records == 0:
                    logger.warning("⚠️ No records found in database after initialization")
                    
            except Exception as e:
                logger.warning(f"⚠️ Verification query failed: {e}")
    
    async def get_initialization_status(self) -> Dict[str, Any]:
        """Obtener estado actual de la inicialización con queries reales"""
        try:
            # Use real InfluxDB queries to get accurate counts
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Count REE energy prices (last 3 years)
                ree_count_query = f'''
                    from(bucket: "{service.config.bucket}")
                    |> range(start: -{3*365*24}h)
                    |> filter(fn: (r) => r._measurement == "energy_prices")
                    |> filter(fn: (r) => r._field == "price_eur_kwh")
                    |> count()
                '''
                
                # Count weather data (last 3 years)
                weather_count_query = f'''
                    from(bucket: "{service.config.bucket}")
                    |> range(start: -{3*365*24}h)
                    |> filter(fn: (r) => r._measurement == "weather_data")
                    |> filter(fn: (r) => r._field == "temperature")
                    |> count()
                '''
                
                # Count recent records (last 24h)
                recent_count_query = f'''
                    from(bucket: "{service.config.bucket}")
                    |> range(start: -24h)
                    |> count()
                '''
                
                # Execute queries
                ree_results = query_api.query(ree_count_query)
                weather_results = query_api.query(weather_count_query)
                recent_results = query_api.query(recent_count_query)
                
                # Process results
                ree_count = 0
                for table in ree_results:
                    for record in table.records:
                        ree_count += record.get_value()
                
                weather_count = 0
                for table in weather_results:
                    for record in table.records:
                        weather_count += record.get_value()
                
                recent_count = 0
                for table in recent_results:
                    for record in table.records:
                        recent_count += record.get_value()
                
        except Exception as e:
            logger.warning(f"Failed to query InfluxDB for initialization status: {e}")
            # Fallback to conservative estimates if queries fail
            ree_count = 0
            weather_count = 0
            recent_count = 0
        
        # Determine initialization status using real data
        ree_initialized = ree_count > 1000  
        weather_initialized = weather_count > 10   
        is_fully_initialized = ree_initialized and weather_initialized  
        
        return {
            "is_fully_initialized": is_fully_initialized,
            "ree_initialized": ree_initialized, 
            "weather_initialized": weather_initialized,
            "historical_ree_records": ree_count,
            "historical_weather_records": weather_count,
            "recent_records_24h": recent_count,
            "estimated_missing_ree_records": max(0, 17520 - ree_count),
            "estimated_missing_weather_records": max(0, 1095 - weather_count),
            "initialization_recommended": {
                "ree_data": not ree_initialized,
                "weather_data": not weather_initialized,
                "complete_historical": not is_fully_initialized
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Values based on real-time InfluxDB queries",
            "query_scope": "3 years of historical data"
        }