#!/usr/bin/env python3
"""
Script de prueba para Chatbot Service (Sprint 11)
==================================================

Prueba la integración completa del chatbot con contexto real.
"""

import sys
import asyncio
import httpx
import json
from datetime import datetime

# Test questions
TEST_QUESTIONS = [
    "¿Cuándo debo producir hoy?",
    "¿Cuál es el precio actual de energía?",
    "¿Hay alertas activas?",
    "¿Cuánto ahorramos esta semana?",
    "Dame un resumen del estado actual",
]

BASE_URL = "http://localhost:8000"


async def test_chatbot_question(question: str):
    """Prueba una pregunta al chatbot."""
    print(f"\n{'='*80}")
    print(f"❓ PREGUNTA: {question}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Send question
            response = await client.post(
                f"{BASE_URL}/chat/ask",
                json={"question": question, "user_id": "test_script"}
            )

            if response.status_code != 200:
                print(f"❌ ERROR HTTP {response.status_code}")
                print(response.text)
                return False

            data = response.json()

            # Display answer
            print(f"🤖 RESPUESTA:\n")
            print(data["answer"])
            print(f"\n{'-'*80}")

            # Display metadata
            tokens = data["tokens"]
            print(f"📊 MÉTRICAS:")
            print(f"   • Tokens: {tokens['input']} input + {tokens['output']} output = {tokens['total']} total")
            print(f"   • Latencia: {data['latency_ms']}ms")
            print(f"   • Costo: ${data['cost_usd']:.6f}")
            print(f"   • Modelo: {data['model']}")
            print(f"   • Éxito: {'✅' if data['success'] else '❌'}")

            return data["success"]

        except Exception as e:
            print(f"❌ EXCEPCIÓN: {e}")
            return False


async def test_chatbot_stats():
    """Obtiene estadísticas del chatbot."""
    print(f"\n{'='*80}")
    print(f"📊 ESTADÍSTICAS DEL CHATBOT")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/chat/stats")

            if response.status_code != 200:
                print(f"❌ ERROR HTTP {response.status_code}")
                return

            stats = response.json()

            print(f"Total preguntas: {stats['total_questions']}")
            print(f"Tokens input: {stats['total_tokens_input']:,}")
            print(f"Tokens output: {stats['total_tokens_output']:,}")
            print(f"Costo total: ${stats['total_cost_usd']:.6f}")
            print(f"Preguntas hoy: {stats['questions_today']}")
            print(f"Último reset: {stats['last_reset']}")

        except Exception as e:
            print(f"❌ Error obteniendo stats: {e}")


async def test_context_builder():
    """Prueba que el context builder puede acceder a los endpoints."""
    print(f"\n{'='*80}")
    print(f"🔍 VERIFICANDO ENDPOINTS DE CONTEXTO")
    print(f"{'='*80}\n")

    endpoints = [
        ("/dashboard/complete", "Dashboard completo"),
        ("/insights/optimal-windows", "Ventanas óptimas"),
        ("/ree/prices/latest", "Precios REE recientes"),
        ("/insights/alerts", "Alertas"),
        ("/insights/savings-tracking", "Tracking ahorros"),
    ]

    async with httpx.AsyncClient(timeout=15.0) as client:
        for endpoint, description in endpoints:
            try:
                print(f"🔗 Probando: {description} ({endpoint})...", end=" ")
                response = await client.get(f"{BASE_URL}{endpoint}")

                if response.status_code == 200:
                    data = response.json()
                    size = len(json.dumps(data))
                    print(f"✅ OK ({size:,} bytes)")
                else:
                    print(f"❌ ERROR {response.status_code}")

            except Exception as e:
                print(f"❌ EXCEPCIÓN: {e}")


async def main():
    """Test completo del chatbot."""
    print(f"\n🤖 TEST INTEGRACIÓN CHATBOT BI - Sprint 11")
    print(f"{'='*80}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*80}\n")

    # 1. Test context builder endpoints
    await test_context_builder()

    # 2. Test chatbot questions
    success_count = 0
    for question in TEST_QUESTIONS:
        success = await test_chatbot_question(question)
        if success:
            success_count += 1
        await asyncio.sleep(1)  # Rate limiting

    # 3. Show stats
    await test_chatbot_stats()

    # Summary
    print(f"\n{'='*80}")
    print(f"📋 RESUMEN")
    print(f"{'='*80}")
    print(f"Preguntas probadas: {len(TEST_QUESTIONS)}")
    print(f"Exitosas: {success_count}")
    print(f"Fallidas: {len(TEST_QUESTIONS) - success_count}")
    print(f"Tasa de éxito: {(success_count/len(TEST_QUESTIONS)*100):.1f}%")

    if success_count == len(TEST_QUESTIONS):
        print(f"\n✅ TODOS LOS TESTS PASARON")
        return 0
    else:
        print(f"\n⚠️ ALGUNOS TESTS FALLARON")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
