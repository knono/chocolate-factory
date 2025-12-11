#!/usr/bin/env python3
"""
Backfill Gas Generation Data to InfluxDB
=========================================

Carga los datos de Ciclo Combinado (gas) desde el CSV descargado a InfluxDB.
Incluye detección de gaps y reporting.

Uso (inside Docker):
    python3 /app/scripts/backfill_gas_to_influx.py

Uso (host):
    python3 scripts/backfill_gas_to_influx.py

Author: Gemini
Date: December 2025
"""

import os
import sys
import csv
from datetime import datetime, timedelta
import logging

sys.path.insert(0, "/app")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# PATHS
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAS_CSV = os.path.join(SCRIPT_DIR, "data", "gas_generation_36m.csv")

# ==============================================================================
# INFLUXDB CONFIG
# ==============================================================================
MEASUREMENT = "generation_mix"
TAG_SOURCE = "ree_generation"
TAG_TECHNOLOGY = "ciclo_combinado"

# ==============================================================================
# FUNCTIONS
# ==============================================================================
def load_csv_data() -> list:
    """Load gas generation data from CSV."""
    logger.info(f"📥 Loading CSV: {GAS_CSV}")
    
    if not os.path.exists(GAS_CSV):
        raise FileNotFoundError(f"CSV not found: {GAS_CSV}")
    
    records = []
    with open(GAS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "date": row["date"],
                "gas_gen_mwh": float(row["gas_gen_mwh"]),
                "percentage": float(row["gas_gen_percentage"])
            })
    
    logger.info(f"✅ Loaded {len(records)} records from CSV")
    return records

def detect_gaps(records: list) -> list:
    """Detect gaps in daily data."""
    if len(records) < 2:
        return []
    
    gaps = []
    dates = sorted([datetime.strptime(r["date"], "%Y-%m-%d").date() for r in records])
    
    for i in range(1, len(dates)):
        expected = dates[i-1] + timedelta(days=1)
        if dates[i] != expected:
            gap_days = (dates[i] - dates[i-1]).days - 1
            gaps.append({
                "start": dates[i-1],
                "end": dates[i],
                "missing_days": gap_days
            })
    
    if gaps:
        logger.warning(f"⚠️ Found {len(gaps)} gaps in data:")
        for g in gaps:
            logger.warning(f"   {g['start']} → {g['end']} ({g['missing_days']} missing days)")
    else:
        logger.info("✅ No gaps detected in data")
    
    return gaps

def write_to_influxdb(records: list):
    """Write gas data to InfluxDB."""
    logger.info("📤 Writing to InfluxDB...")
    
    try:
        from infrastructure.influxdb import get_influxdb_client
        from influxdb_client import Point
        
        influx = get_influxdb_client()
        
        points = []
        for r in records:
            # Parse date and set time to 00:00:00 UTC
            dt = datetime.strptime(r["date"], "%Y-%m-%d")
            
            point = Point(MEASUREMENT) \
                .tag("source", TAG_SOURCE) \
                .tag("technology", TAG_TECHNOLOGY) \
                .field("value_mwh", r["gas_gen_mwh"]) \
                .field("percentage", r["percentage"]) \
                .time(dt)
            
            points.append(point)
        
        # Write in batches using the wrapper's method
        BATCH_SIZE = 500
        total_written = 0
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i:i+BATCH_SIZE]
            influx.write_points(batch, bucket="energy_data")
            total_written += len(batch)
            logger.info(f"   Written batch {i//BATCH_SIZE + 1} ({len(batch)} points)")
        
        logger.info(f"✅ Successfully wrote {total_written} points to InfluxDB")
        
    except ImportError as e:
        logger.error(f"❌ Cannot import InfluxDB client - run inside Docker: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error writing to InfluxDB: {e}")
        return False
    
    return True

def verify_data():
    """Verify data was written correctly."""
    logger.info("🔍 Verifying data in InfluxDB...")
    
    try:
        from infrastructure.influxdb import get_influxdb_client
        
        influx = get_influxdb_client()
        
        query = f'''
        from(bucket: "energy_data")
          |> range(start: -36mo)
          |> filter(fn: (r) => r["_measurement"] == "{MEASUREMENT}")
          |> filter(fn: (r) => r["source"] == "{TAG_SOURCE}")
          |> filter(fn: (r) => r["_field"] == "value_mwh")
          |> count()
        '''
        
        results = influx.query(query)
        
        count = 0
        for record in results:
            count = record["_value"]
        
        logger.info(f"✅ Verified: {count} records in InfluxDB")
        return count
        
    except Exception as e:
        logger.error(f"❌ Error verifying: {e}")
        return 0

def main():
    logger.info("=" * 60)
    logger.info("Backfill Gas Generation to InfluxDB")
    logger.info("=" * 60)
    
    # 1. Load CSV
    try:
        records = load_csv_data()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    
    # 2. Detect gaps
    gaps = detect_gaps(records)
    
    # 3. Write to InfluxDB
    if not write_to_influxdb(records):
        return 1
    
    # 4. Verify
    count = verify_data()
    
    # 5. Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 BACKFILL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"CSV records: {len(records)}")
    logger.info(f"InfluxDB records: {count}")
    logger.info(f"Gaps found: {len(gaps)}")
    logger.info(f"Measurement: {MEASUREMENT}")
    logger.info(f"Tags: source={TAG_SOURCE}, technology={TAG_TECHNOLOGY}")
    logger.info("")
    
    if len(gaps) > 0:
        logger.warning("⚠️ Review gaps above before training model")
    else:
        logger.info("✅ Ready for Prophet training with gas feature")
    
    return 0

if __name__ == "__main__":
    exit(main())
