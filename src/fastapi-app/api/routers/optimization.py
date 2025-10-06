"""
Production Optimization Router
================================

RESTful endpoints for hourly production optimization.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimize", tags=["Production Optimization"])


@router.post("/production/daily")
async def optimize_daily_production(
    target_date: Optional[str] = None,
    target_kg: Optional[float] = None
) -> Dict[str, Any]:
    """
    🎯 24-hour hourly optimization for chocolate production.

    Combines REE predictions (Sprint 06) + SIAR climate (Sprint 07) + production constraints.

    Generates optimized plan that:
    - Maximizes production
    - Minimizes energy cost
    - Respects constraints (sequence, timings, climate)
    - Calculates savings vs baseline

    Args:
        target_date: Target date ISO (default: tomorrow)
        target_kg: Target kg (default: 200kg)

    Returns:
        24h optimized plan with scheduled batches and estimated savings
    """
    try:
        from services.hourly_optimizer_service import get_optimizer_service
        from services.data_ingestion import DataIngestionService

        # Parse target date
        target_datetime = None
        if target_date:
            target_datetime = datetime.fromisoformat(target_date.replace("Z", "+00:00"))

        # Get InfluxDB client through DataIngestionService
        async with DataIngestionService() as service:
            influx_client = service.client

            # Get optimizer service
            optimizer = get_optimizer_service(influxdb_client=influx_client)

            # Optimize
            result = await optimizer.optimize_daily_production(
                target_date=target_datetime,
                target_kg=target_kg
            )

            return {
                "🏭": "Chocolate Factory - Optimización Horaria 24h",
                "timestamp": datetime.now().isoformat(),
                "optimization": result
            }

    except Exception as e:
        logger.error(f"❌ Error en optimización producción: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/production/summary")
async def get_optimization_summary() -> Dict[str, Any]:
    """
    📊 Summary of optimization capacity and current constraints.

    Returns:
        Information about optimization engine, constraints, and capabilities
    """
    try:
        return {
            "🏭": "Chocolate Factory - Motor Optimización",
            "status": "✅ Operacional",
            "algorithm": "Greedy Heuristic con scoring multi-objetivo",
            "optimization_factors": {
                "energy_prices": "60% peso - Predicciones Prophet 168h",
                "weather_conditions": "40% peso - Análisis SIAR + AEMET",
                "production_constraints": "Secuencia obligatoria + buffers + capacidades"
            },
            "production_capacity": {
                "batch_size_kg": 10,
                "daily_target_kg": 200,
                "max_batches_per_day": 20,
                "quality_mix": "70% standard (5h conchado) + 30% premium (10h conchado)"
            },
            "constraints": {
                "process_sequence": ["Mezclado", "Refinado", "Conchado", "Templado", "Moldeo", "Enfriamiento"],
                "temperature_limits": {
                    "optimal_range": "18-24°C",
                    "warning_threshold": "25°C",
                    "critical_threshold": "28°C"
                },
                "humidity_limits": {
                    "optimal_range": "45-65%",
                    "warning_threshold": "70%",
                    "critical_threshold": "80%"
                }
            },
            "optimization_horizon": "24 hours",
            "update_frequency": "Hourly recalculation recommended",
            "data_sources": {
                "energy_prices": "Prophet ML (REE historical + predictions)",
                "weather": "SIAR historical (88k records) + AEMET current",
                "production_model": "Chocolate Factory process simulation"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Optimization summary failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")
