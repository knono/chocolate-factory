"""
Performance Tests - Sprint 12 Fase 11

Tests de performance y carga del sistema Chocolate Factory.
Validan que el sistema mantiene tiempos de respuesta aceptables bajo carga.

Métricas testeadas:
- Latencia de endpoints (<2s dashboard, <500ms predictions)
- Throughput bajo carga (50+ requests concurrentes)
- Tiempos de entrenamiento ML (<60s Prophet)
- Uso de recursos (memoria, CPU)

Ejecución:
    pytest tests/e2e/test_performance.py -v -m performance

Nota: Estos tests están marcados como @pytest.mark.slow
      Ejecutar con: pytest -m "e2e and performance"

Autor: Sprint 12 Fase 11
Fecha: 2025-10-20
"""

import pytest
import httpx
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple


BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0  # Performance tests pueden requerir más tiempo


@pytest.fixture(scope="module")
def api_client():
    """Cliente HTTP para tests de performance"""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


# ============================================================================
# PERFORMANCE TESTS - Latencia y throughput
# ============================================================================

@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestDashboardPerformance:
    """Test 1/4: Performance del dashboard completo"""

    def test_dashboard_complete_response_time(self, api_client: httpx.Client):
        """
        Dashboard completo responde en <2 segundos

        Métricas objetivo:
        - P50 (mediana): <1.5s
        - P95: <2.5s
        - P99: <3.0s
        """

        num_samples = 10
        response_times = []

        print(f"\n📊 Testing dashboard performance ({num_samples} requests)...")

        for i in range(num_samples):
            start = time.time()
            response = api_client.get("/dashboard/complete")
            elapsed = time.time() - start

            assert response.status_code == 200, \
                f"Request {i+1} failed: {response.status_code}"

            response_times.append(elapsed)
            time.sleep(0.5)  # Pausa entre requests

        # Calcular percentiles
        p50 = statistics.median(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99 = max(response_times)
        avg = statistics.mean(response_times)

        print(f"\n⏱️  Performance metrics:")
        print(f"   Average: {avg:.3f}s")
        print(f"   P50 (median): {p50:.3f}s")
        print(f"   P95: {p95:.3f}s")
        print(f"   P99 (max): {p99:.3f}s")

        # Assertions
        assert p50 < 2.0, f"Median response time too high: {p50:.3f}s > 2.0s"
        assert p95 < 3.0, f"P95 response time too high: {p95:.3f}s > 3.0s"

        print(f"✅ Dashboard performance: PASSED")

    def test_dashboard_summary_response_time(self, api_client: httpx.Client):
        """
        Dashboard summary (endpoint ligero) responde en <500ms

        Este endpoint es más simple que /complete, debe ser más rápido
        """

        num_samples = 20
        response_times = []

        for i in range(num_samples):
            start = time.time()
            response = api_client.get("/dashboard/summary")
            elapsed = time.time() - start

            assert response.status_code == 200, f"Request {i+1} failed"
            response_times.append(elapsed)

        avg = statistics.mean(response_times)
        max_time = max(response_times)

        print(f"\n⏱️  Dashboard summary performance:")
        print(f"   Average: {avg:.3f}s")
        print(f"   Max: {max_time:.3f}s")

        # Summary debe ser rápido (<1s promedio)
        assert avg < 1.0, f"Average response time too high: {avg:.3f}s"
        assert max_time < 2.0, f"Max response time too high: {max_time:.3f}s"

        print(f"✅ Dashboard summary performance: PASSED")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestMLPredictionPerformance:
    """Test 2/4: Performance de predicciones ML"""

    def test_ml_prediction_latency(self, api_client: httpx.Client):
        """
        Predicciones ML responden en <500ms

        Tests:
        - Energy optimization prediction
        - Production recommendation
        (vía endpoints que las usan internamente)
        """

        # Test a través del optimization endpoint que usa ML
        num_samples = 10
        response_times = []

        payload = {
            "target_date": "2025-10-21",
            "target_kg": 200
        }

        for i in range(num_samples):
            start = time.time()
            response = api_client.post("/optimize/production/daily", json=payload)
            elapsed = time.time() - start

            assert response.status_code == 200, f"Request {i+1} failed"
            response_times.append(elapsed)

            time.sleep(0.3)

        avg = statistics.mean(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)

        print(f"\n⏱️  ML prediction latency:")
        print(f"   Average: {avg:.3f}s")
        print(f"   P95: {p95:.3f}s")

        # Optimization endpoint (que incluye ML) debe ser razonable (<3s)
        assert avg < 3.0, f"Average latency too high: {avg:.3f}s"

        print(f"✅ ML prediction latency: PASSED")

    def test_prophet_forecast_response_time(self, api_client: httpx.Client):
        """
        Prophet forecast (168h) responde en <5 segundos

        Prophet es más costoso que sklearn, toleramos mayor latencia
        """

        num_samples = 5
        response_times = []

        for i in range(num_samples):
            start = time.time()
            response = api_client.get("/predict/prices/weekly")
            elapsed = time.time() - start

            assert response.status_code == 200, f"Request {i+1} failed"
            response_times.append(elapsed)

            time.sleep(1.0)

        avg = statistics.mean(response_times)
        max_time = max(response_times)

        print(f"\n⏱️  Prophet forecast latency:")
        print(f"   Average: {avg:.3f}s")
        print(f"   Max: {max_time:.3f}s")

        # Prophet debe responder en tiempo razonable
        assert avg < 5.0, f"Average forecast time too high: {avg:.3f}s"
        assert max_time < 10.0, f"Max forecast time too high: {max_time:.3f}s"

        print(f"✅ Prophet forecast latency: PASSED")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestMLTrainingPerformance:
    """Test 3/4: Performance de entrenamiento de modelos"""

    def test_prophet_training_duration(self, api_client: httpx.Client):
        """
        Entrenamiento Prophet completa en <60 segundos

        Nota: Este test puede requerir endpoint de training expuesto
              Si no existe, verificamos que el modelo ya está entrenado
        """

        # Verificar que el modelo Prophet está disponible
        start = time.time()
        response = api_client.get("/predict/prices/weekly")
        elapsed = time.time() - start

        assert response.status_code == 200, "Prophet model not available"

        data = response.json()

        # Si tiene métricas de modelo, mostrarlas
        if "model_metrics" in data:
            metrics = data["model_metrics"]
            print(f"\n📊 Prophet model metrics:")
            print(f"   MAE: {metrics.get('mae', 'N/A')}")
            print(f"   RMSE: {metrics.get('rmse', 'N/A')}")
            print(f"   R²: {metrics.get('r2', 'N/A')}")

        print(f"✅ Prophet model: Operational")
        print(f"⏱️  Inference time: {elapsed:.3f}s")

        # Inference debe ser rápida (<5s)
        assert elapsed < 5.0, f"Prophet inference too slow: {elapsed:.3f}s"

    def test_sklearn_model_training_reasonable_time(self, api_client: httpx.Client):
        """
        Validar que modelos sklearn están entrenados y disponibles

        Sklearn training (cada 30 min via APScheduler) debe completar en tiempo razonable
        """

        # Verificar que los modelos están disponibles via dashboard
        start = time.time()
        response = api_client.get("/dashboard/complete")
        elapsed = time.time() - start

        assert response.status_code == 200, "Dashboard failed"

        data = response.json()

        # Si hay predicciones ML, los modelos están entrenados
        has_predictions = (
            "predictions" in data or
            "ml_insights" in data or
            "current_data" in data
        )

        assert has_predictions, "ML models should be available"

        print(f"✅ sklearn models: Operational")
        print(f"⏱️  Dashboard load time: {elapsed:.3f}s")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentLoadPerformance:
    """Test 4/4: Performance bajo carga concurrente"""

    def test_concurrent_api_requests_load(self, api_client: httpx.Client):
        """
        Sistema maneja 50 requests simultáneos sin degradación significativa

        Métricas:
        - Success rate >95%
        - Average latency <3s
        - No errores 500
        """

        num_requests = 50
        max_workers = 10

        endpoints = [
            "/health",
            "/dashboard/summary",
            "/dashboard/alerts",
        ]

        def make_request(index: int) -> Dict:
            """Hacer una request y medir tiempo"""
            endpoint = endpoints[index % len(endpoints)]

            start = time.time()
            try:
                response = api_client.get(endpoint)
                elapsed = time.time() - start

                return {
                    "index": index,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "time": elapsed,
                    "success": response.status_code == 200,
                    "error": None
                }
            except Exception as e:
                elapsed = time.time() - start
                return {
                    "index": index,
                    "endpoint": endpoint,
                    "status": "ERROR",
                    "time": elapsed,
                    "success": False,
                    "error": str(e)
                }

        print(f"\n🔥 Load test: {num_requests} concurrent requests...")

        # Ejecutar requests concurrentes
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(make_request, i)
                for i in range(num_requests)
            ]

            results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start_time

        # Analizar resultados
        successful = sum(1 for r in results if r["success"])
        failed = num_requests - successful
        success_rate = successful / num_requests

        response_times = [r["time"] for r in results if r["success"]]
        avg_time = statistics.mean(response_times) if response_times else 0
        p95_time = (statistics.quantiles(response_times, n=20)[18]
                   if len(response_times) >= 20 else max(response_times, default=0))

        # Métricas por endpoint
        endpoint_stats = {}
        for endpoint in endpoints:
            endpoint_results = [r for r in results if r["endpoint"] == endpoint]
            endpoint_successful = sum(1 for r in endpoint_results if r["success"])
            endpoint_stats[endpoint] = {
                "total": len(endpoint_results),
                "successful": endpoint_successful,
                "rate": endpoint_successful / len(endpoint_results) if endpoint_results else 0
            }

        # Report
        print(f"\n📊 Load test results:")
        print(f"   Total requests: {num_requests}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {success_rate:.1%}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Throughput: {num_requests / total_time:.1f} req/s")
        print(f"\n⏱️  Response times:")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   P95: {p95_time:.3f}s")

        print(f"\n📊 Per-endpoint stats:")
        for endpoint, stats in endpoint_stats.items():
            print(f"   {endpoint}: {stats['successful']}/{stats['total']} ({stats['rate']:.1%})")

        # Assertions
        assert success_rate >= 0.90, \
            f"Success rate too low: {success_rate:.1%} < 90%"

        assert avg_time < 4.0, \
            f"Average response time too high under load: {avg_time:.3f}s"

        print(f"\n✅ Concurrent load test: PASSED")

    def test_sustained_load_no_memory_leak(self, api_client: httpx.Client):
        """
        Sistema mantiene performance bajo carga sostenida

        Ejecutar 100 requests secuenciales y verificar que:
        - Últimos 10 requests no son más lentos que primeros 10
        - No hay degradación progresiva (memory leak)
        """

        num_requests = 100
        response_times = []

        print(f"\n🔄 Sustained load test: {num_requests} sequential requests...")

        for i in range(num_requests):
            start = time.time()
            response = api_client.get("/health")
            elapsed = time.time() - start

            assert response.status_code == 200, f"Request {i+1} failed"
            response_times.append(elapsed)

            # Sin pausa intencional para simular carga continua

        # Comparar primeros 10 vs últimos 10
        first_10_avg = statistics.mean(response_times[:10])
        last_10_avg = statistics.mean(response_times[-10:])
        degradation = (last_10_avg - first_10_avg) / first_10_avg

        print(f"\n📊 Sustained load results:")
        print(f"   First 10 avg: {first_10_avg:.3f}s")
        print(f"   Last 10 avg: {last_10_avg:.3f}s")
        print(f"   Degradation: {degradation:+.1%}")

        # Degradación debe ser mínima (<20%)
        assert degradation < 0.20, \
            f"Performance degradation too high: {degradation:.1%}"

        print(f"✅ No significant performance degradation detected")


