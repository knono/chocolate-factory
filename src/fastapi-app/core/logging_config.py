"""
Structured Logging Configuration
=================================

Provides centralized logging configuration for the entire application.
Supports both JSON structured logging (for production) and human-readable
format (for development).

Features:
- JSON structured logs for production
- Color-coded console logs for development
- Request ID tracking for distributed tracing
- Log rotation and file output
- Performance metrics logging
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from core.config import settings


# =================================================================
# LOG FORMATTERS
# =================================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON structured logging formatter for production.

    Outputs logs in JSON format with standard fields:
    - timestamp: ISO 8601 format
    - level: Log level (INFO, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - module: Python module name
    - function: Function name
    - line: Line number
    - request_id: Request ID (if available)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available (from context)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Color-coded console formatter for development.

    Provides visual distinction between log levels:
    - DEBUG: Gray
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red background
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[37m",      # Gray
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname:8}{self.RESET}"
            )

        # Format message
        formatted = super().format(record)

        # Reset levelname for next use
        record.levelname = levelname

        return formatted


# =================================================================
# LOG HANDLERS
# =================================================================

def get_console_handler() -> logging.StreamHandler:
    """
    Get console handler with appropriate formatter.

    Returns:
        StreamHandler: Console handler for stdout
    """
    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        # JSON structured logs for production
        formatter = StructuredFormatter()
    else:
        # Color-coded human-readable logs for development
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)-30s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    return handler


def get_file_handler(log_file: Path) -> logging.FileHandler:
    """
    Get file handler with JSON formatter.

    Args:
        log_file: Path to log file

    Returns:
        FileHandler: File handler for JSON logs
    """
    # Ensure log directory exists with proper permissions
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True, mode=0o777)
    except (OSError, PermissionError) as e:
        # If we can't create the log directory, skip file logging
        import warnings
        warnings.warn(f"Could not create log directory: {e}. File logging disabled.")
        return None

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(StructuredFormatter())

    return handler


# =================================================================
# LOGGER SETUP
# =================================================================

def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_file_logging: bool = True
) -> None:
    """
    Configure logging for the entire application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to settings.LOG_LEVEL
        log_file: Path to log file. Defaults to /app/logs/fastapi.log
        enable_file_logging: Whether to enable file logging

    Example:
        >>> setup_logging(log_level="DEBUG")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Determine log level
    level = log_level or settings.LOG_LEVEL
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    console_handler = get_console_handler()
    root_logger.addHandler(console_handler)

    # Add file handler if enabled
    if enable_file_logging:
        if log_file is None:
            log_file = Path("/app/logs/fastapi.log")

        file_handler = get_file_handler(log_file)
        if file_handler:  # Only add if handler was created successfully
            root_logger.addHandler(file_handler)

    # Configure third-party loggers (reduce noise)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"🔧 Logging configured: level={level}, environment={settings.ENVIRONMENT}")
    if enable_file_logging:
        logger.info(f"📝 File logging enabled: {log_file}")


# =================================================================
# REQUEST ID CONTEXT (for distributed tracing)
# =================================================================

import contextvars

# Context variable for request ID
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request-id"
)


class RequestIDFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.

    This enables distributed tracing by including a unique request ID
    in all logs for a given request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with request ID tracking.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger: Logger instance with request ID filter

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"user_id": 123})
    """
    logger = logging.getLogger(name)
    logger.addFilter(RequestIDFilter())
    return logger


# =================================================================
# PERFORMANCE LOGGING
# =================================================================

class PerformanceLogger:
    """
    Context manager for performance logging.

    Logs execution time of code blocks.

    Example:
        >>> with PerformanceLogger("fetch_ree_data"):
        ...     data = await ree_client.get_prices()
    """

    def __init__(self, operation_name: str, logger_name: Optional[str] = None):
        self.operation_name = operation_name
        self.logger = get_logger(logger_name or __name__)
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"⏱️  Started: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if exc_type:
            self.logger.error(
                f"❌ Failed: {self.operation_name} ({elapsed:.2f}s)",
                exc_info=True
            )
        else:
            self.logger.info(
                f"✅ Completed: {self.operation_name} ({elapsed:.2f}s)"
            )


# =================================================================
# UTILITY FUNCTIONS
# =================================================================

def log_api_call(
    logger: logging.Logger,
    method: str,
    url: str,
    status_code: int,
    elapsed_ms: float,
    **extra_data
):
    """
    Log external API call with structured data.

    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        url: API URL
        status_code: HTTP status code
        elapsed_ms: Request duration in milliseconds
        **extra_data: Additional data to log

    Example:
        >>> log_api_call(
        ...     logger,
        ...     method="GET",
        ...     url="https://api.ree.es/prices",
        ...     status_code=200,
        ...     elapsed_ms=234.5,
        ...     records_fetched=24
        ... )
    """
    log_data = {
        "api_call": {
            "method": method,
            "url": url,
            "status_code": status_code,
            "elapsed_ms": elapsed_ms,
            **extra_data
        }
    }

    level = logging.INFO if status_code < 400 else logging.ERROR
    logger.log(level, f"API Call: {method} {url} [{status_code}] ({elapsed_ms:.1f}ms)")


def log_ml_metrics(
    logger: logging.Logger,
    model_name: str,
    metrics: dict,
    operation: str = "training"
):
    """
    Log ML model metrics.

    Args:
        logger: Logger instance
        model_name: Name of ML model
        metrics: Dictionary of metrics (MAE, RMSE, R², etc.)
        operation: Operation type (training, validation, prediction)

    Example:
        >>> log_ml_metrics(
        ...     logger,
        ...     model_name="prophet_price_forecast",
        ...     metrics={"mae": 0.033, "rmse": 0.045, "r2": 0.49},
        ...     operation="training"
        ... )
    """
    logger.info(
        f"📊 ML {operation.capitalize()}: {model_name}",
        extra={"extra_data": {"model": model_name, "metrics": metrics}}
    )


# Initialize logging on module import (console only by default)
setup_logging(enable_file_logging=False)
