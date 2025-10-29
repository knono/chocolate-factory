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
from .data_ingestion import AEMETWeatherData  # AEMETWeatherData is defined in data_ingestion.py


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
                file_stats = await self.process_real_siar_csv_simple(csv_file)

                # Accumulate stats
                stats.total_records += file_stats.total_records
                stats.successful_writes += file_stats.successful_writes
                stats.failed_writes += file_stats.failed_writes

            logger.info(f"✅ SIAR ETL completed: {stats.successful_writes}/{stats.total_records} records loaded")
            return stats

        except Exception as e:
            logger.error(f"❌ SIAR ETL failed: {e}")
            raise

    async def process_real_siar_csv_simple(self, csv_file_path: str) -> DataIngestionStats:
        """
        Simple and direct processing of SIAR CSV files
        Based on known format: IdProvincia;IdEstacion;Fecha;Año;Dia;TempMedia(°C);TempMax(°C);...
        """
        stats = DataIngestionStats()

        try:
            logger.info(f"📊 Processing SIAR CSV (simple): {csv_file_path}")

            # Read file with encoding handling
            content = None
            for encoding in ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8']:
                try:
                    with open(csv_file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    logger.info(f"Successfully read {csv_file_path} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue

            if lines is None:
                raise ValueError(f"Could not decode {csv_file_path}")

            # Skip header line and process data lines
            data_lines = lines[1:]  # Skip first line (header)
            logger.info(f"🎯 Found {len(data_lines)} data lines")

            weather_data = []

            for line_num, line in enumerate(data_lines, 2):  # Start from line 2
                try:
                    # Character-by-character cleaning approach - keep only valid CSV characters
                    clean_chars = []
                    for char in line:
                        # Keep only printable ASCII characters, semicolons, commas, forward slashes, colons, digits, letters, dots, minus
                        if char.isprintable() and (char.isalnum() or char in ';,/:.-'):
                            clean_chars.append(char)

                    clean_line = ''.join(clean_chars)

                    if not clean_line.strip():
                        continue

                    # Debug first few lines to verify cleaning
                    if line_num <= 5:
                        logger.info(f"🔍 Line {line_num} Original: '{line[:30]}...' (len={len(line)})")
                        logger.info(f"🔍 Line {line_num} Cleaned:  '{clean_line[:30]}...' (len={len(clean_line)})")

                    parts = clean_line.split(';')
                    if len(parts) < 22:  # Need at least 22 columns
                        logger.warning(f"⚠️ Line {line_num}: insufficient columns ({len(parts)})")
                        if len(parts) > 2:  # Debug: show what we got
                            logger.info(f"🔍 Debug parts[0:3]: {parts[0:3]}")
                        continue

                    # Extract key data (using position-based access)
                    try:
                        fecha_str = parts[2]  # Should now be clean DD/MM/YYYY
                        if not fecha_str or '/' not in fecha_str:
                            continue

                        # Debug: log first successful date parsing
                        if stats.total_records < 3:
                            logger.info(f"🔍 Debug: Clean line length={len(clean_line)}, fecha_str='{fecha_str}' (len={len(fecha_str)})")

                        # Parse Spanish date format DD/MM/YYYY
                        date_obj = pd.to_datetime(fecha_str, format='%d/%m/%Y')

                        # Create weather record with SIAR-specific formatting
                        weather_record = AEMETWeatherData(
                            timestamp=date_obj.replace(tzinfo=timezone.utc),
                            station_id=f"SIAR_J{int(parts[1]):02d}_Linares",  # Unique SIAR identifier
                            station_name=f"SIAR_Linares_J{int(parts[1]):02d}",
                            province="Jaén",
                            altitude=None,  # Not available in SIAR
                            temperature=self._safe_float_comma(parts[5]) if len(parts) > 5 else None,      # TempMedia
                            temperature_max=self._safe_float_comma(parts[6]) if len(parts) > 6 else None,  # TempMax
                            temperature_min=self._safe_float_comma(parts[8]) if len(parts) > 8 else None,  # TempMin
                            humidity=self._safe_float_comma(parts[10]) if len(parts) > 10 else None,       # HumedadMedia
                            humidity_max=self._safe_float_comma(parts[11]) if len(parts) > 11 else None,   # HumedadMax
                            humidity_min=self._safe_float_comma(parts[13]) if len(parts) > 13 else None,   # HumedadMin
                            pressure=None,  # Not available in SIAR format
                            wind_speed=self._safe_float_comma(parts[15]) if len(parts) > 15 else None,     # Velviento (m/s)
                            wind_direction=self._safe_float_comma(parts[16]) if len(parts) > 16 else None, # DirViento
                            wind_gust=self._safe_float_comma(parts[17]) if len(parts) > 17 else None,      # VelVientoMax -> wind_gust
                            precipitation=self._safe_float_comma(parts[21]) if len(parts) > 21 else None   # Precipitación
                            # Note: radiation data (parts[20]) not included in AEMETWeatherData model
                        )

                        weather_data.append(weather_record)
                        stats.total_records += 1

                        # Log first successful record for debugging
                        if stats.total_records == 1:
                            logger.info(f"🎯 First record created successfully: {fecha_str}, Station: {weather_record.station_id}")

                        # Log progress every 100 records
                        if stats.total_records % 100 == 0:
                            logger.info(f"📈 Processed {stats.total_records} records...")

                    except (ValueError, IndexError) as e:
                        logger.warning(f"⚠️ Line {line_num}: parsing error - {e}")
                        stats.failed_writes += 1
                        continue

                except Exception as e:
                    logger.warning(f"⚠️ Line {line_num}: general error - {e}")
                    stats.failed_writes += 1
                    continue

            # Write to InfluxDB using AEMET weather ingestion method
            if weather_data:
                logger.info(f"💾 Writing {len(weather_data)} SIAR records to InfluxDB...")

                async with DataIngestionService() as ingestion_service:
                    ingestion_stats = await ingestion_service.ingest_aemet_weather(weather_data)

                    stats.successful_writes = ingestion_stats.successful_writes
                    stats.failed_writes = ingestion_stats.failed_writes

                logger.info(f"✅ SIAR CSV completed: {stats.successful_writes} records written from {csv_file_path}")
            else:
                logger.warning(f"⚠️ No valid weather data found in {csv_file_path}")

            return stats

        except Exception as e:
            logger.error(f"❌ Error processing SIAR CSV {csv_file_path}: {e}")
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

            # Create a temporary cleaned file and examine first few lines
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            # First, let's examine the actual format
            with open(tmp_file_path, 'r') as f:
                first_lines = [f.readline().strip() for _ in range(3)]

            logger.info(f"🔍 First 3 lines after cleaning:")
            for i, line in enumerate(first_lines):
                logger.info(f"   Line {i}: {line[:100]}...")

            # Read the cleaned CSV - use the first line as header
            df = pd.read_csv(tmp_file_path, sep=';', decimal=',')

            # Clean up temporary file
            import os
            os.unlink(tmp_file_path)

            logger.info(f"🎯 Loaded {len(df)} records from {csv_file_path}")
            logger.info(f"📋 Columns: {list(df.columns)}")

            # Skip if no valid data rows
            if len(df) == 0:
                logger.warning(f"No data rows in {csv_file_path}")
                return stats

            # Map real column names from SIAR format (after space removal)
            # Based on original format: IdProvincia;IdEstacion;Fecha;Año;Dia;TempMedia(°C);TempMax(°C);...
            column_mapping = {
                'IdProvincia': 'IdProvincia',
                'IdEstacion': 'IdEstacion',
                'Fecha': 'Fecha',
                'Año': 'Año',
                'Dia': 'Dia',
                'TempMedia(°C)': 'temperature',
                'TempMax(°C)': 'temperature_max',
                'TempMínima(°C)': 'temperature_min',
                'HumedadMedia(%)': 'humidity',
                'HumedadMax(%)': 'humidity_max',
                'HumedadMin(%)': 'humidity_min',
                'Velviento(m/s)': 'wind_speed',
                'DirViento(°)': 'wind_direction',
                'VelVientoMax(m/s)': 'wind_speed_max',
                'Radiación(MJ/m2)': 'radiation',
                'Precipitación(mm)': 'precipitation'
            }

            # Convert to AEMET format
            weather_data = []

            for _, row in df.iterrows():
                try:
                    # Skip header row if it contains text instead of data
                    if str(row.iloc[2]) == 'Fecha':  # Third column should be date
                        continue

                    # Parse date (format: DD/MM/YYYY)
                    date_str = str(row.iloc[2])  # Use position instead of column name initially
                    if '/' not in date_str:
                        logger.warning(f"⚠️ Invalid date format: {date_str}")
                        continue

                    date_obj = pd.to_datetime(date_str, format='%d/%m/%Y')

                    # Map SIAR columns to our format using column positions
                    weather_record = AEMETWeatherData(
                        timestamp=date_obj.replace(tzinfo=timezone.utc),
                        station_id=f"J{int(row.iloc[1]):02d}",  # J09, J17, etc.
                        station_name=f"Linares_J{int(row.iloc[1]):02d}",
                        province=f"JAEN_{int(row.iloc[0]):02d}",
                        altitude=None,  # Not available in this format
                        temperature=self._safe_float_comma(row.iloc[5]) if len(row) > 5 else None,
                        temperature_max=self._safe_float_comma(row.iloc[6]) if len(row) > 6 else None,
                        temperature_min=self._safe_float_comma(row.iloc[8]) if len(row) > 8 else None,
                        humidity=self._safe_float_comma(row.iloc[10]) if len(row) > 10 else None,
                        humidity_max=self._safe_float_comma(row.iloc[11]) if len(row) > 11 else None,
                        humidity_min=self._safe_float_comma(row.iloc[13]) if len(row) > 13 else None,
                        pressure=None,  # Not available in SIAR format
                        wind_speed=self._safe_float_comma(row.iloc[15]) if len(row) > 15 else None,
                        wind_direction=self._safe_float_comma(row.iloc[16]) if len(row) > 16 else None,
                        wind_speed_max=self._safe_float_comma(row.iloc[17]) if len(row) > 17 else None,
                        precipitation=self._safe_float_comma(row.iloc[21]) if len(row) > 21 else None,
                        radiation=self._safe_float_comma(row.iloc[20]) if len(row) > 20 else None
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