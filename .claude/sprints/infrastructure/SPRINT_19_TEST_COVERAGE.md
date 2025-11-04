# Sprint 19 - Test Coverage Expansion

**Status**: EN PROGRESO
**Start Date**: 2025-11-04
**Completion Date**: TBD
**Duration**: 3 días
**Type**: Testing + Quality
**Last Update**: 2025-11-04

## Objetivo

Aumentar test coverage de 32% → 50% enfocándose en servicios críticos (backfill, gap detection, API clients, scheduler).

**Motivación**:
- 68% código sin tests (riesgo alto en refactoring)
- Servicios críticos undertested (backfill 53%, gap 66%, API clients 23-26%)
- E2E tests con 11 failing (performance/resilience)

---

## Baseline

**Estado actual (Sprint 17)**:
- Coverage: 32%
- Tests totales: 134
- Tests passing: 123
- Tests failing: 11 (E2E performance/resilience)

**Servicios críticos coverage**:
- backfill_service.py: 53%
- gap_detector.py: 66%
- ree_client.py: 23%
- aemet_client.py: 26%
- openweather_client.py: 25%
- scheduler_config.py: 0%

---

## Fase 1: Backfill Service Tests (1 día)

**Status**: INCOMPLETA (11/14 passing)

### Target

`services/backfill_service.py`: 53% → 75% coverage

### Progreso 2025-11-04

**Archivo creado**: `tests/unit/test_backfill_service_extended.py` (648 líneas, 14 tests)

**Cambios en código**:
- `backfill_service.py:155` - Fix crítico: `get_pvpc_prices(target_date=...)` en lugar de `get_pvpc_prices(start_date=..., end_date=...)`
  - API solo acepta `target_date` (fecha única), no rangos
- Import añadido en tests: `from services.data_ingestion import DataIngestionStats`
- Mock fixture mejorado: `ingest_ree_prices_historical` retorna `DataIngestionStats` en lugar de int

**Tests implementados (14 total)**:

REE Backfill (5 tests):
1. ✅ test_backfill_ree_single_gap_success
2. ✅ test_backfill_ree_multiple_gaps
3. ❌ test_backfill_ree_api_failure - Mock no intercepta API real
4. ❌ test_backfill_ree_empty_response - API real retorna 25 records
5. ❌ test_backfill_ree_partial_data - API real retorna 25 en lugar de 5

Weather Backfill (4 tests):
6. ✅ test_backfill_weather_aemet_recent_gap - Patch profundo AEMETClient funcionó
7. ✅ test_backfill_weather_old_gap_uses_siar
8. ✅ test_backfill_weather_aemet_failure_fallback
9. ✅ test_backfill_weather_multiple_sources

Intelligent Backfill (5 tests):
10. ✅ test_execute_intelligent_backfill_no_gaps
11. ✅ test_execute_intelligent_backfill_with_gaps
12. ✅ test_execute_intelligent_backfill_telegram_alert
13. ✅ test_execute_intelligent_backfill_exception_handling
14. ✅ test_execute_intelligent_backfill_partial_success

**Resultado**: 11/14 passing (79%)

**Problema pendiente**:
Mocking de REEAPIClient no intercepta todas las llamadas. Tests que configuran `side_effect` o `return_value` personalizados fallan porque la API real es llamada y retorna 25 registros (24 horas de datos).

Tests afectados usan:
```python
with patch('services.backfill_service.REEAPIClient', return_value=mock_ree_client):
```

El mock funciona para test #1 (return_value por defecto) pero no para tests que modifican el comportamiento (side_effect, empty list, partial data).

**Root cause**: Context manager `async with REEAPIClient()` probablemente no usa el mock correctamente o el fixture `mock_ree_client.__aenter__` no retorna el objeto mockeado apropiadamente.

### Entregables

- [x] `tests/unit/test_backfill_service_extended.py` (14 tests, 648 líneas)
- [ ] Coverage backfill_service.py: 75%+ (pendiente medición)
- [ ] Tests passing: 14/14 (actualmente 11/14)

---

## Fase 2: Gap Detector Tests (0.5 días)

### Target

`services/gap_detector.py`: 66% → 85% coverage

### Tests a crear

**Archivo**: `tests/unit/test_gap_detector_extended.py`

1. **test_detect_ree_gaps_multiple_separated**
   - Múltiples gaps no consecutivos
   - Verificar gaps agrupados correctamente
   - Assert 3 gaps detectados (no 1 largo)

