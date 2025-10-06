"""
ML Model Trainer (Domain Logic)
================================

Pure business logic for ML model training.
Framework-agnostic, testable, and reusable.

Usage:
    from domain.ml.model_trainer import ModelTrainer

    trainer = ModelTrainer()
    metrics = trainer.validate_model(predictions, actuals)
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    ML model training and validation logic.

    Note: This is a simplified placeholder. Full ML implementation
    is in services/direct_ml.py and services/price_forecasting_service.py
    """

    def validate_model(
        self,
        predictions: List[float],
        actuals: List[float]
    ) -> Dict[str, float]:
        """
        Calculate validation metrics for model predictions.

        Args:
            predictions: Predicted values
            actuals: Actual values

        Returns:
            Dictionary with MAE, RMSE, R² metrics

        Example:
            >>> metrics = trainer.validate_model(predictions, actuals)
            >>> print(f"MAE: {metrics['mae']:.4f}")
        """
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")

        if not predictions:
            return {"mae": 0.0, "rmse": 0.0, "r2": 0.0}

        # Mean Absolute Error
        mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(predictions)

        # Root Mean Squared Error
        mse = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions)
        rmse = mse ** 0.5

        # R² Score
        mean_actual = sum(actuals) / len(actuals)
        ss_total = sum((a - mean_actual) ** 2 for a in actuals)
        ss_residual = sum((a - p) ** 2 for a, p in zip(actuals, predictions))

        if ss_total == 0:
            r2 = 0.0
        else:
            r2 = 1 - (ss_residual / ss_total)

        return {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "samples": len(predictions)
        }

    def calculate_feature_importance(
        self,
        feature_names: List[str],
        importances: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate and sort feature importance.

        Args:
            feature_names: List of feature names
            importances: List of importance scores

        Returns:
            List of features sorted by importance
        """
        features = [
            {"name": name, "importance": imp}
            for name, imp in zip(feature_names, importances)
        ]

        return sorted(features, key=lambda x: x["importance"], reverse=True)
