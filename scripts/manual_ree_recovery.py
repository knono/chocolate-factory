#!/usr/bin/env python3
"""
Script para ingesta manual directa de datos REE para resolver gap de 9 días
"""
import requests
import json
from datetime import datetime, timedelta

def manual_ree_recovery():
    """Recuperar datos REE día por día usando llamadas directas a la API"""

    print("🔧 Iniciando Recuperación Manual REE")
    print("=" * 50)

    # Definir rango de fechas del gap
    start_date = datetime(2025, 9, 8)  # Desde 8 septiembre
    end_date = datetime(2025, 9, 17)   # Hasta 17 septiembre

    base_ree_url = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

    current_date = start_date
    total_records = 0
    successful_days = 0

    while current_date <= end_date:
        day_str = current_date.strftime("%Y-%m-%d")
        print(f"\n📅 Procesando {day_str}...")

        # Construir parámetros para REE API
        start_param = f"{day_str}T00:00"
        end_param = f"{day_str}T23:59"

        try:
            # Llamada directa a REE API
            ree_url = f"{base_ree_url}?start_date={start_param}&end_date={end_param}&time_trunc=hour"

            print(f"🔗 URL: {ree_url}")

            response = requests.get(ree_url, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Procesar datos REE
                records_count = 0
                if "included" in data:
                    for item in data["included"]:
                        if item.get("type") == "PVPC" and "attributes" in item:
                            values = item["attributes"].get("values", [])
                            records_count = len(values)

                            # Mostrar algunos precios para verificar
                            if values:
                                first_price = values[0].get("value", "N/A")
                                last_price = values[-1].get("value", "N/A")
                                print(f"✅ {records_count} registros - Precios: {first_price}€/MWh ... {last_price}€/MWh")
                                total_records += records_count
                                successful_days += 1
                            else:
                                print("⚠️ No hay valores en la respuesta")
                else:
                    print("❌ No hay datos 'included' en la respuesta")

                if records_count == 0:
                    print("❌ No se obtuvieron registros para este día")

            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Error procesando {day_str}: {e}")

        # Avanzar al siguiente día
        current_date += timedelta(days=1)

        # Pausa entre llamadas para no sobrecargar la API
        import time
        time.sleep(1)

    # Resumen final
    print("\n" + "=" * 50)
    print("📊 Resumen de Recuperación Manual:")
    print(f"Días procesados exitosamente: {successful_days}/{(end_date - start_date).days + 1}")
    print(f"Total registros obtenidos: {total_records}")
    print(f"Promedio por día: {total_records / max(successful_days, 1):.1f} registros")

    if successful_days > 0:
        print("✅ Los datos están disponibles en REE API")
        print("💡 El problema está en la ingesta al sistema interno")
        print("🔧 Necesitamos usar el endpoint de ingesta con fechas específicas")
    else:
        print("❌ No se pudieron obtener datos de REE API")

    print("\n🎯 Próximo paso: Usar estos datos para ingesta manual en InfluxDB")

if __name__ == "__main__":
    manual_ree_recovery()