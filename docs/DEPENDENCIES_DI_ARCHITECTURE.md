# Dependency Injection Architecture

**File**: `src/fastapi-app/dependencies.py`
**Pattern**: Singleton with `@lru_cache()` and lazy loading
**Status**: Production (Sprint 15 documented)

## Overview

`dependencies.py` is the Dependency Injection (DI) container. It provides all service and infrastructure instances to FastAPI routers via the `Depends()` pattern.

## DI Pattern

### Singleton with Lazy Loading

```python
_service_instance: Optional[object] = None

def get_service():
    """Get singleton instance with lazy initialization"""
    global _service_instance

    if _service_instance is None:
        from services.some_service import SomeService
        _service_instance = SomeService()
        logger.info("✅ Service initialized")

    return _service_instance
```

**Benefits**:
- Single instance per application lifetime
- Lazy initialization (created on first use)
- Thread-safe via global module-level state

## Infrastructure Dependencies

### InfluxDB Client

```python
@lru_cache()
def get_influxdb_client() -> InfluxDBClient:
    """Get InfluxDB singleton with connection test"""
    client = InfluxDBClient(...)
    health = client.health()  # Test connection
    logger.info(f"✅ InfluxDB connected: {health.status}")
    return client
```

**Features**:
- Connection validation on startup
- Error handling with clear logging
- Reused across all requests

### API Clients

```python
def get_ree_client():
    """REE API client (lazy singleton)"""
    # Uses infrastructure/external_apis/REEAPIClient (Sprint 15)
    # NOT services/ree_client.py (deleted, was duplicate)
```

**Source**: `infrastructure/external_apis/` (single source of truth)

## Service Dependencies

### Orchestration Services

```python
def get_ree_service():
    """REE orchestration service"""
    # Depends on: get_influxdb_client(), get_ree_client()
    # Location: services/ree_service.py
```

### Business Logic Services (Domain Layer)

```python
def get_direct_ml_service():
    """Direct ML service (moved to domain/ml/direct_ml.py in Sprint 15)"""
    from domain.ml.direct_ml import DirectML  # Moved from services/
    return DirectML()
```

**Migration Note**: Business logic services moved to `domain/` in Sprint 15 while maintaining backward compatibility via compatibility layers.

### Feature Services

- `get_chatbot_service()` - Conversational BI
- `get_tailscale_health_service()` - Tailnet monitoring
- `get_health_logs_service()` - Event logging

## Usage in Routers

### Pattern

```python
@router.get("/endpoint")
async def endpoint(
    service: REEService = Depends(get_ree_service),
    influxdb: InfluxDBClient = Depends(get_influxdb_client)
):
    return await service.process(influxdb)
```

**FastAPI Behavior**:
1. FastAPI inspects function signature
2. Identifies `Depends()` parameters
3. Calls dependency function to get instance
4. Injects instance into function parameter

## Lifecycle Management

### Initialization

```python
async def init_scheduler():
    """Called during app startup"""
    scheduler = get_scheduler()
    from tasks.scheduler_config import register_all_jobs
    await register_all_jobs(scheduler)
    scheduler.start()
```

### Cleanup

```python
async def cleanup_dependencies():
    """Called during app shutdown"""
    await shutdown_scheduler()
    # Other cleanup tasks
```

## Backward Compatibility (Sprint 15)

### API Client Consolidation

**Before (duplicates)**:
- `services/ree_client.py` (612 lines)
- `infrastructure/external_apis/ree_client.py` (259 lines)

**After (Sprint 15)**:
- Keep: `infrastructure/external_apis/ree_client.py` (single source)
- Remove: `services/ree_client.py` (deleted)
- Compatibility: `services/__init__.py` re-exports as `REEClient`

**Result**:
- Old imports still work: `from services import REEClient`
- New imports preferred: `from infrastructure.external_apis import REEAPIClient`

### Domain Logic Services

**Moved to domain/ (Sprint 15)**:
- `domain/ml/direct_ml.py` (from services/direct_ml.py)
- `domain/recommendations/business_logic_service.py` (from services/)
- `domain/analysis/siar_analysis_service.py` (from services/)

**Compatibility Modules**:
- `services/ml_domain_compat.py` - Re-exports from domain/ml/
- `services/recommendation_domain_compat.py` - Re-exports from domain/recommendations/
- `services/analysis_domain_compat.py` - Re-exports from domain/analysis/

## Current DI Graph

```
FastAPI App
├── get_influxdb_client() → InfluxDBClient
├── get_ree_client() → REEAPIClient (infrastructure/)
├── get_aemet_client() → AEMETAPIClient (infrastructure/)
├── get_openweather_client() → OpenWeatherMapAPIClient (infrastructure/)
│
├── get_ree_service() → REEService (services/)
├── get_aemet_service() → AemetService (services/)
├── get_weather_aggregation_service() → WeatherAggregationService (services/)
│
├── get_direct_ml_service() → DirectML (domain/ml/)
├── get_enhanced_ml_service() → EnhancedMLService (domain/ml/)
│
├── get_dashboard_service() → DashboardService (services/)
├── get_scheduler() → AsyncIOScheduler
│
└── [11+ other services...]
```

## Best Practices

1. **Always use Depends()** - Let FastAPI manage instances
2. **Lazy initialization** - Create instances on first use
3. **Singleton pattern** - One instance per app lifetime
4. **Error handling** - Log issues clearly
5. **Single responsibility** - Each service does one thing

## Testing

### Mocking Dependencies

```python
@pytest.fixture
def mock_influxdb():
    return Mock(spec=InfluxDBClient)

@pytest.fixture
def app(mock_influxdb, monkeypatch):
    # Override DI
    monkeypatch.setattr(
        "dependencies.get_influxdb_client",
        lambda: mock_influxdb
    )
    return app
```

## Notes

- Documented in Sprint 15 (was critical but undocumented before)
- All services properly injected via Depends()
- No circular dependencies (validated in tests)
- Production-ready as of October 29, 2025
