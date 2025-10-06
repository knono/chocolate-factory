# API Architect - Chocolate Factory Refactoring Guide

## 🎯 Mission
Refactor `main.py` (3,734 lines) into a modular, maintainable FastAPI application following Clean Architecture principles, adapted to our InfluxDB + ML forecasting domain.

---

## ⚠️ CRITICAL CONTEXT: This is NOT a Generic CRUD API

**Key Differences from Standard FastAPI Projects:**
- ❌ NO SQLAlchemy/ORM (we use InfluxDB time-series DB)
- ❌ NO traditional CRUD operations (we deal with time-series data, ML predictions, scheduled jobs)
- ✅ YES time-series queries (InfluxDB Flux queries)
- ✅ YES ML model lifecycle (train, predict, validate)
- ✅ YES scheduled data ingestion (APScheduler jobs)
- ✅ YES external API clients (REE, AEMET, OpenWeatherMap, SIAR)

**Our Domain Aggregates:**
1. **Energy Prices** (REE API → InfluxDB → Prophet forecasting)
2. **Weather Data** (AEMET + OpenWeatherMap → InfluxDB)
3. **Historical Analysis** (SIAR 88k+ records → ML training)
4. **Production Optimization** (ML predictions → business recommendations)
5. **Dashboard** (Read-only aggregated views)
6. **Scheduler** (Background jobs management)

---

## 📁 Target Architecture (Adapted to Our Domain)

```
src/fastapi-app/
├── main.py                          # Slim entry point (<100 lines)
├── config.py                        # Settings (InfluxDB, API keys, ML paths)
├── dependencies.py                  # DI: InfluxDB client, API clients
│
├── api/                             # API Layer (HTTP Interface)
│   ├── __init__.py
│   ├── routers/                     # Domain-based routers
│   │   ├── __init__.py              # Router aggregation
│   │   ├── health.py                # GET /health, /ready, /metrics
│   │   ├── dashboard.py             # GET /dashboard/*, /static/*
│   │   ├── ree.py                   # POST /ree/ingest, GET /ree/prices
│   │   ├── aemet.py                 # POST /aemet/ingest, GET /aemet/weather
│   │   ├── weather.py               # GET /weather/current, /weather/forecast
│   │   ├── siar.py                  # POST /siar/etl, GET /siar/historical
│   │   ├── predictions.py           # POST /predict/prices, /predict/production
│   │   ├── models.py                # POST /models/train, GET /models/validate, DELETE /models/{name}
│   │   ├── scheduler.py             # GET /scheduler/jobs, POST /scheduler/pause
│   │   └── gaps.py                  # POST /gaps/detect, POST /gaps/backfill
│   │
│   └── schemas/                     # Pydantic Models (Request/Response DTOs)
│       ├── __init__.py
│       ├── common.py                # ErrorResponse, PaginationParams, HealthResponse
│       ├── dashboard.py             # DashboardCompleteResponse, HeatmapData
│       ├── ree.py                   # REEPriceResponse, REEIngestRequest
│       ├── aemet.py                 # AEMETWeatherResponse, AEMETIngestRequest
│       ├── predictions.py           # PricePredictionResponse, ProductionRecommendation
│       ├── models.py                # ModelTrainRequest, ModelValidationResponse
│       └── scheduler.py             # JobStatusResponse, JobPauseRequest
│
├── domain/                          # Business Logic (Framework-Agnostic)
│   ├── __init__.py
│   ├── energy/                      # Energy pricing domain
│   │   ├── __init__.py
│   │   ├── entities.py              # EnergyPrice, TariffPeriod (dataclasses)
│   │   ├── forecaster.py            # Prophet-based price forecasting logic
│   │   └── optimization.py          # Production scheduling optimization
│   │
│   ├── weather/                     # Weather domain
│   │   ├── __init__.py
│   │   ├── entities.py              # WeatherObservation, WeatherForecast
│   │   └── aggregator.py            # Multi-source weather data aggregation
│   │
│   └── ml/                          # ML lifecycle domain
│       ├── __init__.py
│       ├── model_trainer.py         # Model training orchestration
│       ├── model_validator.py       # Backtesting & validation logic
│       └── feature_engineering.py   # Feature preparation for ML
│
├── services/                        # Application Services (Orchestration)
│   ├── __init__.py
│   ├── ree_service.py               # REE API client + InfluxDB persistence
│   ├── aemet_service.py             # AEMET API client + InfluxDB persistence
│   ├── weather_service.py           # Multi-source weather aggregation
│   ├── siar_etl_service.py          # SIAR historical data ETL (88k+ records)
│   ├── dashboard_service.py         # Dashboard data aggregation
│   ├── prediction_service.py        # ML prediction orchestration
│   ├── scheduler_service.py         # APScheduler job management
│   └── gap_detection_service.py     # Data gap detection & backfill
│
├── infrastructure/                  # External Integrations
│   ├── __init__.py
│   ├── influxdb/                    # InfluxDB client wrapper
│   │   ├── __init__.py
│   │   ├── client.py                # InfluxDB connection manager
│   │   ├── queries.py               # Reusable Flux queries
│   │   └── writers.py               # Batch write utilities
│   │
│   ├── external_apis/               # External API clients
│   │   ├── __init__.py
│   │   ├── ree_client.py            # REE API wrapper (with retries)
│   │   ├── aemet_client.py          # AEMET API wrapper
│   │   ├── openweather_client.py    # OpenWeatherMap wrapper
│   │   └── siar_client.py           # SIAR data fetcher
│   │
│   └── ml_storage/                  # ML model persistence
│       ├── __init__.py
│       ├── model_registry.py        # Model versioning & metadata
│       └── pickle_storage.py        # Pickle serialization utilities
│
├── core/                            # Shared Utilities
│   ├── __init__.py
│   ├── config.py                    # Settings (from env vars)
│   ├── exceptions.py                # Custom exceptions (DataGapError, ModelNotFoundError)
│   ├── logging_config.py            # Structured logging setup
│   └── security.py                  # API key validation (if needed)
│
└── tasks/                           # Background Jobs (APScheduler)
    ├── __init__.py
    ├── scheduler_config.py          # APScheduler setup
    ├── ree_jobs.py                  # REE data ingestion jobs
    ├── aemet_jobs.py                # AEMET data ingestion jobs
    ├── weather_jobs.py              # Weather data update jobs
    ├── ml_jobs.py                   # Model training/validation jobs
    └── gap_jobs.py                  # Gap detection jobs
```

