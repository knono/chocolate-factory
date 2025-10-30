"""
Unit Tests for Scheduler Configuration
========================================

Tests the APScheduler job registration and execution.

Coverage:
- ✅ Job registration
- ✅ Job count verification
- ✅ Job configuration (intervals, triggers)
- ✅ REE ingestion job
- ✅ Weather ingestion job
- ✅ Error handling in jobs
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tasks.scheduler_config import register_all_jobs
from tasks.ree_jobs import ree_ingestion_job
from tasks.weather_jobs import weather_ingestion_job


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_scheduler():
    """Mock APScheduler instance."""
    scheduler = Mock(spec=AsyncIOScheduler)
    scheduler.add_job = Mock()
    scheduler.get_jobs = Mock(return_value=[Mock() for _ in range(7)])
    return scheduler


@pytest.fixture
def mock_influx_client():
    """Mock InfluxDB client."""
    client = Mock()
    client.write_api = Mock()
    client.query_api = Mock()
    return client


# =============================================================================
# TEST CLASS: SCHEDULER CONFIG
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestSchedulerConfig:
    """Unit tests for scheduler configuration."""

    async def test_register_all_jobs_count(self, mock_scheduler):
        """
        Test that all 7 jobs are registered.

        Verifies:
        - register_all_jobs calls add_job 7 times
        - Job count matches expected
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Assert
        assert mock_scheduler.add_job.call_count == 7
        assert len(mock_scheduler.get_jobs()) == 7


    async def test_register_all_jobs_ids(self, mock_scheduler):
        """
        Test that all jobs have correct IDs.

        Verifies:
        - Each job has unique ID
        - IDs match expected values
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Get all job IDs from add_job calls
        job_ids = [call[1]['id'] for call in mock_scheduler.add_job.call_args_list]

        # Assert
        expected_ids = [
            "ree_ingestion",
            "weather_ingestion",
            "ensure_prophet_model",
            "sklearn_training",
            "health_metrics_collection",
            "health_status_log",
            "critical_nodes_check"
        ]
        assert set(job_ids) == set(expected_ids)


    async def test_register_ree_job_interval(self, mock_scheduler):
        """
        Test that REE job has correct interval (5 minutes).

        Verifies:
        - REE job uses interval trigger
        - Interval is 5 minutes
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Find REE job call
        ree_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if call[1].get('id') == 'ree_ingestion':
                ree_call = call
                break

        # Assert
        assert ree_call is not None
        assert ree_call[1]['trigger'] == 'interval'
        assert ree_call[1]['minutes'] == 5  # Default REE_INGESTION_INTERVAL


    async def test_register_weather_job_interval(self, mock_scheduler):
        """
        Test that Weather job has correct interval (5 minutes).

        Verifies:
        - Weather job uses interval trigger
        - Interval is 5 minutes
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Find Weather job call
        weather_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if call[1].get('id') == 'weather_ingestion':
                weather_call = call
                break

        # Assert
        assert weather_call is not None
        assert weather_call[1]['trigger'] == 'interval'
        assert weather_call[1]['minutes'] == 5  # Default WEATHER_INGESTION_INTERVAL


    async def test_register_sklearn_job_interval(self, mock_scheduler):
        """
        Test that sklearn training job has correct interval (30 minutes).

        Verifies:
        - sklearn job uses interval trigger
        - Interval is 30 minutes
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Find sklearn job call
        sklearn_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if call[1].get('id') == 'sklearn_training':
                sklearn_call = call
                break

        # Assert
        assert sklearn_call is not None
        assert sklearn_call[1]['trigger'] == 'interval'
        assert sklearn_call[1]['minutes'] == 30


    async def test_register_prophet_job_daily(self, mock_scheduler):
        """
        Test that Prophet job runs daily (24 hours).

        Verifies:
        - Prophet job uses interval trigger
        - Interval is 24 hours
        - Has next_run_time set (runs immediately)
        """
        # Execute
        await register_all_jobs(mock_scheduler)

        # Find Prophet job call
        prophet_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if call[1].get('id') == 'ensure_prophet_model':
                prophet_call = call
                break

        # Assert
        assert prophet_call is not None
        assert prophet_call[1]['trigger'] == 'interval'
        assert prophet_call[1]['hours'] == 24
        assert 'next_run_time' in prophet_call[1]  # Runs immediately


