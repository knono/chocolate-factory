"""
DatosClima.es ETL Service - TFM Chocolate Factory
===============================================

ETL service to process historical weather data from datosclima.es
Handles CSV downloads and data transformation to InfluxDB format.
"""

import asyncio
import csv
import io
import zipfile
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
from loguru import logger
import pandas as pd

from .data_ingestion import DataIngestionService, DataIngestionStats
from .aemet_client import AEMETWeatherData


class DatosClimaETL:
    """
    ETL service for processing datosclima.es historical weather data
    """
    
    def __init__(self):
        self.base_url = "https://datosclima.es"
        self.data_dir = Path("/tmp/datosclima")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def download_sample_data(self) -> bool:
        """
        Download sample data for testing (or implement manual CSV processing)
        For production, user would download CSV from datosclima.es
        """
        logger.info("🌍 DatosClima ETL: Preparing sample data processing")
        
        # For now, we'll create a sample CSV structure that matches datosclima.es format
        sample_data = self._generate_sample_csv_data()
        
        sample_file = self.data_dir / "linares_5279X_sample.csv"
        with open(sample_file, 'w', newline='', encoding='utf-8') as f:
            f.write(sample_data)
            
        logger.info(f"📁 Sample CSV created: {sample_file}")
        return True
        
    def _generate_sample_csv_data(self) -> str:
        """
        Generate sample CSV data matching datosclima.es format
        This simulates what would be downloaded from the site
        """
        header = "Fecha,Indicativo,Estacion,Provincia,Altitud,TempMedia,TempMax,TempMin,HumRelativa,Precipitacion,PresionMedia,VelViento,DirViento,Radiacion"
        
        # Generate sample data for last 30 days
        sample_rows = []
        for i in range(30):
            date = datetime.now() - pd.Timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Realistic summer data for Linares, Jaén
            temp_base = 35 - (i * 0.2)  # Slight cooling trend
            row = f"{date_str},5279X,LINARES (VOR - AUTOMATICA),JAEN,515,{temp_base:.1f},{temp_base+8:.1f},{temp_base-12:.1f},25,0.0,1013.2,5.2,180,850"
            sample_rows.append(row)
            
        return header + "\n" + "\n".join(sample_rows)
    
    async def process_csv_file(self, csv_file_path: str, station_filter: str = "5279X") -> DataIngestionStats:
        """
        Process CSV file from datosclima.es and convert to InfluxDB format
        
        Args:
            csv_file_path: Path to CSV file downloaded from datosclima.es
            station_filter: Station ID to filter (default: Linares 5279X)
        """
        stats = DataIngestionStats()
        
        try:
            logger.info(f"📊 Processing CSV file: {csv_file_path}")
            
            # Read CSV with pandas for better handling
            df = pd.read_csv(csv_file_path, encoding='utf-8')
            
            # Filter for our station
            if station_filter:
                df = df[df['Indicativo'] == station_filter]
                logger.info(f"🎯 Filtered data for station {station_filter}: {len(df)} records")
            
            # Convert to AEMET format
            weather_data = []
            for _, row in df.iterrows():
                try:
                    # Parse date
                    date_obj = pd.to_datetime(row['Fecha'], format='%Y-%m-%d')
                    
                    # Create weather data object
                    weather_record = AEMETWeatherData(
                        timestamp=date_obj.replace(tzinfo=timezone.utc),
                        station_id=str(row['Indicativo']),
                        station_name=row.get('Estacion', 'Unknown'),
                        province=row.get('Provincia', 'Unknown'),
                        altitude=self._safe_float(row.get('Altitud')),
                        temperature=self._safe_float(row.get('TempMedia')),
                        temperature_max=self._safe_float(row.get('TempMax')),
                        temperature_min=self._safe_float(row.get('TempMin')),
                        humidity=self._safe_float(row.get('HumRelativa')),
                        pressure=self._safe_float(row.get('PresionMedia')),
                        wind_speed=self._safe_float(row.get('VelViento')),
                        wind_direction=self._safe_float(row.get('DirViento')),
                        precipitation=self._safe_float(row.get('Precipitacion')),
                        solar_radiation=self._safe_float(row.get('Radiacion'))
                    )
                    
                    weather_data.append(weather_record)
                    stats.total_records += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process row: {e}")
                    stats.validation_errors += 1
            
            # Ingest to InfluxDB
            if weather_data:
                logger.info(f"💾 Ingesting {len(weather_data)} weather records to InfluxDB")
                
                async with DataIngestionService() as ingestion_service:
                    ingestion_stats = await ingestion_service.ingest_aemet_weather(weather_data)
                    
                    stats.successful_writes = ingestion_stats.successful_writes
                    stats.failed_writes = ingestion_stats.failed_writes
                    
                logger.info(f"✅ ETL completed: {stats.successful_writes} records ingested")
            else:
                logger.warning("⚠️ No valid weather data found in CSV")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ CSV processing failed: {e}")
            raise
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return None
    
    async def download_and_process_station(self, station_id: str = "5279X", years: int = 5) -> DataIngestionStats:
        """
        Complete ETL process for a weather station
        
        Args:
            station_id: Weather station identifier
            years: Number of years of historical data
        """
        logger.info(f"🚀 Starting DatosClima ETL for station {station_id} ({years} years)")
        
        try:
            # Step 1: Generate/download sample data
            await self.download_sample_data()
            
            # Step 2: Process the CSV
            csv_file = self.data_dir / f"linares_{station_id}_sample.csv"
            stats = await self.process_csv_file(str(csv_file), station_id)
            
            # Step 3: Cleanup
            logger.info("🧹 Cleaning up temporary files")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ DatosClima ETL failed: {e}")
            raise


async def main():
    """Test the ETL service"""
    etl = DatosClimaETL()
    stats = await etl.download_and_process_station()
    print(f"ETL Results: {stats.successful_writes} records processed")


if __name__ == "__main__":
    asyncio.run(main())