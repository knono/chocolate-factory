"""
Unit Tests for Weather Services
=================================

Tests the weather aggregation service and hybrid source handling.

Coverage:
- ✅ Fetch AEMET data
- ✅ Fetch OpenWeatherMap data
- ✅ Hybrid weather fallback logic
- ✅ Transform weather data to InfluxDB
- ✅ Handle weather API timeout
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any

# Services under test
from services.weather_aggregation_service import WeatherAggregationService
from services.aemet_service import AEMETService
from core.exceptions import AEMETDataError, WeatherDataError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client."""
    mock = MagicMock()
    mock.write_points = MagicMock(return_value=1)
    mock.query = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_aemet_service():
    """Mock AEMET service."""
    mock = MagicMock(spec=AEMETService)
    mock.get_latest_weather = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def weather_service(mock_influxdb_client, mock_aemet_service):
    """Weather aggregation service instance."""
    return WeatherAggregationService(
        influxdb_client=mock_influxdb_client,
        aemet_service=mock_aemet_service
    )


@pytest.fixture
def aemet_service(mock_influxdb_client):
    """AEMET service instance."""
    return AEMETService(mock_influxdb_client)


@pytest.fixture
def sample_aemet_response():
    """Sample AEMET weather data."""
    return [
        {
            "timestamp": datetime(2025, 10, 20, 6, 0, tzinfo=timezone.utc),
            "temperature": 18.5,
            "humidity": 65.0,
            "pressure": 1013.2,
            "wind_speed": 5.2,
            "source": "aemet",
            "station_id": "3195"
        }
    ]


@pytest.fixture
def sample_openweather_response():
    """Sample OpenWeatherMap data."""
    return {
        "timestamp": datetime(2025, 10, 20, 14, 0, tzinfo=timezone.utc),
        "temperature": 24.3,
        "humidity": 45.0,
        "pressure": 1015.8,
        "wind_speed": 3.1,
        "description": "Clear sky",
        "source": "openweathermap"
    }


# =============================================================================
# TEST CLASS: AEMET SERVICE
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAEMETService:
    """Unit tests for AEMETService."""

    async def test_fetch_aemet_data_success(
        self,
        aemet_service,
        mock_influxdb_client,
        sample_aemet_response
    ):
        """
        Test successful fetching of AEMET weather data.

        Verifies:
        - AEMET API is called correctly
        - Data is transformed to InfluxDB format
        - Write to InfluxDB succeeds
        """
        # Mock AEMET API client
        with patch('services.aemet_service.AEMETAPIClient') as MockAEMETClient:
            mock_aemet_instance = MockAEMETClient.return_value
            mock_aemet_instance.__aenter__ = AsyncMock(return_value=mock_aemet_instance)
            mock_aemet_instance.__aexit__ = AsyncMock()
            mock_aemet_instance.get_current_weather = AsyncMock(
                return_value=sample_aemet_response
            )

            # Execute
            result = await aemet_service.ingest_weather(
                station_id="3195",
                force_refresh=True
            )

            # Assert
            assert result['records_written'] == 1
            assert 'latest_temperature' in result
            assert result['source'] == 'aemet'

            # Verify InfluxDB write was called
            mock_influxdb_client.write_points.assert_called_once()


    async def test_handle_aemet_api_errors(
        self,
        aemet_service,
        mock_influxdb_client
    ):
        """
        Test error handling when AEMET API fails.

        Verifies:
        - AEMETDataError is raised on failure
        - No data written on error
        """
        # Mock AEMET API to raise exception
        with patch('services.aemet_service.AEMETAPIClient') as MockAEMETClient:
            mock_aemet_instance = MockAEMETClient.return_value
            mock_aemet_instance.__aenter__ = AsyncMock(return_value=mock_aemet_instance)
            mock_aemet_instance.__aexit__ = AsyncMock()
            mock_aemet_instance.get_current_weather = AsyncMock(
                side_effect=Exception("AEMET API timeout")
            )

            # Execute & Assert
            with pytest.raises(AEMETDataError):
                await aemet_service.ingest_weather(station_id="3195")

            # Verify no data was written
            mock_influxdb_client.write_points.assert_not_called()


