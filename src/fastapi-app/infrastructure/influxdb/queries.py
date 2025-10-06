"""
InfluxDB Flux Query Templates
==============================

Provides reusable Flux query builders for common operations.

Usage:
    from infrastructure.influxdb.queries import (
        QueryBuilder,
        get_latest_prices,
        get_weather_data
    )

    query = QueryBuilder("energy_data") \
        .range("-1h") \
        .filter_measurement("energy_prices") \
        .filter_field("price_eur_kwh") \
        .build()
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class QueryBuilder:
    """
    Fluent interface for building Flux queries.

    Example:
        >>> query = QueryBuilder("energy_data") \
        ...     .range("-1h") \
        ...     .filter_measurement("energy_prices") \
        ...     .filter_field("price_eur_kwh") \
        ...     .build()
    """

    def __init__(self, bucket: str):
        self.bucket = bucket
        self._range = None
        self._filters = []
        self._aggregations = []
        self._limit = None
        self._sort = None

    def range(self, start: str, stop: Optional[str] = None) -> "QueryBuilder":
        """
        Add range filter.

        Args:
            start: Start time (e.g., "-1h", "2025-10-01T00:00:00Z")
            stop: Optional stop time

        Returns:
            Self for chaining
        """
        if stop:
            self._range = f'range(start: {start}, stop: {stop})'
        else:
            self._range = f'range(start: {start})'
        return self

    def filter_measurement(self, measurement: str) -> "QueryBuilder":
        """Add measurement filter."""
        self._filters.append(f'filter(fn: (r) => r["_measurement"] == "{measurement}")')
        return self

    def filter_field(self, field: str) -> "QueryBuilder":
        """Add field filter."""
        self._filters.append(f'filter(fn: (r) => r["_field"] == "{field}")')
        return self

    def filter_tag(self, tag_key: str, tag_value: str) -> "QueryBuilder":
        """Add tag filter."""
        self._filters.append(f'filter(fn: (r) => r["{tag_key}"] == "{tag_value}")')
        return self

    def filter_custom(self, condition: str) -> "QueryBuilder":
        """Add custom filter condition."""
        self._filters.append(f'filter(fn: (r) => {condition})')
        return self

    def aggregate_mean(self, window: str = "1h") -> "QueryBuilder":
        """Aggregate by mean."""
        self._aggregations.append(f'aggregateWindow(every: {window}, fn: mean)')
        return self

    def aggregate_sum(self, window: str = "1h") -> "QueryBuilder":
        """Aggregate by sum."""
        self._aggregations.append(f'aggregateWindow(every: {window}, fn: sum)')
        return self

    def aggregate_count(self) -> "QueryBuilder":
        """Count records."""
        self._aggregations.append('count()')
        return self

    def limit(self, n: int) -> "QueryBuilder":
        """Limit number of results."""
        self._limit = f'limit(n: {n})'
        return self

    def sort_desc(self) -> "QueryBuilder":
        """Sort by time descending."""
        self._sort = 'sort(columns: ["_time"], desc: true)'
        return self

    def sort_asc(self) -> "QueryBuilder":
        """Sort by time ascending."""
        self._sort = 'sort(columns: ["_time"], desc: false)'
        return self

    def build(self) -> str:
        """Build final Flux query."""
        parts = [f'from(bucket: "{self.bucket}")']

        if self._range:
            parts.append(self._range)

        parts.extend(self._filters)
        parts.extend(self._aggregations)

        if self._sort:
            parts.append(self._sort)

        if self._limit:
            parts.append(self._limit)

        return '\n  |> '.join(parts)


# =================================================================
# PRE-BUILT QUERIES
# =================================================================

def get_latest_prices(
    bucket: str = "energy_data",
    limit: int = 24
) -> str:
    """
    Get latest electricity prices.

    Args:
        bucket: Bucket name
        limit: Number of records to return

    Returns:
        Flux query string
    """
    return QueryBuilder(bucket) \
        .range("-24h") \
        .filter_measurement("energy_prices") \
        .filter_field("price_eur_kwh") \
        .sort_desc() \
        .limit(limit) \
        .build()


def get_weather_data(
    bucket: str = "energy_data",
    hours_back: int = 1,
    source: Optional[str] = None
) -> str:
    """
    Get recent weather data.

    Args:
        bucket: Bucket name
        hours_back: Hours of history to retrieve
        source: Optional data source filter (e.g., "aemet", "openweathermap")

    Returns:
        Flux query string
    """
    builder = QueryBuilder(bucket) \
        .range(f"-{hours_back}h") \
        .filter_measurement("weather")

    if source:
        builder.filter_tag("source", source)

    return builder.build()


def get_data_gap_query(
    bucket: str,
    measurement: str,
    start_time: str,
    end_time: str
) -> str:
    """
    Query to detect data gaps in a measurement.

    Args:
        bucket: Bucket name
        measurement: Measurement name
        start_time: Start time (ISO format)
        end_time: End time (ISO format)

    Returns:
        Flux query string
    """
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start_time}, stop: {end_time})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> aggregateWindow(every: 1h, fn: count, createEmpty: true)
  |> filter(fn: (r) => r["_value"] == 0)
'''


def get_historical_data_query(
    bucket: str,
    measurement: str,
    field: str,
    start_date: str,
    end_date: str,
    tags: Optional[Dict[str, str]] = None
) -> str:
    """
    Query for historical data with optional tag filters.

    Args:
        bucket: Bucket name
        measurement: Measurement name
        field: Field name
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        tags: Optional tag filters

    Returns:
        Flux query string
    """
    builder = QueryBuilder(bucket) \
        .range(start_date, end_date) \
        .filter_measurement(measurement) \
        .filter_field(field)

    if tags:
        for key, value in tags.items():
            builder.filter_tag(key, value)

    return builder.build()


def get_aggregated_stats_query(
    bucket: str,
    measurement: str,
    field: str,
    window: str = "1d",
    start: str = "-30d"
) -> str:
    """
    Get aggregated statistics (min, max, mean).

    Args:
        bucket: Bucket name
        measurement: Measurement name
        field: Field name
        window: Aggregation window (e.g., "1h", "1d")
        start: Start time

    Returns:
        Flux query string
    """
    return f'''
from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["_field"] == "{field}")
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
  |> yield(name: "mean")

from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["_field"] == "{field}")
  |> aggregateWindow(every: {window}, fn: min, createEmpty: false)
  |> yield(name: "min")

from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["_field"] == "{field}")
  |> aggregateWindow(every: {window}, fn: max, createEmpty: false)
  |> yield(name: "max")
'''
