"""ML Predictions Router - sklearn models (energy + production)"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services.direct_ml import DirectMLService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["ML Predictions"])

class PredictionRequest(BaseModel):
    price_eur_kwh: float
    temperature: float
    humidity: float

@router.post("/energy-optimization")
async def predict_energy_optimization(request: PredictionRequest) -> Dict[str, Any]:
    """🔮 Energy optimization score (0-100)"""
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
