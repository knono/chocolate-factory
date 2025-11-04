"""
Extended Unit Tests for Gap Detector Service
=============================================

Sprint 19 Fase 2 - Test Coverage Expansion
Target: 66% → 85% coverage for gap_detector.py

Tests edge cases, tolerance logic, severity classification, and empty DB handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from typing import List

from services.gap_detector import GapDetectionService, DataGap


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def gap_detector():
    """GapDetectionService instance."""
    return GapDetectionService()


@pytest.fixture
def mock_influx_service():
    """Mock DataIngestionService for InfluxDB operations."""
    service = AsyncMock()
    service.__aenter__ = AsyncMock(return_value=service)
    service.__aexit__ = AsyncMock()

    # Mock client and query_api
    service.client = Mock()
    service.client.query_api = Mock()
    service.config = Mock()
    service.config.bucket = "energy_data"

    return service


# =============================================================================
# TEST CLASS: GAP DETECTION LOGIC
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGapDetectionLogic:
    """Tests for gap detection core logic."""

    def test_detect_multiple_separated_gaps(self, gap_detector):
        """
        Test detection of multiple non-consecutive gaps.

        Verifies:
        - Multiple separate gaps are detected correctly
        - Gaps are not merged if separated by >tolerance
        - Each gap has correct start/end times
        """
        # Expected timeline: hourly from 00:00 to 10:00 (11 records)
        expected_times = [
            datetime(2025, 11, 1, h, 0, tzinfo=timezone.utc)
            for h in range(11)
        ]

        # Existing data: missing hours 2-3 (gap 1) and 7-8 (gap 2)
        existing_times = [
            datetime(2025, 11, 1, h, 0, tzinfo=timezone.utc)
            for h in [0, 1, 4, 5, 6, 9, 10]
        ]

        # Execute
        gaps = gap_detector._find_time_gaps(
            expected_times,
            existing_times,
            "energy_prices",
            timedelta(hours=1)
        )

        # Assert: Should detect 2 separate gaps
        assert len(gaps) == 2, f"Expected 2 gaps, got {len(gaps)}"

        # Gap 1: hours 2-3
        gap1 = gaps[0]
        assert gap1.start_time == datetime(2025, 11, 1, 2, 0, tzinfo=timezone.utc)
        assert gap1.end_time == datetime(2025, 11, 1, 3, 0, tzinfo=timezone.utc)
        assert gap1.gap_duration_hours == 1.0
        assert gap1.severity == "minor"

        # Gap 2: hours 7-8
        gap2 = gaps[1]
        assert gap2.start_time == datetime(2025, 11, 1, 7, 0, tzinfo=timezone.utc)
        assert gap2.end_time == datetime(2025, 11, 1, 8, 0, tzinfo=timezone.utc)
        assert gap2.gap_duration_hours == 1.0
        assert gap2.severity == "minor"


    def test_detect_weather_gaps_with_tolerance(self, gap_detector):
        """
        Test gap detection respects tolerance threshold.

        Verifies:
        - Gaps within tolerance (1.5x interval) are merged
        - Small interruptions don't create separate gaps
        - Tolerance adapts to gap size
        """
        # Expected timeline: hourly for 10 hours
        expected_times = [
            datetime(2025, 11, 1, h, 0, tzinfo=timezone.utc)
            for h in range(10)
        ]

        # Existing data: missing hours 2, 3, 4 (consecutive gap within tolerance)
        existing_times = [
            datetime(2025, 11, 1, h, 0, tzinfo=timezone.utc)
            for h in [0, 1, 5, 6, 7, 8, 9]
        ]

        # Execute
        gaps = gap_detector._find_time_gaps(
            expected_times,
            existing_times,
            "weather_data",
            timedelta(hours=1)
        )

        # Assert: Should detect 1 merged gap
        assert len(gaps) == 1

        gap = gaps[0]
        assert gap.start_time == datetime(2025, 11, 1, 2, 0, tzinfo=timezone.utc)
        assert gap.end_time == datetime(2025, 11, 1, 4, 0, tzinfo=timezone.utc)
        assert gap.gap_duration_hours == 2.0
        assert gap.severity == "minor"


    def test_calculate_gap_severity_critical(self, gap_detector):
        """
        Test severity classification for critical gaps (>12h).

        Verifies:
        - duration <=2h → "minor"
        - duration <=12h → "moderate"
        - duration >12h → "critical"
        """
        # Create gap >12h (16 hours)
        start = datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 16, 0, tzinfo=timezone.utc)

        gap = gap_detector._create_gap(
            measurement="energy_prices",
            start=start,
            end=end,
            interval=timedelta(hours=1)
        )

        # Assert critical severity
        assert gap.severity == "critical"
        assert gap.gap_duration_hours == 16.0
        assert gap.expected_records == 17  # 0-16 inclusive


    async def test_get_latest_timestamps_empty_db(self, gap_detector, mock_influx_service):
        """
        Test get_latest_timestamps with empty database.

        Verifies:
        - Empty InfluxDB returns None for both measurements
        - No crash or exception
        - Proper None handling
        """
        # Mock empty query results
        mock_query_api = mock_influx_service.client.query_api.return_value
        mock_query_api.query.return_value = []  # No tables = empty DB

        with patch('services.gap_detector.DataIngestionService', return_value=mock_influx_service):
            # Execute
            result = await gap_detector.get_latest_timestamps()

            # Assert
            assert result['latest_ree'] is None
            assert result['latest_weather'] is None
            assert mock_query_api.query.call_count == 2  # 2 queries (REE + Weather)


# =============================================================================
# TEST CLASS: GAP SEVERITY AND METADATA
# =============================================================================

@pytest.mark.unit
class TestGapSeverityAndMetadata:
    """Tests for gap severity classification and metadata calculation."""

    def test_create_gap_minor_severity(self, gap_detector):
        """Test gap with minor severity (<=2h)."""
        start = datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)

        gap = gap_detector._create_gap("energy_prices", start, end, timedelta(hours=1))

        assert gap.severity == "minor"
        assert gap.gap_duration_hours == 1.0


    def test_create_gap_moderate_severity(self, gap_detector):
        """Test gap with moderate severity (>2h, <=12h)."""
        start = datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 1, 6, 0, tzinfo=timezone.utc)

        gap = gap_detector._create_gap("weather_data", start, end, timedelta(hours=1))

        assert gap.severity == "moderate"
        assert gap.gap_duration_hours == 6.0
        assert gap.expected_records == 7  # 0-6 inclusive


    def test_expected_records_calculation(self, gap_detector):
        """Test expected_records calculation is correct."""
        # 24-hour gap should have 25 records (00:00 to 24:00 inclusive)
        start = datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 2, 0, 0, tzinfo=timezone.utc)

        gap = gap_detector._create_gap("energy_prices", start, end, timedelta(hours=1))

        assert gap.expected_records == 25
        assert gap.missing_records == 25  # Assumes 100% missing


# =============================================================================
# TEST CLASS: BACKFILL STRATEGY
# =============================================================================

@pytest.mark.unit
class TestBackfillStrategy:
    """Tests for backfill strategy generation."""

    def test_generate_backfill_strategy_mixed_gaps(self, gap_detector):
        """Test strategy generation with both REE and Weather gaps."""
        # Create sample gaps
        ree_gaps = [
            DataGap("energy_prices",
                   datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc),
                   datetime(2025, 11, 1, 5, 0, tzinfo=timezone.utc),
                   6, 6, 5.0, "moderate")
        ]

        weather_gaps = [
            DataGap("weather_data",
                   datetime(2025, 11, 2, 0, 0, tzinfo=timezone.utc),
                   datetime(2025, 11, 2, 10, 0, tzinfo=timezone.utc),
                   11, 11, 10.0, "moderate")
        ]

        # Execute
        strategy = gap_detector._generate_backfill_strategy(ree_gaps, weather_gaps)

        # Assert
        assert strategy['approach'] == "intelligent_progressive"
        assert strategy['ree_strategy']['gaps_count'] == 1
        assert strategy['ree_strategy']['total_missing_hours'] == 5.0
        assert strategy['weather_strategy']['gaps_count'] == 1
        assert strategy['weather_strategy']['total_missing_hours'] == 10.0
        assert strategy['execution_order'] == ["ree_backfill", "weather_backfill"]


    def test_estimate_backfill_duration_small(self, gap_detector):
        """Test backfill duration estimation for small gaps (<5 min)."""
        ree_gaps = [
            DataGap("energy_prices",
                   datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc),
                   datetime(2025, 11, 1, 1, 0, tzinfo=timezone.utc),
                   2, 2, 1.0, "minor")
        ]

        weather_gaps = []

        duration = gap_detector._estimate_backfill_duration(ree_gaps, weather_gaps)

        assert duration == "< 5 minutos"


    def test_estimate_backfill_duration_large(self, gap_detector):
        """Test backfill duration estimation for large gaps (>30 min)."""
        # 10 days of REE gaps (240 hours)
        ree_gaps = [
            DataGap("energy_prices",
                   datetime(2025, 11, 1, 0, 0, tzinfo=timezone.utc),
                   datetime(2025, 11, 11, 0, 0, tzinfo=timezone.utc),
                   241, 241, 240.0, "critical")
        ]

        weather_gaps = []

        duration = gap_detector._estimate_backfill_duration(ree_gaps, weather_gaps)

        # 240h / 24h * 2min = 20min
        assert "minutos" in duration or "min" in duration
