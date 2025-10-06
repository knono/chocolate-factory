"""
Energy Price Forecaster (Domain Logic)
=======================================

Pure business logic for energy price forecasting.
Framework-agnostic, testable, and reusable.

Usage:
    from domain.energy.forecaster import PriceForecaster

    forecaster = PriceForecaster()
    predictions = forecaster.predict_next_hours(historical_prices, hours=24)
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta


class PriceForecaster:
    """
    Energy price forecasting logic.

    Note: This is a simplified version. Full Prophet-based forecasting
    is in services/price_forecasting_service.py (Sprint 06).
    """

    def predict_next_hours(
        self,
        historical_prices: List[Dict[str, Any]],
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Predict energy prices for next N hours.

        Args:
            historical_prices: List of historical price records
            hours: Number of hours to forecast

        Returns:
            List of predicted prices

        Note:
            This is a placeholder. Real forecasting uses Prophet model
            in services/price_forecasting_service.py
        """
        if not historical_prices:
            return []

        # Simple moving average (placeholder)
        recent_prices = historical_prices[-24:] if len(historical_prices) > 24 else historical_prices
        avg_price = sum(p["price_eur_kwh"] for p in recent_prices) / len(recent_prices)

        # Generate predictions
        last_timestamp = historical_prices[-1]["timestamp"]
        predictions = []

        for i in range(1, hours + 1):
            next_timestamp = last_timestamp + timedelta(hours=i)
            predictions.append({
                "timestamp": next_timestamp,
                "price_eur_kwh": avg_price,
                "confidence": 0.5,
                "method": "simple_average"
            })

        return predictions

    def calculate_optimal_hours(
        self,
        predicted_prices: List[Dict[str, Any]],
        target_hours: int = 6
    ) -> List[datetime]:
        """
        Find optimal hours for production based on predicted prices.

        Args:
            predicted_prices: List of price predictions
            target_hours: Number of hours needed for production

        Returns:
            List of optimal timestamps
        """
        # Sort by price (ascending)
        sorted_prices = sorted(predicted_prices, key=lambda x: x["price_eur_kwh"])

        # Return cheapest hours
        optimal = sorted_prices[:target_hours]
        return [p["timestamp"] for p in optimal]
