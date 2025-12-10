#!/usr/bin/env python3
"""
Test Context Builder Service
Sprint 11 - Chatbot BI

Test de categorización de keywords (sin requerir API running)
"""

import sys
from pathlib import Path

# Añadir src/fastapi-app al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "fastapi-app"))

# Mock settings para evitar crear /app/models
import os
os.environ['ML_MODELS_DIR'] = str(Path(__file__).parent.parent / 'models')

from services.chatbot_context_service import ChatbotContextService


def test_context_builder():
    """Test del context builder con diferentes tipos de preguntas."""

    service = ChatbotContextService()

    test_questions = [
        "¿Cuándo debo producir hoy?",
        "¿Cuál es el precio actual de la energía?",
        "¿Hay alguna alerta activa?",
        "¿Cuánto hemos ahorrado esta semana?",
        "Dame un resumen general del sistema",
    ]

    print("🧪 Test Context Builder Service\n")
    print("=" * 60)

    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Pregunta: '{question}'")
        print("-" * 60)

        try:
            # Detectar categorías
            question_lower = question.lower()
            categories = service._detect_categories(question_lower)
            print(f"   Categorías detectadas: {categories if categories else 'general (fallback)'}")

            # Construir contexto (requiere API running)
            # context = await service.build_context(question)
            # estimated_tokens = len(context) // 4
            # print(f"   Tokens estimados: ~{estimated_tokens}")
            # print(f"   Contexto (preview):\n{context[:200]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Test de categorización completado")
    print("\n⚠️  Para test completo, asegúrate de tener la API corriendo:")
    print("   docker compose up -d chocolate_factory_brain")


if __name__ == "__main__":
    test_context_builder()
