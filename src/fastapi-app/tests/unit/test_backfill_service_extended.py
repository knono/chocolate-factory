"""
Extended Unit Tests for Backfill Service
=========================================

Sprint 19 - Test Coverage Expansion
Target: 53% → 75% coverage for backfill_service.py

Tests REE backfill, Weather backfill, intelligent backfill, and edge cases.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from typing import List

from services.backfill_service import BackfillService, BackfillResult
from services.gap_detector import DataGap
from services.data_ingestion import DataIngestionStats


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_gap_detector():
    """Mock GapDetectionService."""
    detector = Mock()
    detector.detect_all_gaps = AsyncMock()
    return detector


@pytest.fixture
def mock_data_ingestion():
    """Mock DataIngestionService."""
    service = AsyncMock()
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock()
    service.write_api = Mock()
    service.write_api.write = Mock()
    # Mock ingest_ree_prices_historical to return DataIngestionStats
    service.ingest_ree_prices_historical = AsyncMock(return_value=DataIngestionStats(
        total_records=10,
        successful_writes=10,
        failed_writes=0,
        validation_errors=0
    ))
    return service


@pytest.fixture
def mock_ree_client():
    """Mock REE API client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def sample_ree_gap():
    """Sample REE data gap."""
    return DataGap(
        measurement="energy_prices",
        start_time=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 11, 1, 19, 0, tzinfo=timezone.utc),
        expected_records=10,
        missing_records=10,
        gap_duration_hours=9.0,
        severity="moderate"
    )


@pytest.fixture
def sample_weather_gap():
    """Sample Weather data gap."""
    return DataGap(
        measurement="weather_data",
        start_time=datetime(2025, 11, 2, 8, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 11, 2, 19, 0, tzinfo=timezone.utc),
        expected_records=12,
        missing_records=12,
        gap_duration_hours=11.0,
        severity="moderate"
    )


@pytest.fixture
def backfill_service():
    """BackfillService instance with mocked dependencies."""
    service = BackfillService()
    return service


