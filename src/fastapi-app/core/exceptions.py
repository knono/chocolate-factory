"""
Custom Exceptions Module
=========================

Domain-specific exceptions for the Chocolate Factory application.

Exception Hierarchy:
    ChocolateFactoryException (base)
    ├── DataIngestionError
    │   ├── REEDataError
    │   ├── AEMETDataError
    │   └── SIARDataError
    ├── MLModelError
    │   ├── ModelNotFoundError
    │   ├── ModelTrainingError
    │   └── ModelPredictionError
    ├── ExternalAPIError
    │   ├── REEAPIError
    │   ├── AEMETAPIError
    │   └── OpenWeatherMapError
    ├── DataGapError
    ├── InfluxDBError
    └── ValidationError

Usage:
    from core.exceptions import REEDataError, handle_exceptions

    try:
        data = await fetch_ree_data()
    except REEAPIError as e:
        logger.error(f"REE API failed: {e}")
        raise REEDataError("Failed to fetch REE data") from e
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


# =================================================================
# BASE EXCEPTION
# =================================================================

class ChocolateFactoryException(Exception):
    """
    Base exception for all Chocolate Factory errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


# =================================================================
# DATA INGESTION EXCEPTIONS
# =================================================================

class DataIngestionError(ChocolateFactoryException):
    """Base exception for data ingestion errors."""
    pass


class REEDataError(DataIngestionError):
    """REE (Red Eléctrica de España) data ingestion error."""
    pass


class AEMETDataError(DataIngestionError):
    """AEMET (Agencia Estatal de Meteorología) data ingestion error."""
    pass


class SIARDataError(DataIngestionError):
    """SIAR (Sistema de Información Agroclimática) data ingestion error."""
    pass


class WeatherDataError(DataIngestionError):
    """Weather data ingestion error (hybrid sources)."""
    pass


# =================================================================
# ML MODEL EXCEPTIONS
# =================================================================

class MLModelError(ChocolateFactoryException):
    """Base exception for ML model errors."""
    pass


class ModelNotFoundError(MLModelError):
    """ML model file not found on disk."""

    def __init__(self, model_name: str, model_path: str):
        super().__init__(
            message=f"Model '{model_name}' not found at {model_path}",
            details={"model_name": model_name, "model_path": model_path},
            error_code="MODEL_NOT_FOUND"
        )


class ModelTrainingError(MLModelError):
    """Error during ML model training."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"Failed to train model '{model_name}': {reason}",
            details={"model_name": model_name, "reason": reason},
            error_code="MODEL_TRAINING_FAILED"
        )


class ModelPredictionError(MLModelError):
    """Error during ML model prediction."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"Prediction failed for model '{model_name}': {reason}",
            details={"model_name": model_name, "reason": reason},
            error_code="MODEL_PREDICTION_FAILED"
        )


class InsufficientDataError(MLModelError):
    """Insufficient data for ML model training or prediction."""

    def __init__(self, required_samples: int, actual_samples: int):
        super().__init__(
            message=f"Insufficient data: need {required_samples}, got {actual_samples}",
            details={"required": required_samples, "actual": actual_samples},
            error_code="INSUFFICIENT_DATA"
        )


# =================================================================
# EXTERNAL API EXCEPTIONS
# =================================================================

class ExternalAPIError(ChocolateFactoryException):
    """Base exception for external API errors."""
    pass


class REEAPIError(ExternalAPIError):
    """REE API communication error."""

    def __init__(self, status_code: int, reason: str):
        super().__init__(
            message=f"REE API error [{status_code}]: {reason}",
            details={"status_code": status_code, "api": "REE"},
            error_code="REE_API_ERROR"
        )


class AEMETAPIError(ExternalAPIError):
    """AEMET API communication error."""

    def __init__(self, status_code: int, reason: str):
        super().__init__(
            message=f"AEMET API error [{status_code}]: {reason}",
            details={"status_code": status_code, "api": "AEMET"},
            error_code="AEMET_API_ERROR"
        )


class OpenWeatherMapError(ExternalAPIError):
    """OpenWeatherMap API communication error."""

    def __init__(self, status_code: int, reason: str):
        super().__init__(
            message=f"OpenWeatherMap API error [{status_code}]: {reason}",
            details={"status_code": status_code, "api": "OpenWeatherMap"},
            error_code="OPENWEATHERMAP_API_ERROR"
        )


class APIRateLimitError(ExternalAPIError):
    """External API rate limit exceeded."""

    def __init__(self, api_name: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded for {api_name} API",
            details={"api": api_name, "retry_after": retry_after},
            error_code="RATE_LIMIT_EXCEEDED"
        )