2. **test_detect_weather_gaps_tolerance**
   - Tolera 1.5x expected_interval
   - Interval 5min → tolera hasta 7.5min
   - Assert gap NO detectado si <7.5min

3. **test_calculate_gap_severity_critical**
   - Gap >24h → severity "critical"
   - Assert severity == "critical"

4. **test_get_latest_timestamps_empty_db**
   - InfluxDB vacío (sin datos)
   - Verificar retorna None
   - No crash

### Entregables

- [ ] `tests/unit/test_gap_detector_extended.py` (4 tests, ~150 líneas)
- [ ] Coverage gap_detector.py: 85%+
- [ ] Tests passing: 4/4

---

## Fase 3: API Clients Tests (1 día)

### Target

`infrastructure/external_apis/*.py`: 23-26% → 60% coverage

### Tests a crear

**Archivo**: `tests/unit/test_api_clients_extended.py`

**REE Client** (3 tests):

1. **test_ree_client_retry_on_timeout**
   - Mock httpx timeout exception
   - Verificar retry 3 veces
   - Assert log WARNING

2. **test_ree_client_invalid_json_response**
   - API retorna HTML en vez de JSON
   - Assert JSONDecodeError capturado
   - Log ERROR escrito

3. **test_ree_client_date_range_validation**
   - start_date > end_date
   - Assert ValueError raised

**AEMET Client** (4 tests):

4. **test_aemet_get_current_weather_success**
   - Mock API retorna 200 + JSON
   - Verificar datos parseados correctamente
   - Assert temperatura, humedad presentes

5. **test_aemet_get_current_weather_404**
   - API retorna 404 (estación sin datos)
   - Assert retorna None (no crash)
   - Log WARNING

6. **test_aemet_get_daily_weather_recent_fails**
   - Fecha <72h
   - Assert ValueError (AEMET no tiene datos recientes)

7. **test_aemet_token_caching**
   - 2 requests consecutivos
   - Verificar token request solo 1 vez
   - Assert cache funciona

**OpenWeather Client** (3 tests):

8. **test_openweather_current_success**
   - Mock API retorna weather data
   - Verificar parsing correcto
   - Assert fields correctos

9. **test_openweather_api_key_invalid**
   - API retorna 401 Unauthorized
   - Assert APIKeyError raised
   - Log ERROR

10. **test_openweather_no_historical_support**
    - Llamar con fecha pasada
    - Assert NotImplementedError
    - (OpenWeather gratis NO soporta históricos)

### Entregables

- [ ] `tests/unit/test_api_clients_extended.py` (10 tests, ~350 líneas)
- [ ] Coverage ree_client.py: 60%+
- [ ] Coverage aemet_client.py: 60%+
- [ ] Coverage openweather_client.py: 60%+
- [ ] Tests passing: 10/10

---

## Fase 4: Scheduler Tests (0.5 días)

### Target

`tasks/scheduler_config.py`: 0% → 50% coverage

### Tests a crear

**Archivo**: `tests/unit/test_scheduler_extended.py`

1. **test_register_all_jobs_count**
   - Llamar register_all_jobs(scheduler)
   - Verificar 7 jobs registrados
   - Assert len(scheduler.get_jobs()) == 7

2. **test_job_intervals_correct**
   - Verificar intervalos:
     - REE ingestion: 5 min
     - Weather ingestion: 5 min
     - sklearn training: 30 min
     - Prophet check: 24h
     - Health metrics: 5 min
   - Assert trigger.interval correcto

3. **test_job_failure_does_not_crash_scheduler**
   - Mock job lanza exception
   - Scheduler sigue running
   - Assert scheduler.running == True

4. **test_scheduler_shutdown_graceful**
   - Scheduler running
   - Llamar shutdown(wait=True)
   - Assert scheduler.running == False

5. **test_job_next_run_time_scheduled**
   - Job registrado
   - Assert next_run_time is not None
   - (job programado para ejecutar)

### Entregables

- [ ] `tests/unit/test_scheduler_extended.py` (5 tests, ~180 líneas)
- [ ] Coverage scheduler_config.py: 50%+
- [ ] Tests passing: 5/5

---

## Fase 5: E2E Tests Fix (0.5 días)

### Target

Arreglar 11 E2E tests failing (performance/resilience)

### Tests failing

**test_performance.py** (3 failing):
- Latencia >2s en algunos endpoints
- **Solución**: Ajustar thresholds (2s → 5s) o optimizar queries InfluxDB

**test_resilience.py** (4 failing):
- Mocks API externos no funcionan correctamente
- **Solución**: Revisar mocks httpx, fixture setup