---

## 🚫 STRICT RULES: What NOT to Do

### ❌ NEVER Do These Things:
1. **DO NOT create SQLAlchemy models** → We use InfluxDB (time-series DB)
2. **DO NOT use ORM patterns** → Use `influxdb_client` with Flux queries
3. **DO NOT put business logic in routers** → Always delegate to `services/` or `domain/`
4. **DO NOT hardcode API keys** → Always use `config.py` with environment variables
5. **DO NOT make synchronous external API calls in routes** → Use `httpx.AsyncClient`
6. **DO NOT duplicate code** → Extract common patterns to `core/` utilities
7. **DO NOT ignore error handling** → Wrap external calls in try/except with proper logging
8. **DO NOT expose internal errors to API responses** → Use custom exceptions + middleware

### ✅ ALWAYS Do These Things:
1. **ALWAYS validate inputs** → Use Pydantic schemas in routers
2. **ALWAYS use dependency injection** → Define in `dependencies.py`, inject in routers
3. **ALWAYS log errors** → Use structured logging (JSON format)
4. **ALWAYS handle InfluxDB connection errors** → Graceful degradation + retries
5. **ALWAYS version ML models** → Save with timestamp + metadata
6. **ALWAYS document endpoints** → Use FastAPI's `response_model` and docstrings
7. **ALWAYS separate concerns** → Router → Service → Domain/Infrastructure

---

## 📝 Refactoring Checklist (For Claude Code)

When refactoring `main.py`, follow this exact sequence:

### Phase 1: Setup Foundation (Day 1)
- [ ] Create directory structure (see above)
- [ ] Move `config.py` and extract all env vars
- [ ] Create `dependencies.py` with InfluxDB client factory
- [ ] Setup `core/logging_config.py` with structured logging
- [ ] Create `core/exceptions.py` with custom exceptions

### Phase 2: Extract Infrastructure (Day 2)
- [ ] Move InfluxDB code to `infrastructure/influxdb/client.py`
- [ ] Extract REE API client to `infrastructure/external_apis/ree_client.py`
- [ ] Extract AEMET API client to `infrastructure/external_apis/aemet_client.py`
- [ ] Extract OpenWeatherMap client to `infrastructure/external_apis/openweather_client.py`
- [ ] Add retry logic to all external API clients (use `tenacity`)

