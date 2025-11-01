# Sprint 21: OpenWeatherMap One Call 3.0 - Historical Data Integration

**Status**: Planned
**Priority**: Medium
**Estimated Duration**: 2-3 días
**Dependencies**: None

---

## Objetivo

Eliminar pérdida de datos en gaps >12h implementando OpenWeatherMap One Call API 3.0 con acceso a históricos.

---

## Problema Actual

AEMET `/observacion/convencional` solo retorna últimas 12h:
- Apagado 8h: pérdida 4h
- Weekend 48h: pérdida 36h
- Threshold 3.5h mitiga pero no elimina pérdida

---

## Solución

Integrar OWM One Call 3.0 como fuente primaria para backfill gaps 12h-5días.

**Capacidades OWM:**
- Históricos desde 1979
- 1000 calls/día gratis
- Hourly resolution
- 100% recuperación gaps hasta 5 días

---

## Tareas

### Fase 1: Registro y Configuración (30 min)

- [ ] Registrar cuenta OWM One Call by Call
- [ ] Añadir tarjeta crédito
- [ ] Configurar hard limit 1000 calls/día en dashboard
- [ ] Obtener API key
- [ ] Añadir `OWM_ONECALL_API_KEY` a `.env`

### Fase 2: Cliente API (2-3 horas)

- [ ] Crear `src/fastapi-app/infrastructure/external_apis/owm_onecall_client.py`
- [ ] Implementar métodos:
  - `get_historical_weather(lat, lon, dt)` - Unix timestamp
  - `get_historical_hourly(lat, lon, start_dt, end_dt)` - Rango horario
- [ ] Rate limiting: 1000 calls/día
- [ ] Contador llamadas diarias (Redis o InfluxDB)
- [ ] Tests unitarios

**Endpoint:**
```
GET /data/3.0/onecall/timemachine
Parameters:
  - lat: 38.151107 (Linares)
  - lon: -3.629453
  - dt: Unix timestamp
  - appid: API key
```

### Fase 3: Integración Backfill Service (3-4 horas)

- [ ] Nuevo método `_backfill_weather_owm_onecall(gap)` en `backfill_service.py`
- [ ] Actualizar estrategia backfill:
  ```python
  if gap_duration_hours <= 12:
      # AEMET (gratis, oficial)
      result = await self._backfill_weather_aemet_hourly(gap)
  elif gap_duration_hours <= 120:  # 5 días
      # OWM One Call 3.0 (gratis hasta 1000 calls)
      result = await self._backfill_weather_owm_onecall(gap)
  else:
      # SIAR manual (>5 días)
      logger.warning("Gap >5 días, usar SIAR manual")
  ```
- [ ] Logging llamadas OWM (contador diario)
- [ ] Fallback a AEMET si budget excedido

### Fase 4: Monitoreo y Alertas (1-2 horas)

- [ ] Dashboard endpoint `/owm-onecall/usage`:
  - Calls hoy
  - Calls restantes
  - Reset timestamp
- [ ] Alerta si >900 calls/día
- [ ] Logs budget exceeded

### Fase 5: UI Attribution (1 hora)

- [ ] Añadir footer dashboard: "Weather data powered by OpenWeather"
- [ ] Link: https://openweathermap.org
- [ ] Cumplir ODbL license requirements

### Fase 6: Testing (2 horas)

- [ ] Test gaps 13h-24h (recovery 100%)
- [ ] Test gaps 48h (weekend recovery 100%)
- [ ] Test budget limit (mock 1000 calls)
- [ ] Test fallback AEMET si budget excedido
- [ ] E2E backfill con OWM

### Fase 7: Documentación (1 hora)

- [ ] Actualizar `docs/BACKFILL_SYSTEM.md` con estrategia final
- [ ] README attribution requirements
- [ ] `.env.example` con `OWM_ONECALL_API_KEY`

---

## Estimación Llamadas

**Uso típico:**
- Apagado diario 8h: 8 calls
- Weekend 48h: 48 calls
- Budget mensual: 30,000 calls
- Uso mensual estimado: ~400 calls (13 apagados 8h + 4 weekends)

**Margen seguridad:** 30,000 - 400 = 29,600 calls disponibles/mes

---

## Riesgos

1. **Overage charges**: Mitigado con hard limit 1000 calls
2. **API deprecation**: OWM mantiene APIs largo plazo (v2.5 deprecated tras 5+ años)
3. **Budget insuficiente**: Fallback AEMET mantiene operación básica
4. **Vendor lock-in**: AEMET + SIAR siguen disponibles como backup

---

## Criterios Aceptación

- [ ] Gaps 13h-120h: 100% recuperación
- [ ] Contador llamadas diarias funcionando
- [ ] Hard limit 1000 calls configurado
- [ ] Alertas >900 calls activas
- [ ] Attribution visible en dashboard
- [ ] Tests passing (unit + E2E)
- [ ] Fallback AEMET operativo

---

## Referencias

- API Docs: https://openweathermap.org/api/one-call-3
- Historical endpoint: https://openweathermap.org/api/one-call-3#history
- Pricing: https://openweathermap.org/price
- License: https://openweathermap.org/terms
