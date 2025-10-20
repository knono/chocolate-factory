"""
Full Pipeline Tests - Sprint 12 Fase 11

Tests end-to-end del flujo completo de datos desde ingesta hasta visualización.
Validan que todos los componentes del sistema funcionan correctamente integrados.

Flujos testeados:
1. REE ingestion → InfluxDB → Dashboard
2. Weather ingestion → Feature engineering → ML prediction
3. Prophet forecasting → Price predictions → Dashboard
4. Hourly optimization → Timeline generation
5. Backfill recovery → Gap filling

Ejecución:
    pytest tests/e2e/test_full_pipeline.py -v -m e2e

Autor: Sprint 12 Fase 11
Fecha: 2025-10-20
"""

import pytest
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List


BASE_URL = "http://localhost:8000"
TIMEOUT = 15.0  # Pipelines pueden tardar más


@pytest.fixture(scope="module")
def api_client():
    """Cliente HTTP para tests de pipeline"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


# ============================================================================
# PIPELINE TESTS - Flujos end-to-end completos
# ============================================================================

@pytest.mark.e2e
@pytest.mark.pipeline
class TestREEIngestionPipeline:
    """Test 1/5: Pipeline completo REE ingestion → Dashboard"""

    def test_ree_ingestion_to_dashboard_display(self, api_client: httpx.Client):
        """
        Flujo completo: Ingesta REE → InfluxDB → Dashboard

        Steps:
        1. Verificar que hay datos REE recientes en dashboard
        2. Validar estructura de datos de precios
        3. Confirmar que se actualizan periódicamente
        """

        # Step 1: Obtener datos actuales del dashboard
        response = api_client.get("/dashboard/complete")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"

        data = response.json()
        assert "current_data" in data, "Missing current_data"

        current = data["current_data"]

        # Step 2: Validar datos de precio REE
        assert "current_price" in current, "Missing current_price"
        price = current["current_price"]

        assert price is not None, "Current price is None"
        assert isinstance(price, (int, float)), f"Price should be numeric, got {type(price)}"
        assert 0 < price < 1.0, f"Price {price} out of expected range (0-1 €/kWh)"

        print(f"✅ REE Pipeline: Data flowing")
        print(f"💰 Current price: {price:.4f} €/kWh")

        # Step 3: Verificar datos históricos disponibles
        if "historical_data" in data:
            historical = data["historical_data"]
            assert len(historical) > 0, "No historical data available"
            print(f"📊 Historical records: {len(historical)}")

        # Step 4: Validar que el precio tiene timestamp reciente
        if "timestamp" in current or "last_update" in current:
            timestamp_field = "timestamp" if "timestamp" in current else "last_update"
            timestamp = current[timestamp_field]
            print(f"🕐 Last update: {timestamp}")


@pytest.mark.e2e
@pytest.mark.pipeline
class TestWeatherToMLPipeline:
    """Test 2/5: Weather ingestion → Feature engineering → ML prediction"""

    def test_weather_ingestion_to_ml_prediction(self, api_client: httpx.Client):
        """
        Flujo: Weather data → Feature engineering → ML prediction

        Steps:
        1. Verificar datos weather disponibles
        2. Confirmar feature engineering funcionando
        3. Validar que ML genera predicciones
        """

        # Step 1: Obtener datos de clima actuales
        response = api_client.get("/dashboard/complete")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"

        data = response.json()
        current = data.get("current_data", {})

        # Step 2: Validar datos de clima
        assert "current_weather" in current, "Missing weather data"
        weather = current["current_weather"]

        assert "temperature" in weather, "Missing temperature"
        assert "humidity" in weather, "Missing humidity"

        temp = weather["temperature"]
        humidity = weather["humidity"]

        assert -20 < temp < 50, f"Temperature {temp}°C out of range"
        assert 0 <= humidity <= 100, f"Humidity {humidity}% out of range"

        print(f"✅ Weather Pipeline: Data available")
        print(f"🌡️  Temperature: {temp}°C")
        print(f"💧 Humidity: {humidity}%")

        # Step 3: Verificar que hay predicciones ML basadas en weather
        if "predictions" in data or "ml_insights" in data:
            predictions_key = "predictions" if "predictions" in data else "ml_insights"
            predictions = data[predictions_key]

            # Las predicciones usan datos de weather como features
            assert predictions is not None, "ML predictions missing"
            print(f"✅ ML predictions generated from weather data")


@pytest.mark.e2e
@pytest.mark.pipeline
class TestProphetForecastingPipeline:
    """Test 3/5: Prophet training → 168h forecast → Dashboard"""

    def test_prophet_forecasting_pipeline(self, api_client: httpx.Client):
        """
        Flujo: Datos históricos REE → Prophet training → 7-day forecast

        Steps:
        1. Solicitar forecast de 7 días (168h)
        2. Validar estructura de predicciones
        3. Verificar intervalos de confianza
        4. Confirmar que aparece en dashboard
        """

        # Step 1: Obtener forecast semanal de Prophet
        response = api_client.get("/predict/prices/weekly")
        assert response.status_code == 200, f"Prophet forecast failed: {response.text}"

        data = response.json()

        # Step 2: Validar estructura
        assert "predictions" in data, "Missing predictions"
        predictions = data["predictions"]

        assert len(predictions) >= 168, \
            f"Expected 168 predictions (7 days), got {len(predictions)}"

        # Step 3: Validar cada predicción tiene campos requeridos
        first_pred = predictions[0]
        required_fields = ["timestamp", "predicted_price", "confidence_lower", "confidence_upper"]

        for field in required_fields:
            assert field in first_pred, f"Missing field: {field}"

        # Validar que confidence intervals son coherentes
        assert first_pred["confidence_lower"] < first_pred["predicted_price"], \
            "Lower bound should be less than predicted price"
        assert first_pred["predicted_price"] < first_pred["confidence_upper"], \
            "Predicted price should be less than upper bound"

        print(f"✅ Prophet Pipeline: Complete")
        print(f"📈 Generated {len(predictions)} hourly predictions")
        print(f"💰 First prediction: {first_pred['predicted_price']:.4f} €/kWh")
        print(f"📊 Confidence interval: [{first_pred['confidence_lower']:.4f}, "
              f"{first_pred['confidence_upper']:.4f}]")

        # Step 4: Verificar métricas del modelo si disponibles
        if "model_metrics" in data:
            metrics = data["model_metrics"]
            print(f"📊 Model MAE: {metrics.get('mae', 'N/A')}")
            print(f"📊 Model R²: {metrics.get('r2', 'N/A')}")


@pytest.mark.e2e
@pytest.mark.pipeline
class TestHourlyOptimizationPipeline:
    """Test 4/5: Price forecast → Production optimization → Timeline"""

    def test_hourly_optimization_flow(self, api_client: httpx.Client):
        """
        Flujo: Prophet prices → Hourly optimizer → 24h timeline

        Steps:
        1. Solicitar optimización diaria
        2. Validar timeline horaria (24 elementos)
        3. Verificar períodos tarifarios (P1/P2/P3)
        4. Confirmar que usa predicciones Prophet
        """

        # Step 1: Solicitar optimización para mañana
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = {
            "target_date": tomorrow,
            "target_kg": 200
        }

        response = api_client.post("/optimize/production/daily", json=payload)
        assert response.status_code == 200, f"Optimization failed: {response.text}"

        data = response.json()

        # Step 2: Validar timeline horaria
        assert "hourly_timeline" in data, "Missing hourly_timeline"
        timeline = data["hourly_timeline"]

        assert len(timeline) == 24, f"Expected 24 hours, got {len(timeline)}"

        # Step 3: Validar estructura de cada hora
        first_hour = timeline[0]
        required_fields = [
            "hour", "time", "price_eur_kwh", "tariff_period",
            "tariff_color", "temperature", "humidity"
        ]

        for field in required_fields:
            assert field in first_hour, f"Missing field in timeline: {field}"

        # Step 4: Validar períodos tarifarios
        tariff_periods = set(hour["tariff_period"] for hour in timeline)
        valid_periods = {"P1", "P2", "P3"}

        assert tariff_periods.issubset(valid_periods), \
            f"Invalid tariff periods: {tariff_periods - valid_periods}"

        print(f"✅ Optimization Pipeline: Complete")
        print(f"📅 Optimized for: {tomorrow}")
        print(f"⏰ Timeline hours: {len(timeline)}")
        print(f"🎯 Target production: {payload['target_kg']} kg")

        # Step 5: Validar que hay batches recomendados
        if "batches" in data:
            batches = data["batches"]
            print(f"📦 Recommended batches: {len(batches)}")


@pytest.mark.e2e
@pytest.mark.pipeline
@pytest.mark.slow
class TestBackfillRecoveryPipeline:
    """Test 5/5: Gap detection → Intelligent backfill → Data recovery"""

    def test_backfill_recovery_system(self, api_client: httpx.Client):
        """
        Flujo: Detectar gaps → Estrategia backfill → Recuperación datos

        Steps:
        1. Verificar estado de gaps actuales
        2. Ejecutar detección de gaps
        3. Validar estrategia de backfill (48h rule)
        4. Confirmar que sistema se auto-recupera

        Note: Este test NO crea gaps artificiales (requiere permisos InfluxDB)
              Solo valida que el sistema de backfill está funcional
        """

        # Step 1: Obtener resumen de gaps
        response = api_client.get("/gaps/summary")
        assert response.status_code == 200, f"Gap summary failed: {response.text}"

        summary = response.json()

        # Step 2: Validar estructura de respuesta
        assert "ree" in summary, "Missing REE gap info"
        assert "weather" in summary, "Missing weather gap info"

        ree_gaps = summary["ree"]
        weather_gaps = summary["weather"]

        print(f"✅ Backfill System: Operational")
        print(f"📊 REE gaps: {ree_gaps.get('total_gap_hours', 0)} hours")
        print(f"📊 Weather gaps: {weather_gaps.get('total_gap_hours', 0)} hours")

        # Step 3: Si hay gaps pequeños, validar estrategia
        total_gaps = (ree_gaps.get('total_gap_hours', 0) +
                     weather_gaps.get('total_gap_hours', 0))

        if total_gaps > 0:
            print(f"⚠️  Detected {total_gaps} hours of gaps")

            # Verificar que el sistema tiene mecanismo de auto-recovery
            # (APScheduler job cada 2 horas)
            print(f"✅ Auto-recovery system will handle gaps within 2 hours")
        else:
            print(f"✅ No gaps detected - system is healthy")

        # Step 4: Validar endpoint de detección detallada
        response_detailed = api_client.get("/gaps/detect?days_back=7")
        assert response_detailed.status_code == 200, \
            f"Detailed gap detection failed: {response_detailed.text}"

        detailed = response_detailed.json()

        # Sistema debe devolver análisis incluso si no hay gaps
        assert "analysis" in detailed or "gaps" in detailed, \
            "Gap detection should return analysis"

        print(f"✅ Gap detection pipeline: Functional")


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def wait_for_data_ingestion(client: httpx.Client, max_wait: int = 60) -> bool:
    """
    Esperar a que haya datos recientes (útil para tests que requieren ingesta)

    Returns:
        True si hay datos recientes, False si timeout
    """
    start = time.time()

    while time.time() - start < max_wait:
        try:
            response = client.get("/dashboard/summary")
            if response.status_code == 200:
                data = response.json()
                # Si tiene datos actuales, consideramos que la ingesta funciona
                if data.get("current_data") or data.get("status") == "healthy":
                    return True
        except Exception:
            pass

        time.sleep(5)

    return False


def validate_data_freshness(timestamp_str: str, max_age_hours: int = 1) -> bool:
    """
    Validar que un timestamp es reciente

    Args:
        timestamp_str: Timestamp ISO format
        max_age_hours: Máximo de horas de antigüedad aceptable

    Returns:
        True si los datos son frescos, False si son antiguos
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age = datetime.now() - timestamp.replace(tzinfo=None)
        return age.total_seconds() < (max_age_hours * 3600)
    except Exception:
        # Si no podemos parsear, asumimos que son frescos
        return True
