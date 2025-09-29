# src/core/config.py
"""Central configuration for Chocolate Factory application."""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings for environment management."""
    
    # Application
    APP_NAME: str = "Chocolate Factory API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    
    # Database (preparado para futura implementación)
    DATABASE_URL: Optional[str] = "sqlite:///./chocolate_factory.db"
    
    # ML Configuration
    ML_MODEL_PATH: str = "models/"
    ML_DATA_PATH: str = "src/ml/data/"
    ML_LOG_PATH: str = "logs/ml/"
    
    # Production Settings
    DEFAULT_BATCH_SIZE: int = 10
    QUALITY_THRESHOLD: float = 70.0
    
    # Dashboard Settings
    REFRESH_INTERVAL: int = 5000  # milliseconds
    MAX_DISPLAY_BATCHES: int = 10
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Monitoring
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()