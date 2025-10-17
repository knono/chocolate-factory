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


def get_secret(secret_name: str, env_var_name: Optional[str] = None) -> Optional[str]:
    """
    Read a secret from Docker Secrets or environment variable.

    Order of precedence:
    1. Docker Secret file at /run/secrets/{secret_name}
    2. Environment variable {ENV_VAR_NAME}_FILE pointing to a file
    3. Environment variable {ENV_VAR_NAME} directly

    Args:
        secret_name: Name of the secret file (without path)
        env_var_name: Environment variable name (if different from secret_name)

    Returns:
        Secret value or None if not found
    """
    if env_var_name is None:
        env_var_name = secret_name.upper()

    # 1. Try Docker Secret path
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        try:
            return secret_path.read_text().strip()
        except Exception as e:
            print(f"⚠️  Failed to read secret from {secret_path}: {e}")

    # 2. Try environment variable pointing to file (e.g., INFLUXDB_TOKEN_FILE)
    file_env_var = f"{env_var_name}_FILE"
    if file_env_var in os.environ:
        file_path = Path(os.environ[file_env_var])
        if file_path.exists():
            try:
                return file_path.read_text().strip()
            except Exception as e:
                print(f"⚠️  Failed to read secret from {file_path}: {e}")

    # 3. Fallback to direct environment variable (for local development)
    return os.environ.get(env_var_name)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=False  # Don't validate defaults, secrets loaded in post_init
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
    INFLUXDB_TOKEN: str = ""  # Will be loaded from secret
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
    REE_API_TOKEN: Optional[str] = None  # REE API doesn't require auth, will be loaded from secret
    AEMET_API_KEY: str = ""  # Will be loaded from secret
    OPENWEATHERMAP_API_KEY: str = ""  # Will be loaded from secret
    ANTHROPIC_API_KEY: str = ""  # Sprint 11: Chatbot BI with Claude Haiku, will be loaded from secret

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
    # CHATBOT SETTINGS (Sprint 11 - Migrated to Haiku 4.5)
    # =================================================================
    CHATBOT_MODEL: str = "claude-haiku-4-5"
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

    def model_post_init(self, __context) -> None:
        """Load secrets from Docker Secrets after model initialization."""
        # Load InfluxDB secrets
        influxdb_token = get_secret("influxdb_token", "INFLUXDB_TOKEN")
        if influxdb_token:
            self.INFLUXDB_TOKEN = influxdb_token

        # Load external API keys
        ree_token = get_secret("ree_api_token", "REE_API_TOKEN")
        if ree_token:
            self.REE_API_TOKEN = ree_token

        aemet_key = get_secret("aemet_api_key", "AEMET_API_KEY")
        if aemet_key:
            self.AEMET_API_KEY = aemet_key

        openweather_key = get_secret("openweathermap_api_key", "OPENWEATHERMAP_API_KEY")
        if openweather_key:
            self.OPENWEATHERMAP_API_KEY = openweather_key

        anthropic_key = get_secret("anthropic_api_key", "ANTHROPIC_API_KEY")
        if anthropic_key:
            self.ANTHROPIC_API_KEY = anthropic_key

        # Validate that required secrets were loaded
        if not self.INFLUXDB_TOKEN:
            print("⚠️  WARNING: INFLUXDB_TOKEN not found in secrets or environment")
        if not self.AEMET_API_KEY:
            print("⚠️  WARNING: AEMET_API_KEY not found in secrets or environment")
        if not self.OPENWEATHERMAP_API_KEY:
            print("⚠️  WARNING: OPENWEATHERMAP_API_KEY not found in secrets or environment")
        if not self.ANTHROPIC_API_KEY:
            print("⚠️  WARNING: ANTHROPIC_API_KEY not found in secrets or environment")

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
