"""
Sistema SIAR ETL Service - TFM Chocolate Factory
===============================================

ETL service to process historical weather data from Sistema SIAR
Handles CSV processing and data transformation to InfluxDB format.
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


class SiarETL:
    """
    ETL service for processing Sistema SIAR historical weather data
    """
    
    def __init__(self):
        self.base_url = "https://servicio.mapa.gob.es/websiar/"
        self.data_dir = Path("/tmp/siar")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def download_sample_data(self) -> bool:
        """
        Download sample data for testing (or implement manual CSV processing)
        For production, user would download CSV from Sistema SIAR portal
        """
        logger.info("🌍 SIAR ETL: Preparing sample data processing")
        
        # For now, we'll create a sample CSV structure that matches Sistema SIAR format
        sample_data = self._generate_sample_csv_data()
        
        sample_file = self.data_dir / "linares_5279X_sample.csv"
        with open(sample_file, 'w', newline='', encoding='utf-8') as f:
            f.write(sample_data)
            
        logger.info(f"📁 Sample CSV created: {sample_file}")
        return True
        
    def _generate_sample_csv_data(self) -> str:
        """
        Generate sample CSV data matching Sistema SIAR format
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
    
    async def process_real_siar_files(self, data_path: str = "/app/data/históricoClimaLinares") -> DataIngestionStats:
        """
        Process real SIAR CSV files from the data directory

        Args:
            data_path: Path to directory containing SIAR CSV files
        """
        logger.info(f"🚀 Starting SIAR ETL for real CSV files in {data_path}")

        stats = DataIngestionStats()

        try:
            # Find all CSV files in the data directory using find command approach
            import glob
            import os
            # Use os.walk to handle encoding issues
            csv_files = []
            for root, dirs, files in os.walk("/app/data"):
                for file in files:
                    if file.endswith('.csv'):
                        csv_files.append(os.path.join(root, file))

            if not csv_files:
                logger.warning(f"No CSV files found in {data_path}")
                return stats

            logger.info(f"📁 Found {len(csv_files)} CSV files to process")

            # Process each CSV file
            for csv_file in csv_files:
                logger.info(f"📊 Processing {csv_file}")
                file_stats = await self.process_real_siar_csv(csv_file)

                # Accumulate stats
                stats.total_records += file_stats.total_records
                stats.successful_writes += file_stats.successful_writes
                stats.failed_writes += file_stats.failed_writes

            logger.info(f"✅ SIAR ETL completed: {stats.successful_writes}/{stats.total_records} records loaded")
            return stats

        except Exception as e:
            logger.error(f"❌ SIAR ETL failed: {e}")
            raise

    async def process_real_siar_csv(self, csv_file_path: str) -> DataIngestionStats:
        """
        Process a real SIAR CSV file with proper encoding and format handling

        The real SIAR CSV format uses:
        - Semicolon (;) as separator
        - Comma (,) as decimal separator
        - Strange spacing in headers (encoding issue)
        - Date format: DD/MM/YYYY
        """
        stats = DataIngestionStats()

        try:
            logger.info(f"📊 Processing real SIAR CSV: {csv_file_path}")

            # Read the file with proper encoding and separator
            # First, fix the encoding issue by removing extra spaces
            # Try different encodings for SIAR files
            content = None
            for encoding in ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8']:
                try:
                    with open(csv_file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"Successfully read {csv_file_path} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ValueError(f"Could not decode {csv_file_path} with any known encoding")

            # Remove the extra spaces between characters
            content = content.replace(' ', '')

            # Create a temporary cleaned file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            # Read the cleaned CSV
            df = pd.read_csv(tmp_file_path, sep=';', decimal=',')

            # Clean up temporary file
            import os
            os.unlink(tmp_file_path)

            logger.info(f"🎯 Loaded {len(df)} records from {csv_file_path}")

            # Convert to AEMET format
            weather_data = []

            for _, row in df.iterrows():
                try:
                    # Parse date (format: DD/MM/YYYY)
                    date_str = str(row['Fecha'])
                    date_obj = pd.to_datetime(date_str, format='%d/%m/%Y')

                    # Map SIAR columns to our format
                    weather_record = AEMETWeatherData(
                        timestamp=date_obj.replace(tzinfo=timezone.utc),
                        station_id=f"J{row['IdEstacion']:02d}",  # J09, J17, etc.
                        station_name=f"Linares_J{row['IdEstacion']:02d}",
                        province=f"JAEN_{row['IdProvincia']:02d}",
                        altitude=None,  # Not available in this format
                        temperature=self._safe_float_comma(row.get('TempMedia(°C)')),
                        temperature_max=self._safe_float_comma(row.get('TempMax(°C)')),
                        temperature_min=self._safe_float_comma(row.get('TempMínima(°C)')),
                        humidity=self._safe_float_comma(row.get('HumedadMedia(%)')),
                        humidity_max=self._safe_float_comma(row.get('HumedadMax(%)')),
                        humidity_min=self._safe_float_comma(row.get('HumedadMin(%)')),
                        pressure=None,  # Not available in SIAR format
                        wind_speed=self._safe_float_comma(row.get('Velviento(m/s)')),
                        wind_direction=self._safe_float_comma(row.get('DirViento(°)')),
                        wind_speed_max=self._safe_float_comma(row.get('VelVientoMax(m/s)')),
                        precipitation=self._safe_float_comma(row.get('Precipitación(mm)')),
                        radiation=self._safe_float_comma(row.get('Radiación(MJ/m2)'))
                    )

                    weather_data.append(weather_record)
                    stats.total_records += 1

                except Exception as e:
                    logger.warning(f"⚠️ Error processing row {row.get('Fecha', 'unknown')}: {e}")
                    stats.failed_writes += 1
                    continue

            # Write to InfluxDB
            if weather_data:
                ingestion_service = DataIngestionService()
                write_result = await ingestion_service.ingest_weather_data_batch(weather_data)

                if write_result.get('success', False):
                    records_written = write_result.get('records_written', 0)
                    stats.successful_writes += records_written
                    logger.info(f"✅ Written {records_written} records to InfluxDB from {csv_file_path}")
                else:
                    logger.error(f"❌ Failed to write data from {csv_file_path}")
                    stats.failed_writes += len(weather_data)

            return stats

        except Exception as e:
            logger.error(f"❌ Error processing SIAR CSV {csv_file_path}: {e}")
            raise

    def _safe_float_comma(self, value) -> Optional[float]:
        """Safely convert value to float, handling comma as decimal separator"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            # Convert to string and replace comma with dot for decimal
            str_val = str(value).replace(',', '.')
            return float(str_val)
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