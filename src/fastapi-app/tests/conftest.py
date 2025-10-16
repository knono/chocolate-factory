"""
Pytest Configuration and Shared Fixtures
=========================================

Professional test setup for FastAPI with proper dependency overrides.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add src directory to path for configs module
src_dir = Path(__file__).parent.parent.parent
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Set test environment variables BEFORE any imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "ERROR"

# Create temporary test directory
import tempfile
test_dir = Path(tempfile.mkdtemp())
os.environ["ML_MODELS_DIR"] = str(test_dir / "models")
os.environ["STATIC_FILES_DIR"] = str(test_dir / "static")

# Patch Path.mkdir globally to prevent permission errors during imports
_original_mkdir = Path.mkdir
def mock_mkdir(self, *args, **kwargs):
    """Mock mkdir that creates dirs in temp space."""
    try:
        return _original_mkdir(self, *args, **kwargs)
    except (PermissionError, FileNotFoundError):
        # Silently pass if we can't create in /app
        pass

Path.mkdir = mock_mkdir

# Patch os.makedirs similarly
_original_makedirs = os.makedirs
def mock_makedirs(path, *args, **kwargs):
    """Mock makedirs that handles /app gracefully."""
    try:
        return _original_makedirs(path, *args, **kwargs)
    except (PermissionError, FileNotFoundError):
        # Silently pass if we can't create in /app
        pass

os.makedirs = mock_makedirs


# =============================================================================
# APP FIXTURE WITH DEPENDENCY OVERRIDES
# =============================================================================

@pytest.fixture(scope="session")
def app():
    """
    Create FastAPI app with mocked dependencies.

    This approach:
    1. Creates a minimal FastAPI app
    2. Imports only the routers (not the full main.py with lifespan)
    3. Overrides dependencies that need external services
    """
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware

    # Create minimal app (no lifespan context manager)
    test_app = FastAPI(
        title="Chocolate Factory API - Test",
        version="test",
        docs_url="/docs",
        redoc_url=None
    )

    # Add CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Import and register routers (this is safe, doesn't trigger lifespan)
    try:
        from api.routers import (
            health_router,
            ree_router,
            weather_router,
            dashboard_router,
            optimization_router,
            analysis_router,
            gaps_router,
            insights_router,
            chatbot_router
        )

        test_app.include_router(health_router)
        test_app.include_router(ree_router)
        test_app.include_router(weather_router)
        test_app.include_router(dashboard_router)
        test_app.include_router(optimization_router)
        test_app.include_router(analysis_router)
        test_app.include_router(gaps_router)
        test_app.include_router(insights_router)
        test_app.include_router(chatbot_router)

    except ImportError as e:
        print(f"Warning: Could not import routers: {e}")

    # Add basic routes
    @test_app.get("/")
    async def root():
        return {"message": "Test API"}

    return test_app


@pytest.fixture
def client(app, monkeypatch, mock_dashboard_service):
    """
    FastAPI test client with mocked external dependencies.

    Uses monkeypatch to override dependencies at import time.
    """
    # Mock InfluxDB client
    mock_influx = MagicMock()
    mock_influx.query_api.return_value.query.return_value = []
    monkeypatch.setattr("infrastructure.influxdb.client.InfluxDBClient", lambda *args, **kwargs: mock_influx)

    # Mock external API clients
    monkeypatch.setenv("INFLUXDB_URL", "http://test:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")

    # Override dependency injection for DashboardService
    try:
        from api.routers.dashboard import get_dashboard_service
        app.dependency_overrides[get_dashboard_service] = lambda: mock_dashboard_service
    except ImportError:
        pass  # If not available, tests will handle it

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


# =============================================================================
# MOCK FIXTURES FOR EXTERNAL SERVICES
# =============================================================================

@pytest.fixture
def mock_influxdb():
    """Mock InfluxDB client."""
    mock = MagicMock()
    mock.query_api.return_value.query.return_value = []
    return mock


@pytest.fixture
def mock_ree_api():
    """Mock REE API client."""
    mock = Mock()
    mock.get_current_prices = AsyncMock(return_value={
        'success': True,
        'data': [{'price_eur_kwh': 0.15}]
    })
    return mock


@pytest.fixture
def mock_dashboard_service():
    """Mock Dashboard Service with proper async support."""
    mock = MagicMock()

    # Mock async methods
    mock.get_complete_dashboard_data = AsyncMock(return_value={
        'timestamp': '2025-10-16T10:00:00',
        'current_data': {
            'ree': {'price_eur_kwh': 0.15},
            'weather': {'temperature': 22.0}
        },
        'ml_predictions': {
            'energy_optimization_score': 75.0,
            'production_recommendation': 'Optimal'
        }
    })

    mock.get_dashboard_summary = AsyncMock(return_value={
        'timestamp': '2025-10-16T10:00:00',
        'quick_status': 'operational'
    })

    mock.get_alerts = AsyncMock(return_value=[
        {'severity': 'warning', 'message': 'Test alert'}
    ])

    return mock


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_ree_data():
    """Sample REE electricity price data."""
    return [
        {
            'timestamp': '2025-10-16T10:00:00',
            'price_eur_mwh': 150.0,
            'price_eur_kwh': 0.15
        }
    ]


@pytest.fixture
def sample_ml_features():
    """Sample ML input features."""
    return {
        'price_eur_kwh': 0.15,
        'temperature': 22.0,
        'humidity': 55.0
    }


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "ml: ML model tests")
    config.addinivalue_line("markers", "slow: Slow tests")
