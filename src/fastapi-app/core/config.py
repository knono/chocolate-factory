"""
Core Configuration Module
=========================

Centralized configuration management using Pydantic Settings.
All environment variables are loaded and validated here.

Environment Variables Required:
- INFLUXDB_URL: InfluxDB connection URL
- INFLUXDB_TOKEN: InfluxDB authentication token
- INFLUXDB_ORG: InfluxDB organization name
- INFLUXDB_BUCKET: Default bucket name
- REE_API_TOKEN: REE API token (optional)
- AEMET_API_KEY: AEMET API key
- OPENWEATHERMAP_API_KEY: OpenWeatherMap API key
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # =================================================================
    # APPLICATION SETTINGS
    # =================================================================
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TZ: str = "Europe/Madrid"
    API_VERSION: str = "0.41.0"

    # =================================================================
    # INFLUXDB SETTINGS
    # =================================================================
    INFLUXDB_URL: str = "http://influxdb:8086"
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str = "chocolate_factory"
    INFLUXDB_BUCKET: str = "energy_data"
    INFLUXDB_BUCKET_SIAR: str = "siar_historical"

    # InfluxDB connection settings
    INFLUXDB_TIMEOUT: int = 10000  # milliseconds
    INFLUXDB_VERIFY_SSL: bool = False
    INFLUXDB_ENABLE_GZIP: bool = True

    # =================================================================
    # EXTERNAL API KEYS
    # =================================================================
    REE_API_TOKEN: Optional[str] = None  # REE API doesn't require auth
    AEMET_API_KEY: str
    OPENWEATHERMAP_API_KEY: str
    ANTHROPIC_API_KEY: str  # Sprint 11: Chatbot BI with Claude Haiku

    # API endpoints (with fallback defaults)
    REE_API_BASE_URL: str = "https://apidatos.ree.es/es/datos"
    AEMET_API_BASE_URL: str = "https://opendata.aemet.es/opendata/api"
    OPENWEATHERMAP_API_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # =================================================================
    # ML MODEL SETTINGS
    # =================================================================
    ML_MODELS_DIR: Path = Path("/app/models")
    ML_PROPHET_MODEL_PATH: Path = Path("/app/models/price_forecast_prophet.pkl")
    ML_ENERGY_MODEL_PATH: Path = Path("/app/models/energy_optimization_rf.pkl")
    ML_PRODUCTION_MODEL_PATH: Path = Path("/app/models/production_classifier_rf.pkl")

    # Model training settings
    ML_TRAINING_INTERVAL_MINUTES: int = 30
    ML_PROPHET_TRAINING_INTERVAL_MINUTES: int = 60
    ML_MIN_TRAINING_SAMPLES: int = 100

    # =================================================================
    # SCHEDULER SETTINGS (APScheduler)
    # =================================================================
    SCHEDULER_TIMEZONE: str = "Europe/Madrid"
    SCHEDULER_JOB_DEFAULTS: dict = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 300
    }

    # Job intervals (minutes)
    REE_INGESTION_INTERVAL: int = 5
    WEATHER_INGESTION_INTERVAL: int = 5
    ML_TRAINING_INTERVAL: int = 30
    ML_PREDICTION_INTERVAL: int = 30
    PROPHET_FORECAST_INTERVAL: int = 60
    BACKFILL_INTERVAL: int = 120
    HEALTH_CHECK_INTERVAL: int = 15

    # =================================================================
    # DATA INGESTION SETTINGS
    # =================================================================
    # REE data settings
    REE_HISTORICAL_START_DATE: str = "2022-01-01"
    REE_MAX_RETRY_ATTEMPTS: int = 3
    REE_RETRY_DELAY_SECONDS: int = 5

    # AEMET settings
    AEMET_DEFAULT_STATION: str = "3195"  # Madrid-Retiro
    AEMET_TOKEN_REFRESH_DAYS: int = 6

    # Weather hybrid settings
    WEATHER_PRIMARY_SOURCE: str = "aemet"  # aemet or openweathermap
    WEATHER_FALLBACK_ENABLED: bool = True

    # =================================================================
    # GAP DETECTION & BACKFILL
    # =================================================================
    GAP_DETECTION_ENABLED: bool = True
    GAP_MAX_HOURS: float = 6.0
    BACKFILL_BATCH_SIZE: int = 100
    BACKFILL_AUTO_RUN: bool = True

    # =================================================================
    # CORS & SECURITY
    # =================================================================
    CORS_ORIGINS: List[str] = ["*"]  # In production, specify exact domains
    CORS_ALLOW_CREDENTIALS: bool = True

    # Rate limiting (Sprint 05)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_ML: str = "10/minute"

    # =================================================================
    # CACHE SETTINGS (Sprint 05)
    # =================================================================
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000

    # =================================================================
    # DASHBOARD SETTINGS
    # =================================================================
    STATIC_FILES_DIR: Path = Path("/app/static")
    DASHBOARD_REFRESH_INTERVAL: int = 30  # seconds

    # =================================================================
    # BUSINESS LOGIC SETTINGS
    # =================================================================
    BUSINESS_RULES_PATH: Path = Path("/app/.claude/rules/business-logic-suggestions.md")

    # Production optimization settings
    PRODUCTION_TARGET_KG_PER_DAY: int = 200
    PRODUCTION_BATCH_DURATION_HOURS: int = 6
    PRODUCTION_PROCESSES: List[str] = [
        "Molienda de cacao",
        "Conchado Premium",
        "Temperado fino",
        "Moldeado de barras"
    ]

    # Tariff periods (Spanish electricity)
    TARIFF_PERIODS: dict = {
        "P1": {"name": "Punta", "color": "#dc2626", "hours": [10, 11, 12, 18, 19, 20]},
        "P2": {"name": "Llano", "color": "#f59e0b", "hours": [8, 14, 15, 16, 22]},
        "P3": {"name": "Valle", "color": "#10b981", "hours": [0, 1, 2, 3, 4, 5, 6, 7, 9, 13, 17, 21, 23]}
    }

    # =================================================================
    # CHATBOT SETTINGS (Sprint 11)
    # =================================================================
    CHATBOT_MODEL: str = "claude-3-5-haiku-20241022"
    CHATBOT_MAX_TOKENS: int = 300  # Respuestas concisas
    CHATBOT_RATE_LIMIT: str = "20/minute"  # Max requests per minute
    CHATBOT_CONTEXT_MAX_TOKENS: int = 2000  # Max tokens for context

    # =================================================================
    # FEATURE FLAGS (Sprint control)
    # =================================================================
    SPRINT03_ENABLED: bool = False  # Service Layer
    SPRINT05_ENABLED: bool = False  # Optimization (cache, rate limiting)
    SPRINT06_ENABLED: bool = True   # Prophet forecasting
    SPRINT07_ENABLED: bool = True   # SIAR historical analysis
    SPRINT08_ENABLED: bool = True   # Hourly production optimization
    SPRINT11_ENABLED: bool = True   # Chatbot BI conversacional

    # =================================================================
    # VALIDATION
    # =================================================================

    @property
    def ml_models_exist(self) -> bool:
        """Check if ML models directory exists."""
        return self.ML_MODELS_DIR.exists()

    @property
    def influxdb_url_docker(self) -> str:
        """Get InfluxDB URL for Docker network."""
        return self.INFLUXDB_URL

    @property
    def influxdb_url_local(self) -> str:
        """Get InfluxDB URL for local development."""
        return self.INFLUXDB_URL.replace("influxdb", "localhost")

    def __repr__(self):
        """Safe representation without exposing secrets."""
        return (
            f"Settings("
            f"env={self.ENVIRONMENT}, "
            f"influxdb_url={self.INFLUXDB_URL}, "
            f"org={self.INFLUXDB_ORG}, "
            f"bucket={self.INFLUXDB_BUCKET})"
        )


# Global settings instance
settings = Settings()

# Ensure ML models directory exists
settings.ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
