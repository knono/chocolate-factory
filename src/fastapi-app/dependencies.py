"""
Dependency Injection Module
============================

Provides dependency injection for FastAPI endpoints.
All external dependencies (InfluxDB, API clients, services) are created here.

Usage in routers:
    @router.get("/endpoint")
    async def endpoint(
        influxdb: InfluxDBClient = Depends(get_influxdb_client),
        ree_service: REEService = Depends(get_ree_service)
    ):
        ...
"""

from functools import lru_cache
from typing import Generator, Optional
import logging

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from core.config import settings

logger = logging.getLogger(__name__)


# =================================================================
# INFLUXDB CLIENT
# =================================================================

@lru_cache()
def get_influxdb_client() -> InfluxDBClient:
    """
    Get InfluxDB client instance (singleton pattern).

    Returns:
        InfluxDBClient: Configured InfluxDB client

    Raises:
        ConnectionError: If InfluxDB is unreachable
    """
    try:
        client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
            timeout=settings.INFLUXDB_TIMEOUT,
            verify_ssl=settings.INFLUXDB_VERIFY_SSL,
            enable_gzip=settings.INFLUXDB_ENABLE_GZIP
        )

        # Test connection
        health = client.health()
        logger.info(f"✅ InfluxDB connected: {health.status} - {settings.INFLUXDB_URL}")

        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to InfluxDB: {e}")
        raise ConnectionError(f"InfluxDB connection failed: {e}")


def get_influxdb_write_api():
    """
    Get InfluxDB write API (for synchronous writes).

    Returns:
        WriteApi: InfluxDB write API instance
    """
    client = get_influxdb_client()
    return client.write_api(write_options=SYNCHRONOUS)


def get_influxdb_query_api():
    """
    Get InfluxDB query API.

    Returns:
        QueryApi: InfluxDB query API instance
    """
    client = get_influxdb_client()
    return client.query_api()


# =================================================================
# EXTERNAL API CLIENTS (Lazy loading)
# =================================================================

_ree_client_instance: Optional[object] = None
_aemet_client_instance: Optional[object] = None
_openweather_client_instance: Optional[object] = None


def get_ree_client():
    """
    Get REE API client instance (lazy singleton).

    Returns:
        REEClient: REE API client
    """
    global _ree_client_instance

    if _ree_client_instance is None:
        # Import here to avoid circular dependencies
        from services.ree_client import REEClient
        _ree_client_instance = REEClient()
        logger.info("✅ REE client initialized")

    return _ree_client_instance


def get_aemet_client():
    """
    Get AEMET API client instance (lazy singleton).

    Returns:
        AEMETClient: AEMET API client
    """
    global _aemet_client_instance

    if _aemet_client_instance is None:
        # Import here to avoid circular dependencies
        from services.aemet_client import AEMETClient
        _aemet_client_instance = AEMETClient()
        logger.info("✅ AEMET client initialized")

    return _aemet_client_instance


def get_openweather_client():
    """
    Get OpenWeatherMap API client instance (lazy singleton).

    Returns:
        OpenWeatherMapClient: OpenWeatherMap API client
    """
    global _openweather_client_instance

    if _openweather_client_instance is None:
        # Import here to avoid circular dependencies
        from services.openweathermap_client import OpenWeatherMapClient
        _openweather_client_instance = OpenWeatherMapClient()
        logger.info("✅ OpenWeatherMap client initialized")

    return _openweather_client_instance


# =================================================================
# ML SERVICES (Lazy loading)
# =================================================================

_direct_ml_service_instance: Optional[object] = None
_enhanced_ml_service_instance: Optional[object] = None


def get_direct_ml_service():
    """
    Get Direct ML Service instance (lazy singleton).

    Returns:
        DirectMLService: Direct ML service
    """
    global _direct_ml_service_instance

    if _direct_ml_service_instance is None:
        from services.direct_ml import DirectMLService
        _direct_ml_service_instance = DirectMLService()
        logger.info("✅ Direct ML Service initialized")

    return _direct_ml_service_instance


def get_enhanced_ml_service():
    """
    Get Enhanced ML Service instance (lazy singleton).

    Returns:
        EnhancedMLService: Enhanced ML service
    """
    global _enhanced_ml_service_instance

    if _enhanced_ml_service_instance is None:
        from services.enhanced_ml_service import EnhancedMLService
        _enhanced_ml_service_instance = EnhancedMLService()
        logger.info("✅ Enhanced ML Service initialized")

    return _enhanced_ml_service_instance


# =================================================================
# DASHBOARD SERVICE
# =================================================================

_dashboard_service_instance: Optional[object] = None


def get_dashboard_service():
    """
    Get Dashboard Service instance (lazy singleton).

    Returns:
        DashboardService: Dashboard service
    """
    global _dashboard_service_instance

    if _dashboard_service_instance is None:
        from services.dashboard import DashboardService
        _dashboard_service_instance = DashboardService()
        logger.info("✅ Dashboard Service initialized")

    return _dashboard_service_instance


# =================================================================
# SCHEDULER (APScheduler)
# =================================================================

_scheduler_instance: Optional[object] = None


def get_scheduler():
    """
    Get APScheduler instance (lazy singleton).

    Returns:
        AsyncIOScheduler: APScheduler instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.jobstores.memory import MemoryJobStore

        jobstores = {
            'default': MemoryJobStore()
        }

        _scheduler_instance = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults=settings.SCHEDULER_JOB_DEFAULTS,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        logger.info("✅ APScheduler initialized")

    return _scheduler_instance


async def init_scheduler():
    """
    Initialize and start the APScheduler.

    This function should be called during application startup.
    """
    scheduler = get_scheduler()

    if not scheduler.running:
        # Import and register all jobs
        from tasks.scheduler_config import register_all_jobs
        await register_all_jobs(scheduler)

        # Start scheduler
        scheduler.start()
        logger.info("🚀 APScheduler started with all jobs registered")

    return scheduler


async def shutdown_scheduler():
    """
    Shutdown the APScheduler gracefully.

    This function should be called during application shutdown.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("🛑 APScheduler stopped")


# =================================================================
# CLEANUP
# =================================================================

async def cleanup_dependencies():
    """
    Cleanup all dependency resources.

    This function should be called during application shutdown.
    """
    # Shutdown scheduler
    await shutdown_scheduler()

    # Close InfluxDB client
    try:
        client = get_influxdb_client()
        client.close()
        logger.info("✅ InfluxDB client closed")
    except Exception as e:
        logger.error(f"❌ Error closing InfluxDB client: {e}")

    logger.info("🧹 All dependencies cleaned up")
