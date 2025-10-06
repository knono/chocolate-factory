"""
Infrastructure Layer
====================

External integrations and data access layer.
"""

from .influxdb import (
    get_influxdb_client,
    QueryBuilder
)

from .external_apis import (
    REEAPIClient,
    AEMETAPIClient,
    OpenWeatherMapAPIClient
)

__all__ = [
    "get_influxdb_client",
    "QueryBuilder",
    "REEAPIClient",
    "AEMETAPIClient",
    "OpenWeatherMapAPIClient",
]