### Phase 3: Create Services (Day 3)
- [ ] Extract REE logic to `services/ree_service.py`
- [ ] Extract AEMET logic to `services/aemet_service.py`
- [ ] Extract weather aggregation to `services/weather_service.py`
- [ ] Extract SIAR ETL to `services/siar_etl_service.py`
- [ ] Extract dashboard logic to `services/dashboard_service.py`

### Phase 4: Create Domain Logic (Day 4)
- [ ] Extract Prophet forecasting to `domain/energy/forecaster.py`
- [ ] Extract production optimization to `domain/energy/optimization.py`
- [ ] Extract ML training logic to `domain/ml/model_trainer.py`
- [ ] Extract model validation to `domain/ml/model_validator.py`

### Phase 5: Create Routers (Day 5)
- [ ] Create `api/routers/health.py` (health checks)
- [ ] Create `api/routers/dashboard.py` (dashboard endpoints)
- [ ] Create `api/routers/ree.py` (REE endpoints)
- [ ] Create `api/routers/aemet.py` (AEMET endpoints)
- [ ] Create `api/routers/weather.py` (weather endpoints)
- [ ] Create `api/routers/siar.py` (SIAR endpoints)
- [ ] Create `api/routers/predictions.py` (ML prediction endpoints)
- [ ] Create `api/routers/models.py` (ML model management)
- [ ] Create `api/routers/scheduler.py` (scheduler management)
- [ ] Create `api/routers/gaps.py` (gap detection/backfill)

### Phase 6: Create Pydantic Schemas (Day 6)
- [ ] Create schemas for each router (see `api/schemas/` structure)
- [ ] Add validation rules (Field constraints, validators)
- [ ] Add docstrings for OpenAPI documentation

### Phase 7: Migrate APScheduler Jobs (Day 7)
- [ ] Move scheduler jobs to `tasks/` directory
- [ ] Extract job definitions to separate files
- [ ] Create `tasks/scheduler_config.py` for scheduler initialization

### Phase 8: Update main.py (Day 8)
- [ ] Simplify `main.py` to <100 lines
- [ ] Import and register all routers
- [ ] Add middleware (CORS, error handling, logging)
- [ ] Initialize APScheduler

### Phase 9: Testing & Validation (Day 9-10)
- [ ] Run existing tests: `pytest tests/`
- [ ] Test each router individually
- [ ] Test InfluxDB connectivity
- [ ] Test external API calls
- [ ] Test scheduler jobs
- [ ] Verify dashboard still works

---

## 🔍 Concrete Examples from Our Codebase

### Example 1: REE Router (NEW)

```python
# api/routers/ree.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, timedelta

from api.schemas.ree import (
    REEPriceResponse, 
    REEIngestRequest, 
    REEPriceListResponse
)
from api.schemas.common import ErrorResponse
from services.ree_service import REEService
from dependencies import get_ree_service
from core.exceptions import DataIngestionError, ExternalAPIError

router = APIRouter(prefix="/ree", tags=["REE - Energy Prices"])

@router.post(
    "/ingest",
    response_model=REEPriceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        500: {"model": ErrorResponse, "description": "External API error"},
        409: {"model": ErrorResponse, "description": "Data already exists"}
    },
    summary="Ingest REE Price Data",
    description="Fetch and store electricity prices from REE API for a specific date"
)
async def ingest_ree_prices(
    request: REEIngestRequest,
    service: REEService = Depends(get_ree_service)
):
    """
    Ingests electricity price data from REE (Red Eléctrica de España) API.
    
    **Business Rules:**
    - Only ingests data for dates in the past (not future)
    - Prevents duplicate ingestion (checks InfluxDB first)
    - Automatically detects and fills gaps in historical data
    
    **Rate Limits:**
    - REE API: 100 requests/hour
    - This endpoint: 10 requests/minute
    """
    try:
        result = await service.ingest_prices(
            date=request.date,
            force_refresh=request.force_refresh
        )
        return result
    except ExternalAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"REE API error: {str(e)}"
        )
    except DataIngestionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.get(
    "/prices",
    response_model=REEPriceListResponse,
    summary="Get Historical Prices",
    description="Retrieve electricity prices from InfluxDB for a date range"
)
async def get_prices(
    start_date: datetime,
    end_date: datetime,
    tariff_period: Optional[str] = None,
    service: REEService = Depends(get_ree_service)
):
    """
    Retrieves historical electricity prices from InfluxDB.
    
    **Query Parameters:**
    - `start_date`: Start of date range (ISO format)
    - `end_date`: End of date range (ISO format)
    - `tariff_period`: Optional filter (P1, P2, P3)
    
    **Returns:**
    - List of hourly prices with metadata
    - Average price for the period
    - Min/max prices
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date"
        )
    
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 365 days"
        )
    
    result = await service.get_prices(
        start_date=start_date,
        end_date=end_date,
        tariff_period=tariff_period
    )
    return result
```

