#!/usr/bin/env python3
"""
Foundation Setup Test Script
=============================

Tests Phase 1 implementation:
1. Config loading
2. Logging setup
3. Exception handling
4. Dependency injection (without actual connections)
5. Directory structure

Run: python test_foundation.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all foundation modules can be imported."""
    print("🧪 Testing imports...")

    try:
        from core.config import settings
        print(f"   ✅ core.config: {settings}")

        from core.logging_config import setup_logging, get_logger
        print(f"   ✅ core.logging_config")

        from core.exceptions import (
            ChocolateFactoryException,
            ModelNotFoundError,
            REEAPIError,
            DataGapError
        )
        print(f"   ✅ core.exceptions")

        # Note: dependencies.py will fail without InfluxDB connection
        # We'll test the structure only
        import dependencies
        print(f"   ✅ dependencies (structure)")

        from tasks.scheduler_config import register_all_jobs
        print(f"   ✅ tasks.scheduler_config")

    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\n🧪 Testing configuration...")

    try:
        from core.config import settings

        print(f"   Environment: {settings.ENVIRONMENT}")
        print(f"   InfluxDB URL: {settings.INFLUXDB_URL}")
        print(f"   InfluxDB Org: {settings.INFLUXDB_ORG}")
        print(f"   ML Models Dir: {settings.ML_MODELS_DIR}")
        print(f"   Sprint 06 Enabled: {settings.SPRINT06_ENABLED}")
        print(f"   Sprint 07 Enabled: {settings.SPRINT07_ENABLED}")
        print(f"   Sprint 08 Enabled: {settings.SPRINT08_ENABLED}")

        # Test validation
        assert settings.INFLUXDB_TOKEN, "INFLUXDB_TOKEN not set"
        assert settings.AEMET_API_KEY, "AEMET_API_KEY not set"

        print("   ✅ Configuration valid")
        return True

    except Exception as e:
        print(f"   ❌ Config test failed: {e}")
        return False


def test_logging():
    """Test logging setup."""
    print("\n🧪 Testing logging...")

    try:
        from core.logging_config import get_logger, PerformanceLogger

        logger = get_logger(__name__)
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        # Test performance logger
        with PerformanceLogger("test_operation"):
            import time
            time.sleep(0.1)

        print("   ✅ Logging works")
        return True

    except Exception as e:
        print(f"   ❌ Logging test failed: {e}")
        return False


def test_exceptions():
    """Test custom exceptions."""
    print("\n🧪 Testing exceptions...")

    try:
        from core.exceptions import (
            ModelNotFoundError,
            REEAPIError,
            DataGapError,
            to_http_exception
        )

        # Test exception creation
        exc1 = ModelNotFoundError("prophet", "/models/prophet.pkl")
        print(f"   Model error: {exc1.message}")
        print(f"   Error dict: {exc1.to_dict()}")

        exc2 = REEAPIError(500, "Connection timeout")
        print(f"   API error: {exc2.message}")

        exc3 = DataGapError("REE", "2025-10-01", "2025-10-02", 24.0)
        print(f"   Gap error: {exc3.message}")

        # Test HTTP conversion
        http_exc = to_http_exception(exc1)
        print(f"   HTTP status: {http_exc.status_code}")

        print("   ✅ Exceptions work")
        return True

    except Exception as e:
        print(f"   ❌ Exception test failed: {e}")
        return False


def test_directory_structure():
    """Test directory structure."""
    print("\n🧪 Testing directory structure...")

    required_dirs = [
        "api",
        "api/routers",
        "api/schemas",
        "domain",
        "domain/energy",
        "domain/weather",
        "domain/ml",
        "infrastructure",
        "infrastructure/influxdb",
        "infrastructure/external_apis",
        "infrastructure/ml_storage",
        "core",
        "tasks"
    ]

    base_path = Path(__file__).parent
    all_exist = True

    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            print(f"   ✅ {dir_path}")
        else:
            print(f"   ❌ {dir_path} (missing)")
            all_exist = False

    if all_exist:
        print("   ✅ Directory structure complete")
    else:
        print("   ❌ Some directories missing")

    return all_exist


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1: Foundation Setup - Test Suite")
    print("=" * 60)

    results = {
        "imports": test_imports(),
        "config": test_config(),
        "logging": test_logging(),
        "exceptions": test_exceptions(),
        "structure": test_directory_structure()
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name:15s}: {status}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)

    if all_passed:
        print("🎉 Phase 1 Foundation Setup: ALL TESTS PASSED")
        print("\n✅ Ready for Phase 2: Extract Infrastructure")
    else:
        print("❌ Phase 1 Foundation Setup: SOME TESTS FAILED")
        print("\n⚠️  Fix errors before proceeding to Phase 2")

    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
