"""
InfluxDB Infrastructure Module
===============================

Provides InfluxDB client and query utilities.
"""

from .client import (
    InfluxDBClientWrapper,
    get_influxdb_client
)

from .queries import (
    QueryBuilder,
    get_latest_prices,
    get_weather_data,
    get_data_gap_query,
    get_historical_data_query,
    get_aggregated_stats_query
)

__all__ = [
    "InfluxDBClientWrapper",
    "get_influxdb_client",
    "QueryBuilder",
    "get_latest_prices",
    "get_weather_data",
    "get_data_gap_query",
    "get_historical_data_query",
    "get_aggregated_stats_query",
]
