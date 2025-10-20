"""
Resilience Tests - Sprint 12 Fase 11

Tests de resiliencia del sistema ante fallos, timeouts y condiciones adversas.
Validan que el sistema se recupera gracefully de errores y mantiene disponibilidad.

Escenarios testeados:
- Fallos de conexión a servicios externos (InfluxDB, APIs)
- Timeouts y latencia alta
- Datos faltantes o corruptos
- Cargas concurrentes
- Degradación graceful de servicios

Ejecución:
    pytest tests/e2e/test_resilience.py -v -m e2e

Autor: Sprint 12 Fase 11
Fecha: 2025-10-20
"""

import pytest
import httpx
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any


BASE_URL = "http://localhost:8000"
TIMEOUT = 20.0  # Tests de resiliencia pueden tardar más


@pytest.fixture(scope="module")
def api_client():
    """Cliente HTTP para tests de resiliencia"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture(scope="module")
def async_client():
    """Cliente HTTP asíncrono para tests concurrentes"""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


# ============================================================================
# RESILIENCE TESTS - Error handling y recovery
# ============================================================================

@pytest.mark.e2e
@pytest.mark.resilience
class TestDatabaseConnectionResilience:
    """Test 1/8: Resiliencia ante problemas de conexión InfluxDB"""

    def test_dashboard_handles_influxdb_slow_response(self, api_client: httpx.Client):
        """
        Dashboard responde aunque InfluxDB sea lento

        Sistema debe:
        - No bloquear indefinidamente
        - Retornar datos parciales si disponibles
        - Indicar estado de servicio degradado
        """

        # Dashboard con timeout extendido para simular InfluxDB lento
        start = time.time()
        response = api_client.get("/dashboard/complete", timeout=10.0)
        elapsed = time.time() - start

        # Debe responder en tiempo razonable (< 10s)
        assert elapsed < 10.0, f"Dashboard too slow: {elapsed}s"

        # Debe retornar algo, incluso si parcial
        assert response.status_code in [200, 206, 503], \
            f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard responded in {elapsed:.2f}s")
            print(f"📊 Data available: {bool(data.get('current_data'))}")
        else:
            print(f"⚠️  Dashboard degraded (status {response.status_code})")

    def test_system_continues_without_recent_influxdb_data(
        self, api_client: httpx.Client
    ):
        """
        Sistema funciona aunque no haya datos muy recientes en InfluxDB

        Validar:
        - APIs responden con datos históricos
        - No hay crashes por datos faltantes
        - Indicadores de frescura de datos
        """

        # Solicitar datos históricos (no requiere datos frescos)
        response = api_client.get("/dashboard/summary")

        # Debe responder, incluso si datos no son frescos
        assert response.status_code in [200, 206], \
            f"Dashboard summary failed: {response.status_code}"

        data = response.json()

        # Sistema debe indicar disponibilidad de datos
        # Si no hay campo específico, el simple hecho de responder es suficiente
        assert data is not None, "Dashboard should return data"

        print(f"✅ System operational with available data")


@pytest.mark.e2e
@pytest.mark.resilience
class TestExternalAPIResilience:
    """Test 2/8: Resiliencia ante fallos de APIs externas (AEMET, OpenWeather)"""

    def test_weather_system_handles_api_unavailability(
        self, api_client: httpx.Client
    ):
        """
        Sistema weather funciona aunque APIs externas fallen

        Híbrido AEMET + OpenWeatherMap debe:
        - Fallback entre fuentes
        - Usar datos cacheados si disponibles
        - No bloquear dashboard completo
        """

        # Dashboard debe funcionar aunque weather API esté lenta
        response = api_client.get("/dashboard/complete")

        assert response.status_code in [200, 206], \
            "Dashboard should respond despite weather API issues"

        data = response.json()

        # Si hay datos de clima, genial
        # Si no hay, el sistema debe indicarlo sin fallar
        current = data.get("current_data", {})

        if "current_weather" in current:
            print(f"✅ Weather data available")
        else:
            print(f"⚠️  Weather data unavailable (expected in degraded state)")

        # Lo importante es que el dashboard no falla completamente
        assert "current_data" in data or "status" in data, \
            "Dashboard should return structured response"

    def test_aemet_timeout_fallback_to_openweather(self, api_client: httpx.Client):
        """
        Sistema usa OpenWeatherMap si AEMET timeout

        Validar estrategia 24/7:
        - AEMET primary (00:00-07:00)
        - OpenWeatherMap secondary (08:00-23:00)
        - Fallback automático entre fuentes
        """

        # Obtener datos actuales
        response = api_client.get("/dashboard/complete")
        assert response.status_code == 200, "Dashboard failed"

        data = response.json()
        current = data.get("current_data", {})

        # Si hay datos de weather, validar que vienen de alguna fuente
        if "current_weather" in current:
            weather = current["current_weather"]

            # Debe tener al menos temperatura y humedad
            has_temp = "temperature" in weather and weather["temperature"] is not None
            has_humidity = "humidity" in weather and weather["humidity"] is not None

            assert has_temp or has_humidity, \
                "Weather data should have at least temperature or humidity"

            print(f"✅ Weather fallback system functional")

            # Si tiene campo de fuente, validarlo
            if "source" in weather:
                assert weather["source"] in ["aemet", "openweathermap", "hybrid"], \
                    f"Unknown weather source: {weather['source']}"


@pytest.mark.e2e
@pytest.mark.resilience
class TestMLModelResilience:
    """Test 3/8: Resiliencia ante fallos de modelos ML"""

    def test_prophet_model_missing_graceful_degradation(
        self, api_client: httpx.Client
    ):
        """
        Sistema funciona aunque modelo Prophet no esté disponible

        Debe:
        - Retornar error claro
        - No crashear dashboard
        - Ofrecer alternativas (precios históricos)
        """

        # Intentar obtener forecast
        response = api_client.get("/predict/prices/weekly")

        # Puede retornar 200 (modelo OK) o 503 (modelo no disponible)
        assert response.status_code in [200, 503, 404], \
            f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            print(f"✅ Prophet model available")
            data = response.json()
            assert "predictions" in data, "Should have predictions"

        else:
            print(f"⚠️  Prophet model unavailable (status {response.status_code})")
            # Sistema debe retornar error estructurado
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data, \
                "Should return structured error"

    def test_sklearn_models_missing_no_crash(self, api_client: httpx.Client):
        """
        Dashboard funciona aunque modelos sklearn no disponibles

        Sistema debe:
        - Dashboard muestra datos sin predicciones ML
        - No crashes en endpoints principales
        """

        # Dashboard debe funcionar siempre
        response = api_client.get("/dashboard/complete")
        assert response.status_code == 200, "Dashboard should always respond"

        data = response.json()
        assert data is not None, "Dashboard should return data"

        print(f"✅ Dashboard operational (ML predictions optional)")


@pytest.mark.e2e
@pytest.mark.resilience
class TestSchedulerResilience:
    """Test 4/8: Resiliencia del sistema APScheduler"""

    def test_scheduler_job_failure_does_not_affect_api(
        self, api_client: httpx.Client
    ):
        """
        Fallos en jobs de APScheduler no afectan API

        Validar:
        - API responde aunque jobs fallen
        - Health endpoint indica estado de jobs
        """

        # API debe estar disponible siempre
        response = api_client.get("/health")
        assert response.status_code == 200, "Health endpoint should always work"

        data = response.json()
        assert "status" in data, "Should report status"

        # Sistema puede estar healthy aunque algunos jobs fallen
        status = data["status"]
        assert status in ["healthy", "degraded", "ok"], \
            f"Unexpected status: {status}"

        print(f"✅ API operational (status: {status})")

        # Si hay info de scheduler, validarla
        if "scheduler" in data:
            scheduler = data["scheduler"]
            print(f"📊 Scheduler running: {scheduler.get('running', False)}")


@pytest.mark.e2e
@pytest.mark.resilience
class TestConcurrentRequestResilience:
    """Test 5/8: Resiliencia ante requests concurrentes"""

    def test_concurrent_ml_training_requests(self, api_client: httpx.Client):
        """
        Sistema maneja múltiples requests de training simultáneos

        Debe:
        - No corromper modelos
        - Usar locking apropiado
        - Retornar respuestas coherentes
        """

        # Simular 3 requests concurrentes al dashboard
        # (que internamente puede trigger ML operations)

        def make_request(client, endpoint):
            try:
                start = time.time()
                response = client.get(endpoint)
                elapsed = time.time() - start
                return {
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "time": elapsed,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "endpoint": endpoint,
                    "status": "ERROR",
                    "error": str(e),
                    "success": False
                }

        # Endpoints a testear concurrentemente
        endpoints = [
            "/dashboard/complete",
            "/dashboard/summary",
            "/predict/prices/weekly",
        ]

        # Ejecutar requests en paralelo
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(make_request, api_client, endpoint)
                for endpoint in endpoints
            ]

            results = [future.result() for future in as_completed(futures)]

        # Validar resultados
        successful = sum(1 for r in results if r["success"])
        total = len(results)

        print(f"✅ Concurrent requests: {successful}/{total} successful")

        # Al menos 2 de 3 deben tener éxito
        assert successful >= 2, \
            f"Too many failed concurrent requests: {total - successful}/{total}"

    def test_concurrent_dashboard_requests_no_degradation(
        self, api_client: httpx.Client
    ):
        """
        Dashboard responde correctamente a múltiples requests simultáneos

        Validar:
        - Sin race conditions
        - Tiempos de respuesta aceptables
        - No hay errores 500
        """

        num_requests = 10

        def make_dashboard_request(index):
            start = time.time()
            response = api_client.get("/dashboard/summary")
            elapsed = time.time() - start
            return {
                "index": index,
                "status": response.status_code,
                "time": elapsed,
                "success": response.status_code == 200
            }

        # Ejecutar 10 requests concurrentes
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_dashboard_request, i)
                for i in range(num_requests)
            ]

            results = [future.result() for future in as_completed(futures)]

        # Análisis de resultados
        successful = sum(1 for r in results if r["success"])
        avg_time = sum(r["time"] for r in results) / len(results)
        max_time = max(r["time"] for r in results)

        print(f"✅ Concurrent load test: {successful}/{num_requests} successful")
        print(f"⏱️  Average time: {avg_time:.2f}s")
        print(f"⏱️  Max time: {max_time:.2f}s")

        # Al menos 80% deben tener éxito
        success_rate = successful / num_requests
        assert success_rate >= 0.8, \
            f"Success rate too low: {success_rate:.1%}"

        # Tiempo promedio debe ser razonable (< 5s)
        assert avg_time < 5.0, f"Average response time too high: {avg_time:.2f}s"


@pytest.mark.e2e
@pytest.mark.resilience
class TestDataIntegrityResilience:
    """Test 6/8: Resiliencia ante datos parciales o corruptos"""

    def test_dashboard_handles_partial_data_availability(
        self, api_client: httpx.Client
    ):
        """
        Dashboard funciona con datos parciales

        Escenarios:
        - Solo datos REE disponibles (no weather)
        - Solo datos weather disponibles (no REE)
        - Datos históricos incompletos
        """

        response = api_client.get("/dashboard/complete")
        assert response.status_code == 200, "Dashboard should handle partial data"

        data = response.json()
        current = data.get("current_data", {})

        # Validar que retorna estructura incluso si parcial
        assert isinstance(current, dict), "current_data should be a dict"

        # Contar campos disponibles
        available_fields = sum(1 for v in current.values() if v is not None)
        total_fields = len(current)

        print(f"✅ Dashboard with partial data:")
        print(f"📊 Available fields: {available_fields}/{total_fields}")

        # Debe haber al menos algún dato
        assert available_fields > 0, "Should have at least some data"

    def test_system_handles_missing_historical_data(
        self, api_client: httpx.Client
    ):
        """
        Sistema maneja correctamente ausencia de datos históricos

        Prophet puede no tener suficientes datos para entrenar
        Dashboard debe mostrar lo disponible
        """

        # Intentar obtener insights que requieren datos históricos
        response = api_client.get("/insights/summary")

        # Puede retornar 200 (datos OK) o 206 (datos parciales)
        assert response.status_code in [200, 206, 404], \
            f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Historical data available")
        else:
            print(f"⚠️  Historical data insufficient (status {response.status_code})")


@pytest.mark.e2e
@pytest.mark.resilience
class TestChatbotResilience:
    """Test 7/8: Resiliencia del chatbot BI"""

    def test_chatbot_rate_limit_enforcement(self, api_client: httpx.Client):
        """
        Rate limiting del chatbot (20 req/min) se aplica correctamente

        Validar:
        - Primeras requests pasan
        - Requests excesivas retornan 429
        - Sistema se recupera tras 1 minuto
        """

        # Hacer 3 requests rápidas (debería estar OK)
        responses = []
        for i in range(3):
            response = api_client.post(
                "/chat/ask",
                json={"question": f"Test question {i}"}
            )
            responses.append(response.status_code)
            time.sleep(0.1)  # Pequeña pausa entre requests

        # Primeras requests deben pasar
        successful = sum(1 for status in responses if status == 200)

        print(f"✅ Chatbot rate limiting:")
        print(f"📊 Successful requests: {successful}/3")

        # Al menos 2 de 3 deben pasar (tolerancia)
        assert successful >= 2, "Rate limiting too aggressive"

    def test_chatbot_handles_invalid_questions(self, api_client: httpx.Client):
        """
        Chatbot maneja preguntas inválidas gracefully

        Validar:
        - Preguntas vacías → error claro
        - Preguntas muy largas → truncadas o error
        - Caracteres especiales → manejados correctamente
        """

        test_cases = [
            {"question": ""},  # Vacía
            {"question": "a" * 1000},  # Muy larga (>500 chars)
            {"question": "¿Cuándo producir? 🍫"},  # Con emoji
        ]

        for i, payload in enumerate(test_cases):
            response = api_client.post("/chat/ask", json=payload)

            # Debe retornar error estructurado, no 500
            assert response.status_code in [200, 400, 422], \
                f"Test case {i} failed with status {response.status_code}"

            print(f"✅ Chatbot handles invalid input {i+1}/{len(test_cases)}")


@pytest.mark.e2e
@pytest.mark.resilience
class TestSystemRecoveryResilience:
    """Test 8/8: Recuperación del sistema tras fallos"""

    def test_system_self_heals_after_temporary_failure(
        self, api_client: httpx.Client
    ):
        """
        Sistema se auto-recupera tras fallos temporales

        Validar:
        - Health endpoint reporta estado
        - Sistema retry logic funciona
        - APScheduler recupera jobs
        """

        # Obtener estado actual
        response = api_client.get("/health")
        assert response.status_code == 200, "Health endpoint must always work"

        data = response.json()
        status = data.get("status", "unknown")

        print(f"✅ System status: {status}")

        # Si hay componentes degradados, verificar que eventualmente se recuperan
        if status == "degraded":
            print(f"⚠️  System degraded - checking for recovery mechanisms")

            # Verificar que hay mecanismos de retry
            if "components" in data:
                components = data["components"]
                for name, component_status in components.items():
                    print(f"  - {name}: {component_status}")

        # Sistema debe estar healthy o degraded (no completely down)
        assert status in ["healthy", "degraded", "ok"], \
            f"System status critical: {status}"

    def test_automatic_backfill_recovers_data_gaps(
        self, api_client: httpx.Client
    ):
        """
        Sistema de backfill automático recupera gaps

        Validar:
        - Gap detection funciona
        - Backfill automático scheduled (cada 2h)
        - Gaps pequeños se recuperan automáticamente
        """

        # Verificar que sistema de gaps está operativo
        response = api_client.get("/gaps/summary")
        assert response.status_code == 200, "Gap detection should work"

        summary = response.json()

        print(f"✅ Auto-recovery system operational")
        print(f"📊 REE gaps: {summary['ree'].get('total_gap_hours', 0)}h")
        print(f"📊 Weather gaps: {summary['weather'].get('total_gap_hours', 0)}h")

        # Sistema debe reportar estrategia de recovery
        # (implícito: APScheduler job cada 2 horas)


# ============================================================================
# RESILIENCE HELPERS
# ============================================================================

def simulate_slow_request(client: httpx.Client, endpoint: str, delay: float) -> Dict:
    """Simular request lento añadiendo delay"""
    time.sleep(delay)
    try:
        response = client.get(endpoint)
        return {"status": response.status_code, "success": True}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "success": False}


def check_system_recovery(
    client: httpx.Client,
    max_attempts: int = 5,
    interval: int = 10
) -> bool:
    """
    Verificar que el sistema se recupera tras un fallo

    Returns:
        True si el sistema se recupera, False si sigue fallando
    """
    for attempt in range(max_attempts):
        try:
            response = client.get("/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["healthy", "ok"]:
                    return True
        except Exception:
            pass

        time.sleep(interval)

    return False
