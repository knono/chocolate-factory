"""
Pytest Configuration and Shared Fixtures
=========================================

Provides:
- FastAPI test client
- Mock InfluxDB client
- Mock external APIs (AEMET, OpenWeatherMap, REE)
- Sample test data
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Ensure proper imports from parent directory
import os
os.chdir(Path(__file__).parent.parent)

try:
    from main import app
except ImportError:
    # Fallback: create a minimal app for testing
    from fastapi import FastAPI
    app = FastAPI(title="Test App")


# =============================================================================
# TEST CLIENT
# =============================================================================

@pytest.fixture
def client():
    """FastAPI test client for API endpoint testing."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def async_client():
    """Async test client for async endpoints."""
    from httpx import AsyncClient
    import asyncio

    async def _get_client():
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    return asyncio.run(_get_client().__anext__())


# =============================================================================
# MOCK INFLUXDB
# =============================================================================

@pytest.fixture
def mock_influxdb():
    """Mock InfluxDB client for tests."""
    mock_client = Mock()
    mock_query_api = Mock()
    mock_write_api = Mock()

    # Configure query responses
    mock_query_api.query.return_value = []
    mock_client.query_api.return_value = mock_query_api
    mock_client.write_api.return_value = mock_write_api

    with patch('infrastructure.influxdb.client.InfluxDBClient') as mock:
        mock.return_value = mock_client
        yield mock_client


# =============================================================================
# MOCK EXTERNAL APIS
# =============================================================================

@pytest.fixture
def mock_ree_api():
    """Mock REE API client."""
    mock = Mock()
    mock.get_current_prices = AsyncMock(return_value={
        'success': True,
        'data': [
            {
                'timestamp': datetime.now().isoformat(),
                'price_eur_mwh': 150.0,
                'price_eur_kwh': 0.15
            }
        ]
    })
    return mock


@pytest.fixture
def mock_aemet_api():
    """Mock AEMET API client."""
    mock = Mock()
    mock.get_current_observations = AsyncMock(return_value={
        'success': True,
        'data': {
            'temperature': 22.0,
            'humidity': 55.0,
            'pressure': 1013.0
        }
    })
    return mock


@pytest.fixture
def mock_openweather_api():
    """Mock OpenWeatherMap API client."""
    mock = Mock()
    mock.get_current_weather = AsyncMock(return_value={
        'main': {
            'temp': 22.0,
            'humidity': 55,
            'pressure': 1013
        },
        'weather': [{'description': 'clear sky'}]
    })
    return mock


# =============================================================================
# SAMPLE TEST DATA
# =============================================================================

@pytest.fixture
def sample_ree_data():
    """Sample REE electricity price data."""
    now = datetime.now()
    return [
        {
            'timestamp': (now - timedelta(hours=i)).isoformat(),
            'price_eur_mwh': 150.0 + (i * 5),
            'price_eur_kwh': 0.15 + (i * 0.005),
            'tariff_period': 'P1' if 10 <= (now - timedelta(hours=i)).hour <= 13 else 'P3'
        }
        for i in range(24)
    ]


@pytest.fixture
def sample_weather_data():
    """Sample weather observation data."""
    now = datetime.now()
    return [
        {
            'timestamp': (now - timedelta(hours=i)).isoformat(),
            'temperature': 20.0 + i,
            'humidity': 50.0 + i,
            'pressure': 1013.0 - i,
            'source': 'aemet'
        }
        for i in range(24)
    ]


@pytest.fixture
def sample_ml_features():
    """Sample ML input features."""
    return {
        'price_eur_kwh': 0.15,
        'temperature': 22.0,
        'humidity': 55.0,
        'pressure': 1013.0,
        'tariff_period': 'P3',
        'hour': 14,
        'day_of_week': 3,
        'month': 10
    }


@pytest.fixture
def sample_prophet_predictions():
    """Sample Prophet price predictions."""
    now = datetime.now()
    return [
        {
            'timestamp': (now + timedelta(hours=i)).isoformat(),
            'predicted_price': 0.12 + (i * 0.002),
            'lower_bound': 0.10 + (i * 0.002),
            'upper_bound': 0.14 + (i * 0.002)
        }
        for i in range(168)  # 7 days
    ]


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for isolated components")
    config.addinivalue_line("markers", "integration: Integration tests for API endpoints")
    config.addinivalue_line("markers", "ml: ML model tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # Reduce noise in tests
    monkeypatch.setenv("INFLUXDB_URL", "http://test-influxdb:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
