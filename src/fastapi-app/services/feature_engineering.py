"""
Feature Engineering Service - Chocolate Factory ML
==================================================

Pipeline de features para modelos de optimización de producción
de chocolate basado en datos REE (energía) + Weather (clima).
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)


@dataclass
class FeatureSet:
    """Conjunto de features para modelos ML"""
    timestamp: datetime
    
    # Energy Features (REE)
    price_eur_kwh: float
    price_trend_1h: float
    price_volatility_24h: float
    tariff_period: str
    energy_cost_index: float
    
    # Weather Features (Hybrid)
    temperature: float
    humidity: float
    temperature_comfort_index: float
    humidity_stress_factor: float
    
    # Chocolate Production Features (Derived)
    chocolate_production_index: float
    energy_optimization_score: float
    quality_risk_factor: float
    production_recommendation: str


class ChocolateFeatureEngine:
    """Motor de feature engineering para fábrica de chocolate"""
    
    def __init__(self):
        self.optimal_temp_range = (18, 24)  # °C para chocolate
        self.optimal_humidity_range = (45, 65)  # % para chocolate
        self.peak_tariff_hours = [(18, 22), (10, 14)]  # Horarios punta
        
    async def extract_raw_data(self, hours_back: int = 48) -> pd.DataFrame:
        """Extraer datos raw de InfluxDB para feature engineering"""
        try:
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Calculate UTC timestamps for proper timezone handling
                from datetime import datetime, timezone, timedelta
                # Add 1 hour buffer to end_time to catch recent data
                end_time = datetime.now(timezone.utc) + timedelta(hours=1)
                start_time = end_time - timedelta(hours=hours_back + 1)
                
                # Format timestamps for InfluxDB (RFC3339)
                start_rfc3339 = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc3339 = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                logger.info(f"🔍 Querying InfluxDB data from {start_rfc3339} to {end_rfc3339} ({hours_back}h)")
                logger.debug(f"🔍 Start time: {start_time}")
                logger.debug(f"🔍 End time: {end_time}")
                logger.debug(f"🔍 Current UTC time: {datetime.now(timezone.utc)}")
                
                # Use the SAME query pattern that works in /influxdb/verify
                energy_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours_back}h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 168)
                '''
                
                # Use the SAME query pattern for weather that works in /influxdb/verify
                temp_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours_back}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 300)
                '''
                
                humidity_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours_back}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "humidity")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 300)
                '''
                
                # Execute queries with debug logging
                logger.info(f"🔍 Executing energy query...")
                energy_results = query_api.query(energy_query)
                
                logger.info(f"🔍 Executing temperature query...")
                temp_results = query_api.query(temp_query)
                
                logger.info(f"🔍 Executing humidity query...")
                humidity_results = query_api.query(humidity_query)
                
                # Process energy data
                energy_data = []
                energy_table_count = 0
                for table in energy_results:
                    energy_table_count += 1
                    record_count = 0
                    for record in table.records:
                        record_count += 1
                        energy_data.append({
                            'timestamp': record.get_time(),
                            'price_eur_kwh': record.get_value()
                        })
                    logger.info(f"🔋 Energy table {energy_table_count}: {record_count} records")
                logger.info(f"🔋 Total energy tables: {energy_table_count}, total records: {len(energy_data)}")
                if len(energy_data) > 0:
                    logger.info(f"🔋 Energy sample: {energy_data[0]}")
                
                # Process temperature data
                temp_data = []
                for table in temp_results:
                    for record in table.records:
                        temp_data.append({
                            'timestamp': record.get_time(),
                            'temperature': record.get_value()
                        })
                
                logger.info(f"🌡️ Total temperature records: {len(temp_data)}")
                if len(temp_data) > 0:
                    logger.info(f"🌡️ Temperature sample: {temp_data[0]}")
                
                # Process humidity data
                humidity_data = []
                for table in humidity_results:
                    for record in table.records:
                        humidity_data.append({
                            'timestamp': record.get_time(),
                            'humidity': record.get_value()
                        })
                
                # Convert to DataFrames
                df_energy = pd.DataFrame(energy_data)
                df_temp = pd.DataFrame(temp_data)
                df_humidity = pd.DataFrame(humidity_data)
                
                # Merge data on timestamp
                if not df_energy.empty and not df_temp.empty:
                    df_energy['timestamp'] = pd.to_datetime(df_energy['timestamp'])
                    df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
                    df_humidity['timestamp'] = pd.to_datetime(df_humidity['timestamp'])
                    
                    # Merge energy and temperature
                    df = pd.merge(df_energy, df_temp, on='timestamp', how='inner')
                    
                    # Merge with humidity if available
                    if not df_humidity.empty:
                        df = pd.merge(df, df_humidity, on='timestamp', how='inner')
                    else:
                        # Use default humidity if not available
                        df['humidity'] = 60.0  # Default humidity for chocolate
                    
                    df = df.dropna()  # Remove incomplete records
                    logger.info(f"✅ Extracted {len(df)} raw data points for feature engineering")
                    return df
                else:
                    logger.warning("No energy or temperature data found")
                    return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to extract raw data: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Energy query: {energy_query}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def calculate_energy_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular features energéticas"""
        if df.empty:
            return df
            
        # Price trend (1h change)
        df['price_trend_1h'] = df['price_eur_kwh'].diff()
        
        # Price volatility (24h rolling std)
        df['price_volatility_24h'] = df['price_eur_kwh'].rolling(window=24, min_periods=1).std()
        
        # Tariff period classification
        df['hour'] = df['timestamp'].dt.hour
        df['tariff_period'] = df['hour'].apply(self._classify_tariff_period)
        
        # Energy cost index (normalized 0-100)
        price_min = df['price_eur_kwh'].min()
        price_max = df['price_eur_kwh'].max()
        if price_max > price_min:
            df['energy_cost_index'] = ((df['price_eur_kwh'] - price_min) / (price_max - price_min)) * 100
        else:
            df['energy_cost_index'] = 50  # Neutral if no variation
        
        return df
    
    def calculate_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular features meteorológicas para chocolate"""
        if df.empty:
            return df
            
        # Temperature comfort index for chocolate production
        optimal_temp_center = np.mean(self.optimal_temp_range)
        temp_deviation = np.abs(df['temperature'] - optimal_temp_center)
        df['temperature_comfort_index'] = np.maximum(0, 100 - (temp_deviation * 10))
        
        # Humidity stress factor
        optimal_humidity_center = np.mean(self.optimal_humidity_range)
        humidity_deviation = np.abs(df['humidity'] - optimal_humidity_center)
        df['humidity_stress_factor'] = humidity_deviation / optimal_humidity_center * 100
        
        return df
    
    def calculate_chocolate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular features específicas para producción de chocolate"""
        if df.empty:
            return df
            
        # Chocolate Production Index (combinación de clima + energía)
        # Fórmula: Comfort climático - Costo energético - Estrés por humedad
        df['chocolate_production_index'] = (
            df['temperature_comfort_index'] - 
            df['energy_cost_index'] * 0.5 - 
            df['humidity_stress_factor'] * 0.3
        ).clip(0, 100)
        
        # Energy Optimization Score
        # Alto cuando precio bajo Y condiciones climáticas buenas
        df['energy_optimization_score'] = (
            (100 - df['energy_cost_index']) * 0.7 + 
            df['temperature_comfort_index'] * 0.3
        ).clip(0, 100)
        
        # Quality Risk Factor
        # Alto cuando condiciones no son óptimas para chocolate
        temp_risk = np.where(
            (df['temperature'] < self.optimal_temp_range[0]) | 
            (df['temperature'] > self.optimal_temp_range[1]), 
            50, 0
        )
        humidity_risk = np.where(
            (df['humidity'] < self.optimal_humidity_range[0]) | 
            (df['humidity'] > self.optimal_humidity_range[1]), 
            30, 0
        )
        df['quality_risk_factor'] = temp_risk + humidity_risk
        
        # Production Recommendation
        df['production_recommendation'] = df['chocolate_production_index'].apply(
            self._classify_production_recommendation
        )
        
        return df
    
    def _classify_tariff_period(self, hour: int) -> str:
        """Clasificar período tarifario español"""
        if 10 <= hour <= 13 or 18 <= hour <= 21:
            return "P1_Punta"
        elif 8 <= hour <= 9 or 14 <= hour <= 17 or 22 <= hour <= 23:
            return "P2_Llano"
        else:
            return "P3_Valle"
    
    def _classify_production_recommendation(self, score: float) -> str:
        """Clasificar recomendación de producción"""
        if score >= 75:
            return "Optimal_Production"
        elif score >= 50:
            return "Moderate_Production"
        elif score >= 25:
            return "Reduced_Production"
        else:
            return "Halt_Production"
    
    async def generate_feature_set(self, hours_back: int = 48, include_synthetic: bool = False) -> List[FeatureSet]:
        """Generar conjunto completo de features"""
        logger.info(f"🔍 generate_feature_set called with hours_back={hours_back}, include_synthetic={include_synthetic}")
        try:
            # Extract raw data
            df = await self.extract_raw_data(hours_back)
            if df.empty:
                logger.warning("No raw data available for feature engineering")
                if not include_synthetic:
                    logger.info("🚫 Synthetic data disabled, returning empty list")
                    return []
                else:
                    logger.info("🔄 Generating synthetic data since no real data available")
                    # Generate synthetic base data
                    df = self._generate_synthetic_base_data(target_samples=50)
                    logger.info(f"🔄 Synthetic base data generated: {len(df)} rows")
            
            # Calculate all features
            df = self.calculate_energy_features(df)
            df = self.calculate_weather_features(df)
            df = self.calculate_chocolate_features(df)
            
            # Add synthetic data if requested and we have limited samples
            if include_synthetic and len(df) < 50:
                synthetic_df = self._generate_synthetic_data(df, target_samples=50)
                df = pd.concat([df, synthetic_df], ignore_index=True)
                logger.info(f"📊 Added {len(synthetic_df)} synthetic samples")
            
            # Convert to FeatureSet objects
            feature_sets = []
            for _, row in df.iterrows():
                try:
                    feature_set = FeatureSet(
                        timestamp=row['timestamp'],
                        price_eur_kwh=float(row['price_eur_kwh']),
                        price_trend_1h=float(row['price_trend_1h']) if pd.notna(row['price_trend_1h']) else 0.0,
                        price_volatility_24h=float(row['price_volatility_24h']) if pd.notna(row['price_volatility_24h']) else 0.0,
                        tariff_period=str(row['tariff_period']),
                        energy_cost_index=float(row['energy_cost_index']),
                        temperature=float(row['temperature']),
                        humidity=float(row['humidity']),
                        temperature_comfort_index=float(row['temperature_comfort_index']),
                        humidity_stress_factor=float(row['humidity_stress_factor']),
                        chocolate_production_index=float(row['chocolate_production_index']),
                        energy_optimization_score=float(row['energy_optimization_score']),
                        quality_risk_factor=float(row['quality_risk_factor']),
                        production_recommendation=str(row['production_recommendation'])
                    )
                    feature_sets.append(feature_set)
                except Exception as e:
                    logger.debug(f"Skipping invalid row: {e}")
                    continue
            
            logger.info(f"✅ Generated {len(feature_sets)} feature sets for ML models")
            return feature_sets
            
        except Exception as e:
            logger.error(f"Feature engineering failed: {e}")
            return []
    
    def features_to_dataframe(self, feature_sets: List[FeatureSet]) -> pd.DataFrame:
        """Convertir feature sets a DataFrame para ML"""
        if not feature_sets:
            return pd.DataFrame()
        
        data = []
        for fs in feature_sets:
            data.append({
                'timestamp': fs.timestamp,
                'price_eur_kwh': fs.price_eur_kwh,
                'price_trend_1h': fs.price_trend_1h,
                'price_volatility_24h': fs.price_volatility_24h,
                'tariff_period': fs.tariff_period,
                'energy_cost_index': fs.energy_cost_index,
                'temperature': fs.temperature,
                'humidity': fs.humidity,
                'temperature_comfort_index': fs.temperature_comfort_index,
                'humidity_stress_factor': fs.humidity_stress_factor,
                'chocolate_production_index': fs.chocolate_production_index,
                'energy_optimization_score': fs.energy_optimization_score,
                'quality_risk_factor': fs.quality_risk_factor,
                'production_recommendation': fs.production_recommendation
            })
        
        return pd.DataFrame(data)
    
    def _generate_synthetic_base_data(self, target_samples: int = 50) -> pd.DataFrame:
        """Generar datos sintéticos base cuando no hay datos reales"""
        synthetic_data = []
        current_time = pd.Timestamp.now()
        
        # Definir rangos realistas para España
        price_ranges = {
            'low': (0.05, 0.15),      # Valle nocturno
            'medium': (0.15, 0.25),   # Llano
            'high': (0.25, 0.35)      # Punta
        }
        
        temp_ranges = {
            'cold': (5, 15),          # Invierno
            'optimal': (18, 24),      # Óptimo chocolate
            'warm': (25, 30),         # Verano
            'hot': (31, 40)           # Ola calor
        }
        
        humidity_ranges = {
            'low': (30, 45),          # Seco
            'optimal': (45, 65),      # Óptimo chocolate
            'high': (65, 85)          # Húmedo
        }
        
        # Generar combinaciones diversas
        scenarios = [
            ('low', 'optimal', 'optimal'),     # Optimal production
            ('medium', 'optimal', 'optimal'),  # Moderate production
            ('high', 'warm', 'high'),          # Reduced production
            ('high', 'hot', 'high'),           # Halt production
        ]
        
        for i in range(target_samples):
            # Seleccionar escenario (rotando para diversidad)
            scenario = scenarios[i % len(scenarios)]
            price_cat, temp_cat, humidity_cat = scenario
            
            # Generar valores dentro de rangos
            price = np.random.uniform(*price_ranges[price_cat])
            temperature = np.random.uniform(*temp_ranges[temp_cat])
            humidity = np.random.uniform(*humidity_ranges[humidity_cat])
            
            # Generar timestamp (últimas 72 horas)
            hours_ago = np.random.randint(0, 72)
            timestamp = current_time - pd.Timedelta(hours=hours_ago)
            
            synthetic_data.append({
                'timestamp': timestamp,
                'price_eur_kwh': price,
                'temperature': temperature,
                'humidity': humidity
            })
        
        logger.info(f"🔄 Generated {len(synthetic_data)} synthetic base samples")
        return pd.DataFrame(synthetic_data)
    
    def _generate_synthetic_data(self, base_df: pd.DataFrame, target_samples: int = 50) -> pd.DataFrame:
        """Generar datos sintéticos para aumentar diversidad de clases"""
        if base_df.empty:
            return pd.DataFrame()
        
        synthetic_data = []
        samples_needed = max(0, target_samples - len(base_df))
        
        # Definir rangos realistas para España
        price_ranges = {
            'low': (0.05, 0.15),      # Valle nocturno
            'medium': (0.15, 0.25),   # Llano
            'high': (0.25, 0.35)      # Punta
        }
        
        temp_ranges = {
            'cold': (5, 15),          # Invierno
            'optimal': (18, 24),      # Óptimo chocolate
            'warm': (25, 30),         # Verano
            'hot': (31, 40)           # Ola calor
        }
        
        humidity_ranges = {
            'low': (30, 45),          # Seco
            'optimal': (45, 65),      # Óptimo chocolate
            'high': (65, 85)          # Húmedo
        }
        
        # Generar combinaciones diversas para GARANTIZAR todas las 4 clases
        scenarios = [
            # Optimal_Production (score >= 75): precio bajo + condiciones óptimas
            ('low', 'optimal', 'optimal'),     # score ~85-90
            ('low', 'optimal', 'optimal'),     # score ~85-90
            
            # Moderate_Production (score 50-74): condiciones medias
            ('medium', 'optimal', 'optimal'),  # score ~65-70
            ('low', 'warm', 'optimal'),        # score ~60-65
            ('medium', 'warm', 'optimal'),     # score ~55-60
            
            # Reduced_Production (score 25-49): condiciones subóptimas
            ('high', 'optimal', 'high'),       # score ~40-45
            ('medium', 'hot', 'high'),         # score ~30-35
            ('high', 'warm', 'high'),          # score ~25-30
            
            # Halt_Production (score < 25): condiciones extremas
            ('high', 'hot', 'high'),           # score ~10-15
            ('high', 'cold', 'high'),          # score ~5-10
            ('high', 'hot', 'low'),            # score ~0-5
        ]
        
        for i in range(samples_needed):
            scenario = scenarios[i % len(scenarios)]
            price_cat, temp_cat, humidity_cat = scenario
            
            # Generar valores realistas
            price = np.random.uniform(*price_ranges[price_cat])
            temperature = np.random.uniform(*temp_ranges[temp_cat])
            humidity = np.random.uniform(*humidity_ranges[humidity_cat])
            
            # Simular timestamp incremental
            if 'timestamp' in base_df.columns and not base_df.empty:
                base_time = base_df['timestamp'].max()
                # Ensure timezone consistency
                if hasattr(base_time, 'tz') and base_time.tz is not None:
                    timestamp = base_time + pd.Timedelta(hours=i+1)
                else:
                    timestamp = base_time + pd.Timedelta(hours=i+1)
            else:
                timestamp = pd.Timestamp.now().replace(tzinfo=None) + pd.Timedelta(hours=i+1)
            
            # Crear row sintético
            synthetic_row = {
                'timestamp': timestamp,
                'price_eur_kwh': price,
                'temperature': temperature,
                'humidity': humidity
            }
            
            synthetic_data.append(synthetic_row)
        
        # Crear DataFrame y calcular features
        synthetic_df = pd.DataFrame(synthetic_data)
        
        if not synthetic_df.empty:
            # Calcular features para datos sintéticos
            synthetic_df = self.calculate_energy_features(synthetic_df)
            synthetic_df = self.calculate_weather_features(synthetic_df)
            synthetic_df = self.calculate_chocolate_features(synthetic_df)
        
        return synthetic_df