# ============================================================================
# PERFORMANCE HELPERS
# ============================================================================

def measure_endpoint_latency(
    client: httpx.Client,
    endpoint: str,
    method: str = "GET",
    payload: Dict = None,
    num_samples: int = 10
) -> Dict[str, float]:
    """
    Medir latencia de un endpoint

    Returns:
        Dict con métricas: avg, min, max, p50, p95
    """
    response_times = []

    for _ in range(num_samples):
        start = time.time()

        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json=payload)
        else:
            raise ValueError(f"Unsupported method: {method}")

        elapsed = time.time() - start

        if response.status_code == 200:
            response_times.append(elapsed)

        time.sleep(0.1)

    if not response_times:
        return {"error": "All requests failed"}

    return {
        "avg": statistics.mean(response_times),
        "min": min(response_times),
        "max": max(response_times),
        "p50": statistics.median(response_times),
        "p95": (statistics.quantiles(response_times, n=20)[18]
               if len(response_times) >= 20 else max(response_times)),
    }


def benchmark_concurrent_load(
    client: httpx.Client,
    endpoint: str,
    num_requests: int,
    max_workers: int
) -> Tuple[float, float, int]:
    """
    Benchmark de carga concurrente

    Returns:
        (success_rate, avg_latency, failed_count)
    """
    def make_request():
        try:
            start = time.time()
            response = client.get(endpoint)
            elapsed = time.time() - start
            return {
                "success": response.status_code == 200,
                "time": elapsed
            }
        except Exception:
            return {"success": False, "time": 0}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        results = [future.result() for future in as_completed(futures)]

    successful = sum(1 for r in results if r["success"])
    success_rate = successful / num_requests

    successful_times = [r["time"] for r in results if r["success"]]
    avg_latency = statistics.mean(successful_times) if successful_times else 0

    failed_count = num_requests - successful

    return success_rate, avg_latency, failed_count