# =============================================================================
# TEST CLASS: WEATHER AGGREGATION SERVICE
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestWeatherAggregationService:
    """Unit tests for WeatherAggregationService."""

    async def test_fetch_openweather_data(
        self,
        weather_service,
        sample_openweather_response
    ):
        """
        Test fetching OpenWeatherMap data.

        Verifies:
        - OpenWeatherMap API is called
        - Data format is correct
        - Temperature and humidity are present
        """
        # Mock OpenWeatherMap API client
        with patch('services.weather_aggregation_service.OpenWeatherMapAPIClient') as MockOWMClient:
            mock_owm_instance = MockOWMClient.return_value
            mock_owm_instance.__aenter__ = AsyncMock(return_value=mock_owm_instance)
            mock_owm_instance.__aexit__ = AsyncMock()
            mock_owm_instance.get_current_weather = AsyncMock(
                return_value=sample_openweather_response
            )

            # Execute
            weather = await weather_service.get_current_weather(prefer_source="openweathermap")

            # Assert
            assert weather is not None
            assert weather['temperature'] == 24.3
            assert weather['humidity'] == 45.0
            assert weather['source'] == 'openweathermap'


    async def test_hybrid_weather_fallback_aemet_to_owm(
        self,
        weather_service,
        mock_aemet_service,
        sample_openweather_response
    ):
        """
        Test fallback from AEMET to OpenWeatherMap.

        Verifies:
        - When AEMET fails, system falls back to OpenWeatherMap
        - Data is returned from fallback source
        - Source is correctly tagged
        """
        # Mock AEMET to fail
        mock_aemet_service.get_latest_weather = AsyncMock(return_value=None)

        # Mock OpenWeatherMap to succeed
        with patch('services.weather_aggregation_service.OpenWeatherMapAPIClient') as MockOWMClient:
            mock_owm_instance = MockOWMClient.return_value
            mock_owm_instance.__aenter__ = AsyncMock(return_value=mock_owm_instance)
            mock_owm_instance.__aexit__ = AsyncMock()
            mock_owm_instance.get_current_weather = AsyncMock(
                return_value=sample_openweather_response
            )

            # Execute (prefer AEMET but should fallback)
            weather = await weather_service.get_current_weather(prefer_source="aemet")

            # Assert - should get OpenWeatherMap data
            assert weather is not None
            assert weather['source'] == 'openweathermap'
            assert weather['temperature'] == 24.3


    async def test_handle_weather_api_timeout(
        self,
        weather_service,
        mock_aemet_service
    ):
        """
        Test handling of weather API timeouts.

        Verifies:
        - System handles timeout gracefully
        - Returns error state when all sources fail
        - No exception raised (graceful degradation)
        """
        # Mock both sources to fail
        mock_aemet_service.get_latest_weather = AsyncMock(return_value=None)

        with patch('services.weather_aggregation_service.OpenWeatherMapAPIClient') as MockOWMClient:
            mock_owm_instance = MockOWMClient.return_value
            mock_owm_instance.__aenter__ = AsyncMock(return_value=mock_owm_instance)
            mock_owm_instance.__aexit__ = AsyncMock()
            mock_owm_instance.get_current_weather = AsyncMock(
                side_effect=Exception("Connection timeout")
            )

            # Execute
            weather = await weather_service.get_current_weather()

            # Assert - should return error state
            assert weather is not None
            assert 'error' in weather
            assert weather['source'] == 'none'


# =============================================================================
# TEST CLASS: WEATHER DATA TRANSFORMATION
# =============================================================================

@pytest.mark.unit
class TestWeatherDataTransformation:
    """Test weather data transformation to InfluxDB format."""

    def test_transform_aemet_to_influx(
        self,
        aemet_service,
        sample_aemet_response
    ):
        """
        Test transformation of AEMET data to InfluxDB Points.

        Verifies:
        - Data structure is correct
        - Fields are properly typed
        - Tags are present
        """
        # Test internal transformation method
        points = aemet_service._transform_to_points(sample_aemet_response)

        # Assert
        assert isinstance(points, list)
        assert len(points) == 1

        point = points[0]
        assert point._name == "weather"
        assert 'temperature' in point._fields
        assert 'humidity' in point._fields
        assert 'pressure' in point._fields
        assert 'source' in point._tags
        assert point._tags['source'] == 'aemet'
        assert point._fields['temperature'] == 18.5


# =============================================================================
# INTEGRATION NOTES
# =============================================================================

"""
Integration with other test files:
- Complements test_ree_service.py (energy data tests)
- Tests weather data pipeline in isolation
- Mock external APIs (AEMET, OpenWeatherMap)

Coverage impact:
- Target: 80% overall coverage
- Services tested: AEMETService, WeatherAggregationService
- Expected gain: ~5-8% coverage

Next steps:
- Run: pytest tests/unit/test_weather_service.py -v
- Verify: All 5 tests passing
- Continue: test_backfill_service.py (last service tests)
"""
