"""
InfluxDB Schema Definitions for TFM Chocolate Factory
===================================================

Defines the data schemas for energy prices and factory production measurements
based on the system requirements documented in tfm-chocolate-factory-summary.md
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EnergyPricesSchema:
    """Schema for energy_prices measurement"""
    
    # Tags (indexed for queries)
    TAGS = {
        'market_type': ['pvpc', 'spot', 'indexed'],
        'tariff_period': ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'],
        'day_type': ['weekday', 'weekend', 'holiday'],
        'season': ['winter', 'spring', 'summer', 'fall'],
        'provider': ['ree', 'omie']
    }
    
    # Fields (time series values)
    FIELDS = {
        'price_eur_mwh': float,
        'price_eur_kwh': float,
        'energy_cost': float,
        'grid_fees': float,
        'system_charges': float,
        'demand_mw': float,
        'renewable_generation_mw': float,
        'renewable_percentage': float,
        'price_forecast_1h': float,
        'price_forecast_24h': float,
        'confidence_interval_low': float,
        'confidence_interval_high': float
    }
    
    @staticmethod
    def validate_tags(tags: Dict[str, str]) -> bool:
        """Validate tag values against allowed values"""
        for tag_key, tag_value in tags.items():
            if tag_key in EnergyPricesSchema.TAGS:
                if tag_value not in EnergyPricesSchema.TAGS[tag_key]:
                    return False
        return True
    
    @staticmethod
    def create_point(timestamp: datetime, tags: Dict[str, str], fields: Dict[str, Any]) -> Dict:
        """Create InfluxDB point for energy prices"""
        if not EnergyPricesSchema.validate_tags(tags):
            raise ValueError("Invalid tag values")
            
        return {
            "measurement": "energy_prices",
            "time": timestamp,
            "tags": tags,
            "fields": fields
        }


@dataclass
class FactoryProductionSchema:
    """Schema for factory_production measurement"""
    
    # Tags (indexed for queries)
    TAGS = {
        'line': ['main', 'auxiliary'],
        'process': ['mixing', 'rolling', 'conching', 'tempering', 'molding'],
        'shift': ['morning', 'afternoon', 'night', 'overtime'],
        'product': ['dark', 'milk', 'white'],
        'season': ['normal', 'summer_stock']
    }
    
    # Fields (time series values)
    FIELDS = {
        'batch_id': str,
        'quantity_kg': float,
        'temperature_c': float,
        'energy_consumed_kwh': float,
        'process_duration_min': float,
        'energy_cost_eur': float,
        'energy_price_eur_kwh': float,
        'tariff_period': str,
        'holding_tank_kg': float,
        'holding_time_hours': float,
        'scheduled_start': datetime,
        'actual_start': datetime,
        'delay_minutes': float,
        'savings_eur': float
    }
    
    @staticmethod
    def validate_tags(tags: Dict[str, str]) -> bool:
        """Validate tag values against allowed values"""
        for tag_key, tag_value in tags.items():
            if tag_key in FactoryProductionSchema.TAGS:
                if tag_value not in FactoryProductionSchema.TAGS[tag_key]:
                    return False
        return True
    
    @staticmethod
    def create_point(timestamp: datetime, tags: Dict[str, str], fields: Dict[str, Any]) -> Dict:
        """Create InfluxDB point for factory production"""
        if not FactoryProductionSchema.validate_tags(tags):
            raise ValueError("Invalid tag values")
            
        return {
            "measurement": "factory_production",
            "time": timestamp,
            "tags": tags,
            "fields": fields
        }


class SchemaValidator:
    """Utility class for schema validation and data quality checks"""
    
    @staticmethod
    def validate_energy_price_data(data: Dict[str, Any]) -> List[str]:
        """Validate energy price data and return list of validation errors"""
        errors = []
        
        # Required fields check
        required_fields = ['price_eur_mwh', 'price_eur_kwh']
        for field in required_fields:
            if field not in data.get('fields', {}):
                errors.append(f"Missing required field: {field}")
        
        # Price consistency check
        fields = data.get('fields', {})
        if 'price_eur_mwh' in fields and 'price_eur_kwh' in fields:
            mwh_price = fields['price_eur_mwh']
            kwh_price = fields['price_eur_kwh']
            expected_kwh = mwh_price / 1000
            if abs(kwh_price - expected_kwh) > 0.001:
                errors.append(f"Price inconsistency: MWh={mwh_price}, kWh={kwh_price}")
        
        # Range validation
        if 'renewable_percentage' in fields:
            renewable_pct = fields['renewable_percentage']
            if not (0 <= renewable_pct <= 100):
                errors.append(f"Renewable percentage out of range: {renewable_pct}")
        
        return errors
    
    @staticmethod
    def validate_production_data(data: Dict[str, Any]) -> List[str]:
        """Validate production data and return list of validation errors"""
        errors = []
        
        # Required fields check
        required_fields = ['batch_id', 'quantity_kg', 'energy_consumed_kwh']
        for field in required_fields:
            if field not in data.get('fields', {}):
                errors.append(f"Missing required field: {field}")
        
        fields = data.get('fields', {})
        tags = data.get('tags', {})
        
        # Process-specific validations
        process = tags.get('process')
        if process and 'energy_consumed_kwh' in fields:
            energy = fields['energy_consumed_kwh']
            duration = fields.get('process_duration_min', 0)
            
            # Energy consumption ranges by process (kW)
            process_power_ranges = {
                'mixing': (25, 35),      # 30 kW nominal
                'rolling': (37, 47),     # 42 kW nominal  
                'conching': (43, 53),    # 48 kW nominal
                'tempering': (31, 41),   # 36 kW nominal
            }
            
            if process in process_power_ranges and duration > 0:
                power_kw = (energy * 60) / duration
                min_power, max_power = process_power_ranges[process]
                if not (min_power <= power_kw <= max_power):
                    errors.append(f"Power consumption out of range for {process}: {power_kw:.1f} kW")
        
        # Temperature validation by process
        if 'temperature_c' in fields:
            temp = fields['temperature_c']
            if process == 'tempering' and not (27 <= temp <= 32):
                errors.append(f"Tempering temperature out of range: {temp}°C")
            elif process in ['mixing', 'rolling', 'conching'] and not (45 <= temp <= 50):
                errors.append(f"{process.title()} temperature out of range: {temp}°C")
        
        return errors


# Utility functions for common operations
def get_tariff_period(hour: int, is_weekend: bool = False) -> str:
    """
    Determine tariff period based on hour and day type
    Based on 3.0TD tariff structure
    """
    if is_weekend:
        return 'P6'  # Valle weekend
    
    if 10 <= hour < 14 or 18 <= hour < 22:
        return 'P1'  # Punta
    elif 8 <= hour < 10 or 14 <= hour < 18 or 22 <= hour < 24:
        return 'P2'  # Llano
    else:
        return 'P6'  # Valle


@dataclass
class WeatherDataSchema:
    """Schema for weather_data measurement (AEMET data)"""
    
    # Tags (indexed for queries)
    TAGS = {
        'station_id': [],  # Dynamic - station identifiers
        'station_name': [],  # Dynamic - station names
        'province': [],  # Dynamic - Spanish provinces
        'data_source': ['aemet', 'forecast', 'historical'],
        'data_type': ['current', 'daily', 'hourly'],
        'season': ['winter', 'spring', 'summer', 'fall']
    }
    
    # Fields (time series values)
    FIELDS = {
        'temperature': float,  # °C
        'temperature_max': float,  # °C
        'temperature_min': float,  # °C
        'humidity': float,  # %
        'humidity_max': float,  # %
        'humidity_min': float,  # %
        'pressure': float,  # hPa
        'pressure_max': float,  # hPa
        'pressure_min': float,  # hPa
        'wind_speed': float,  # km/h
        'wind_direction': float,  # degrees
        'wind_gust': float,  # km/h
        'precipitation': float,  # mm
        'solar_radiation': float,  # W/m²
        'altitude': float,  # meters
        # Derived fields for chocolate production
        'heat_index': float,  # Calculated comfort index
        'chocolate_production_index': float,  # Custom index for production suitability
    }
    
    @staticmethod
    def validate_tags(tags: Dict[str, str]) -> bool:
        """Validate tag values against allowed values"""
        for tag_key, tag_value in tags.items():
            if tag_key in WeatherDataSchema.TAGS:
                allowed_values = WeatherDataSchema.TAGS[tag_key]
                if allowed_values and tag_value not in allowed_values:
                    return False
        return True
    
    @staticmethod
    def create_point(timestamp: datetime, tags: Dict[str, str], fields: Dict[str, Any]) -> Dict:
        """Create InfluxDB point for weather data"""
        if not WeatherDataSchema.validate_tags(tags):
            raise ValueError("Invalid tag values")
            
        return {
            "measurement": "weather_data",
            "time": timestamp,
            "tags": tags,
            "fields": fields
        }


def calculate_heat_index(temperature_c: float, humidity_percent: float) -> float:
    """
    Calculate heat index (feels-like temperature) for chocolate production planning
    
    Args:
        temperature_c: Temperature in Celsius
        humidity_percent: Relative humidity percentage
        
    Returns:
        Heat index in Celsius
    """
    if temperature_c < 20:  # Heat index not meaningful below 20°C
        return temperature_c
    
    # Convert to Fahrenheit for standard heat index formula
    temp_f = (temperature_c * 9/5) + 32
    
    # Rothfusz heat index formula
    hi_f = (-42.379 + 
            2.04901523 * temp_f + 
            10.14333127 * humidity_percent - 
            0.22475541 * temp_f * humidity_percent - 
            6.83783e-3 * temp_f**2 - 
            5.481717e-2 * humidity_percent**2 + 
            1.22874e-3 * temp_f**2 * humidity_percent + 
            8.5282e-4 * temp_f * humidity_percent**2 - 
            1.99e-6 * temp_f**2 * humidity_percent**2)
    
    # Convert back to Celsius
    return (hi_f - 32) * 5/9


def calculate_chocolate_production_index(temperature_c: float, humidity_percent: float,
                                       pressure_hpa: float = None) -> float:
    """
    Calculate custom index for chocolate production suitability
    
    Optimal conditions for chocolate production:
    - Temperature: 18-22°C (ideal: 20°C)
    - Humidity: 45-55% (ideal: 50%)
    - Pressure: stable (little impact on index)
    
    Args:
        temperature_c: Temperature in Celsius
        humidity_percent: Relative humidity percentage
        pressure_hpa: Atmospheric pressure in hPa (optional)
        
    Returns:
        Index from 0-100 (100 = optimal conditions)
    """
    # Temperature component (0-50 points)
    temp_optimal = 20.0
    temp_tolerance = 4.0  # ±4°C tolerance
    temp_diff = abs(temperature_c - temp_optimal)
    temp_score = max(0, 50 - (temp_diff / temp_tolerance) * 50)
    
    # Humidity component (0-40 points)
    humidity_optimal = 50.0
    humidity_tolerance = 10.0  # ±10% tolerance
    humidity_diff = abs(humidity_percent - humidity_optimal)
    humidity_score = max(0, 40 - (humidity_diff / humidity_tolerance) * 40)
    
    # Pressure component (0-10 points) - less critical
    pressure_score = 10.0  # Default if no pressure data
    if pressure_hpa is not None:
        # Stable pressure around 1013 hPa is good
        pressure_optimal = 1013.0
        pressure_tolerance = 20.0  # ±20 hPa tolerance
        pressure_diff = abs(pressure_hpa - pressure_optimal)
        pressure_score = max(0, 10 - (pressure_diff / pressure_tolerance) * 10)
    
    total_score = temp_score + humidity_score + pressure_score
    return round(total_score, 1)


def get_season_from_date(date: datetime) -> str:
    """Determine season from date for Spanish climate"""
    month = date.month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"


def calculate_energy_cost(price_eur_kwh: float, energy_kwh: float, 
                         grid_fees: float = 0, system_charges: float = 0) -> float:
    """Calculate total energy cost including fees and charges"""
    base_cost = price_eur_kwh * energy_kwh
    return base_cost + grid_fees + system_charges