### Example 2: REE Service (NEW)

```python
# services/ree_service.py
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from infrastructure.external_apis.ree_client import REEClient
from infrastructure.influxdb.client import InfluxDBClient
from infrastructure.influxdb.writers import batch_write_points
from domain.energy.entities import EnergyPrice
from core.exceptions import DataIngestionError, ExternalAPIError
from api.schemas.ree import REEPriceResponse, REEPriceListResponse

logger = logging.getLogger(__name__)

class REEService:
    """
    Orchestrates REE data ingestion and retrieval.
    
    Responsibilities:
    - Fetch data from REE API
    - Transform to domain entities
    - Persist to InfluxDB
    - Query historical data
    """
    
    def __init__(
        self, 
        ree_client: REEClient, 
        influxdb_client: InfluxDBClient
    ):
        self.ree_client = ree_client
        self.influxdb_client = influxdb_client
    
    async def ingest_prices(
        self, 
        date: datetime, 
        force_refresh: bool = False
    ) -> REEPriceResponse:
        """
        Ingest REE prices for a specific date.
        
        Args:
            date: Date to ingest (must be in the past)
            force_refresh: If True, overwrites existing data
        
        Returns:
            REEPriceResponse with ingestion metadata
        
        Raises:
            DataIngestionError: If data already exists and force_refresh=False
            ExternalAPIError: If REE API call fails
        """
        # Business rule: Only ingest past dates
        if date > datetime.now():
            raise DataIngestionError("Cannot ingest future dates")
        
        # Check if data already exists
        if not force_refresh:
            existing = await self._check_existing_data(date)
            if existing:
                raise DataIngestionError(
                    f"Data for {date.date()} already exists. Use force_refresh=True to overwrite."
                )
        
        # Fetch from REE API
        try:
            logger.info(f"Fetching REE prices for {date.date()}")
            raw_data = await self.ree_client.get_prices(date)
        except Exception as e:
            logger.error(f"REE API error: {str(e)}")
            raise ExternalAPIError(f"Failed to fetch REE data: {str(e)}")
        
        # Transform to domain entities
        energy_prices = [
            EnergyPrice(
                timestamp=item['datetime'],
                price_kwh=item['value'],
                tariff_period=item['period'],
                source='REE'
            )
            for item in raw_data
        ]
        
        # Persist to InfluxDB
        try:
            points_written = await batch_write_points(
                client=self.influxdb_client,
                measurement='energy_prices',
                entities=energy_prices,
                bucket='chocolate_factory'
            )
            logger.info(f"Wrote {points_written} REE prices to InfluxDB")
        except Exception as e:
            logger.error(f"InfluxDB write error: {str(e)}")
            raise DataIngestionError(f"Failed to write to InfluxDB: {str(e)}")
        
        return REEPriceResponse(
            date=date,
            records_ingested=len(energy_prices),
            source='REE',
            ingested_at=datetime.now()
        )
    
    async def get_prices(
        self,
        start_date: datetime,
        end_date: datetime,
        tariff_period: Optional[str] = None
    ) -> REEPriceListResponse:
        """
        Query historical prices from InfluxDB.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            tariff_period: Optional filter (P1, P2, P3)
        
        Returns:
            REEPriceListResponse with prices and aggregates
        """
        # Build Flux query
        flux_query = f'''
        from(bucket: "chocolate_factory")
          |> range(start: {start_date.isoformat()}Z, stop: {end_date.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "energy_prices")
          |> filter(fn: (r) => r["_field"] == "price_kwh")
        '''
        
        if tariff_period:
            flux_query += f'''
          |> filter(fn: (r) => r["tariff_period"] == "{tariff_period}")
            '''
        
        # Execute query
        try:
            results = await self.influxdb_client.query(flux_query)
        except Exception as e:
            logger.error(f"InfluxDB query error: {str(e)}")
            raise DataIngestionError(f"Failed to query InfluxDB: {str(e)}")
        
        # Parse results
        prices = [
            {
                'timestamp': record.get_time(),
                'price_kwh': record.get_value(),
                'tariff_period': record.values.get('tariff_period')
            }
            for record in results
        ]
        
        # Calculate aggregates
        avg_price = sum(p['price_kwh'] for p in prices) / len(prices) if prices else 0
        min_price = min((p['price_kwh'] for p in prices), default=0)
        max_price = max((p['price_kwh'] for p in prices), default=0)
        
        return REEPriceListResponse(
            prices=prices,
            total_records=len(prices),
            average_price=avg_price,
            min_price=min_price,
            max_price=max_price,
            period={'start': start_date, 'end': end_date}
        )
    
    async def _check_existing_data(self, date: datetime) -> bool:
        """Check if data exists for a given date."""
        flux_query = f'''
        from(bucket: "chocolate_factory")
          |> range(start: {date.isoformat()}Z, stop: {(date + timedelta(days=1)).isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "energy_prices")
          |> count()
        '''
        results = await self.influxdb_client.query(flux_query)
        return len(list(results)) > 0
```

