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


def calculate_energy_cost(price_eur_kwh: float, energy_kwh: float, 
                         grid_fees: float = 0, system_charges: float = 0) -> float:
    """Calculate total energy cost including fees and charges"""
    base_cost = price_eur_kwh * energy_kwh
    return base_cost + grid_fees + system_charges