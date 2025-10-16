# Chocolate Factory - Testing Suite

## 📋 Overview

Testing suite for Chocolate Factory API following Clean Architecture principles.

**Fase 9 del Sprint 12**: Tests básicos de API (25 tests, coverage >70%)

## 🗂️ Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (isolated components)
├── integration/             # API endpoint tests
│   ├── test_health_endpoints.py        # 7 tests
│   ├── test_dashboard_api.py           # 12 tests
│   └── test_predictions_api.py         # 11 tests
└── ml/                      # ML model tests
```

## 🚀 Running Tests

### Prerequisites

```bash
cd src/fastapi-app
pip install -e .
pip install pytest pytest-cov pytest-asyncio httpx
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
```

### Run Specific Test Categories

```bash
# Only integration tests
pytest tests/ -v -m integration

# Only unit tests
pytest tests/ -v -m unit

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Run Specific Test File

```bash
pytest tests/integration/test_health_endpoints.py -v
```

## 📊 Coverage Requirements

- **Fase 9**: Minimum 70% coverage
- **Fase 10**: Minimum 80% coverage (objetivo)
- **Fase 11**: Minimum 85% coverage (objetivo)

### View Coverage Report

After running tests with `--cov-report=html`:

```bash
open coverage_html/index.html
```

## 🎯 Test Categories (Markers)

- `@pytest.mark.unit` - Unit tests for isolated components
- `@pytest.mark.integration` - API endpoint integration tests
- `@pytest.mark.ml` - Machine learning model tests
- `@pytest.mark.slow` - Slow running tests (skipped in CI by default)

## 🔧 Fixtures Available

### Test Clients
- `client` - Synchronous FastAPI test client
- `async_client` - Asynchronous test client

### Mock Services
- `mock_influxdb` - Mock InfluxDB client
- `mock_ree_api` - Mock REE API
- `mock_aemet_api` - Mock AEMET API
- `mock_openweather_api` - Mock OpenWeatherMap API

### Sample Data
- `sample_ree_data` - 24h electricity price data
- `sample_weather_data` - 24h weather observations
- `sample_ml_features` - ML input features
- `sample_prophet_predictions` - 7-day price predictions

## ✅ Test Summary

### Fase 9 - Tests Básicos (COMPLETADO)

| Category | Tests | File |
|----------|-------|------|
| Health Endpoints | 7 | `test_health_endpoints.py` |
| Dashboard API | 12 | `test_dashboard_api.py` |
| Predictions API | 11 | `test_predictions_api.py` |
| **TOTAL** | **30** | **3 files** |

## 🐛 Troubleshooting

### Import Errors

If you encounter `ModuleNotFoundError`, ensure you're running from the correct directory:

```bash
cd src/fastapi-app
export PYTHONPATH=$PWD
pytest tests/
```

### Async Test Errors

For async test issues, ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio
```

### Coverage Not Working

Install coverage dependencies:

```bash
pip install pytest-cov coverage
```

## 📝 Writing New Tests

### Example Test

```python
import pytest

@pytest.mark.integration
def test_my_endpoint(client, mock_influxdb):
    """Test description."""
    response = client.get("/my-endpoint")

    assert response.status_code == 200
    assert "expected_key" in response.json()
```

### Using Fixtures

```python
def test_with_sample_data(client, sample_ree_data):
    """Test using sample data fixture."""
    # sample_ree_data is automatically provided
    assert len(sample_ree_data) == 24
```

## 🔄 CI/CD Integration

Tests run automatically in Forgejo Actions pipeline:

- ✅ Run on every push to `main` and `develop`
- ✅ Coverage threshold enforced (70%)
- ✅ Blocks deployment if tests fail
- ✅ Coverage report uploaded as artifact

## 📚 Next Steps

- **Fase 10**: Add service and ML regression tests (41 tests, 80% coverage)
- **Fase 11**: Add end-to-end integration tests (22 tests, 85% coverage)

## 🤝 Contributing

When adding new tests:

1. Follow existing test structure
2. Use appropriate markers (`@pytest.mark.integration`, etc.)
3. Add fixtures to `conftest.py` for reusable mocks
4. Ensure tests are deterministic (no random data)
5. Keep tests fast (< 1s per test when possible)