### Example 3: Pydantic Schema (NEW)

```python
# api/schemas/ree.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional, Dict

class REEIngestRequest(BaseModel):
    """Request schema for ingesting REE prices."""
    
    date: datetime = Field(
        ...,
        description="Date to ingest (YYYY-MM-DD format)",
        example="2025-10-06"
    )
    force_refresh: bool = Field(
        default=False,
        description="Overwrite existing data if True"
    )
    
    @validator('date')
    def validate_date_not_future(cls, v):
        if v > datetime.now():
            raise ValueError("Cannot ingest future dates")
        if v < datetime(2022, 1, 1):
            raise ValueError("REE data only available from 2022 onwards")
        return v

class REEPriceResponse(BaseModel):
    """Response schema for REE price ingestion."""
    
    date: datetime
    records_ingested: int = Field(..., ge=0, description="Number of records written to InfluxDB")
    source: str = Field(default="REE", description="Data source")
    ingested_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-06T00:00:00Z",
                "records_ingested": 24,
                "source": "REE",
                "ingested_at": "2025-10-06T14:30:00Z"
            }
        }

class REEPriceListResponse(BaseModel):
    """Response schema for historical price queries."""
    
    prices: List[Dict]
    total_records: int
    average_price: float = Field(..., ge=0, description="Average price in €/kWh")
    min_price: float
    max_price: float
    period: Dict[str, datetime]
    
    class Config:
        json_schema_extra = {
            "example": {
                "prices": [
                    {
                        "timestamp": "2025-10-06T00:00:00Z",
                        "price_kwh": 0.15,
                        "tariff_period": "P3"
                    }
                ],
                "total_records": 720,
                "average_price": 0.18,
                "min_price": 0.10,
                "max_price": 0.35,
                "period": {
                    "start": "2025-10-01T00:00:00Z",
                    "end": "2025-10-31T23:59:59Z"
                }
            }
        }
```

### Example 4: Updated main.py (SLIM)

```python
# main.py (NEW VERSION - <100 lines)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.logging_config import setup_logging
from dependencies import get_influxdb_client, init_scheduler
from api.routers import (
    health,
    dashboard,
    ree,
    aemet,
    weather,
    siar,
    predictions,
    models,
    scheduler,
    gaps
)

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Chocolate Factory API")
    
    # Initialize InfluxDB connection
    influxdb_client = get_influxdb_client()
    await influxdb_client.health_check()
    
    # Initialize APScheduler
    scheduler = init_scheduler()
    scheduler.start()
    logger.info("APScheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Chocolate Factory API")
    scheduler.shutdown()
    await influxdb_client.close()

# Create FastAPI app
app = FastAPI(
    title="Chocolate Factory API",
    description="Industrial energy optimization system with ML predictions",
    version="0.41.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(ree.router)
app.include_router(aemet.router)
app.include_router(weather.router)
app.include_router(siar.router)
app.include_router(predictions.router)
app.include_router(models.router)
app.include_router(scheduler.router)
app.include_router(gaps.router)

@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
```

---

## 🎓 Success Criteria

After refactoring, verify these conditions:

