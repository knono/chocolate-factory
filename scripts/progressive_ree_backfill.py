#!/usr/bin/env python3
"""
Script para backfill progresivo de datos REE usando endpoints existentes
"""
import requests
import time
import json
from datetime import datetime

def progressive_ree_backfill():
    """Ejecutar backfill progresivo para recuperar datos REE históricos"""

    base_url = "http://localhost:8000"

    print("🔄 Iniciando Backfill Progresivo REE")
    print("=" * 50)

    # Verificar estado inicial
    print("📊 Verificando gaps iniciales...")
    response = requests.get(f"{base_url}/gaps/summary")
    if response.status_code == 200:
        data = response.json()
        print(f"REE Status: {data['ree_prices']['status']}")
        print(f"Gap hours: {data['ree_prices']['gap_hours']}")
        print(f"Latest data: {data['ree_prices']['latest_data']}")

    # Estrategia progresiva: Ejecutar backfills en bloques pequeños
    strategies = [
        {"days_back": 1, "description": "Últimas 24 horas"},
        {"days_back": 3, "description": "Últimos 3 días"},
        {"days_back": 5, "description": "Últimos 5 días"},
        {"days_back": 7, "description": "Última semana"},
        {"days_back": 10, "description": "Últimos 10 días"},
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"\n🎯 Fase {i}: {strategy['description']} ({strategy['days_back']} días)")

        # Ejecutar backfill
        payload = {"days_back": strategy["days_back"]}

        try:
            response = requests.post(
                f"{base_url}/gaps/backfill",
                params=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Iniciado: {result.get('status', 'unknown')}")
                print(f"⏱️ Estimación: {result.get('estimated_duration', 'unknown')}")

                # Esperar tiempo suficiente para que termine
                wait_time = 60 + (strategy["days_back"] * 15)  # 60s base + 15s por día
                print(f"⏳ Esperando {wait_time}s para completar...")
                time.sleep(wait_time)

                # Verificar progreso
                check_response = requests.get(f"{base_url}/gaps/summary")
                if check_response.status_code == 200:
                    check_data = check_response.json()
                    new_gap_hours = check_data['ree_prices']['gap_hours']
                    print(f"📈 Gap actual: {new_gap_hours} horas")

                    if new_gap_hours < 24:  # Menos de 1 día de gap
                        print("🎉 ¡Gap reducido significativamente! Continuando...")
                    else:
                        print("⚠️ Gap aún significativo, continuando con siguiente fase...")
                else:
                    print("❌ Error verificando progreso")

            else:
                print(f"❌ Error iniciando fase {i}: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ Error en fase {i}: {e}")

        # Pausa entre fases
        if i < len(strategies):
            print("⏸️ Pausa entre fases...")
            time.sleep(10)

    # Verificar resultado final
    print("\n" + "=" * 50)
    print("📊 Estado Final:")

    try:
        final_response = requests.get(f"{base_url}/gaps/summary")
        if final_response.status_code == 200:
            final_data = final_response.json()
            print(f"REE Status: {final_data['ree_prices']['status']}")
            print(f"Gap final: {final_data['ree_prices']['gap_hours']} horas")
            print(f"Latest data: {final_data['ree_prices']['latest_data']}")

            # Evaluar éxito
            final_gap = final_data['ree_prices']['gap_hours']
            if final_gap < 24:
                print("🎉 ¡ÉXITO! Gap reducido a menos de 24 horas")
            elif final_gap < 72:
                print("✅ PROGRESO: Gap reducido significativamente")
            else:
                print("⚠️ PARCIAL: Aún hay gap significativo")

        else:
            print("❌ Error obteniendo estado final")

    except Exception as e:
        print(f"❌ Error verificando estado final: {e}")

    print("\n🎯 Backfill progresivo completado!")
    print("💡 Si persisten gaps, considera ejecutar de nuevo o usar estrategia manual")

if __name__ == "__main__":
    progressive_ree_backfill()