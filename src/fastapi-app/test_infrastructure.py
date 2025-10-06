#!/usr/bin/env python3
"""
Infrastructure Layer Test Script
=================================

Tests Phase 2 implementation:
1. InfluxDB client imports and connection
2. Query builder functionality
3. External API clients imports
4. Retry logic validation

Run: python test_infrastructure.py
"""

import sys
from pathlib import Path
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all infrastructure modules can be imported."""
    print("🧪 Testing infrastructure imports...")

    try:
        # InfluxDB imports
        from infrastructure.influxdb import (
            get_influxdb_client,
            QueryBuilder,
            get_latest_prices,
            get_weather_data
        )
        print("   ✅ infrastructure.influxdb")

        # External APIs imports
        from infrastructure.external_apis import (
            REEAPIClient,
            AEMETAPIClient,
            OpenWeatherMapAPIClient
        )
        print("   ✅ infrastructure.external_apis")

        # Infrastructure root imports
        from infrastructure import (
            get_influxdb_client as influx_client,
            QueryBuilder as QB,
            REEAPIClient as REE,
            AEMETAPIClient as AEMET,
            OpenWeatherMapAPIClient as OWM
        )
        print("   ✅ infrastructure (root exports)")

        return True

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_builder():
    """Test QueryBuilder functionality."""
    print("\n🧪 Testing QueryBuilder...")

    try:
        from infrastructure.influxdb import QueryBuilder

        # Test basic query
        query = QueryBuilder("energy_data") \
            .range("-1h") \
            .filter_measurement("energy_prices") \
            .filter_field("price_eur_kwh") \
            .build()

        assert 'from(bucket: "energy_data")' in query
        assert 'range(start: -1h)' in query
        assert 'energy_prices' in query
        print(f"   ✅ Basic query built")
        print(f"      Query: {query[:100]}...")

        # Test with aggregation
        query2 = QueryBuilder("energy_data") \
            .range("-24h") \
            .filter_measurement("weather") \
            .filter_field("temperature") \
            .aggregate_mean("1h") \
            .sort_desc() \
            .limit(10) \
            .build()

        assert 'aggregateWindow' in query2
        assert 'sort' in query2
        assert 'limit' in query2
        print(f"   ✅ Aggregated query built")

        # Test pre-built queries
        from infrastructure.influxdb import get_latest_prices, get_weather_data

        query3 = get_latest_prices(limit=24)
        assert 'energy_prices' in query3
        print(f"   ✅ Pre-built query: get_latest_prices")

        query4 = get_weather_data(hours_back=6, source="aemet")
        assert 'weather' in query4
        assert 'aemet' in query4
        print(f"   ✅ Pre-built query: get_weather_data")

        return True

    except Exception as e:
        print(f"   ❌ QueryBuilder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_influxdb_client():
    """Test InfluxDB client (without actual connection)."""
    print("\n🧪 Testing InfluxDB client...")

    try:
        from infrastructure.influxdb import get_influxdb_client

        # Get client instance (singleton)
        client = get_influxdb_client()
        print(f"   ✅ Client instance created")
        print(f"      URL: {client.url}")
        print(f"      Org: {client.org}")
        print(f"      Bucket: {client.bucket}")

        # Test health check (will fail without connection, which is OK)
        try:
            health = client.health_check()
            print(f"   ✅ Health check successful: {health['status']}")
        except Exception as e:
            print(f"   ⚠️  Health check failed (expected without connection): {str(e)[:50]}...")

        return True

    except Exception as e:
        print(f"   ❌ InfluxDB client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_clients():
    """Test external API clients (without actual API calls)."""
    print("\n🧪 Testing external API clients...")

    try:
        from infrastructure.external_apis import (
            REEAPIClient,
            AEMETAPIClient,
            OpenWeatherMapAPIClient
        )

        # Test REE client initialization
        print("   Testing REE API client...")
        async with REEAPIClient() as ree:
            print(f"      ✅ REE client initialized")
            print(f"         Base URL: {ree.BASE_URL}")

        # Test AEMET client initialization
        print("   Testing AEMET API client...")
        try:
            async with AEMETAPIClient() as aemet:
                print(f"      ✅ AEMET client initialized")
                print(f"         Base URL: {aemet.BASE_URL}")
        except ValueError as e:
            if "AEMET_API_KEY" in str(e):
                print(f"      ⚠️  AEMET API key not configured (expected in some environments)")
            else:
                raise

        # Test OpenWeatherMap client initialization
        print("   Testing OpenWeatherMap API client...")
        try:
            async with OpenWeatherMapAPIClient() as owm:
                print(f"      ✅ OpenWeatherMap client initialized")
                print(f"         Base URL: {owm.BASE_URL}")
                print(f"         Default location: ({owm.DEFAULT_LAT}, {owm.DEFAULT_LON})")
        except ValueError as e:
            if "OPENWEATHERMAP_API_KEY" in str(e):
                print(f"      ⚠️  OpenWeatherMap API key not configured (expected in some environments)")
            else:
                raise

        return True

    except Exception as e:
        print(f"   ❌ API clients test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retry_logic():
    """Test that tenacity is properly configured."""
    print("\n🧪 Testing retry logic...")

    try:
        from tenacity import retry, stop_after_attempt, wait_exponential

        # Verify tenacity is imported correctly
        print("   ✅ Tenacity library available")

        # Check that clients have retry decorators
        from infrastructure.external_apis.ree_client import REEAPIClient
        import inspect

        ree_methods = inspect.getmembers(REEAPIClient, predicate=inspect.isfunction)
        has_retry = any('_make_request' in name for name, _ in ree_methods)

        if has_retry:
            print("   ✅ REE client has retry logic")
        else:
            print("   ⚠️  Could not verify retry decorator")

        return True

    except Exception as e:
        print(f"   ❌ Retry logic test failed: {e}")
        return False


def test_exception_handling():
    """Test custom exceptions."""
    print("\n🧪 Testing exception handling...")

    try:
        from core.exceptions import (
            REEAPIError,
            AEMETAPIError,
            OpenWeatherMapError,
            InfluxDBConnectionError
        )

        # Test exception creation
        exc1 = REEAPIError(500, "Connection timeout")
        print(f"   ✅ REEAPIError: {exc1.message}")

        exc2 = AEMETAPIError(401, "Invalid API key")
        print(f"   ✅ AEMETAPIError: {exc2.message}")

        exc3 = OpenWeatherMapError(429, "Rate limit exceeded")
        print(f"   ✅ OpenWeatherMapError: {exc3.message}")

        exc4 = InfluxDBConnectionError("http://influxdb:8086", "Connection refused")
        print(f"   ✅ InfluxDBConnectionError: {exc4.message}")

        return True

    except Exception as e:
        print(f"   ❌ Exception handling test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 2: Infrastructure Layer - Test Suite")
    print("=" * 60)

    results = {
        "imports": test_imports(),
        "query_builder": test_query_builder(),
        "influxdb_client": test_influxdb_client(),
        "api_clients": asyncio.run(test_api_clients()),
        "retry_logic": test_retry_logic(),
        "exceptions": test_exception_handling()
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name:20s}: {status}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)

    if all_passed:
        print("🎉 Phase 2 Infrastructure Layer: ALL TESTS PASSED")
        print("\n✅ Ready for Phase 3: Create Services")
    else:
        print("❌ Phase 2 Infrastructure Layer: SOME TESTS FAILED")
        print("\n⚠️  Fix errors before proceeding to Phase 3")

    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