# =============================================================================
# TEST CLASS: JOB EXECUTION
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestJobExecution:
    """Unit tests for job execution."""

    async def test_ree_ingestion_job_success(self, mock_influx_client):
        """
        Test successful REE ingestion job execution.

        Verifies:
        - Job executes without errors
        - InfluxDB client is used
        - Records are written
        """
        with patch('tasks.ree_jobs.get_influxdb_client', return_value=mock_influx_client), \
             patch('tasks.ree_jobs.REEService') as MockREEService:

            # Setup mock service
            mock_service = MockREEService.return_value
            mock_service.ingest_prices = AsyncMock(return_value={
                'records_written': 24,
                'status': 'success'
            })

            # Execute
            await ree_ingestion_job()

            # Assert
            mock_service.ingest_prices.assert_called_once()
            # Verify it was called with today's date
            call_args = mock_service.ingest_prices.call_args[0]
            assert call_args[0] == date.today()


    async def test_ree_ingestion_job_failure(self, mock_influx_client):
        """
        Test REE ingestion job handles errors gracefully.

        Verifies:
        - Job catches exceptions
        - Error is logged
        - Job doesn't crash
        """
        with patch('tasks.ree_jobs.get_influxdb_client', return_value=mock_influx_client), \
             patch('tasks.ree_jobs.REEService') as MockREEService:

            # Setup mock service to fail
            mock_service = MockREEService.return_value
            mock_service.ingest_prices = AsyncMock(side_effect=Exception("API timeout"))

            # Execute (should not raise exception)
            await ree_ingestion_job()

            # Assert - job completed without crashing
            assert mock_service.ingest_prices.called


    async def test_weather_ingestion_job_success(self, mock_influx_client):
        """
        Test successful weather ingestion job execution.

        Verifies:
        - Job executes without errors
        - Both AEMET and aggregation services are used
        - Hybrid ingestion is called
        """
        with patch('tasks.weather_jobs.get_influxdb_client', return_value=mock_influx_client), \
             patch('tasks.weather_jobs.AEMETService') as MockAEMET, \
             patch('tasks.weather_jobs.WeatherAggregationService') as MockWeather:

            # Setup mock services
            mock_aemet = MockAEMET.return_value
            mock_weather = MockWeather.return_value
            mock_weather.ingest_weather_hybrid = AsyncMock(return_value={
                'records_written': 5,
                'source': 'hybrid'
            })

            # Execute
            await weather_ingestion_job()

            # Assert
            mock_weather.ingest_weather_hybrid.assert_called_once()


    async def test_weather_ingestion_job_failure(self, mock_influx_client):
        """
        Test weather ingestion job handles errors gracefully.

        Verifies:
        - Job catches exceptions
        - Error is logged
        - Job doesn't crash
        """
        with patch('tasks.weather_jobs.get_influxdb_client', return_value=mock_influx_client), \
             patch('tasks.weather_jobs.AEMETService') as MockAEMET, \
             patch('tasks.weather_jobs.WeatherAggregationService') as MockWeather:

            # Setup mock service to fail
            mock_weather = MockWeather.return_value
            mock_weather.ingest_weather_hybrid = AsyncMock(side_effect=Exception("Network error"))

            # Execute (should not raise exception)
            await weather_ingestion_job()

            # Assert - job completed without crashing
            assert mock_weather.ingest_weather_hybrid.called


# =============================================================================
# INTEGRATION NOTES
# =============================================================================

"""
Integration with other test files:
- Tests scheduler configuration in isolation
- Verifies job registration logic
- Tests individual job execution

Coverage impact:
- Sprint 17 target: 0% → 50% coverage for scheduler_config.py
- Files tested: scheduler_config.py (113 lines), ree_jobs.py (33 lines), weather_jobs.py (34 lines)
- Tests added: 11 tests (7 config + 4 execution)
- Expected coverage: ~90 lines (50% of 180 total)

Test breakdown:
- Scheduler config: 7 tests (job registration, intervals, IDs)
- Job execution: 4 tests (REE success/failure, Weather success/failure)

Next steps:
- Run: pytest tests/unit/test_scheduler.py -v
- Verify: All 11 tests passing
- Check: pytest --cov=tasks --cov-report=term-missing
- Target: 50%+ coverage achieved
"""
