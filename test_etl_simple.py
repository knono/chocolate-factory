"""
Test simple ETL for DatosClima.es data
"""

import asyncio
import pandas as pd
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

async def test_simple_etl():
    """Simple ETL test without complex dependencies"""
    
    # Create sample data (like datosclima.es CSV)
    print("📊 Creating sample weather data...")
    
    sample_data = []
    for i in range(365):  # 1 year of data
        date = datetime.now() - pd.Timedelta(days=i)
        temp_base = 25 + (i % 15) - 7  # Realistic temperature variation
        
        row = {
            'Fecha': date.strftime('%Y-%m-%d'),
            'Indicativo': '5279X',
            'Estacion': 'LINARES (VOR - AUTOMATICA)',
            'Provincia': 'JAEN',
            'Altitud': 515,
            'TempMedia': temp_base,
            'TempMax': temp_base + 8,
            'TempMin': temp_base - 5,
            'HumRelativa': 45 + (i % 20),
            'Precipitacion': 0.5 if i % 10 == 0 else 0.0,
            'PresionMedia': 1013.2,
            'VelViento': 3.5 + (i % 5),
            'DirViento': 180 + (i % 90),
            'Radiacion': 850 - (i % 200)
        }
        sample_data.append(row)
    
    print(f"✅ Generated {len(sample_data)} weather records")
    
    # Connect to InfluxDB directly
    print("📝 Connecting to InfluxDB...")
    
    client = InfluxDBClient(
        url="http://localhost:8086",
        token="chocolate_factory_token_123",
        org="chocolate_factory"
    )
    
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Convert to InfluxDB points
    print("🔄 Converting to InfluxDB points...")
    
    points = []
    for row in sample_data:
        point = (
            Point("weather_data")
            .tag("station_id", row['Indicativo'])
            .tag("station_name", row['Estacion'])
            .tag("province", row['Provincia'])
            .tag("source", "DatosClima_ETL")
            .field("temperature", float(row['TempMedia']))
            .field("temperature_max", float(row['TempMax']))
            .field("temperature_min", float(row['TempMin']))
            .field("humidity", float(row['HumRelativa']))
            .field("precipitation", float(row['Precipitacion']))
            .field("pressure", float(row['PresionMedia']))
            .field("wind_speed", float(row['VelViento']))
            .field("wind_direction", float(row['DirViento']))
            .field("solar_radiation", float(row['Radiacion']))
            .field("altitude", float(row['Altitud']))
            .time(pd.to_datetime(row['Fecha']).to_pydatetime().replace(tzinfo=timezone.utc))
        )
        points.append(point)
    
    # Write to InfluxDB
    print("💾 Writing to InfluxDB...")
    
    try:
        write_api.write(bucket="energy_data", record=points)
        print(f"✅ Successfully wrote {len(points)} weather records to InfluxDB")
        
        # Verify write
        query_api = client.query_api()
        verify_query = '''
            from(bucket: "energy_data")
            |> range(start: -2y)
            |> filter(fn: (r) => r._measurement == "weather_data")
            |> filter(fn: (r) => r.source == "DatosClima_ETL")
            |> count()
        '''
        
        result = query_api.query(verify_query)
        total_records = 0
        for table in result:
            for record in table.records:
                total_records = record.get_value()
                break
        
        print(f"📊 Verification: {total_records} records found in InfluxDB")
        
    except Exception as e:
        print(f"❌ Error writing to InfluxDB: {e}")
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_simple_etl())