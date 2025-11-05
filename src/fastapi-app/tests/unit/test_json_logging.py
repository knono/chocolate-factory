"""
Unit Tests for JSON Structured Logging
=======================================

Sprint 20 Fase 2 - Tests for JSONFormatter and log search functionality.
"""

import json
import pytest
import pytest_asyncio
import logging
from datetime import datetime
from pathlib import Path
from core.logging_config import StructuredFormatter, get_logger


class TestStructuredFormatter:
    """Tests for StructuredFormatter (JSON logging)."""

    def test_basic_log_format(self):
        """Test basic JSON log formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        assert log_data["timestamp"].endswith("Z")

    def test_log_with_user_identity(self):
        """Test log formatting with user identity (Tailscale auth)."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User action",
            args=(),
            exc_info=None
        )

        # Simulate user_login attribute from Tailscale auth middleware
        record.user_login = "test@example.com"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["user"] == "test@example.com"
        assert log_data["message"] == "User action"

    def test_log_with_exception(self):
        """Test log formatting with exception info."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=20,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )

            result = formatter.format(record)
            log_data = json.loads(result)

            assert log_data["level"] == "ERROR"
            assert "exception" in log_data
            assert "ValueError" in log_data["exception"]
            assert "Test error" in log_data["exception"]

    def test_log_with_request_id(self):
        """Test log formatting with request ID."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=15,
            msg="Request processed",
            args=(),
            exc_info=None
        )

        record.request_id = "abc-123-def"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["request_id"] == "abc-123-def"

    def test_json_parseable(self):
        """Test that all log entries are valid JSON."""
        formatter = StructuredFormatter()

        log_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]

        for level in log_levels:
            record = logging.LogRecord(
                name="test_logger",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"Test message for {logging.getLevelName(level)}",
                args=(),
                exc_info=None
            )

            result = formatter.format(record)

            # Should not raise JSONDecodeError
            log_data = json.loads(result)
            assert log_data["level"] == logging.getLevelName(level)


class TestLoggerIntegration:
    """Integration tests for logger with StructuredFormatter."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a valid logger instance."""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_logger_has_request_id_filter(self):
        """Test logger has RequestIDFilter attached."""
        logger = get_logger("test.module")

        # Check that RequestIDFilter is in the filters
        filter_types = [type(f).__name__ for f in logger.filters]
        assert "RequestIDFilter" in filter_types


class TestLogSearchEndpoint:
    """Tests for /logs/search endpoint."""

    def test_log_search_default(self, client):
        """Test log search with default parameters."""
        response = client.get("/logs/search")

        assert response.status_code == 200
        data = response.json()

        # Should have default filters
        assert data["filters"]["level"] == "all"  # Default is 'all', not 'INFO'
        assert data["filters"]["hours"] == 24
        assert isinstance(data["logs"], list)

    def test_log_search_with_level_filter(self, client):
        """Test log search with level filter."""
        response = client.get("/logs/search?level=ERROR")

        assert response.status_code == 200
        data = response.json()

        assert data["filters"]["level"] == "ERROR"

    def test_log_search_with_time_filter(self, client):
        """Test log search with time window filter."""
        response = client.get("/logs/search?hours=1")

        assert response.status_code == 200
        data = response.json()

        assert data["filters"]["hours"] == 1

    def test_log_search_with_module_filter(self, client):
        """Test log search with module filter."""
        response = client.get("/logs/search?module=services.ree_service")

        assert response.status_code == 200
        data = response.json()

        assert data["filters"]["module"] == "services.ree_service"
