#!/usr/bin/env python3
"""
Simple SIAR ETL Test - Process single CSV file to dedicated bucket
"""

import pandas as pd
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os

# Configuration
INFLUX_URL = "http://chocolate_factory_storage:8086"
INFLUX_TOKEN = "chocolate_factory_token_123"
INFLUX_ORG = "chocolate_factory"
BUCKET_NAME = "siar_historical"
# Find ALL CSV files dynamically
import subprocess
result = subprocess.run(['find', '/app/data', '-name', '*.csv', '-type', 'f'],
                       capture_output=True, text=True)
CSV_FILES = result.stdout.strip().split('\n') if result.stdout.strip() else []
print(f"Found {len(CSV_FILES)} CSV files to process")

def clean_line(line):
    """Clean Unicode spaces from CSV line"""
    clean_chars = []
    for char in line:
        if char.isprintable() and (char.isalnum() or char in ';,/:.-'):
            clean_chars.append(char)
    return ''.join(clean_chars)

def safe_float(value):
    """Convert Spanish decimal format to float"""
    if not value or value == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return None

def process_siar_csv(csv_file):
    """Process single SIAR CSV file"""
    print(f"🚀 Processing SIAR file: {csv_file}")

    # Determine station type from filename
    station_type = "J17" if "J17" in csv_file else "J09"
    station_id = f"SIAR_{station_type}_Linares"
    station_name = f"SIAR_Linares_{station_type}"

    # Read file with encoding handling
    lines = None
    for encoding in ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8']:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                lines = f.readlines()
            print(f"✅ Successfully read file with {encoding} encoding")
            break
        except UnicodeDecodeError:
            continue

    if not lines:
        raise ValueError(f"Could not decode {csv_file}")

    # Skip header and process data
    data_lines = lines[1:]
    print(f"📊 Found {len(data_lines)} data lines")

    # Initialize InfluxDB client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    points = []
    processed = 0

    for line_num, line in enumerate(data_lines, 2):
        try:
            # Clean the line
            clean_line_text = clean_line(line)
            if not clean_line_text:
                continue

            parts = clean_line_text.split(';')
            if len(parts) < 22:
                continue

            # Extract and parse date
            fecha_str = parts[2]
            if not fecha_str or '/' not in fecha_str:
                continue

            # Parse Spanish date format DD/MM/YYYY
            date_obj = pd.to_datetime(fecha_str, format='%d/%m/%Y')

            # Create InfluxDB point
            point = Point("siar_weather") \
                .tag("station_id", station_id) \
                .tag("station_name", station_name) \
                .tag("province", "Jaén") \
                .tag("data_source", "siar_historical") \
                .time(date_obj.replace(tzinfo=timezone.utc))

            # Add weather fields
            if len(parts) > 5 and parts[5]:
                point = point.field("temperature", safe_float(parts[5]))
            if len(parts) > 6 and parts[6]:
                point = point.field("temperature_max", safe_float(parts[6]))
            if len(parts) > 8 and parts[8]:
                point = point.field("temperature_min", safe_float(parts[8]))
            if len(parts) > 10 and parts[10]:
                point = point.field("humidity", safe_float(parts[10]))
            if len(parts) > 11 and parts[11]:
                point = point.field("humidity_max", safe_float(parts[11]))
            if len(parts) > 13 and parts[13]:
                point = point.field("humidity_min", safe_float(parts[13]))
            if len(parts) > 15 and parts[15]:
                point = point.field("wind_speed", safe_float(parts[15]))
            if len(parts) > 16 and parts[16]:
                point = point.field("wind_direction", safe_float(parts[16]))
            if len(parts) > 17 and parts[17]:
                point = point.field("wind_gust", safe_float(parts[17]))
            if len(parts) > 21 and parts[21]:
                point = point.field("precipitation", safe_float(parts[21]))

            points.append(point)
            processed += 1

            # Write in batches of 100
            if len(points) >= 100:
                write_api.write(bucket=BUCKET_NAME, record=points)
                if processed % 1000 == 0:  # Less frequent logging
                    print(f"📝 Wrote batch (total: {processed})")
                points = []

        except Exception as e:
            if line_num <= 10:  # Only log first few errors
                print(f"⚠️ Line {line_num}: {e}")
            continue

    # Write remaining points
    if points:
        write_api.write(bucket=BUCKET_NAME, record=points)

    client.close()
    print(f"✅ {csv_file}: {processed} records written")
    return processed

if __name__ == "__main__":
    try:
        total_records = 0
        successful_files = 0

        print(f"🚀 Starting SIAR ETL for {len(CSV_FILES)} files")

        for i, csv_file in enumerate(CSV_FILES, 1):
            try:
                print(f"\n[{i}/{len(CSV_FILES)}] Processing {csv_file}")
                count = process_siar_csv(csv_file)
                total_records += count
                successful_files += 1
            except Exception as e:
                print(f"❌ Failed to process {csv_file}: {e}")
                continue

        print(f"\n🎉 ETL Complete!")
        print(f"📊 Files processed: {successful_files}/{len(CSV_FILES)}")
        print(f"📊 Total records loaded: {total_records}")
        print(f"📊 Bucket: {BUCKET_NAME}")

    except Exception as e:
        print(f"❌ ETL Error: {e}")