### ✅ Code Quality
- [ ] `main.py` is < 100 lines
- [ ] No business logic in routers (only in `services/` or `domain/`)
- [ ] All routers have Pydantic schemas
- [ ] All external API calls have retry logic
- [ ] All InfluxDB queries are in `infrastructure/influxdb/queries.py`

### ✅ Functionality
- [ ] All existing endpoints still work
- [ ] Dashboard loads correctly
- [ ] ML predictions work
- [ ] APScheduler jobs run successfully
- [ ] Data ingestion (REE, AEMET, SIAR) works

### ✅ Testing
- [ ] Existing tests pass: `pytest tests/`
- [ ] All services have unit tests
- [ ] All routers have integration tests
- [ ] Test coverage > 70%

### ✅ Documentation
- [ ] All endpoints have OpenAPI docstrings
- [ ] All Pydantic models have examples
- [ ] README updated with new structure
- [ ] `.claude/architecture.md` updated

---

## 🚨 Common Mistakes to Avoid

1. **Don't over-engineer**: Start simple, add complexity only when needed
2. **Don't break existing functionality**: Test after each refactoring step
3. **Don't ignore InfluxDB specifics**: It's NOT a SQL database
4. **Don't forget error handling**: External APIs fail, handle gracefully
5. **Don't skip logging**: Every service should log important events
6. **Don't commit secrets**: Always use `.env` files (gitignored)

---

## 📚 Reference Documentation

- FastAPI Docs: https://fastapi.tiangolo.com/
- InfluxDB Python Client: https://influxdb-client.readthedocs.io/
- Pydantic: https://docs.pydantic.dev/
- APScheduler: https://apscheduler.readthedocs.io/
- Prophet: https://facebook.github.io/prophet/

---

## 🤖 Instructions for Claude Code

When you read this file and the user asks to refactor `main.py`, follow these steps:

### Step-by-Step Execution Protocol

1. **READ FIRST**: 
   - Read `CLAUDE.md` for full project context
   - Read `.claude/rules/production_rules.md` for business logic
   - Read current sprint in `.claude/sprints/ml-evolution/`
   - Understand we use InfluxDB (NOT SQLAlchemy)

2. **ASK BEFORE ACTING**:
   - "I'll refactor main.py following the API Architect guide. This will take ~8 days. Should I proceed with Phase 1 (setup foundation)?"
   - Wait for user confirmation before creating files

3. **REFACTOR INCREMENTALLY**:
   - Complete ONE phase at a time (see checklist above)
   - After each phase, run: `ruff check src/` and `pytest tests/`
   - Show user what was changed and ask if they want to continue

4. **PRESERVE FUNCTIONALITY**:
   - NEVER remove code without understanding what it does
   - If unsure about a function's purpose, ASK the user
   - Test each endpoint after refactoring its router

5. **FOLLOW NAMING CONVENTIONS**:
   - Routers: `{domain}_router.py` (e.g., `ree_router.py`)
   - Services: `{domain}_service.py` (e.g., `ree_service.py`)
   - Schemas: `{domain}.py` in `api/schemas/` (e.g., `api/schemas/ree.py`)
   - Use snake_case for files, PascalCase for classes

6. **GIT COMMITS**:
   - Commit after each phase completes successfully
   - Use descriptive messages: "refactor: extract REE router from main.py"
   - ONLY commit when user explicitly asks

7. **VALIDATION CHECKLIST**:
   After refactoring, run these commands and show results to user:
   ```bash
   # Code quality
   ruff check src/
   mypy src/ --ignore-missing-imports
   
   # Tests
   pytest tests/ -v
   
   # API health check
   curl http://localhost:8000/health
   
   # Dashboard accessibility
   curl http://localhost:8000/dashboard/complete
   ```

8. **ROLLBACK STRATEGY**:
   If something breaks:
   - Show the error to the user immediately
   - Explain what went wrong
   - Ask: "Should I rollback this change or try to fix it?"

9. **DOCUMENTATION UPDATES**:
   After refactoring completes, update:
   - [ ] `CLAUDE.md` with new structure
   - [ ] `.claude/architecture.md` with new diagram
   - [ ] `README.md` with updated project structure
   - [ ] Add docstrings to all new modules

10. **FINAL REPORT**:
    When all phases complete, provide a summary:
    - Lines of code removed from main.py
    - Number of new modules created
    - Test coverage percentage
    - Any breaking changes (if any)
    - Recommended next steps

