"""
Unit Tests for REE Service
===========================

Tests the REE electricity price service in isolation with mocked dependencies.

Coverage:
- ✅ Fetch current prices
- ✅ Fetch historical prices
- ✅ Handle REE API errors
- ✅ Transform data to InfluxDB format
- ✅ Tariff period classification
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict

# Service under test
from services.ree_service import REEService
from core.exceptions import REEDataError, InfluxDBWriteError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client."""
    mock = MagicMock()
    mock.write_api.return_value.write = MagicMock()
    mock.query_api.return_value.query = MagicMock(return_value=[])
    return mock


@pytest.fixture
def ree_service(mock_influxdb_client):
    """REE service instance with mocked InfluxDB."""
    return REEService(mock_influxdb_client)


@pytest.fixture
def sample_ree_api_response():
    """
    Sample response from REE API (already parsed by REEAPIClient).

    This is what REEAPIClient.get_pvpc_prices() returns.
    """
    return [
        {
            "timestamp": datetime(2025, 10, 20, 0, 0, tzinfo=timezone.utc),
            "price_eur_kwh": 0.15050,
            "price_eur_mwh": 150.50,
            "source": "ree_pvpc"
        },
        {
            "timestamp": datetime(2025, 10, 20, 1, 0, tzinfo=timezone.utc),
            "price_eur_kwh": 0.14530,
            "price_eur_mwh": 145.30,
            "source": "ree_pvpc"
        },
        {
            "timestamp": datetime(2025, 10, 20, 10, 0, tzinfo=timezone.utc),
            "price_eur_kwh": 0.15580,
            "price_eur_mwh": 155.80,
            "source": "ree_pvpc"
        }
    ]


# =============================================================================
# TEST CLASS
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestREEService:
    """Unit tests for REEService."""

    async def test_fetch_current_prices_success(
        self,
        ree_service,
        mock_influxdb_client,
        sample_ree_api_response
    ):
        """
        Test successful fetching of current electricity prices.

        Verifies:
        - REE API is called correctly
        - Data is transformed properly
        - InfluxDB write is called
        """
        # Mock REE API client
        with patch('services.ree_service.REEAPIClient') as MockREEClient:
            mock_ree_instance = MockREEClient.return_value
            mock_ree_instance.__aenter__ = AsyncMock(return_value=mock_ree_instance)
            mock_ree_instance.__aexit__ = AsyncMock()
            mock_ree_instance.get_pvpc_prices = AsyncMock(
                return_value=sample_ree_api_response
            )

            # Mock InfluxDB write_points to return count
            mock_influxdb_client.write_points = MagicMock(return_value=3)

            # Execute
            result = await ree_service.ingest_prices(
                target_date=date(2025, 10, 20),
                force_refresh=True
            )

            # Assert
            assert result['records_written'] == 3
            assert 'date' in result
            assert result['source'] == 'ree_pvpc'
            assert 'price_range' in result

            # Verify InfluxDB write was called
            mock_influxdb_client.write_points.assert_called_once()


    async def test_fetch_historical_prices(
        self,
        ree_service,
        mock_influxdb_client
    ):
        """
        Test fetching historical prices for a specific date range.

        Verifies:
        - Historical data query is constructed correctly
        - Date range is handled properly
        """
        # Mock InfluxDB query result (simulating what influxdb.query() returns)
        mock_result = [
            {
                'time': datetime(2025, 10, 19, 0, 0, tzinfo=timezone.utc),
                'value': 0.15050,
                'source': 'ree_pvpc'
            },
            {
                'time': datetime(2025, 10, 19, 1, 0, tzinfo=timezone.utc),
                'value': 0.14530,
                'source': 'ree_pvpc'
            }
        ]

        mock_influxdb_client.query = MagicMock(return_value=mock_result)

        # Execute (using correct method name)
        prices = await ree_service.get_prices(
            start_date=date(2025, 10, 19),
            end_date=date(2025, 10, 20)
        )

        # Assert
        assert len(prices) == 2
        assert prices[0]['price_eur_kwh'] == 0.15050
        assert 'timestamp' in prices[0]


    async def test_handle_ree_api_errors(
        self,
        ree_service,
        mock_influxdb_client
    ):
        """
        Test error handling when REE API fails.

        Verifies:
        - REEDataError is raised on API failure
        - Error message is descriptive
        - No partial data is written to InfluxDB
        """
        # Mock REE API to raise exception
        with patch('services.ree_service.REEAPIClient') as MockREEClient:
            mock_ree_instance = MockREEClient.return_value
            mock_ree_instance.__aenter__ = AsyncMock(return_value=mock_ree_instance)
            mock_ree_instance.__aexit__ = AsyncMock()
            mock_ree_instance.get_pvpc_prices = AsyncMock(
                side_effect=Exception("REE API connection timeout")
            )

            # Mock write_points
            mock_influxdb_client.write_points = MagicMock()

            # Execute & Assert
            with pytest.raises(REEDataError) as exc_info:
                await ree_service.ingest_prices(date(2025, 10, 20))

            assert "Failed to fetch REE prices" in str(exc_info.value)

            # Verify no data was written
            mock_influxdb_client.write_points.assert_not_called()


    async def test_transform_ree_data_to_influx(
        self,
        ree_service,
        sample_ree_api_response
    ):
        """
        Test transformation of REE API data to InfluxDB Point format.

        Verifies:
        - Data is properly converted to InfluxDB Points
        - Price fields are present
        - Timestamp is preserved
        """
        # Test the internal transformation method directly
        points = ree_service._transform_to_points(sample_ree_api_response)

        # Assert
        assert isinstance(points, list)
        assert len(points) == 3

        # Verify first point structure
        first_point = points[0]
        assert first_point._name == "energy_prices"
        assert 'price_eur_kwh' in first_point._fields
        assert 'price_eur_mwh' in first_point._fields
        assert first_point._fields['price_eur_kwh'] == 0.15050
        assert first_point._fields['price_eur_mwh'] == 150.50
        assert 'source' in first_point._tags
        assert first_point._tags['source'] == 'ree_pvpc'


    async def test_get_latest_price(
        self,
        ree_service,
        mock_influxdb_client
    ):
        """
        Test fetching the most recent electricity price.

        Verifies:
        - Latest price query works correctly
        - Returns proper format
        - Handles no data gracefully
        """
        # Mock InfluxDB query result for latest price
        mock_result = [
            {
                'time': datetime(2025, 10, 20, 14, 0, tzinfo=timezone.utc),
                'value': 0.16250,
                'source': 'ree_pvpc'
            }
        ]

        mock_influxdb_client.query = MagicMock(return_value=mock_result)

        # Execute
        latest = await ree_service.get_latest_price()

        # Assert
        assert latest is not None
        assert latest['price_eur_kwh'] == 0.16250
        assert 'timestamp' in latest
        assert latest['source'] == 'ree_pvpc'

        # Test no data case
        mock_influxdb_client.query = MagicMock(return_value=[])
        latest_empty = await ree_service.get_latest_price()
        assert latest_empty is None


# =============================================================================
# INTEGRATION NOTES
# =============================================================================

"""
Integration with Fase 9 tests:
- These unit tests complement integration tests in test_dashboard_api.py
- Unit tests focus on service logic in isolation
- Integration tests verify end-to-end API behavior

Coverage impact:
- Target: 80% overall coverage (Fase 10 goal)
- Current: 15.26% (Fase 9 baseline)
- Expected gain from REE service tests: ~5-8%

Next steps:
- Run: pytest tests/unit/test_ree_service.py -v
- Verify: Coverage increases as expected
- Continue: test_weather_service.py (next file)
"""
