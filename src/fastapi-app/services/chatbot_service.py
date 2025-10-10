"""
Chatbot Service - Claude Haiku Integration
===========================================

Sprint 11 - Chatbot BI Conversacional

Integración con Claude Haiku API para consultas conversacionales.
Optimizado para respuestas concisas y costo bajo.
"""

import logging
import time
from typing import Dict, Optional
from anthropic import Anthropic, APIError, APITimeoutError

from core.config import settings
from services.chatbot_context_service import ChatbotContextService

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Servicio de chatbot usando Claude Haiku API.

    Características:
    - Respuestas concisas (max 300 tokens)
    - Context optimizado (< 2000 tokens)
    - Cost tracking automático
    - Error handling robusto
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.context_service = ChatbotContextService()
        self.model = settings.CHATBOT_MODEL
        self.max_tokens = settings.CHATBOT_MAX_TOKENS

        # System prompt especializado para Chocolate Factory
        self.system_prompt = """Eres un asistente BI especializado en la Chocolate Factory de Linares, España.

DATOS DISPONIBLES:
- Precios energía REE en tiempo real + predicciones Prophet ML (168h)
- Clima actual + histórico SIAR (88,935 registros 2000-2025)
- Ventanas óptimas de producción calculadas con ML
- Alertas predictivas del sistema
- Análisis de ahorro energético

CONTEXTO DE NEGOCIO:
- Producción chocolate requiere temperatura 18-22°C óptima
- Consumo energético intensivo: 350 kWh/batch conchado
- Periodos tarifarios: P1 (caro 10-13h, 18-21h), P2 (medio), P3 (valle madrugada)
- Objetivo: maximizar producción en P3 y ventanas de precio bajo

TU ROL:
1. Interpretar datos técnicos y dar recomendaciones ACCIONABLES
2. Priorizar CUÁNDO producir (fecha + horas específicas)
3. Explicar el PORQUÉ (precio, clima, ahorro)
4. Ser CONCISO: máximo 3-4 frases

FORMATO DE RESPUESTA:
✅ RESPUESTA DIRECTA (qué hacer)
💡 RAZÓN (por qué)
📊 DATOS CLAVE (números del contexto)

REGLAS CRÍTICAS:
- USA SOLO datos del CONTEXTO proporcionado
- Si preguntan "¿cuándo producir?": lista horas ESPECÍFICAS con precios
- Si no hay datos: "No tengo información actualizada para responder"
- NUNCA inventes precios, fechas o métricas
- Formatea números: 0.14 €/kWh, 23.5°C, 85.2%"""

    async def ask(self, question: str, user_id: Optional[str] = None) -> Dict:
        """
        Procesa una pregunta del usuario y retorna respuesta de Claude.

        Args:
            question: Pregunta del usuario
            user_id: ID del usuario (para logging)

        Returns:
            Dict con: answer, tokens, latency_ms, cost_usd
        """
        start_time = time.time()

        try:
            # 1. Construir contexto relevante
            logger.info(f"User {user_id}: '{question}'")
            context = await self.context_service.build_context(question)

            # 2. Preparar mensaje para Claude
            user_message = f"""CONTEXTO:
{context}

PREGUNTA DEL USUARIO:
{question}

Responde de forma concisa y accionable basándote SOLO en el contexto anterior."""

            # 3. Llamar a Claude Haiku API
            logger.info(f"Calling Claude Haiku API...")
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # 4. Extraer respuesta
            answer = message.content[0].text

            # 5. Calcular métricas
            latency_ms = int((time.time() - start_time) * 1000)
            tokens = {
                "input": message.usage.input_tokens,
                "output": message.usage.output_tokens,
                "total": message.usage.input_tokens + message.usage.output_tokens
            }

            # 6. Calcular costo (Haiku pricing)
            cost_usd = self._calculate_cost(
                message.usage.input_tokens,
                message.usage.output_tokens
            )

            logger.info(
                f"Response: {len(answer)} chars, "
                f"{tokens['total']} tokens, "
                f"{latency_ms}ms, "
                f"${cost_usd:.6f}"
            )

            return {
                "answer": answer,
                "tokens": tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "model": self.model,
                "success": True
            }

        except APITimeoutError as e:
            logger.error(f"Claude API timeout: {e}")
            return self._error_response(
                "⏱️ Timeout: El servicio está tardando demasiado. Inténtalo de nuevo.",
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except APIError as e:
            logger.error(f"Claude API error: {e}")
            return self._error_response(
                "❌ Error del servicio Claude. Por favor, inténtalo más tarde.",
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return self._error_response(
                "⚠️ Error inesperado. Contacta al administrador si persiste.",
                latency_ms=int((time.time() - start_time) * 1000)
            )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calcula costo en USD según pricing de Haiku.

        Haiku pricing (Oct 2024):
        - Input: $0.80 per 1M tokens
        - Output: $4.00 per 1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 0.80
        output_cost = (output_tokens / 1_000_000) * 4.00
        return input_cost + output_cost

    def _error_response(self, message: str, latency_ms: int) -> Dict:
        """Respuesta de error estandarizada."""
        return {
            "answer": message,
            "tokens": {"input": 0, "output": 0, "total": 0},
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
            "model": self.model,
            "success": False
        }


# Singleton instance para reutilizar cliente
_chatbot_service_instance: Optional[ChatbotService] = None


def get_chatbot_service() -> ChatbotService:
    """Dependency injection para FastAPI."""
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        _chatbot_service_instance = ChatbotService()
    return _chatbot_service_instance
