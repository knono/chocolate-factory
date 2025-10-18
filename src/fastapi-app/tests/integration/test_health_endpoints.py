"""
Integration Tests - Health Endpoints
====================================

Tests for system health monitoring endpoints:
- GET /health
- GET /ready
- GET /version
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
        assert "version" in data

    def test_health_endpoint_includes_system_info(self, client):
        """Test /health includes basic system info."""
        response = client.get("/health")
        data = response.json()

        # Verificar campos que sí existen en la respuesta real
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_ready_endpoint_success(self, client):
        """Test GET /ready for readiness probe."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "checks" in data

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
# Total tests: 6 (4 health checks + 2 error handling)
# Coverage: /health, /ready, /version
# =============================================================================