# =================================================================
# DATA GAP EXCEPTIONS
# =================================================================

class DataGapError(ChocolateFactoryException):
    """Data gap detected in time series."""

    def __init__(self, source: str, gap_start: str, gap_end: str, gap_hours: float):
        super().__init__(
            message=f"Data gap in {source}: {gap_hours:.1f} hours ({gap_start} to {gap_end})",
            details={
                "source": source,
                "gap_start": gap_start,
                "gap_end": gap_end,
                "gap_hours": gap_hours
            },
            error_code="DATA_GAP_DETECTED"
        )


class BackfillError(ChocolateFactoryException):
    """Error during data backfill operation."""

    def __init__(self, source: str, reason: str):
        super().__init__(
            message=f"Backfill failed for {source}: {reason}",
            details={"source": source, "reason": reason},
            error_code="BACKFILL_FAILED"
        )


# =================================================================
# INFLUXDB EXCEPTIONS
# =================================================================

class InfluxDBError(ChocolateFactoryException):
    """InfluxDB operation error."""
    pass


class InfluxDBConnectionError(InfluxDBError):
    """InfluxDB connection error."""

    def __init__(self, url: str, reason: str):
        super().__init__(
            message=f"Failed to connect to InfluxDB at {url}: {reason}",
            details={"url": url, "reason": reason},
            error_code="INFLUXDB_CONNECTION_FAILED"
        )


class InfluxDBQueryError(InfluxDBError):
    """InfluxDB query execution error."""

    def __init__(self, query: str, reason: str):
        super().__init__(
            message=f"Query failed: {reason}",
            details={"query": query[:100] + "..." if len(query) > 100 else query, "reason": reason},
            error_code="INFLUXDB_QUERY_FAILED"
        )


class InfluxDBWriteError(InfluxDBError):
    """InfluxDB write operation error."""

    def __init__(self, measurement: str, reason: str):
        super().__init__(
            message=f"Write failed for measurement '{measurement}': {reason}",
            details={"measurement": measurement, "reason": reason},
            error_code="INFLUXDB_WRITE_FAILED"
        )


# =================================================================
# VALIDATION EXCEPTIONS
# =================================================================

class ValidationError(ChocolateFactoryException):
    """Data validation error."""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Validation failed for '{field}': {reason}",
            details={"field": field, "value": str(value), "reason": reason},
            error_code="VALIDATION_FAILED"
        )


# =================================================================
# BUSINESS LOGIC EXCEPTIONS
# =================================================================

class ProductionOptimizationError(ChocolateFactoryException):
    """Production optimization error."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Production optimization failed: {reason}",
            details={"reason": reason},
            error_code="OPTIMIZATION_FAILED"
        )


class SchedulerError(ChocolateFactoryException):
    """APScheduler job error."""

    def __init__(self, job_id: str, reason: str):
        super().__init__(
            message=f"Scheduler job '{job_id}' failed: {reason}",
            details={"job_id": job_id, "reason": reason},
            error_code="SCHEDULER_JOB_FAILED"
        )


# =================================================================
# HTTP EXCEPTION CONVERTERS
# =================================================================

def to_http_exception(exc: ChocolateFactoryException) -> HTTPException:
    """
    Convert custom exception to FastAPI HTTPException.

    Args:
        exc: Custom exception instance

    Returns:
        HTTPException: FastAPI HTTP exception

    Example:
        >>> try:
        ...     raise ModelNotFoundError("prophet", "/models/prophet.pkl")
        ... except ChocolateFactoryException as e:
        ...     raise to_http_exception(e)
    """
    # Map exception types to HTTP status codes
    status_map = {
        ModelNotFoundError: status.HTTP_404_NOT_FOUND,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        APIRateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        InsufficientDataError: status.HTTP_400_BAD_REQUEST,
        DataGapError: status.HTTP_409_CONFLICT,
    }

    status_code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    return HTTPException(
        status_code=status_code,
        detail=exc.to_dict()
    )


# =================================================================
# EXCEPTION HANDLER DECORATOR
# =================================================================

from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)


def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator to handle exceptions in route handlers.

    Converts custom exceptions to HTTP exceptions and logs errors.

    Example:
        >>> @router.get("/endpoint")
        ... @handle_exceptions
        ... async def endpoint():
        ...     raise ModelNotFoundError("prophet", "/models/prophet.pkl")
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ChocolateFactoryException as e:
            logger.error(f"Business error in {func.__name__}: {e.message}", exc_info=True)
            raise to_http_exception(e)
        except HTTPException:
            # Re-raise FastAPI exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)}
            )

    return wrapper
