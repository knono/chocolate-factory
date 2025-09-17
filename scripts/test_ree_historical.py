#!/usr/bin/env python3
"""
Test script para verificar que REE API funciona con fechas históricas
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the source directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'fastapi-app'))

from services.ree_client import REEClient

async def test_ree_historical():
    """Test REE API con fechas históricas específicas"""
    print("🧪 Testing REE API with historical dates...")

    # Fechas problemáticas detectadas
    test_dates = [
        datetime(2025, 9, 10, tzinfo=timezone.utc),  # 7 días atrás
        datetime(2025, 9, 8, tzinfo=timezone.utc),   # 9 días atrás
        datetime(2025, 9, 1, tzinfo=timezone.utc),   # 16 días atrás
        datetime(2025, 8, 15, tzinfo=timezone.utc),  # 1 mes atrás
    ]

    async with REEClient() as ree_client:
        for test_date in test_dates:
            end_date = test_date + timedelta(hours=23, minutes=59)

            try:
                print(f"\n📅 Testing: {test_date.strftime('%Y-%m-%d')} ({(datetime.now(timezone.utc) - test_date).days} days ago)")

                prices = await ree_client.get_pvpc_prices(
                    start_date=test_date,
                    end_date=end_date
                )

                if prices:
                    print(f"✅ SUCCESS: {len(prices)} records retrieved")
                    print(f"   First record: {prices[0].timestamp} - {prices[0].price_eur_mwh}€/MWh")
                    print(f"   Last record:  {prices[-1].timestamp} - {prices[-1].price_eur_mwh}€/MWh")
                else:
                    print("❌ FAIL: No data returned")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n🎯 Summary: REE API historical capability test completed")

if __name__ == "__main__":
    asyncio.run(test_ree_historical())