**test_full_pipeline.py** (4 failing):
- Estructura JSON response cambió
- **Solución**: Actualizar asserts con nueva estructura

### Tareas

1. Ejecutar tests con verbose: `pytest -vv tests/e2e/`
2. Identificar causa exacta de cada fallo
3. Ajustar thresholds o actualizar asserts
4. Re-run hasta 100% passing

### Entregables

- [ ] E2E tests: 102/102 passing
- [ ] Performance thresholds ajustados
- [ ] Mocks resilience arreglados

---

## Fase 6: Coverage Report & Docs (0.5 días)

### Tareas

1. **Generar coverage report HTML**
   ```bash
   pytest --cov=src/fastapi-app --cov-report=html
   open htmlcov/index.html
   ```

2. **Documentar tests nuevos**
   - Actualizar `README.md` sección Testing
   - Añadir en `docs/TESTING.md`:
     - Coverage targets por módulo
     - Cómo ejecutar tests
     - Fixtures disponibles

3. **Actualizar CLAUDE.md**
   - Sprint 19 completado
   - Coverage: 32% → 50%
   - Tests: 134 → 159 (+25)

### Entregables

- [ ] Coverage report HTML generado
- [ ] `docs/TESTING.md` actualizado
- [ ] `CLAUDE.md` actualizado

---

## Métricas de Éxito

- [ ] Coverage: 32% → 50%+ (target alcanzado)
- [ ] Tests totales: 134 → 159 (+25)
- [ ] Tests passing: 100% (159/159)
- [ ] backfill_service.py: 75%+ coverage
- [ ] gap_detector.py: 85%+ coverage
- [ ] API clients: 60%+ coverage
- [ ] scheduler_config.py: 50%+ coverage
- [ ] E2E tests: 0 failing

---

## Archivos Nuevos/Modificados

**Tests creados**:
- `tests/unit/test_backfill_service_extended.py` (6 tests)
- `tests/unit/test_gap_detector_extended.py` (4 tests)
- `tests/unit/test_api_clients_extended.py` (10 tests)
- `tests/unit/test_scheduler_extended.py` (5 tests)

**Documentación**:
- `docs/TESTING.md` (actualizado)
- `CLAUDE.md` (Sprint 19 añadido)
- `README.md` (testing section actualizada)

**Total**: 4 archivos test nuevos, 25 tests nuevos, ~880 líneas código test

---

## Notas Técnicas

### Mocking httpx AsyncClient

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_ree_client_timeout():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        client = REEAPIClient()
        with pytest.raises(httpx.TimeoutException):
            await client.get_prices()
```

### Mocking InfluxDB write_api

```python
from unittest.mock import MagicMock

def test_backfill_writes_to_influxdb():
    mock_influx = MagicMock()
    mock_write_api = MagicMock()
    mock_influx.write_api.return_value = mock_write_api

    service = BackfillService(influx_client=mock_influx)
    service.backfill_ree_gaps(days_back=1)

    # Verify write_api.write called 24 times (1 day = 24 hours)
    assert mock_write_api.write.call_count == 24
```

### Coverage Exclusions

Archivos excluidos de coverage target:
- `main.py` (startup code)
- `dependencies.py` (DI initialization)
- `startup_tasks.py` (bootstrap)
- `services/legacy/*` (deprecated)

---

## Dependencias

- pytest (ya instalado)
- pytest-cov (ya instalado)
- pytest-asyncio (ya instalado)
- pytest-mock (ya instalado)

---

## Riesgos

1. **Tests frágiles (flaky tests)**
   - Causa: Dependencia en timing, estado InfluxDB
   - Solución: Usar mocks, fixtures isolated

2. **Coverage no aumenta suficiente**
   - Causa: Código legacy difícil de testear
   - Solución: Refactor mínimo para testability

3. **E2E tests siguen failing**
   - Causa: Thresholds muy estrictos
   - Solución: Ajustar a valores realistas

---

## Checklist Final Sprint 19

- [ ] Fase 1: Backfill tests (6 tests)
- [ ] Fase 2: Gap detector tests (4 tests)
- [ ] Fase 3: API clients tests (10 tests)
- [ ] Fase 4: Scheduler tests (5 tests)
- [ ] Fase 5: E2E tests fix (11 arreglados)
- [ ] Fase 6: Docs actualizada
- [ ] Coverage 50%+ alcanzado
- [ ] Tests 159/159 passing
- [ ] Coverage report HTML generado
- [ ] CLAUDE.md actualizado
