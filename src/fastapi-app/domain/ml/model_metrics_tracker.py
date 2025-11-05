"""
Model Metrics Tracker
=====================

Trackea métricas de modelos ML a CSV para análisis histórico y detección de degradación.

Features:
- Log metrics to CSV (append-only)
- Get baseline metrics (median over time window)
- Detect degradation (>2x baseline)
- Support multiple models (Prophet, sklearn)

Usage:
    tracker = ModelMetricsTracker()
    tracker.log_metrics("prophet_price_forecast", {
        "mae": 0.033,
        "rmse": 0.048,
        "r2": 0.49,
        "samples": 12493
    })

    baseline_mae = tracker.get_baseline("prophet_price_forecast", "mae")
    if current_mae > baseline_mae * 2:
        # Alert degradation
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import statistics

logger = logging.getLogger(__name__)


class ModelMetricsTracker:
    """
    CSV-based tracker for ML model metrics.

    Stores historical metrics for Prophet and sklearn models with:
    - Timestamp
    - Model name
    - Metrics (MAE, RMSE, R², samples, etc.)
    - Training duration
    """

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize metrics tracker.

        Args:
            csv_path: Path to CSV file (default: models/metrics_history.csv)
        """
        if csv_path is None:
            # Default: models/ directory relative to this file
            self.csv_path = Path(__file__).parent.parent.parent / "models" / "metrics_history.csv"
        else:
            self.csv_path = Path(csv_path)

        # Ensure directory exists
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        # CSV columns
        self.columns = [
            "timestamp",
            "model_name",
            "mae",
            "rmse",
            "r2",
            "samples",
            "duration_seconds",
            "notes"
        ]

        # Initialize CSV if doesn't exist
        if not self.csv_path.exists():
            self._initialize_csv()
            logger.info(f"📊 Metrics tracker initialized: {self.csv_path}")

    def _initialize_csv(self) -> None:
        """Create CSV file with headers."""
        try:
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.columns)
                writer.writeheader()
            logger.debug(f"CSV initialized: {self.csv_path}")
        except Exception as e:
            logger.error(f"Failed to initialize CSV: {e}")
            raise

    def log_metrics(
        self,
        model_name: str,
        metrics: Dict[str, Any],
        notes: str = ""
    ) -> None:
        """
        Log model metrics to CSV.

        Args:
            model_name: Model identifier (e.g., "prophet_price_forecast")
            metrics: Dict with mae, rmse, r2, samples, duration_seconds
            notes: Optional notes (e.g., "initial_training", "scheduled_retrain")

        Example:
            tracker.log_metrics("prophet_price_forecast", {
                "mae": 0.033,
                "rmse": 0.048,
                "r2": 0.49,
                "samples": 12493,
                "duration_seconds": 45.2
            }, notes="daily_retrain")
        """
        try:
            row = {
                "timestamp": datetime.utcnow().isoformat(),
                "model_name": model_name,
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "r2": metrics.get("r2"),
                "samples": metrics.get("samples"),
                "duration_seconds": metrics.get("duration_seconds"),
                "notes": notes
            }

            # Append to CSV
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.columns)
                writer.writerow(row)

            logger.info(
                f"📊 Metrics logged: {model_name} - "
                f"MAE={metrics.get('mae'):.4f}, "
                f"RMSE={metrics.get('rmse'):.4f}, "
                f"R²={metrics.get('r2'):.4f}"
            )

        except Exception as e:
            logger.error(f"Failed to log metrics for {model_name}: {e}")
            # Don't raise - metrics tracking shouldn't break training

    def get_baseline(
        self,
        model_name: str,
        metric: str,
        window_entries: int = 30
    ) -> Optional[float]:
        """
        Get baseline value for a metric (median over recent entries).

        Args:
            model_name: Model identifier
            metric: Metric name (mae, rmse, r2)
            window_entries: Number of recent entries to use (default 30)

        Returns:
            Median value or None if insufficient data

        Example:
            baseline_mae = tracker.get_baseline("prophet_price_forecast", "mae", window_entries=30)
            if current_mae > baseline_mae * 2:
                alert("Model degradation detected")
        """
        try:
            history = self._read_history(model_name, limit=window_entries)

            if len(history) < 3:
                logger.warning(
                    f"Insufficient data for baseline calculation: {len(history)} entries "
                    f"(need at least 3)"
                )
                return None

            # Extract metric values (skip None)
            values = [
                float(entry[metric])
                for entry in history
                if entry.get(metric) is not None
            ]

            if not values:
                return None

            # Return median as baseline
            baseline = statistics.median(values)
            logger.debug(
                f"Baseline calculated: {model_name}.{metric} = {baseline:.4f} "
                f"(from {len(values)} entries)"
            )

            return baseline

        except Exception as e:
            logger.error(f"Failed to calculate baseline for {model_name}.{metric}: {e}")
            return None

    def _read_history(
        self,
        model_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Read metrics history from CSV.

        Args:
            model_name: Filter by model name (None = all models)
            limit: Maximum number of entries to return (most recent)

        Returns:
            List of metric entries (dicts)
        """
        if not self.csv_path.exists():
            return []

        try:
            with open(self.csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Filter by model_name if specified
            if model_name:
                rows = [row for row in rows if row.get("model_name") == model_name]

            # Return most recent entries (CSV is append-only, so last N rows)
            if limit:
                rows = rows[-limit:]

            return rows

        except Exception as e:
            logger.error(f"Failed to read metrics history: {e}")
            return []

    def get_metrics_history(
        self,
        model_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get metrics history for API endpoint.

        Args:
            model_name: Filter by model (None = all models)
            limit: Maximum entries to return

        Returns:
            List of metric entries with parsed values
        """
        history = self._read_history(model_name, limit)

        # Parse numeric values
        for entry in history:
            for key in ["mae", "rmse", "r2", "duration_seconds"]:
                if entry.get(key):
                    try:
                        entry[key] = float(entry[key])
                    except (ValueError, TypeError):
                        entry[key] = None

            if entry.get("samples"):
                try:
                    entry["samples"] = int(entry["samples"])
                except (ValueError, TypeError):
                    entry["samples"] = None

        return history

    def detect_degradation(
        self,
        model_name: str,
        current_metrics: Dict[str, float],
        threshold_multiplier: float = 2.0
    ) -> Dict[str, Any]:
        """
        Detect model degradation by comparing current metrics to baseline.

        Args:
            model_name: Model identifier
            current_metrics: Current MAE, RMSE, R²
            threshold_multiplier: Alert if metric > baseline * multiplier (default 2.0)

        Returns:
            Dict with degradation status and details

        Example:
            result = tracker.detect_degradation("prophet_price_forecast", {
                "mae": 0.070,  # 2x higher than baseline
                "rmse": 0.095,
                "r2": 0.30
            })

            if result["degradation_detected"]:
                alert(result["message"])
        """
        result = {
            "degradation_detected": False,
            "model_name": model_name,
            "current_metrics": current_metrics,
            "baseline_metrics": {},
            "alerts": []
        }

        # Check MAE degradation
        baseline_mae = self.get_baseline(model_name, "mae")
        if baseline_mae is not None:
            result["baseline_metrics"]["mae"] = baseline_mae
            current_mae = current_metrics.get("mae")

            if current_mae and current_mae > baseline_mae * threshold_multiplier:
                result["degradation_detected"] = True
                result["alerts"].append({
                    "metric": "mae",
                    "current": current_mae,
                    "baseline": baseline_mae,
                    "ratio": current_mae / baseline_mae,
                    "message": (
                        f"MAE degradation: {current_mae:.4f} vs baseline {baseline_mae:.4f} "
                        f"({current_mae/baseline_mae:.1f}x higher)"
                    )
                })

        # Check R² degradation (if decreased significantly)
        baseline_r2 = self.get_baseline(model_name, "r2")
        if baseline_r2 is not None:
            result["baseline_metrics"]["r2"] = baseline_r2
            current_r2 = current_metrics.get("r2")

            # Alert if R² drops below 50% of baseline (e.g., 0.49 → 0.24)
            if current_r2 is not None and current_r2 < baseline_r2 * 0.5:
                result["degradation_detected"] = True
                result["alerts"].append({
                    "metric": "r2",
                    "current": current_r2,
                    "baseline": baseline_r2,
                    "ratio": current_r2 / baseline_r2 if baseline_r2 > 0 else 0,
                    "message": (
                        f"R² degradation: {current_r2:.4f} vs baseline {baseline_r2:.4f} "
                        f"({current_r2/baseline_r2*100:.0f}% of baseline)"
                    )
                })

        if result["degradation_detected"]:
            logger.warning(
                f"⚠️ Model degradation detected: {model_name} - "
                f"{len(result['alerts'])} alert(s)"
            )

        return result
