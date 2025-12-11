#!/usr/bin/env python3
"""
Download 36 months of Combined Cycle (Gas) Generation data from REE API
========================================================================

Descarga datos diarios de generación de Ciclo Combinado para usar como
feature en el modelo Prophet.

Output: scripts/data/gas_generation_36m.csv

Endpoint: apidatos.ree.es/es/datos/generacion/estructura-generacion
Parámetro: time_trunc=day (obligatorio)

Uso:
    python3 scripts/download_gas_historical.py

Author: Gemini
Date: December 2025
"""

import json
import urllib.request
import urllib.error
import csv
import os
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
REE_BASE_URL = "https://apidatos.ree.es/es/datos"
GENERATION_ENDPOINT = "generacion/estructura-generacion"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ChocolateFactory/0.41.0"
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "gas_generation_36m.csv")

# 36 months of data
MONTHS_TO_DOWNLOAD = 36

# ==============================================================================
# FUNCTIONS
# ==============================================================================
def fetch_month_data(year: int, month: int) -> list:
    """
    Fetch one month of generation data.
    
    Returns list of daily Ciclo Combinado records.
    """
    # Calculate month range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    url = (
        f"{REE_BASE_URL}/{GENERATION_ENDPOINT}"
        f"?start_date={start_date}T00:00"
        f"&end_date={end_date}T23:59"
        f"&time_trunc=day"
    )
    
    req = urllib.request.Request(url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.getcode() == 200:
                data = json.loads(response.read())
                included = data.get("included", [])
                
                # Find Ciclo Combinado
                for item in included:
                    if "combinado" in item.get("type", "").lower():
                        values = item.get("attributes", {}).get("values", [])
                        return [{
                            "date": v["datetime"][:10],  # YYYY-MM-DD
                            "datetime": v["datetime"],
                            "gas_gen_mwh": v["value"],
                            "gas_gen_percentage": v.get("percentage", 0)
                        } for v in values]
                        
                return []
                
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error {e.code} for {year}-{month:02d}")
        return []
    except Exception as e:
        logger.error(f"Error for {year}-{month:02d}: {e}")
        return []

def main():
    logger.info("=" * 60)
    logger.info("Downloading 36 months of Gas Generation Data")
    logger.info("=" * 60)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Calculate date range (36 months ago to now)
    end_date = date.today()
    start_date = end_date - relativedelta(months=MONTHS_TO_DOWNLOAD)
    
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Output file: {OUTPUT_FILE}")
    
    all_records = []
    
    # Download month by month
    current = start_date
    while current <= end_date:
        year, month = current.year, current.month
        logger.info(f"📥 Downloading {year}-{month:02d}...")
        
        records = fetch_month_data(year, month)
        
        if records:
            all_records.extend(records)
            logger.info(f"   ✅ {len(records)} days")
        else:
            logger.warning(f"   ⚠️ No data")
        
        # Move to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)
        
        # Rate limiting (be nice to the API)
        time.sleep(0.5)
    
    # Sort by date
    all_records.sort(key=lambda x: x["date"])
    
    # Write CSV
    logger.info(f"\n📁 Writing {len(all_records)} records to CSV...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["date", "datetime", "gas_gen_mwh", "gas_gen_percentage"])
        writer.writeheader()
        writer.writerows(all_records)
    
    # Summary
    if all_records:
        values = [r["gas_gen_mwh"] for r in all_records]
        logger.info("\n" + "=" * 60)
        logger.info("✅ DOWNLOAD COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Records: {len(all_records)}")
        logger.info(f"Date range: {all_records[0]['date']} to {all_records[-1]['date']}")
        logger.info(f"Average: {sum(values)/len(values):,.0f} MWh/day")
        logger.info(f"Min: {min(values):,.0f} MWh/day")
        logger.info(f"Max: {max(values):,.0f} MWh/day")
        logger.info(f"Output: {OUTPUT_FILE}")
    else:
        logger.error("❌ No data downloaded")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