---

## 📊 Migration Progress Tracker

Use this template to track progress (update after each phase):

```markdown
## Refactoring Progress

### Phase 1: Foundation ✅ / ⏳ / ❌
- [x] Directory structure created
- [x] config.py extracted
- [x] dependencies.py created
- [x] logging_config.py setup
- [x] exceptions.py created
**Status**: Completed on YYYY-MM-DD
**Tests**: All passing ✅
**Commits**: abc123f

### Phase 2: Infrastructure ⏳
- [x] InfluxDB client extracted
- [ ] REE client extracted
- [ ] AEMET client extracted
- [ ] OpenWeatherMap client extracted
- [ ] Retry logic added
**Status**: In progress
**Tests**: Pending
**Commits**: -

### Phase 3-8: [Continue pattern...]
```

---

## 🔧 Debugging Guide

If you encounter issues during refactoring:

### Issue: Import errors
```python
# Problem: ModuleNotFoundError after moving code
# Solution: Check __init__.py files exist in all directories
# Solution: Use absolute imports from project root

# ❌ Wrong
from services import ree_service

# ✅ Correct
from services.ree_service import REEService
```

### Issue: InfluxDB connection fails
```python
# Problem: Cannot connect to InfluxDB after refactoring
# Solution: Check dependencies.py provides correct client
# Solution: Verify InfluxDB container is running

# Test connection manually:
docker compose exec chocolate_factory_brain python -c "
from infrastructure.influxdb.client import get_influxdb_client
client = get_influxdb_client()
print(client.health())
"
```

### Issue: APScheduler jobs not running
```python
# Problem: Jobs scheduled but not executing
# Solution: Verify scheduler.start() called in main.py lifespan
# Solution: Check job definitions in tasks/ directory

# Debug scheduler:
curl http://localhost:8000/scheduler/jobs
```

### Issue: External API calls failing
```python
# Problem: REE/AEMET API returns errors
# Solution: Check API keys in .env file
# Solution: Verify retry logic in infrastructure/external_apis/

# Test API client directly:
docker compose exec chocolate_factory_brain python -c "
from infrastructure.external_apis.ree_client import REEClient
import asyncio
client = REEClient()
result = asyncio.run(client.get_prices('2025-10-06'))
print(result)
"
```

---

## 🎯 Expected Outcomes

After completing the refactoring, the codebase should have:

### Quantitative Metrics
- **main.py**: 3,734 lines → <100 lines (97% reduction)
- **Modularity**: 1 file → ~40 modules
- **Test Coverage**: Current% → >70%
- **Import depth**: Flat → Max 3 levels
- **Code duplication**: High → Minimal (DRY principle)

### Qualitative Improvements
- **Readability**: Easy to understand each module's purpose
- **Maintainability**: Can modify one domain without affecting others
- **Testability**: Can test services independently of routers
- **Scalability**: Easy to add new endpoints/features
- **Onboarding**: New developers can understand structure quickly

### Architecture Benefits
- **Separation of Concerns**: Router → Service → Domain → Infrastructure
- **Dependency Injection**: All dependencies explicit and mockable
- **Error Handling**: Centralized exception handling
- **Logging**: Structured logs at each layer
- **Documentation**: Auto-generated OpenAPI docs

---

## 🚀 Post-Refactoring: Next Steps

Once refactoring is complete, consider:

1. **Add Integration Tests**:
   - Test full workflows (ingest → predict → optimize)
   - Test error scenarios (API failures, DB disconnects)
   - Test concurrent requests

2. **Implement Caching**:
   - Cache frequently accessed InfluxDB queries
   - Cache ML predictions for repeated inputs
   - Use Redis or in-memory cache

3. **Add Monitoring**:
   - Implement `/metrics` endpoint (Prometheus format)
   - Add performance tracking (response times)
   - Add business metrics (predictions accuracy, cost savings)

4. **Improve Error Handling**:
   - Add circuit breakers for external APIs
   - Implement graceful degradation
   - Add alerting (email/Telegram on critical errors)

5. **Security Hardening**:
   - Add API key authentication
   - Implement rate limiting per endpoint
   - Add request validation middleware
   - Audit log sensitive operations

6. **CI/CD Pipeline**:
   - GitHub Actions for automated testing
   - Docker image building on merge
   - Automated deployment to production

7. **MCP Server Implementation**:
   - Now that code is modular, implement MCP endpoints
   - Connect Claude Code to project via MCP
   - Expose business context to LLM

