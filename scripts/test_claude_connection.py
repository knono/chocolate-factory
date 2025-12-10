#!/usr/bin/env python3
"""
Test básico de conexión con Claude API
Sprint 11 - Chatbot BI
"""

import os
import sys
from pathlib import Path

# Añadir src/fastapi-app al path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "fastapi-app"))

from dotenv import load_dotenv

# Cargar .env desde raíz del proyecto
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def test_claude_connection():
    """Test conexión básica con Claude Haiku API."""
    try:
        from anthropic import Anthropic

        # Verificar API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ERROR: ANTHROPIC_API_KEY no encontrada en .env")
            return False

        print(f"✅ API Key encontrada: {api_key[:20]}...")

        # Crear cliente
        client = Anthropic(api_key=api_key)
        print("✅ Cliente Anthropic creado")

        # Test simple
        print("\n🧪 Testeando llamada a Claude Haiku...")
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Responde solo con: '¡Conexión exitosa con Chocolate Factory!'"}
            ]
        )

        response_text = message.content[0].text
        print(f"✅ Respuesta de Claude: {response_text}")
        print(f"\n📊 Tokens usados:")
        print(f"   - Input: {message.usage.input_tokens}")
        print(f"   - Output: {message.usage.output_tokens}")

        # Calcular costo estimado
        input_cost = (message.usage.input_tokens / 1_000_000) * 0.80  # $0.80 per 1M tokens
        output_cost = (message.usage.output_tokens / 1_000_000) * 4.00  # $4.00 per 1M tokens
        total_cost = input_cost + output_cost

        print(f"\n💰 Costo estimado:")
        print(f"   - Input: ${input_cost:.6f}")
        print(f"   - Output: ${output_cost:.6f}")
        print(f"   - Total: ${total_cost:.6f} (€{total_cost * 0.93:.6f})")

        print("\n✅ ¡Test de conexión completado con éxito!")
        return True

    except ImportError as e:
        print(f"❌ ERROR: Librerías no instaladas: {e}")
        print("Ejecutar: cd src/fastapi-app && pip install anthropic")
        return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_claude_connection()
    exit(0 if success else 1)
