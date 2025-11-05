"""
ML Predictions Router - Optimization Scoring

IMPORTANT: These endpoints provide deterministic scoring based on business rules,
NOT trained ML predictions. The scoring function is formula-based:
- Energy score: Weighted combination of price, temperature, humidity, tariff
- Production state: Rule-based classification using thresholds

While sklearn models are used, they learn the same formula used to generate targets
(circular training), so high accuracy metrics are not indicative of predictive power.

For REAL ML predictions, see /predict/prices/* (Prophet forecasting).
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from domain.ml.direct_ml import DirectMLService
from domain.ml.model_metrics_tracker import ModelMetricsTracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["Optimization Scoring"])

class PredictionRequest(BaseModel):
    price_eur_kwh: float
    temperature: float
    humidity: float

@router.post("/energy-optimization")
async def predict_energy_optimization(request: PredictionRequest) -> Dict[str, Any]:
    """
    🔮 Energy optimization score (0-100)

    Note: Deterministic scoring function, not predictive ML.
    """
    try:
        direct_ml = DirectMLService()
        result = direct_ml.predict_energy_optimization(
            price_eur_kwh=request.price_eur_kwh,
            temperature=request.temperature,
            humidity=request.humidity
        )
        return {"status": "✅", "prediction": result, "model": "RandomForestRegressor"}
    except Exception as e:
        logger.error(f"Energy prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/production-recommendation")
async def predict_production_recommendation(request: PredictionRequest) -> Dict[str, Any]:
    """🏭 Production class (Optimal/Moderate/Reduced/Halt)"""
    try:
        direct_ml = DirectMLService()
        result = direct_ml.predict_production_recommendation(
            price_eur_kwh=request.price_eur_kwh,
            temperature=request.temperature,
            humidity=request.humidity
        )
        return {
            "status": "✅",
            "prediction": result,
            "analysis": {"overall_score": result.get("confidence", 0) * 100},
            "model": "RandomForestClassifier"
        }
    except Exception as e:
        logger.error(f"Production prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train")
async def train_sklearn_models() -> Dict[str, Any]:
    """🤖 Train sklearn models manually"""
    try:
        direct_ml = DirectMLService()
        results = await direct_ml.train_models()
        return {"status": "✅" if results.get("success") else "❌", "results": results}
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train/hybrid")
async def train_hybrid_models() -> Dict[str, Any]:
    """
    🔥 HYBRID TRAINING - OPCIÓN C

    Entrena en 2 fases:
    - Fase 1: SIAR históricos (88k registros, 25 años, weather patterns)
    - Fase 2: Fine-tune con REE reciente (100 días, precios actuales)

    Resultado esperado: R² > 0.75, muestras ~7400
    """
    try:
        logger.info("🔥 Iniciando HYBRID TRAINING (OPCIÓN C)...")
        direct_ml = DirectMLService()
        results = await direct_ml.train_models_hybrid()

        success = results.get("success", False)
        status_icon = "✅" if success else "❌"

        return {
            "status": status_icon,
            "results": results,
            "mode": "HYBRID_OPCION_C",
            "expected_improvement": "R² should increase from 0.33 to 0.75+"
        }
    except Exception as e:
        logger.error(f"Hybrid training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/metrics-history")
async def get_model_metrics_history(
    model_name: Optional[str] = Query(None, description="Filter by model name (e.g., 'prophet_price_forecast')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return")
) -> Dict[str, Any]:
    """
    📊 Get model metrics history from CSV tracker (Sprint 20)

    Returns historical metrics for ML models to track performance over time
    and detect degradation.

    Args:
        model_name: Filter by specific model (None = all models)
        limit: Maximum entries to return (default 100, max 1000)

    Returns:
        Dict with metrics history and summary statistics

    Example response:
        {
            "model_name": "prophet_price_forecast",
            "total_entries": 45,
            "entries": [
                {
                    "timestamp": "2025-11-05T10:30:00",
                    "model_name": "prophet_price_forecast",
                    "mae": 0.033,
                    "rmse": 0.048,
                    "r2": 0.49,
                    "samples": 12493,
                    "duration_seconds": 45.2,
                    "notes": "scheduled_retrain"
                },
                ...
            ],
            "baseline_metrics": {
                "mae": 0.035,
                "rmse": 0.050,
                "r2": 0.48
            }
        }
    """
    try:
        tracker = ModelMetricsTracker()

        # Get history
        history = tracker.get_metrics_history(model_name=model_name, limit=limit)

        if not history:
            return {
                "model_name": model_name or "all",
                "total_entries": 0,
                "entries": [],
                "baseline_metrics": None,
                "message": "No metrics history found"
            }

        # Calculate baseline metrics (if model_name specified)
        baseline_metrics = None
        if model_name:
            baseline_mae = tracker.get_baseline(model_name, "mae")
            baseline_rmse = tracker.get_baseline(model_name, "rmse")
            baseline_r2 = tracker.get_baseline(model_name, "r2")

            if baseline_mae is not None:
                baseline_metrics = {
                    "mae": baseline_mae,
                    "rmse": baseline_rmse,
                    "r2": baseline_r2
                }

        return {
            "model_name": model_name or "all",
            "total_entries": len(history),
            "entries": history,
            "baseline_metrics": baseline_metrics
        }

    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
