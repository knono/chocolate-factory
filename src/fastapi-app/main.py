"""
Chocolate Factory - FastAPI Main Application (Refactored)
==========================================================

Clean Architecture implementation with <100 lines.

All business logic extracted to:
- infrastructure/: External integrations (InfluxDB, APIs)
- services/: Application orchestration
- domain/: Pure business logic
- api/: HTTP interface (routers + schemas)
- tasks/: Background jobs (APScheduler)
- core/: Shared utilities (config, logging, exceptions)
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.logging_config import setup_logging
from dependencies import init_scheduler, cleanup_dependencies

# Import routers
from api.routers import (
    health_router,
    ree_router,
    weather_router,
    dashboard_router,
    optimization_router,
    analysis_router,
    gaps_router,
    insights_router,
    chatbot_router,  # Sprint 11
    health_monitoring_router,  # Sprint 13 (pivoted)
    ml_predictions_router,  # sklearn predictions
    price_forecast_router  # Sprint 06 - Prophet forecasting
)

# Setup logging (console only to avoid permission issues)
setup_logging(enable_file_logging=False)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("🧠 Starting Chocolate Factory API (Clean Architecture)")

    # Prophet model is pre-trained and included in Docker image
    # See docker/fastapi.Dockerfile: COPY models/forecasting/prophet_latest.pkl
    # If model is missing, it will be trained automatically on first prediction request

    # Initialize APScheduler
    scheduler = await init_scheduler()
    logger.info("📅 APScheduler started with background jobs")

    yield

    # Cleanup
    logger.info("🛑 Shutting down Chocolate Factory API")
    await cleanup_dependencies()


# Create FastAPI app
app = FastAPI(
    title="Chocolate Factory API",
    description="Clean Architecture - Energy optimization with ML predictions",
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static files
if settings.STATIC_FILES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_FILES_DIR)), name="static")
    logger.info(f"✅ Static files mounted: {settings.STATIC_FILES_DIR}")

# Register routers
app.include_router(health_router)
app.include_router(ree_router)
app.include_router(weather_router)
app.include_router(dashboard_router)
app.include_router(optimization_router)
app.include_router(analysis_router)
app.include_router(gaps_router)
app.include_router(insights_router)
app.include_router(chatbot_router)  # Sprint 11
app.include_router(health_monitoring_router)  # Sprint 13 (pivoted to health monitoring)
app.include_router(ml_predictions_router)  # sklearn predictions
app.include_router(price_forecast_router)  # Sprint 06 - Prophet forecasting

logger.info("✅ API routers registered")


@app.get("/")
async def root():
    """Redirect to dashboard."""
    return RedirectResponse(url="/static/index.html")


@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect /dashboard to static dashboard."""
    return RedirectResponse(url="/static/index.html")


@app.get("/vpn")
async def vpn_dashboard():
    """Redirect to Tailscale Health Monitoring dashboard (Sprint 13 pivoted)."""
    return RedirectResponse(url="/static/vpn.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_new:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
