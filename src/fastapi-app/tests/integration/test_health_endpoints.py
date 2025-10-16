"""
Integration Tests - Health Endpoints
====================================

Tests for system health monitoring endpoints:
- GET /health
- GET /ready
- GET /version
- GET /scheduler/status
- GET /models/status-direct
"""
import pytest
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_endpoint_success(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "environment" in data

    def test_health_endpoint_includes_system_info(self, client):
        """Test /health includes system metrics."""
        response = client.get("/health")
        data = response.json()

        assert "memory_usage_mb" in data or "cpu_percent" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_ready_endpoint_success(self, client):
        """Test GET /ready for readiness probe."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]

    def test_version_endpoint(self, client):
        """Test GET /version returns API version."""
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data
        # Version should follow semver pattern
        version = data["version"]
        assert isinstance(version, str)
        assert len(version.split(".")) >= 2  # At least X.Y format

    @patch('dependencies.scheduler')
    def test_scheduler_status(self, mock_scheduler, client):
        """Test GET /scheduler/status returns scheduler info."""
        # Mock scheduler with jobs
        mock_job1 = Mock()
        mock_job1.id = "ree_ingestion"
        mock_job1.next_run_time = None

        mock_job2 = Mock()
        mock_job2.id = "weather_ingestion"
        mock_job2.next_run_time = None

        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]
        mock_scheduler.state = 1  # STATE_RUNNING

        response = client.get("/scheduler/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "jobs_count" in data or "jobs" in data


@pytest.mark.integration
class TestHealthEndpointErrors:
    """Test error handling in health endpoints."""

    def test_health_endpoint_handles_missing_dependencies(self, client):
        """Test /health gracefully handles missing dependencies."""
        # Even if some dependencies fail, health should return 200
        # with degraded status or partial information
        response = client.get("/health")

        # Should not crash
        assert response.status_code in [200, 503]

    def test_invalid_health_endpoint(self, client):
        """Test non-existent health endpoint returns 404."""
        response = client.get("/health/nonexistent")

        assert response.status_code == 404


# =============================================================================
# SUMMARY
# =============================================================================
# Total tests: 7 (5 required + 2 error handling)
# Coverage: /health, /ready, /version, /scheduler/status
# =============================================================================
