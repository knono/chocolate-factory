#!/usr/bin/env python3
"""
Script para diagnosticar problemas del gap detector con ventanas grandes
"""
import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta

# Add the source directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'fastapi-app'))

async def diagnose_gap_detector():
    """Diagnosticar gap detector con diferentes ventanas"""

    print("🔍 DIAGNÓSTICO DEL GAP DETECTOR")
    print("=" * 50)

    try:
        from services.gap_detector import gap_detector
        from services.data_ingestion import DataIngestionService

        # Test con diferentes ventanas
        test_windows = [1, 3, 7, 10, 15, 30]

        for days_back in test_windows:
            print(f"\n📅 Probando ventana de {days_back} días...")

            try:
                # Medir tiempo de ejecución
                start_time = datetime.now()

                analysis = await gap_detector.detect_all_gaps(days_back)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                print(f"   ⏱️ Duración: {duration:.2f}s")
                print(f"   📊 Total gaps: {analysis.total_gaps_found}")
                print(f"   🔌 REE gaps: {len(analysis.ree_gaps)}")
                print(f"   🌤️ Weather gaps: {len(analysis.weather_gaps)}")

                # Detalles de gaps REE
                if analysis.ree_gaps:
                    for i, gap in enumerate(analysis.ree_gaps[:3]):  # Solo primeros 3
                        gap_hours = gap.gap_duration_hours
                        print(f"      Gap {i+1}: {gap.start_time.strftime('%m-%d %H:%M')} → {gap.end_time.strftime('%m-%d %H:%M')} ({gap_hours:.1f}h)")

                if duration > 30:
                    print(f"   ⚠️ LENTO: {duration:.1f}s para {days_back} días")

                if analysis.total_gaps_found == 0 and days_back >= 10:
                    print(f"   🚨 PROBLEMA: No detecta gaps con {days_back} días")

            except Exception as e:
                print(f"   ❌ ERROR con {days_back} días: {e}")

        # Test directo de query InfluxDB para diferentes ventanas
        print(f"\n🔎 DIAGNÓSTICO DIRECTO DE INFLUXDB:")

        async with DataIngestionService() as service:
            for days_back in [7, 10, 15, 30]:
                print(f"\n📊 Consultando InfluxDB: últimos {days_back} días...")

                try:
                    start_time = datetime.now()

                    query = f'''
                    from(bucket: "{service.config.bucket}")
                    |> range(start: -{days_back}d)
                    |> filter(fn: (r) => r._measurement == "energy_prices")
                    |> filter(fn: (r) => r._field == "price_eur_kwh")
                    |> count()
                    '''

                    result = service.client.query_api().query(query)

                    total_records = 0
                    for table in result:
                        for record in table.records:
                            total_records += record.get_value()

                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    expected_records = days_back * 24  # 24 horas por día
                    gap_percentage = ((expected_records - total_records) / expected_records) * 100

                    print(f"   📈 Registros: {total_records}/{expected_records} ({gap_percentage:.1f}% gap)")
                    print(f"   ⏱️ Query time: {duration:.2f}s")

                    if duration > 10:
                        print(f"   ⚠️ Query lenta para {days_back} días")

                except Exception as e:
                    print(f"   ❌ Error query InfluxDB {days_back}d: {e}")

        print(f"\n📋 RECOMENDACIONES:")
        print("   1. Si queries >10s son lentas → optimizar InfluxDB")
        print("   2. Si no detecta gaps >10d → revisar lógica de comparación")
        print("   3. Si timeout → implementar chunking")

    except ImportError as e:
        print(f"❌ Error importando: {e}")
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_gap_detector())