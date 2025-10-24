"""
Price Forecast Router - Sprint 06
==================================

RESTful endpoints for Prophet price forecasting.

Endpoints:
- GET /predict/prices/weekly - 7-day (168h) price forecast
- GET /predict/prices/hourly - Configurable hourly forecast (1-168h)
- POST /models/price-forecast/train - Train Prophet model
- GET /models/price-forecast/status - Model metrics and health
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from services.price_forecasting_service import PriceForecastingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict/prices", tags=["Price Forecasting"])


class PriceForecastResponse(BaseModel):
    """Response schema for price forecast"""
    status: str = Field(..., description="Response status")
    forecast_horizon: str = Field(..., description="Forecast time window")
    model_type: str = Field(default="Prophet", description="Model type")
    predictions_count: int = Field(..., description="Number of predictions")
    predictions: List[Dict[str, Any]] = Field(..., description="Forecast data")
    model_metrics: Dict[str, Any] = Field(..., description="Model performance metrics")
    last_training: datetime = Field(..., description="Last training timestamp")
    timestamp: datetime = Field(..., description="Request timestamp")


class ModelStatusResponse(BaseModel):
    """Response schema for model status"""
    status: str = Field(..., description="Model availability status")
    model_info: Dict[str, Any] = Field(..., description="Model information")
    metrics: Dict[str, Any] = Field(..., description="Model metrics")


@router.get("/weekly", response_model=PriceForecastResponse)
async def get_weekly_forecast() -> Dict[str, Any]:
    """
    🔮 Get 7-day (168-hour) price forecast using Prophet ML model.

    Returns:
        - 168 hourly price predictions for next 7 days
        - Confidence intervals (95%)
        - Model performance metrics (MAE, RMSE, R², coverage)

    Example Response:
    ```json
    {
        "status": "success",
        "forecast_horizon": "168 hours (7 days)",
        "model_type": "Prophet",
        "predictions_count": 168,
        "predictions": [
            {
                "timestamp": "2025-10-24T17:00:00",
                "predicted_price": 0.2397,
                "confidence_lower": 0.1823,
                "confidence_upper": 0.2971
            }
        ],
        "model_metrics": {
            "mae": 0.0325,
            "rmse": 0.0396,
            "r2": 0.489,
            "coverage_95": 0.883
        },
        "last_training": "2025-10-23T17:41:39",
        "timestamp": "2025-10-23T17:52:09"
    }
    ```
    """
    try:
        service = PriceForecastingService()

        # Train model if not available
        if service.model is None:
            logger.info("Model not available, training Prophet...")
            await service.train_model()

        # Get 7-day forecast
        forecast = await service.predict_weekly()

        if forecast is None or not forecast:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate price forecast"
            )

        # Format response (forecast is already a list of dicts from predict_weekly)
        predictions = forecast if isinstance(forecast, list) else []

        return {
            "status": "success",
            "forecast_horizon": "168 hours (7 days)",
            "model_type": "Prophet",
            "predictions_count": len(predictions),
            "predictions": predictions,
            "model_metrics": service.metrics,
            "last_training": service.last_training or datetime.now(),
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Error generating 7-day forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly", response_model=PriceForecastResponse)
async def get_hourly_forecast(
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to forecast (1-168)")
) -> Dict[str, Any]:
    """
    🔮 Get configurable hourly price forecast (1-168 hours).

    Args:
        hours: Number of hours to forecast (default 24, max 168)

    Returns:
        - Hourly price predictions for next N hours
        - Confidence intervals (95%)
        - Model performance metrics

    Example:
        - GET /predict/prices/hourly?hours=24 → Next 24 hours
        - GET /predict/prices/hourly?hours=72 → Next 3 days
        - GET /predict/prices/hourly?hours=168 → Full 7 days
    """
    try:
        service = PriceForecastingService()

        # Train model if not available
        if service.model is None:
            logger.info("Model not available, training Prophet...")
            await service.train_model()

        # Get configurable forecast
        forecast = await service.predict_hours(hours)

        if forecast is None or not forecast:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate {hours}-hour forecast"
            )

        # Format response (forecast is already a list of dicts)
        predictions = forecast if isinstance(forecast, list) else []

        return {
            "status": "success",
            "forecast_horizon": f"{hours} hours",
            "model_type": "Prophet",
            "predictions_count": len(predictions),
            "predictions": predictions,
            "model_metrics": service.metrics,
            "last_training": service.last_training or datetime.now(),
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Error generating {hours}-hour forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/price-forecast/train")
async def train_price_forecast_model(
    months_back: int = Query(default=12, ge=1, le=36, description="Months of historical data to use")
) -> Dict[str, Any]:
    """
    🤖 Train Prophet model with historical REE price data.

    Args:
        months_back: Historical months to use for training (default 12, max 36)

    Returns:
        - Training success status
        - Model performance metrics (MAE, RMSE, R², coverage)
        - Model file path

    Example Response:
    ```json
    {
        "status": "success",
        "training_result": {
            "success": true,
            "metrics": {
                "mae": 0.0325,
                "rmse": 0.0396,
                "r2": 0.489,
                "coverage_95": 0.883,
                "train_samples": 1475,
                "test_samples": 369
            },
            "last_training": "2025-10-23T17:41:39",
            "model_file": "/app/models/forecasting/prophet_latest.pkl"
        }
    }
    ```
    """
    try:
        service = PriceForecastingService()

        logger.info(f"🤖 Training Prophet model with {months_back} months of data...")
        result = await service.train_model(months_back=months_back)

        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Model training failed: {result.get('error', 'Unknown error')}"
            )

        return {
            "status": "success",
            "training_result": result
        }

    except Exception as e:
        logger.error(f"Error training Prophet model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/price-forecast/status", response_model=ModelStatusResponse)
async def get_price_forecast_status() -> Dict[str, Any]:
    """
    📊 Get Prophet model status and metrics.

    Returns:
        - Model availability status
        - Model metadata (type, version, last training)
        - Performance metrics (MAE, RMSE, R², coverage)

    Example Response:
    ```json
    {
        "status": "available",
        "model_info": {
            "type": "Prophet",
            "version": "1.1.7",
            "last_training": "2025-10-23T17:41:39"
        },
        "metrics": {
            "mae": 0.0325,
            "rmse": 0.0396,
            "r2": 0.489,
            "coverage_95": 0.883
        }
    }
    ```
    """
    try:
        service = PriceForecastingService()

        if service.model is None:
            return {
                "status": "not_trained",
                "model_info": {
                    "type": "Prophet",
                    "status": "Model not trained yet",
                    "last_training": None
                },
                "metrics": {}
            }

        return {
            "status": "available",
            "model_info": {
                "type": "Prophet",
                "version": "1.1.7",
                "last_training": service.last_training.isoformat() if service.last_training else None
            },
            "metrics": service.metrics
        }

    except Exception as e:
        logger.error(f"Error retrieving model status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
