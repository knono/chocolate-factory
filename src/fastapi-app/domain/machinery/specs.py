"""
Machinery Specifications for Chocolate Factory
===============================================

Real machine specifications based on:
- Power consumption (kW)
- Process duration (minutes)
- Optimal temperature ranges (°C)
- Optimal humidity (%)

Source: .claude/rules/machinery_specs.md
"""

from typing import Dict, Any

# Machine specifications (REAL, not synthetic)
MACHINERY_SPECS: Dict[str, Dict[str, Any]] = {
    'Conchado': {
        'power_kw': 48,
        'duration_minutes': 300,  # 5 hours standard
        'optimal_temp_range': (40, 50),
        'optimal_humidity': 50,
        'process_category': 'intensive',
        'description': 'Conchadora - High power long process'
    },
    'Refinado': {
        'power_kw': 42,
        'duration_minutes': 240,  # 4 hours
        'optimal_temp_range': (30, 40),
        'optimal_humidity': 55,
        'process_category': 'moderate',
        'description': 'Refinadora - Moderate power medium process'
    },
    'Templado': {
        'power_kw': 36,
        'duration_minutes': 120,  # 2 hours
        'optimal_temp_range': (28, 32),
        'optimal_humidity': 60,
        'process_category': 'moderate',
        'description': 'Templadora - Temperature control process'
    },
    'Mezclado': {
        'power_kw': 30,
        'duration_minutes': 60,  # 1 hour
        'optimal_temp_range': (20, 30),
        'optimal_humidity': 50,
        'process_category': 'light',
        'description': 'Mezcladora - Light power short process'
    }
}


def determine_active_process(hour: int) -> str:
    """
    Determine typical process active at given hour.

    Heuristic based on common production schedules:
    - Night (0-6h): Long intensive processes (Conchado)
    - Morning (6-10h): Moderate processes (Refinado)
    - Midday (10-14h): Temperature control (Templado)
    - Afternoon (14-24h): Light processes (Mezclado)

    Args:
        hour: Hour of day (0-23)

    Returns:
        Process name: 'Conchado', 'Refinado', 'Templado', or 'Mezclado'
    """
    if 0 <= hour < 6:
        return 'Conchado'  # Intensive night process
    elif 6 <= hour < 10:
        return 'Refinado'  # Morning refining
    elif 10 <= hour < 14:
        return 'Templado'  # Midday tempering
    else:
        return 'Mezclado'  # Afternoon/evening mixing


def get_machine_specs(process_name: str) -> Dict[str, Any]:
    """
    Get specifications for a given process.

    Args:
        process_name: Name of process

    Returns:
        Dict with machine specifications

    Raises:
        KeyError: If process not found
    """
    if process_name not in MACHINERY_SPECS:
        raise KeyError(f"Process '{process_name}' not found in machinery specs")

    return MACHINERY_SPECS[process_name]


def calculate_process_energy(process_name: str) -> float:
    """
    Calculate total energy consumption for a process.

    Args:
        process_name: Name of process

    Returns:
        Energy in kWh
    """
    machine = get_machine_specs(process_name)
    duration_hours = machine['duration_minutes'] / 60
    energy_kwh = machine['power_kw'] * duration_hours

    return energy_kwh


def calculate_process_cost(process_name: str, price_eur_kwh: float) -> float:
    """
    Calculate total cost for a process at given electricity price.

    Args:
        process_name: Name of process
        price_eur_kwh: Electricity price (€/kWh)

    Returns:
        Cost in euros
    """
    energy_kwh = calculate_process_energy(process_name)
    cost_eur = energy_kwh * price_eur_kwh

    return cost_eur