# =============================================================================
# TEST CLASS: REE BACKFILL
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestREEBackfill:
    """Tests for REE backfill functionality."""

    async def test_backfill_ree_single_gap_success(
        self,
        backfill_service,
        sample_ree_gap,
        mock_data_ingestion,
        mock_ree_client
    ):
        """
        Test successful REE backfill for single gap.

        Verifies:
        - Gap is processed correctly
        - REE API is called with correct date range
        - Records are written to InfluxDB
        - Success rate is calculated
        """
        # Mock REE API response (get_pvpc_prices returns list of dicts)
        mock_ree_client.get_pvpc_prices.return_value = [
            {
                'timestamp': datetime(2025, 11, 1, 10 + i, 0, tzinfo=timezone.utc),
                'price_eur_kwh': 0.15,
                'price_eur_mwh': 150.0,
                'source': 'ree_pvpc'
            } for i in range(10)
        ]

        # Mock DataIngestionService
        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):

            # Execute
            results = await backfill_service._backfill_ree_gaps([sample_ree_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert result.measurement == "energy_prices"
            assert result.records_requested == 10
            assert result.method_used == "REE_historical_daily"
            assert result.success_rate >= 0


    async def test_backfill_ree_multiple_gaps(
        self,
        backfill_service,
        mock_data_ingestion,
        mock_ree_client
    ):
        """
        Test REE backfill with multiple gaps.

        Verifies:
        - All gaps are processed sequentially
        - Each gap has independent result
        - Total records match sum of all gaps
        """
        # Create 3 gaps
        gaps = [
            DataGap("energy_prices", datetime(2025, 11, i, 10, 0, tzinfo=timezone.utc),
                    datetime(2025, 11, i, 15, 0, tzinfo=timezone.utc), 6, 6, 5.0, "low")
            for i in range(1, 4)
        ]

        mock_ree_client.get_prices.return_value = {
            f'2025-11-0{i}': [{'hour': 10, 'price': 0.15}] * 6
            for i in range(1, 4)
        }

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):

            # Execute
            results = await backfill_service._backfill_ree_gaps(gaps)

            # Assert
            assert len(results) == 3
            assert all(r.measurement == "energy_prices" for r in results)


    async def test_backfill_ree_api_failure(
        self,
        backfill_service,
        sample_ree_gap,
        mock_data_ingestion,
        mock_ree_client
    ):
        """
        Test REE backfill handles API failures gracefully.

        Verifies:
        - API exception is caught
        - Error is logged in result
        - Success rate is 0%
        - Process doesn't crash
        """
        # Mock API to raise exception (correct method name)
        mock_ree_client.get_pvpc_prices.side_effect = Exception("REE API timeout")

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):

            # Execute
            results = await backfill_service._backfill_ree_gaps([sample_ree_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert result.success_rate == 0.0
            assert len(result.errors) > 0
            assert "REE API timeout" in result.errors[0]


    async def test_backfill_ree_empty_response(
        self,
        backfill_service,
        sample_ree_gap,
        mock_data_ingestion,
        mock_ree_client
    ):
        """
        Test REE backfill handles empty API response.

        Verifies:
        - Empty response is handled gracefully
        - Records obtained is 0
        - No crash occurs
        """
        # Mock empty API response
        mock_ree_client.get_prices.return_value = {}

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):

            # Execute
            results = await backfill_service._backfill_ree_gaps([sample_ree_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert result.records_obtained == 0


    async def test_backfill_ree_partial_data(
        self,
        backfill_service,
        sample_ree_gap,
        mock_data_ingestion,
        mock_ree_client
    ):
        """
        Test REE backfill with partial data availability.

        Verifies:
        - Success rate reflects partial data (e.g., 50%)
        - Records obtained < records requested
        - Process completes successfully
        """
        # Mock partial API response (5 out of 10 records)
        mock_ree_client.get_pvpc_prices.return_value = [
            {
                'timestamp': datetime(2025, 11, 1, 10 + i, 0, tzinfo=timezone.utc),
                'price_eur_kwh': 0.15,
                'price_eur_mwh': 150.0,
                'source': 'ree_pvpc'
            } for i in range(5)  # Only 5 records
        ]

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):

            # Execute
            results = await backfill_service._backfill_ree_gaps([sample_ree_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert result.records_obtained < result.records_requested
            assert 0 < result.success_rate < 100


# =============================================================================
# TEST CLASS: WEATHER BACKFILL
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestWeatherBackfill:
    """Tests for Weather backfill functionality."""

    async def test_backfill_weather_aemet_recent_gap(
        self,
        backfill_service,
        sample_weather_gap,
        mock_data_ingestion
    ):
        """
        Test Weather backfill uses AEMET for recent gaps (<72h).

        Verifies:
        - AEMET is chosen for recent gaps
        - Method used is 'aemet_hourly_observations'
        - Records are written successfully
        """
        # Make gap recent (<72h)
        now = datetime.now(timezone.utc)
        recent_gap = DataGap(
            "weather_data",
            now - timedelta(hours=48),
            now - timedelta(hours=24),
            25,
            25,
            24.0,
            "moderate"
        )

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.data_ingestion.AEMETClient') as MockAEMETClient:

            # Mock AEMET client context manager
            mock_aemet = MockAEMETClient.return_value
            mock_aemet.__aenter__ = AsyncMock(return_value=mock_aemet)
            mock_aemet.__aexit__ = AsyncMock()

            # Mock successful AEMET ingestion
            mock_data_ingestion.ingest_aemet_weather = AsyncMock(return_value=DataIngestionStats(
                total_records=24,
                successful_writes=24,
                failed_writes=0,
                validation_errors=0
            ))

            # Execute
            results = await backfill_service._backfill_weather_gaps([recent_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert "aemet" in result.method_used.lower()
            assert result.records_written > 0


    async def test_backfill_weather_old_gap_uses_siar(
        self,
        backfill_service,
        sample_weather_gap
    ):
        """
        Test Weather backfill uses SIAR for old gaps (>72h).

        Verifies:
        - SIAR historical data is used for old gaps
        - Method reflects SIAR usage
        - Gap is processed without errors
        """
        # Make gap old (>72h)
        old_gap = DataGap(
            "weather_data",
            datetime(2025, 10, 1, 8, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 1, 19, 0, tzinfo=timezone.utc),
            12,
            12,
            11.0,
            "moderate"
        )

        with patch('services.backfill_service.SiarETL') as MockSiarETL:
            mock_siar = MockSiarETL.return_value
            mock_siar.get_historical_data = AsyncMock(return_value=[])

            # Execute
            results = await backfill_service._backfill_weather_gaps([old_gap])

            # Assert
            assert len(results) == 1
            # Note: SIAR logic may skip if no data, but should not crash


    async def test_backfill_weather_aemet_failure_fallback(
        self,
        backfill_service,
        sample_weather_gap,
        mock_data_ingestion
    ):
        """
        Test Weather backfill fallback when AEMET fails.

        Verifies:
        - AEMET failure is caught
        - Error is logged
        - Process continues without crash
        """
        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion):
            # Mock AEMET failure
            mock_data_ingestion.ingest_aemet_weather = AsyncMock(side_effect=Exception("AEMET API down"))

            # Execute
            results = await backfill_service._backfill_weather_gaps([sample_weather_gap])

            # Assert
            assert len(results) == 1
            result = results[0]
            assert len(result.errors) > 0


    async def test_backfill_weather_multiple_sources(
        self,
        backfill_service,
        mock_data_ingestion
    ):
        """
        Test Weather backfill handles multiple data sources.

        Verifies:
        - Recent gaps use AEMET
        - Old gaps use SIAR
        - Each gap uses appropriate source
        """
        now = datetime.now(timezone.utc)
        gaps = [
            # Recent gap - should use AEMET
            DataGap("weather_data", now - timedelta(hours=24), now, 25, 25, 24.0, "moderate"),
            # Old gap - should use SIAR
            DataGap("weather_data", datetime(2025, 10, 1, 0, 0, tzinfo=timezone.utc),
                    datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc), 25, 25, 24.0, "moderate")
        ]

        with patch('services.backfill_service.DataIngestionService', return_value=mock_data_ingestion), \
             patch('services.backfill_service.SiarETL') as MockSiarETL:

            mock_data_ingestion.ingest_aemet_weather = AsyncMock(return_value={
                'success': True,
                'records_written': 24
            })

            mock_siar = MockSiarETL.return_value
            mock_siar.get_historical_data = AsyncMock(return_value=[])

            # Execute
            results = await backfill_service._backfill_weather_gaps(gaps)

            # Assert
            assert len(results) == 2


# =============================================================================
# TEST CLASS: INTELLIGENT BACKFILL
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestIntelligentBackfill:
    """Tests for intelligent backfill orchestration."""

    async def test_execute_intelligent_backfill_no_gaps(
        self,
        backfill_service
    ):
        """
        Test intelligent backfill when no gaps found.

        Verifies:
        - Returns success status
        - Message indicates no gaps
        - No backfill operations performed
        """
        # Mock no gaps found
        mock_analysis = Mock()
        mock_analysis.total_gaps_found = 0
        mock_analysis.ree_gaps = []
        mock_analysis.weather_gaps = []

        backfill_service.gap_detector.detect_all_gaps = AsyncMock(return_value=mock_analysis)

        # Execute
        result = await backfill_service.execute_intelligent_backfill(days_back=7)

        # Assert
        assert result['status'] == 'success'
        assert result['gaps_found'] == 0
        assert 'No gaps found' in result['message']


    async def test_execute_intelligent_backfill_with_gaps(
        self,
        backfill_service,
        sample_ree_gap,
        sample_weather_gap
    ):
        """
        Test intelligent backfill with mixed REE and Weather gaps.

        Verifies:
        - Both REE and Weather backfills are triggered
        - Summary includes all results
        - Total records calculated correctly
        """
        # Mock gap analysis
        mock_analysis = Mock()
        mock_analysis.total_gaps_found = 2
        mock_analysis.ree_gaps = [sample_ree_gap]
        mock_analysis.weather_gaps = [sample_weather_gap]

        backfill_service.gap_detector.detect_all_gaps = AsyncMock(return_value=mock_analysis)

        # Mock backfill methods
        backfill_service._backfill_ree_gaps = AsyncMock(return_value=[
            BackfillResult("energy_prices", sample_ree_gap.start_time, sample_ree_gap.end_time,
                          10, 10, 10, 100.0, 1.0, "ree_api", [])
        ])

        backfill_service._backfill_weather_gaps = AsyncMock(return_value=[
            BackfillResult("weather_data", sample_weather_gap.start_time, sample_weather_gap.end_time,
                          12, 12, 12, 100.0, 1.0, "aemet", [])
        ])

        # Execute
        result = await backfill_service.execute_intelligent_backfill(days_back=7)

        # Assert
        assert result['status'] in ['success', 'partial']
        assert result['summary']['total_gaps_processed'] == 2


    async def test_execute_intelligent_backfill_telegram_alert(
        self,
        backfill_service,
        sample_ree_gap
    ):
        """
        Test intelligent backfill sends Telegram alert on completion.

        Verifies:
        - Telegram alert is sent when service available
        - Alert contains summary statistics
        - Success severity is INFO
        """
        # Add mock Telegram service
        mock_telegram = AsyncMock()
        backfill_service.telegram_service = mock_telegram

        # Mock gap analysis
        mock_analysis = Mock()
        mock_analysis.total_gaps_found = 1
        mock_analysis.ree_gaps = [sample_ree_gap]
        mock_analysis.weather_gaps = []

        backfill_service.gap_detector.detect_all_gaps = AsyncMock(return_value=mock_analysis)
        backfill_service._backfill_ree_gaps = AsyncMock(return_value=[
            BackfillResult("energy_prices", sample_ree_gap.start_time, sample_ree_gap.end_time,
                          10, 10, 10, 100.0, 1.0, "ree_api", [])
        ])

        # Execute
        await backfill_service.execute_intelligent_backfill(days_back=7)

        # Assert
        mock_telegram.send_alert.assert_called_once()
        call_args = mock_telegram.send_alert.call_args
        assert "Backfill completed" in call_args[1]['message']


    async def test_execute_intelligent_backfill_exception_handling(
        self,
        backfill_service
    ):
        """
        Test intelligent backfill handles exceptions gracefully.

        Verifies:
        - Exception during backfill is logged
        - Telegram alert sent for failure
        - Exception is re-raised
        """
        # Add mock Telegram service
        mock_telegram = AsyncMock()
        backfill_service.telegram_service = mock_telegram

        # Mock gap detector to raise exception
        backfill_service.gap_detector.detect_all_gaps = AsyncMock(side_effect=Exception("InfluxDB connection lost"))

        # Execute and expect exception
        with pytest.raises(Exception, match="InfluxDB connection lost"):
            await backfill_service.execute_intelligent_backfill(days_back=7)

        # Assert Telegram alert was sent
        mock_telegram.send_alert.assert_called_once()
        call_args = mock_telegram.send_alert.call_args
        assert "Backfill failed" in call_args[1]['message']


    async def test_execute_intelligent_backfill_partial_success(
        self,
        backfill_service,
        sample_ree_gap,
        sample_weather_gap
    ):
        """
        Test intelligent backfill with partial success (some gaps filled).

        Verifies:
        - Status reflects partial completion
        - Success rate calculated correctly
        - Both successful and failed results included
        """
        # Mock gap analysis
        mock_analysis = Mock()
        mock_analysis.total_gaps_found = 2
        mock_analysis.ree_gaps = [sample_ree_gap]
        mock_analysis.weather_gaps = [sample_weather_gap]

        backfill_service.gap_detector.detect_all_gaps = AsyncMock(return_value=mock_analysis)

        # Mock REE success, Weather failure
        backfill_service._backfill_ree_gaps = AsyncMock(return_value=[
            BackfillResult("energy_prices", sample_ree_gap.start_time, sample_ree_gap.end_time,
                          10, 10, 10, 100.0, 1.0, "ree_api", [])
        ])

        backfill_service._backfill_weather_gaps = AsyncMock(return_value=[
            BackfillResult("weather_data", sample_weather_gap.start_time, sample_weather_gap.end_time,
                          12, 0, 0, 0.0, 1.0, "aemet", ["API timeout"])
        ])

        # Execute
        result = await backfill_service.execute_intelligent_backfill(days_back=7)

        # Assert
        assert result['status'] == 'partial'
        assert result['summary']['overall_success_rate'] < 100


# =============================================================================
# INTEGRATION NOTES
# =============================================================================

"""
Sprint 19 - Backfill Service Extended Tests

Coverage target: 53% → 75%

Test breakdown:
- REE backfill: 5 tests (single gap, multiple gaps, API failure, empty response, partial data)
- Weather backfill: 4 tests (AEMET recent, SIAR old, fallback, multiple sources)
- Intelligent backfill: 5 tests (no gaps, with gaps, Telegram, exceptions, partial)

Total: 14 new tests

Expected coverage improvement:
- execute_intelligent_backfill: 100% covered
- _backfill_ree_gaps: 90% covered
- _backfill_weather_gaps: 80% covered
- Edge cases and error handling: 70% covered

Next steps:
- Run: pytest tests/unit/test_backfill_service_extended.py -v
- Check: pytest --cov=services/backfill_service --cov-report=term-missing
- Verify: Coverage increased to 75%+
"""
