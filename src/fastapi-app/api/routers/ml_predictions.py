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
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from domain.ml.direct_ml import DirectMLService

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
