"""
Unit Tests - Model Metrics Tracker (Sprint 20 Fase 3)
======================================================

Tests for ModelMetricsTracker class:
- CSV initialization and metrics logging
- Baseline calculation (median over window)
- Degradation detection (>2x baseline MAE)
- Metrics history retrieval
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from domain.ml.model_metrics_tracker import ModelMetricsTracker


@pytest.fixture
def temp_csv_path(tmp_path):
    """Create temporary CSV path for testing"""
    return tmp_path / "test_metrics_history.csv"


@pytest.fixture
def tracker(temp_csv_path):
    """Create ModelMetricsTracker instance with temp CSV"""
    return ModelMetricsTracker(csv_path=temp_csv_path)


class TestModelMetricsTrackerInitialization:
    """Test CSV initialization and setup"""

    def test_csv_created_on_init(self, tracker, temp_csv_path):
        """CSV file should be created with headers"""
        assert temp_csv_path.exists()

        # Check headers
        with open(temp_csv_path, 'r') as f:
            header = f.readline().strip()
            assert "timestamp" in header
            assert "model_name" in header
            assert "mae" in header
            assert "rmse" in header
            assert "r2" in header

    def test_directory_creation(self, tmp_path):
        """Should create directory if doesn't exist"""
        deep_path = tmp_path / "deep" / "nested" / "metrics.csv"
        tracker = ModelMetricsTracker(csv_path=deep_path)

        assert deep_path.exists()
        assert deep_path.parent.exists()


