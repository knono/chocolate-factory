"""
Gaps Router - Data Gap Detection and Backfill Endpoints

Endpoints for detecting and filling data gaps in InfluxDB.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gaps", tags=["Data Management"])


class RangeBackfillRequest(BaseModel):
    """Request model for range backfill"""
    start_date: str
    end_date: str
    data_source: str = "both"  # "both", "ree", "weather"
    chunk_hours: int = 24


# === GAP DETECTION ENDPOINTS ===

@router.get("/summary")
async def get_data_summary() -> Dict[str, Any]:
    """
    📊 Quick summary of data status

    Returns latest timestamps and gap hours for REE and weather data.
    """
    try:
        from services.gap_detector import GapDetectionService

        # Get latest timestamps
        gap_detector_service = GapDetectionService()
        latest = await gap_detector_service.get_latest_timestamps()

        # Calculate time since last update
        now = datetime.now(timezone.utc)

        ree_status = "❌ Sin datos"
        ree_gap_hours = None
        if latest['latest_ree']:
            ree_gap_hours = (now - latest['latest_ree']).total_seconds() / 3600
            if ree_gap_hours < 6:
                ree_status = "✅ Actualizado"
            elif ree_gap_hours < 24:
                ree_status = f"🟡 Normal ({int(ree_gap_hours)}h)"
            elif ree_gap_hours < 48:
                ree_status = f"⚠️ {int(ree_gap_hours)}h atrasado"
            else:
                ree_status = f"🚨 {int(ree_gap_hours // 24)}d atrasado"

        weather_status = "❌ Sin datos"
        weather_gap_hours = None
        if latest['latest_weather']:
            weather_gap_hours = (now - latest['latest_weather']).total_seconds() / 3600
            if weather_gap_hours < 2:
                weather_status = "✅ Actualizado"
            elif weather_gap_hours < 24:
                weather_status = f"⚠️ {int(weather_gap_hours)}h atrasado"
            else:
                weather_status = f"🚨 {int(weather_gap_hours // 24)}d atrasado"

        return {
            "🏭": "Chocolate Factory - Data Summary",
            "📊": "Estado Actual de Datos",
            "timestamp": now.isoformat(),
            "ree_prices": {
                "status": ree_status,
                "latest_data": latest['latest_ree'].isoformat() if latest['latest_ree'] else None,
                "gap_hours": round(ree_gap_hours, 1) if ree_gap_hours else None
            },
            "weather_data": {
                "status": weather_status,
                "latest_data": latest['latest_weather'].isoformat() if latest['latest_weather'] else None,
                "gap_hours": round(weather_gap_hours, 1) if weather_gap_hours else None
            },
            "recommendations": {
                "action_needed": (ree_gap_hours and ree_gap_hours > 48) or (weather_gap_hours and weather_gap_hours > 6),
                "suggested_endpoint": "GET /gaps/detect para análisis completo" if (ree_gap_hours and ree_gap_hours > 48) or (weather_gap_hours and weather_gap_hours > 6) else "Sistema al día"
            }
        }

    except Exception as e:
        logger.error(f"Data summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect")
async def detect_data_gaps(days_back: int = 7) -> Dict[str, Any]:
    """
    🔍 Detect data gaps in InfluxDB

    Args:
        days_back: Number of days to analyze (default: 7)

    Returns:
        Detailed gap analysis with recommended backfill strategy
    """
    try:
        from services.gap_detector import gap_detector

        # Perform gap analysis
        analysis = await gap_detector.detect_all_gaps(days_back)

        # Convert gaps to serializable format
        ree_gaps_data = []
        for gap in analysis.ree_gaps:
            ree_gaps_data.append({
                "measurement": gap.measurement,
                "start_time": gap.start_time.isoformat(),
                "end_time": gap.end_time.isoformat(),
                "duration_hours": round(gap.gap_duration_hours, 1),
                "missing_records": gap.missing_records,
                "severity": gap.severity
            })

        weather_gaps_data = []
        for gap in analysis.weather_gaps:
            weather_gaps_data.append({
                "measurement": gap.measurement,
                "start_time": gap.start_time.isoformat(),
                "end_time": gap.end_time.isoformat(),
                "duration_hours": round(gap.gap_duration_hours, 1),
                "missing_records": gap.missing_records,
                "severity": gap.severity
            })

        return {
            "🏭": "Chocolate Factory - Gap Analysis",
            "🔍": "Análisis de Huecos en Datos",
            "analysis_period": f"Últimos {days_back} días",
            "timestamp": analysis.analysis_timestamp.isoformat(),
            "summary": {
                "total_gaps": analysis.total_gaps_found,
                "ree_gaps": len(analysis.ree_gaps),
                "weather_gaps": len(analysis.weather_gaps),
                "estimated_backfill_time": analysis.estimated_backfill_duration
            },
            "ree_data_gaps": ree_gaps_data,
            "weather_data_gaps": weather_gaps_data,
            "recommended_strategy": analysis.recommended_backfill_strategy,
            "next_steps": {
                "auto_backfill": "POST /gaps/backfill/auto",
                "manual_backfill": "POST /gaps/backfill",
                "range_backfill": "POST /gaps/backfill/range"
            }
        }

    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === BACKFILL ENDPOINTS ===

@router.post("/backfill")
async def execute_backfill(
    days_back: int = 10,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    🔄 Execute intelligent backfill to fill data gaps

    Args:
        days_back: Number of days to process (default: 10)
        background_tasks: FastAPI background tasks (optional)

    Returns:
        Backfill execution status and results
    """
    try:
        from dependencies import get_backfill_service
        backfill_service = get_backfill_service()

        if background_tasks:
            # Execute in background for large gaps
            background_tasks.add_task(
                _execute_backfill_background,
                backfill_service,
                days_back
            )

            return {
                "🏭": "Chocolate Factory - Backfill Started",
                "🔄": "Proceso de Backfill Iniciado",
                "status": "🚀 Executing in background",
                "days_processing": days_back,
                "estimated_duration": "5-15 minutes",
                "monitoring": {
                    "check_progress": "GET /gaps/summary",
                    "verify_results": "GET /influxdb/verify"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Execute synchronously for testing
            result = await backfill_service.execute_intelligent_backfill(days_back)
            return {
                "🏭": "Chocolate Factory - Backfill Completed",
                "🔄": "Proceso de Backfill Terminado",
                **result
            }

    except Exception as e:
        logger.error(f"Backfill execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill/auto")
async def execute_auto_backfill(max_gap_hours: float = 6.0) -> Dict[str, Any]:
    """
    🤖 Automatic backfill only if significant gaps exist

    Args:
        max_gap_hours: Gap threshold in hours to trigger backfill (default: 6.0)

    Returns:
        Auto backfill execution status and results
    """
    try:
        from dependencies import get_backfill_service
        backfill_service = get_backfill_service()

        result = await backfill_service.check_and_execute_auto_backfill(max_gap_hours)

        return {
            "🏭": "Chocolate Factory - Auto Backfill",
            "🤖": "Backfill Automático Inteligente",
            **result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Auto backfill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill/range")
async def execute_range_backfill(
    request: RangeBackfillRequest,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    🎯 Specific backfill for exact date range (for historical gaps)

    Args:
        request: Range backfill configuration
        background_tasks: FastAPI background tasks (optional)

    Returns:
        Range backfill execution status and results
    """
    try:
        from dependencies import get_backfill_service
        backfill_service = get_backfill_service()

        # Parse dates
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))

        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")

        # Calculate days difference
        days_diff = (end_date - start_date).days + 1

        if background_tasks:
            # Execute in background
            background_tasks.add_task(
                _execute_range_backfill_background,
                backfill_service, request
            )

            return {
                "🏭": "Chocolate Factory - Range Backfill Started",
                "🎯": "Backfill de Rango Específico",
                "status": "🚀 Executing in background",
                "date_range": f"{request.start_date} → {request.end_date}",
                "days_processing": days_diff,
                "data_source": request.data_source,
                "chunk_hours": request.chunk_hours,
                "estimated_duration": f"{max(5, days_diff * 2)}-{days_diff * 5} minutes",
                "monitoring": {
                    "check_progress": "GET /gaps/summary",
                    "verify_results": "GET /influxdb/verify"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Execute synchronously (for testing)
            result = await _execute_range_backfill_sync(backfill_service, request)
            return {
                "🏭": "Chocolate Factory - Range Backfill Completed",
                "🎯": "Backfill de Rango Terminado",
                **result
            }

    except Exception as e:
        logger.error(f"Range backfill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === BACKGROUND TASK HELPERS ===

async def _execute_backfill_background(backfill_service, days_back: int):
    """Helper function to execute backfill in background"""
    try:
        logger.info(f"🔄 Starting background backfill for {days_back} days")
        result = await backfill_service.execute_intelligent_backfill(days_back)
        logger.info(f"✅ Background backfill completed: {result.get('summary', {}).get('overall_success_rate', 0)}% success")

    except Exception as e:
        logger.error(f"❌ Background backfill failed: {e}")


async def _execute_range_backfill_background(backfill_service, request: RangeBackfillRequest):
    """Helper function to execute range backfill in background"""
    try:
        logger.info(f"🎯 Starting background range backfill: {request.start_date} → {request.end_date}")
        result = await _execute_range_backfill_sync(backfill_service, request)
        logger.info(f"✅ Background range backfill completed")

    except Exception as e:
        logger.error(f"❌ Background range backfill failed: {e}")


async def _execute_range_backfill_sync(backfill_service, request: RangeBackfillRequest):
    """Execute range backfill synchronously"""
    from datetime import datetime, timezone

    # Parse dates
    start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))

    # Execute range backfill
    result = await backfill_service.execute_range_backfill(
        start_date=start_date,
        end_date=end_date,
        data_source=request.data_source,
        chunk_hours=request.chunk_hours
    )

    return result
