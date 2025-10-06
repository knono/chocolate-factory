"""
External APIs Infrastructure Module
====================================

Provides clients for external data sources.
"""

from .ree_client import REEAPIClient
from .aemet_client import AEMETAPIClient
from .openweather_client import OpenWeatherMapAPIClient

__all__ = [
    "REEAPIClient",
    "AEMETAPIClient",
    "OpenWeatherMapAPIClient",
]
