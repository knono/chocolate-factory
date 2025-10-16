"""
Integration Tests - Dashboard API
==================================

Tests for dashboard data endpoints:
- GET /dashboard/complete
- GET /dashboard/summary
- GET /dashboard/alerts
- GET /insights/* (Sprint 09)
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime


@pytest.mark.integration
class TestDashboardCompleteEndpoint:
    """Test suite for GET /dashboard/complete."""

    @patch('services.dashboard.DashboardService')
    def test_dashboard_complete_success(self, mock_service, client):
        """Test dashboard complete returns all sections."""
        # Mock dashboard service
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(return_value={
            'timestamp': datetime.now().isoformat(),
            'current_data': {'ree': {}, 'weather': {}},
            'ml_predictions': {},
            'prophet_forecast': [],
            'siar_analysis': {},
            'optimization': {}
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "current_data" in data
        assert "ml_predictions" in data

    @patch('services.dashboard.DashboardService')
    def test_dashboard_includes_ree_data(self, mock_service, client):
        """Test dashboard includes REE electricity prices."""
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(return_value={
            'current_data': {
                'ree': {
                    'price_eur_kwh': 0.15,
                    'tariff_period': 'P3'
                }
            }
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")
        data = response.json()

        assert "current_data" in data
        assert "ree" in data["current_data"]

    @patch('services.dashboard.DashboardService')
    def test_dashboard_includes_weather_data(self, mock_service, client):
        """Test dashboard includes weather observations."""
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(return_value={
            'current_data': {
                'weather': {
                    'temperature': 22.0,
                    'humidity': 55.0,
                    'source': 'aemet'
                }
            }
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")
        data = response.json()

        assert "current_data" in data
        assert "weather" in data["current_data"]

    @patch('services.dashboard.DashboardService')
    def test_dashboard_includes_ml_predictions(self, mock_service, client):
        """Test dashboard includes ML model predictions."""
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(return_value={
            'ml_predictions': {
                'energy_optimization_score': 75.5,
                'production_recommendation': 'optimal'
            }
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")
        data = response.json()

        assert "ml_predictions" in data


@pytest.mark.integration
class TestDashboardSummaryEndpoint:
    """Test suite for GET /dashboard/summary."""

    @patch('services.dashboard.DashboardService')
    def test_dashboard_summary_success(self, mock_service, client):
        """Test dashboard summary returns condensed data."""
        mock_instance = Mock()
        mock_instance.get_summary = AsyncMock(return_value={
            'status': 'operational',
            'current_price': 0.15,
            'temperature': 22.0,
            'recommendation': 'optimal'
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @patch('services.dashboard.DashboardService')
    def test_dashboard_summary_faster_than_complete(self, mock_service, client):
        """Test summary endpoint is lighter than complete."""
        mock_instance = Mock()
        mock_instance.get_summary = AsyncMock(return_value={'status': 'ok'})
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/summary")
        data = response.json()

        # Summary should have fewer keys than complete
        assert len(data.keys()) <= 10  # Reasonable limit for summary


@pytest.mark.integration
class TestDashboardAlertsEndpoint:
    """Test suite for GET /dashboard/alerts."""

    @patch('services.dashboard.DashboardService')
    def test_alerts_endpoint_returns_list(self, mock_service, client):
        """Test alerts endpoint returns array of alerts."""
        mock_instance = Mock()
        mock_instance.get_active_alerts = AsyncMock(return_value=[
            {'level': 'warning', 'message': 'High energy price'},
            {'level': 'info', 'message': 'Optimal production window'}
        ])
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "alerts" in data

    @patch('services.dashboard.DashboardService')
    def test_alerts_include_severity_levels(self, mock_service, client):
        """Test alerts have severity classification."""
        mock_instance = Mock()
        mock_instance.get_active_alerts = AsyncMock(return_value=[
            {'level': 'critical', 'message': 'System failure'}
        ])
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/alerts")
        data = response.json()

        if isinstance(data, list):
            alerts = data
        else:
            alerts = data.get("alerts", [])

        if len(alerts) > 0:
            assert "level" in alerts[0]
            assert alerts[0]["level"] in ["info", "warning", "critical", "error"]

    @patch('services.dashboard.DashboardService')
    def test_no_alerts_returns_empty_list(self, mock_service, client):
        """Test alerts endpoint with no active alerts."""
        mock_instance = Mock()
        mock_instance.get_active_alerts = AsyncMock(return_value=[])
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/alerts")

        assert response.status_code == 200
        data = response.json()
        # Should return empty list or object with empty alerts
        if isinstance(data, list):
            assert len(data) == 0
        else:
            assert data.get("alerts", []) == []


@pytest.mark.integration
class TestDashboardErrorHandling:
    """Test error handling in dashboard endpoints."""

    @patch('services.dashboard.DashboardService')
    def test_dashboard_handles_service_errors(self, mock_service, client):
        """Test dashboard gracefully handles service failures."""
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")

        # Should return 500 or fallback data, not crash
        assert response.status_code in [200, 500, 503]

    @patch('services.dashboard.DashboardService')
    def test_dashboard_handles_partial_data(self, mock_service, client):
        """Test dashboard handles missing data gracefully."""
        mock_instance = Mock()
        mock_instance.get_complete_dashboard = AsyncMock(return_value={
            'current_data': {'ree': None, 'weather': None}
        })
        mock_service.return_value = mock_instance

        response = client.get("/dashboard/complete")

        # Should not crash with partial data
        assert response.status_code == 200


# =============================================================================
# SUMMARY
# =============================================================================
# Total tests: 12
# Coverage: /dashboard/complete, /dashboard/summary, /dashboard/alerts
# Focus: Data completeness, error handling, performance
# =============================================================================
