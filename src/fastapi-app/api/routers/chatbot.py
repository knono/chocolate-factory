"""
Chatbot Router
==============

Sprint 11 - Chatbot BI Conversacional

Endpoints para interacción con chatbot Claude Haiku.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict
import logging
from datetime import datetime

from services.chatbot_service import get_chatbot_service
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/chat", tags=["Chatbot"])

# In-memory stats (en producción usarías InfluxDB)
_chatbot_stats = {
    "total_questions": 0,
    "total_tokens_input": 0,
    "total_tokens_output": 0,
    "total_cost_usd": 0.0,
    "questions_today": 0,
    "last_reset": datetime.now().date()
}


# ============================================================================
# SCHEMAS
# ============================================================================

class ChatRequest(BaseModel):
    """Request schema para pregunta al chatbot."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Pregunta del usuario (3-500 caracteres)"
    )
    user_id: Optional[str] = Field(
        None,
        description="ID del usuario (opcional, para tracking)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "¿Cuándo debo producir hoy?",
                    "user_id": "mobile_user_001"
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response schema con respuesta del chatbot."""
    answer: str = Field(..., description="Respuesta del chatbot")
    tokens: Dict[str, int] = Field(..., description="Tokens usados (input, output, total)")
    latency_ms: int = Field(..., description="Latencia en milisegundos")
    cost_usd: float = Field(..., description="Costo en USD")
    model: str = Field(..., description="Modelo usado (claude-3-5-haiku)")
    success: bool = Field(..., description="Si la respuesta fue exitosa")
    timestamp: str = Field(..., description="Timestamp de la respuesta")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "✅ Ventanas óptimas hoy:\n- 02:00-05:00h (0.06€/kWh)\n- 14:00-16:00h (0.09€/kWh)",
                    "tokens": {"input": 600, "output": 150, "total": 750},
                    "latency_ms": 1534,
                    "cost_usd": 0.001080,
                    "model": "claude-3-5-haiku-20241022",
                    "success": True,
                    "timestamp": "2025-10-10T14:30:00"
                }
            ]
        }
    }


class ChatStatsResponse(BaseModel):
    """Response schema para estadísticas del chatbot."""
    total_questions: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    avg_latency_ms: Optional[int] = None
    questions_today: int
    last_reset: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_questions": 1247,
                    "total_tokens_input": 1245000,
                    "total_tokens_output": 187000,
                    "total_cost_usd": 2.74,
                    "avg_latency_ms": 1534,
                    "questions_today": 42,
                    "last_reset": "2025-10-10"
                }
            ]
        }
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/ask", response_model=ChatResponse)
@limiter.limit("20/minute")  # Max 20 preguntas por minuto
async def ask_chatbot(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """
    Endpoint principal del chatbot.

    Acepta preguntas en lenguaje natural y retorna respuestas de Claude Haiku.

    **Ejemplos de preguntas**:
    - "¿Cuándo debo producir hoy?"
    - "¿Cuál es el precio actual de energía?"
    - "¿Hay alertas activas?"
    - "¿Cuánto ahorramos esta semana?"
    - "Dame un resumen del sistema"

    **Rate limit**: 20 preguntas por minuto por IP.

    **Costo estimado**: ~€0.001-0.002 por pregunta (Haiku pricing).
    """
    try:
        # Obtener servicio
        chatbot_service = get_chatbot_service()

        # Procesar pregunta
        logger.info(f"Question from {chat_request.user_id or 'anonymous'}: {chat_request.question}")
        response = await chatbot_service.ask(
            question=chat_request.question,
            user_id=chat_request.user_id
        )

        # Actualizar stats
        _update_stats(response)

        # Preparar respuesta
        return ChatResponse(
            answer=response["answer"],
            tokens=response["tokens"],
            latency_ms=response["latency_ms"],
            cost_usd=response["cost_usd"],
            model=response["model"],
            success=response["success"],
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error in chatbot endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando pregunta: {str(e)}"
        )


@router.get("/stats", response_model=ChatStatsResponse)
async def get_chatbot_stats() -> ChatStatsResponse:
    """
    Obtener estadísticas de uso del chatbot.

    Incluye:
    - Total de preguntas procesadas
    - Tokens usados (input/output)
    - Costo total acumulado
    - Preguntas del día actual

    **Nota**: Stats se resetean diariamente a las 00:00.
    """
    # Reset diario automático
    today = datetime.now().date()
    if _chatbot_stats["last_reset"] != today:
        _chatbot_stats["questions_today"] = 0
        _chatbot_stats["last_reset"] = today

    return ChatStatsResponse(
        total_questions=_chatbot_stats["total_questions"],
        total_tokens_input=_chatbot_stats["total_tokens_input"],
        total_tokens_output=_chatbot_stats["total_tokens_output"],
        total_cost_usd=round(_chatbot_stats["total_cost_usd"], 6),
        questions_today=_chatbot_stats["questions_today"],
        last_reset=str(_chatbot_stats["last_reset"])
    )


@router.get("/health")
async def chatbot_health() -> Dict:
    """
    Health check del chatbot.

    Verifica que el servicio está operacional y retorna info básica.
    """
    try:
        chatbot_service = get_chatbot_service()
        return {
            "status": "healthy",
            "model": chatbot_service.model,
            "max_tokens": chatbot_service.max_tokens,
            "total_questions": _chatbot_stats["total_questions"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Chatbot service unhealthy: {str(e)}")


# ============================================================================
# HELPERS
# ============================================================================

def _update_stats(response: Dict):
    """Actualizar estadísticas en memoria."""
    if response["success"]:
        _chatbot_stats["total_questions"] += 1
        _chatbot_stats["total_tokens_input"] += response["tokens"]["input"]
        _chatbot_stats["total_tokens_output"] += response["tokens"]["output"]
        _chatbot_stats["total_cost_usd"] += response["cost_usd"]
        _chatbot_stats["questions_today"] += 1
