#!/usr/bin/env python3
"""
Script para ingesta directa de datos REE a InfluxDB - Bypass del sistema de gaps
"""
import sys
import os
import asyncio
import requests
from datetime import datetime, timedelta, timezone

# Add the source directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'fastapi-app'))

async def direct_ree_ingestion():
    """Ingesta directa de datos REE del gap faltante"""

    print("🚀 Iniciando Ingesta Directa REE → InfluxDB")
    print("=" * 60)

    try:
        # Import interno del sistema
        from services.ree_client import REEClient
        from services.data_ingestion import DataIngestionService

        # Rango de fechas del gap
        start_date = datetime(2025, 9, 8, tzinfo=timezone.utc)
        end_date = datetime(2025, 9, 17, tzinfo=timezone.utc)

        print(f"📅 Rango: {start_date.date()} → {end_date.date()}")

        total_records_obtained = 0
        total_records_written = 0
        successful_days = 0

        async with REEClient() as ree_client:
            async with DataIngestionService() as ingestion_service:

                current_date = start_date.date()
                end_date_date = end_date.date()

                while current_date <= end_date_date:
                    print(f"\n📊 Procesando {current_date}...")

                    try:
                        # Crear rango del día completo
                        day_start = datetime.combine(
                            current_date, datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                        day_end = day_start + timedelta(days=1) - timedelta(minutes=1)

                        print(f"   🕐 Rango: {day_start.strftime('%H:%M')} - {day_end.strftime('%H:%M')}")

                        # Obtener datos REE para este día
                        daily_data = await ree_client.get_pvpc_prices(
                            start_date=day_start,
                            end_date=day_end
                        )

                        if daily_data:
                            print(f"   ✅ Obtenidos {len(daily_data)} registros de REE")

                            # Escribir a InfluxDB usando el método histórico
                            write_result = await ingestion_service.ingest_ree_prices_historical(daily_data)

                            total_records_obtained += len(daily_data)
                            total_records_written += write_result.successful_writes

                            success_rate = (write_result.successful_writes / len(daily_data)) * 100
                            print(f"   💾 Escritos {write_result.successful_writes}/{len(daily_data)} registros ({success_rate:.1f}%)")

                            if write_result.successful_writes == len(daily_data):
                                successful_days += 1
                                print(f"   🎉 Día {current_date} completado exitosamente")
                            else:
                                print(f"   ⚠️ Día {current_date} con escritura parcial")

                        else:
                            print(f"   ❌ No se obtuvieron datos REE para {current_date}")

                        # Rate limiting
                        await asyncio.sleep(2)

                    except Exception as day_error:
                        print(f"   ❌ Error procesando {current_date}: {day_error}")

                    current_date += timedelta(days=1)

        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE INGESTA DIRECTA:")
        print(f"Días procesados exitosamente: {successful_days}/10")
        print(f"Total registros obtenidos: {total_records_obtained}")
        print(f"Total registros escritos: {total_records_written}")

        overall_success_rate = (total_records_written / total_records_obtained * 100) if total_records_obtained > 0 else 0
        print(f"Tasa de éxito general: {overall_success_rate:.1f}%")

        if overall_success_rate > 90:
            print("🎉 ¡INGESTA COMPLETADA EXITOSAMENTE!")
            print("🔍 Verificar gap con: curl http://localhost:8000/gaps/summary")
        elif overall_success_rate > 70:
            print("✅ Ingesta mayormente exitosa")
            print("⚠️ Algunos registros pueden necesitar reintentos")
        else:
            print("❌ Ingesta con problemas significativos")
            print("🔧 Revisar logs de InfluxDB y configuración")

    except ImportError as e:
        print(f"❌ Error importando servicios: {e}")
        print("💡 Ejecutar desde el directorio del proyecto")
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(direct_ree_ingestion())