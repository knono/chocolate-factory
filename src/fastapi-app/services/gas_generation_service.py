"""
Gas Generation Service
======================

Servicio para gestionar datos de generación de Ciclo Combinado (gas)
desde la API de REE y InfluxDB.

Funcionalidades:
- Fetch diario desde REE API
- Write a InfluxDB (bucket energy_data, measurement generation_mix)
- Query histórico para training Prophet
- Query último valor para predicción
- Detección de gaps

Uso:
    service = GasGenerationService()
    await service.ingest_today()  # Ingesta diaria
    gas_df = await service.get_historical(months=36)  # Para training
    latest = await service.get_latest()  # Para predicción
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

from influxdb_client import Point, WritePrecision
from infrastructure.influxdb import get_influxdb_client
from infrastructure.external_apis.ree_client import REEAPIClient

logger = logging.getLogger(__name__)

# InfluxDB schema
MEASUREMENT = "generation_mix"
TAG_SOURCE = "ree_generation"
TAG_TECHNOLOGY = "ciclo_combinado"


class GasGenerationService:
    """
    Servicio para gestionar datos de generación de gas (Ciclo Combinado).
    
    Attributes:
        influx: Cliente InfluxDB
    """
    
    def __init__(self):
        """Inicializa el servicio."""
        self.influx = get_influxdb_client()
    
    async def ingest_gas_data(
        self, 
        target_date: Optional[date] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Ingesta datos de gas para una fecha específica.
        
        Args:
            target_date: Fecha a ingerir (default: ayer)
            force: Si True, sobrescribe datos existentes
            
        Returns:
            Dict con resultado de la ingesta
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"📥 Ingesting gas data for {target_date}")
        
        # Check if data already exists
        if not force:
            existing = await self._check_existing(target_date)
            if existing:
                logger.info(f"⏭️ Data already exists for {target_date}, skipping")
                return {
                    "success": True,
                    "date": str(target_date),
                    "action": "skipped",
                    "reason": "data_exists"
                }
        
        # Fetch from REE API
        try:
            async with REEAPIClient() as client:
                gas_data = await client.get_generation_structure(target_date)
        except Exception as e:
            logger.error(f"❌ Failed to fetch from REE: {e}")
            return {
                "success": False,
                "date": str(target_date),
                "error": str(e)
            }
        
        if not gas_data:
            logger.warning(f"⚠️ No gas data returned for {target_date}")
            return {
                "success": False,
                "date": str(target_date),
                "error": "no_data_returned"
            }
        
        # Write to InfluxDB
        try:
            point = Point(MEASUREMENT) \
                .tag("source", TAG_SOURCE) \
                .tag("technology", TAG_TECHNOLOGY) \
                .field("value_mwh", gas_data["value_mwh"]) \
                .field("percentage", gas_data["percentage"]) \
                .time(datetime.combine(target_date, datetime.min.time()))
            
            self.influx.write_points([point], bucket="energy_data")
            
            logger.info(f"✅ Ingested gas data: {gas_data['value_mwh']:,.0f} MWh ({gas_data['percentage']*100:.1f}%)")
            
            return {
                "success": True,
                "date": str(target_date),
                "action": "ingested",
                "value_mwh": gas_data["value_mwh"],
                "percentage": gas_data["percentage"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to write to InfluxDB: {e}")
            return {
                "success": False,
                "date": str(target_date),
                "error": str(e)
            }
    
    async def _check_existing(self, target_date: date) -> bool:
        """Check if data exists for a specific date."""
        query = f'''
        from(bucket: "energy_data")
          |> range(start: {target_date}T00:00:00Z, stop: {target_date + timedelta(days=1)}T00:00:00Z)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
          |> filter(fn: (r) => r.source == "{TAG_SOURCE}")
          |> limit(n: 1)
        '''
        
        try:
            results = self.influx.query(query)
            return len(results) > 0
        except Exception:
            return False
    
    async def get_historical(self, months: int = 36) -> pd.DataFrame:
        """
        Query historical gas generation data.
        
        Args:
            months: Months of history to retrieve
            
        Returns:
            DataFrame with columns: ds, gas_gen, gas_gen_scaled
        """
        logger.info(f"📊 Querying {months} months of gas history")
        
        query = f'''
        from(bucket: "energy_data")
          |> range(start: -{months}mo)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
          |> filter(fn: (r) => r.source == "{TAG_SOURCE}")
          |> filter(fn: (r) => r._field == "value_mwh")
          |> sort(columns: ["_time"])
        '''
        
        try:
            results = self.influx.query(query)
            
            if not results:
                logger.warning("⚠️ No gas data found in InfluxDB")
                return pd.DataFrame()
            
            records = []
            for r in results:
                records.append({
                    "ds": r["time"].replace(tzinfo=None),
                    "gas_gen": r["value"]
                })
            
            df = pd.DataFrame(records)
            df = df.sort_values("ds").reset_index(drop=True)
            
            # Normalize for Prophet regressor
            if len(df) > 0:
                min_val = df["gas_gen"].min()
                max_val = df["gas_gen"].max()
                df["gas_gen_scaled"] = (df["gas_gen"] - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            
            logger.info(f"✅ Retrieved {len(df)} gas records")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to query gas history: {e}")
            return pd.DataFrame()
    
    async def get_latest(self) -> Optional[Dict[str, float]]:
        """
        Get the most recent gas generation value.
        
        Returns:
            Dict with gas_gen and gas_gen_scaled, or None
        """
        query = f'''
        from(bucket: "energy_data")
          |> range(start: -7d)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
          |> filter(fn: (r) => r.source == "{TAG_SOURCE}")
          |> filter(fn: (r) => r._field == "value_mwh")
          |> last()
        '''
        
        try:
            results = self.influx.query(query)
            
            if not results:
                logger.warning("⚠️ No recent gas data found")
                return None
            
            latest = results[0]
            
            # Get historical stats for normalization
            stats = await self._get_stats()
            
            gas_gen = latest["value"]
            gas_gen_scaled = (gas_gen - stats["min"]) / (stats["max"] - stats["min"]) if stats["max"] > stats["min"] else 0.5
            
            return {
                "gas_gen": gas_gen,
                "gas_gen_scaled": gas_gen_scaled,
                "date": latest["time"].date()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest gas: {e}")
            return None
    
    async def _get_stats(self) -> Dict[str, float]:
        """Get min/max stats for normalization."""
        # Use cached stats or query
        query = f'''
        from(bucket: "energy_data")
          |> range(start: -36mo)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
          |> filter(fn: (r) => r.source == "{TAG_SOURCE}")
          |> filter(fn: (r) => r._field == "value_mwh")
        '''
        
        try:
            results = self.influx.query(query)
            values = [r["value"] for r in results]
            
            if values:
                return {"min": min(values), "max": max(values)}
            else:
                return {"min": 0, "max": 1}
                
        except Exception:
            return {"min": 0, "max": 1}
    
    async def detect_gaps(self, days_back: int = 30) -> List[date]:
        """
        Detect missing dates in gas data.
        
        Args:
            days_back: Days to check for gaps
            
        Returns:
            List of missing dates
        """
        logger.info(f"🔍 Checking for gaps in last {days_back} days")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        query = f'''
        from(bucket: "energy_data")
          |> range(start: {start_date}T00:00:00Z, stop: {end_date}T00:00:00Z)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
          |> filter(fn: (r) => r.source == "{TAG_SOURCE}")
          |> filter(fn: (r) => r._field == "value_mwh")
        '''
        
        try:
            results = self.influx.query(query)
            existing_dates = set(r["time"].date() for r in results)
            
            all_dates = set(start_date + timedelta(days=i) for i in range(days_back))
            missing = sorted(all_dates - existing_dates)
            
            if missing:
                logger.warning(f"⚠️ Found {len(missing)} missing dates: {missing[:5]}...")
            else:
                logger.info("✅ No gaps found")
            
            return missing
            
        except Exception as e:
            logger.error(f"❌ Failed to detect gaps: {e}")
            return []