class TestMetricsLogging:
    """Test logging metrics to CSV"""

    def test_log_metrics_basic(self, tracker, temp_csv_path):
        """Should log metrics to CSV"""
        tracker.log_metrics(
            model_name="prophet_test",
            metrics={
                "mae": 0.033,
                "rmse": 0.048,
                "r2": 0.49,
                "samples": 12493,
                "duration_seconds": 45.2
            },
            notes="test_run"
        )

        # Read CSV and verify
        with open(temp_csv_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2  # header + 1 entry
            assert "prophet_test" in lines[1]
            assert "0.033" in lines[1]
            assert "test_run" in lines[1]

    def test_log_multiple_metrics(self, tracker, temp_csv_path):
        """Should append multiple entries"""
        for i in range(5):
            tracker.log_metrics(
                model_name="prophet_test",
                metrics={
                    "mae": 0.030 + i * 0.005,
                    "rmse": 0.045 + i * 0.007,
                    "r2": 0.50 - i * 0.02,
                    "samples": 10000,
                    "duration_seconds": 40.0
                },
                notes=f"run_{i}"
            )

        # Verify 5 entries (+ header)
        with open(temp_csv_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 6  # header + 5 entries

    def test_log_metrics_error_handling(self, tracker):
        """Should not raise if CSV write fails (graceful degradation)"""
        # This shouldn't raise
        tracker.log_metrics(
            model_name="test",
            metrics={"mae": 0.01},
            notes="should_not_crash"
        )


class TestBaselineCalculation:
    """Test baseline metric calculation (median over window)"""

    def test_get_baseline_insufficient_data(self, tracker):
        """Should return None if less than 3 entries"""
        tracker.log_metrics("test_model", {"mae": 0.01, "rmse": 0.02, "r2": 0.5}, notes="entry1")

        baseline_mae = tracker.get_baseline("test_model", "mae")
        assert baseline_mae is None  # Need at least 3 entries

    def test_get_baseline_median(self, tracker):
        """Should return median of recent entries"""
        # Log 5 entries with varying MAE
        mae_values = [0.030, 0.035, 0.040, 0.032, 0.038]

        for i, mae in enumerate(mae_values):
            tracker.log_metrics(
                "test_model",
                {"mae": mae, "rmse": 0.05, "r2": 0.5, "samples": 1000},
                notes=f"entry_{i}"
            )

        baseline_mae = tracker.get_baseline("test_model", "mae", window_entries=5)

        # Median of [0.030, 0.035, 0.040, 0.032, 0.038] = 0.035
        assert baseline_mae == pytest.approx(0.035, abs=0.001)

    def test_get_baseline_window_limit(self, tracker):
        """Should only use last N entries for baseline"""
        # Log 10 entries, but only use last 3
        for i in range(10):
            tracker.log_metrics(
                "test_model",
                {"mae": 0.01 + i * 0.01, "rmse": 0.05, "r2": 0.5, "samples": 1000},
                notes=f"entry_{i}"
            )

        # Baseline should be median of last 3: [0.08, 0.09, 0.10]
        baseline_mae = tracker.get_baseline("test_model", "mae", window_entries=3)

        # Median = 0.09
        assert baseline_mae == pytest.approx(0.09, abs=0.001)

    def test_get_baseline_nonexistent_model(self, tracker):
        """Should return None for nonexistent model"""
        baseline = tracker.get_baseline("nonexistent_model", "mae")
        assert baseline is None


class TestDegradationDetection:
    """Test model degradation detection"""

    def test_no_degradation(self, tracker):
        """Should not detect degradation if within threshold"""
        # Log baseline entries (MAE ~ 0.03)
        for i in range(5):
            tracker.log_metrics(
                "test_model",
                {"mae": 0.030, "rmse": 0.045, "r2": 0.50, "samples": 1000},
                notes=f"baseline_{i}"
            )

        # Current metrics similar to baseline
        result = tracker.detect_degradation(
            "test_model",
            {"mae": 0.032, "rmse": 0.046, "r2": 0.49},
            threshold_multiplier=2.0
        )

        assert result["degradation_detected"] is False
        assert len(result["alerts"]) == 0

    def test_degradation_mae_2x(self, tracker):
        """Should detect degradation if MAE >2x baseline"""
        # Log baseline entries (MAE ~ 0.03)
        for i in range(5):
            tracker.log_metrics(
                "test_model",
                {"mae": 0.030, "rmse": 0.045, "r2": 0.50, "samples": 1000},
                notes=f"baseline_{i}"
            )

        # Current MAE = 0.070 (> 2x baseline)
        result = tracker.detect_degradation(
            "test_model",
            {"mae": 0.070, "rmse": 0.050, "r2": 0.48},
            threshold_multiplier=2.0
        )

        assert result["degradation_detected"] is True
        assert len(result["alerts"]) > 0
        assert result["alerts"][0]["metric"] == "mae"
        assert result["alerts"][0]["current"] == 0.070

    def test_degradation_r2_drop(self, tracker):
        """Should detect degradation if R² drops significantly"""
        # Log baseline entries (R² ~ 0.50)
        for i in range(5):
            tracker.log_metrics(
                "test_model",
                {"mae": 0.030, "rmse": 0.045, "r2": 0.50, "samples": 1000},
                notes=f"baseline_{i}"
            )

        # Current R² = 0.20 (< 50% of baseline)
        result = tracker.detect_degradation(
            "test_model",
            {"mae": 0.031, "rmse": 0.046, "r2": 0.20},
            threshold_multiplier=2.0
        )

        assert result["degradation_detected"] is True
        assert any(alert["metric"] == "r2" for alert in result["alerts"])

    def test_degradation_insufficient_baseline(self, tracker):
        """Should not detect degradation if insufficient baseline data"""
        # Only 1 entry (need at least 3)
        tracker.log_metrics(
            "test_model",
            {"mae": 0.030, "rmse": 0.045, "r2": 0.50, "samples": 1000},
            notes="single_entry"
        )

        result = tracker.detect_degradation(
            "test_model",
            {"mae": 0.100, "rmse": 0.150, "r2": 0.20},
            threshold_multiplier=2.0
        )

        # Can't detect without baseline
        assert result["degradation_detected"] is False


class TestMetricsHistoryRetrieval:
    """Test retrieving metrics history"""

    def test_get_metrics_history_empty(self, tracker):
        """Should return empty list if no metrics"""
        history = tracker.get_metrics_history("nonexistent_model")
        assert history == []

    def test_get_metrics_history_all_models(self, tracker):
        """Should return all models if model_name=None"""
        tracker.log_metrics("model_a", {"mae": 0.01, "rmse": 0.02, "r2": 0.5}, notes="a")
        tracker.log_metrics("model_b", {"mae": 0.02, "rmse": 0.03, "r2": 0.6}, notes="b")

        history = tracker.get_metrics_history(model_name=None, limit=100)

        assert len(history) == 2
        model_names = [entry["model_name"] for entry in history]
        assert "model_a" in model_names
        assert "model_b" in model_names

    def test_get_metrics_history_filter_by_model(self, tracker):
        """Should filter by model_name"""
        tracker.log_metrics("model_a", {"mae": 0.01, "rmse": 0.02, "r2": 0.5}, notes="a")
        tracker.log_metrics("model_b", {"mae": 0.02, "rmse": 0.03, "r2": 0.6}, notes="b")
        tracker.log_metrics("model_a", {"mae": 0.015, "rmse": 0.025, "r2": 0.55}, notes="a2")

        history = tracker.get_metrics_history(model_name="model_a", limit=100)

        assert len(history) == 2
        assert all(entry["model_name"] == "model_a" for entry in history)

    def test_get_metrics_history_limit(self, tracker):
        """Should respect limit parameter"""
        for i in range(20):
            tracker.log_metrics(
                "test_model",
                {"mae": 0.03, "rmse": 0.04, "r2": 0.5, "samples": 1000},
                notes=f"entry_{i}"
            )

        history = tracker.get_metrics_history("test_model", limit=5)

        # Should return only last 5 entries
        assert len(history) == 5

    def test_get_metrics_history_numeric_conversion(self, tracker):
        """Should convert numeric strings to float/int"""
        tracker.log_metrics(
            "test_model",
            {"mae": 0.033, "rmse": 0.048, "r2": 0.49, "samples": 12493, "duration_seconds": 45.2},
            notes="test"
        )

        history = tracker.get_metrics_history("test_model")

        assert len(history) == 1
        entry = history[0]

        # Check types
        assert isinstance(entry["mae"], float)
        assert isinstance(entry["rmse"], float)
        assert isinstance(entry["r2"], float)
        assert isinstance(entry["samples"], int)
        assert isinstance(entry["duration_seconds"], float)