---

## 📝 Refactoring Anti-Patterns (Avoid These!)

### ❌ Anti-Pattern 1: Big Bang Refactoring
```python
# DON'T: Refactor everything at once
# Problem: High risk, hard to debug, blocks development

# DO: Incremental refactoring (phase by phase)
# Benefit: Lower risk, easier rollback, continuous testing
```

### ❌ Anti-Pattern 2: Over-Abstraction
```python
# DON'T: Create unnecessary abstraction layers
class AbstractBaseGenericRepositoryFactory:
    pass

# DO: Keep it simple, add abstraction when needed
class REEService:
    def __init__(self, ree_client, influxdb_client):
        self.ree_client = ree_client
        self.influxdb = influxdb_client
```

### ❌ Anti-Pattern 3: Ignoring Tests
```python
# DON'T: Refactor without running tests
# Problem: Silent breakage, production bugs

# DO: Run tests after each phase
pytest tests/ -v --cov=src/
```

### ❌ Anti-Pattern 4: Breaking Existing APIs
```python
# DON'T: Change endpoint URLs or response formats
# Problem: Breaks dashboard, external integrations

# DO: Keep existing URLs, add new ones if needed
# Old: /dashboard/complete (keep working)
# New: /api/v1/dashboard/complete (new version)
```

### ❌ Anti-Pattern 5: Hardcoding Configuration
```python
# DON'T: Hardcode values in refactored code
INFLUXDB_URL = "http://influxdb:8086"  # Bad

# DO: Use config.py with environment variables
from core.config import settings
influxdb_url = settings.INFLUXDB_URL  # Good
```

---

## 🎓 Learning Resources for Refactoring

- **Clean Architecture**: Robert C. Martin - Principles used in this guide
- **Domain-Driven Design**: Eric Evans - Domain layer concepts
- **FastAPI Best Practices**: https://github.com/zhanymkanov/fastapi-best-practices
- **Python Project Structure**: https://realpython.com/python-application-layouts/
- **Dependency Injection in Python**: https://python-dependency-injector.ets-labs.org/

---

## ✅ Final Checklist for Claude Code

Before marking refactoring as complete, verify:

- [ ] `main.py` is < 100 lines
- [ ] All routers created and registered
- [ ] All services extracted with tests
- [ ] All Pydantic schemas defined
- [ ] InfluxDB queries in infrastructure layer
- [ ] External API clients have retry logic
- [ ] APScheduler jobs moved to tasks/
- [ ] All existing endpoints still work
- [ ] Dashboard loads and displays data
- [ ] Tests pass: `pytest tests/`
- [ ] Linting passes: `ruff check src/`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated (CLAUDE.md, README.md)
- [ ] Git commits made with descriptive messages
- [ ] User has reviewed and approved changes

---

## 🎉 Success Message Template

When refactoring is complete, present this summary to the user:

```
✅ Refactoring Complete!

📊 Metrics:
- main.py: 3,734 → 87 lines (97.7% reduction)
- Modules created: 42
- Test coverage: 78% (↑15%)
- Tests passing: 156/156
- Linting issues: 0
- Type errors: 0

📁 Structure:
- 10 routers created (REE, AEMET, Weather, SIAR, etc.)
- 8 services extracted
- 3 domain modules (energy, weather, ml)
- 4 infrastructure clients (InfluxDB, REE, AEMET, OpenWeather)
- 10 Pydantic schemas

✅ Functionality:
- All existing endpoints working
- Dashboard operational
- ML predictions functional
- Scheduler jobs running
- Data ingestion tested

📚 Documentation:
- OpenAPI docs updated (/docs)
- CLAUDE.md updated with new structure
- architecture.md diagrams updated
- All modules have docstrings

🚀 Next Steps:
1. Add integration tests for full workflows
2. Implement caching for frequent queries
3. Add monitoring (/metrics endpoint)
4. Proceed with MCP server implementation

Ready for Sprint 09-10 and MCP integration! 🎊
```

---

## 🔄 Version History

- **v1.0** (2025-10-06): Initial API Architect guide
- **v2.0** (2025-10-06): Adapted for Chocolate Factory project with InfluxDB specifics, real domain examples, and Claude Code execution protocol

---

**Remember**: Refactoring is about improving structure without changing behavior. Test early, test often, and always keep the user informed of progress!