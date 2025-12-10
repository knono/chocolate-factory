#!/usr/bin/env python3
"""
Test Chatbot Service Completo
Sprint 11 - Chatbot BI

REQUIERE: API corriendo (docker compose up -d)
"""

import sys
import asyncio
from pathlib import Path

# Añadir src/fastapi-app al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "fastapi-app"))

# Mock settings para evitar crear /app/models
import os
os.environ['ML_MODELS_DIR'] = str(Path(__file__).parent.parent / 'models')
os.environ['STATIC_FILES_DIR'] = str(Path(__file__).parent.parent / 'static')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from services.chatbot_service import ChatbotService


async def test_chatbot():
    """Test del chatbot service con preguntas reales."""

    print("🧪 Test Chatbot Service (Claude Haiku API)\n")
    print("=" * 70)

    service = ChatbotService()

    test_questions = [
        "¿Cuándo debo producir hoy?",
        "¿Cuál es el precio actual?",
        "¿Hay alertas activas?",
    ]

    total_cost = 0.0
    total_tokens = 0

    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Pregunta: '{question}'")
        print("-" * 70)

        try:
            response = await service.ask(question, user_id="test_user")

            if response["success"]:
                print(f"✅ Respuesta: {response['answer']}")
                print(f"\n📊 Métricas:")
                print(f"   - Tokens: {response['tokens']['total']} "
                      f"({response['tokens']['input']} in, {response['tokens']['output']} out)")
                print(f"   - Latencia: {response['latency_ms']}ms")
                print(f"   - Costo: ${response['cost_usd']:.6f} (€{response['cost_usd'] * 0.93:.6f})")

                total_cost += response['cost_usd']
                total_tokens += response['tokens']['total']
            else:
                print(f"❌ Error: {response['answer']}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    print("\n" + "=" * 70)
    print(f"\n📊 RESUMEN TOTAL:")
    print(f"   - Preguntas: {len(test_questions)}")
    print(f"   - Tokens totales: {total_tokens}")
    print(f"   - Costo total: ${total_cost:.6f} (€{total_cost * 0.93:.6f})")
    print(f"   - Costo promedio/pregunta: ${total_cost / len(test_questions):.6f}")

    print("\n✅ Test completado")


if __name__ == "__main__":
    try:
        asyncio.run(test_chatbot())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por usuario")
