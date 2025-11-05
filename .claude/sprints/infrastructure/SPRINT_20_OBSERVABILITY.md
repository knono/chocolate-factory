# Sprint 20 - Observability & Tailscale Logs

**Status**: PENDIENTE
**Start Date**: 2025-11-15 (estimado)
**Completion Date**: TBD
**Duration**: 2.5 días
**Type**: Observability + Tailscale Analytics
**Last Update**: 2025-10-31

## Objetivo

Mejorar observabilidad con:
1. Logs estructurados JSON (aplicación + Tailscale)
2. Model monitoring (Prophet metrics tracking)
3. Tailscale logs avanzados (latency, traffic, relay usage)

**Motivación**:
- Logs plain text dificultan búsqueda/análisis
- Prophet accuracy no monitoreada over time
- Tailscale data infrautilizada (solo online/offline)
- Debugging complicado (logs scattered)

---

## Fase 1: Tailscale Logs Avanzados (1 día)

### Objetivo

Expandir socat HTTP proxy (Sprint 13) para exponer comandos adicionales + logs estructurados de conexiones Tailscale.

### Contexto

**Ya tienes (Sprint 13)**:
- socat HTTP server (puerto 8765) en sidecar
- Endpoints: `/status`, `/whois/<ip>`
- `TailscaleHealthService` consume proxy
- InfluxDB: métricas básicas (online/offline)

**Nuevo (Sprint 20)**:
- Endpoints adicionales: `/netcheck`, `/ping/<host>`, `/debug`
- Logs estructurados JSON: latency trends, traffic stats, relay usage
- Alertas: latency degradation, connection type changes

### Tareas

1. **Expandir socat HTTP proxy**
   - Archivo: `docker/tailscale-http-server.sh`
   - Añadir endpoints:
     ```bash
     /netcheck)
         echo "HTTP/1.1 200 OK"
         echo "Content-Type: application/json"
         echo ""
         /usr/local/bin/tailscale netcheck --format=json 2>&1
         ;;
     /ping/*)
         host=$(echo "$path" | sed 's|/ping/||')
         echo "HTTP/1.1 200 OK"
         echo "Content-Type: text/plain"
         echo ""
         /usr/local/bin/tailscale ping --c 5 "$host" 2>&1
         ;;
     /debug/*)
         peer=$(echo "$path" | sed 's|/debug/||')
         echo "HTTP/1.1 200 OK"
         echo "Content-Type: application/json"
         echo ""
         /usr/local/bin/tailscale debug watch-ipn --json | head -50
         ;;
     ```

2. **Actualizar TailscaleHealthService**
   - Archivo: `services/tailscale_health_service.py`
   - Nuevos métodos:
     ```python
     def get_network_diagnostics(self) -> Dict[str, Any]:
         """Run netcheck for connectivity diagnostics."""
         url = f"{self.tailscale_proxy_url}/netcheck"
         response = self._http_client.get(url)
         return response.json()

     def ping_peer(self, hostname: str, count: int = 5) -> Dict[str, float]:
         """Ping peer and return latency stats."""
         url = f"{self.tailscale_proxy_url}/ping/{hostname}"
         response = self._http_client.get(url)

         # Parse ping output
         output = response.text
         # Example: "pong from chocolate-factory (100.x.x.x) via DERP(fra) in 23ms"
         latencies = []
         for line in output.split('\n'):
             if 'in ' in line and 'ms' in line:
                 ms = float(line.split('in ')[1].split('ms')[0])
                 latencies.append(ms)

         if not latencies:
             return {"min": None, "max": None, "avg": None}

         return {
             "min": min(latencies),
             "max": max(latencies),
             "avg": sum(latencies) / len(latencies),
             "count": len(latencies)
         }

     def get_connection_stats(self, hostname: str) -> Dict[str, Any]:
         """Get detailed connection stats for peer."""
         status = self.get_tailscale_status()
         peers = status.get("Peer", {})

         for peer_key, peer_data in peers.items():
             if peer_data.get("HostName") == hostname:
                 return {
                     "hostname": hostname,
                     "connection_type": "direct" if peer_data.get("CurAddr") else "relay",
                     "relay_node": peer_data.get("Relay", "none"),
                     "tx_bytes": peer_data.get("TxBytes", 0),
                     "rx_bytes": peer_data.get("RxBytes", 0),
                     "last_handshake": peer_data.get("LastHandshake"),
                     "endpoint": peer_data.get("CurAddr", "via DERP")
                 }

         return {}
     ```

3. **Logs estructurados InfluxDB**
   - Measurement: `tailscale_connections`
   - Campos nuevos:
     ```python
     Point("tailscale_connections")
         .tag("hostname", hostname)
         .tag("connection_type", "direct" or "relay")
         .tag("relay_node", relay_node if relay else "none")
         .field("latency_ms", latency_avg)
         .field("latency_min", latency_min)
         .field("latency_max", latency_max)
         .field("tx_bytes", tx_bytes)
         .field("rx_bytes", rx_bytes)
         .time(datetime.utcnow())
     ```

4. **APScheduler job - Connection metrics**
   - Archivo: `tasks/health_monitoring_jobs.py`
   - Nuevo job: `collect_connection_metrics()` - Every 5 min
     ```python
     async def collect_connection_metrics():
         """Collect detailed connection metrics for critical nodes."""
         service = TailscaleHealthService(influx_client=get_influxdb_client())

         for node_name, node_config in service.CRITICAL_NODES.items():
             hostname = node_config["hostname"]

             # Ping peer
             ping_stats = service.ping_peer(hostname)

             # Get connection stats
             conn_stats = service.get_connection_stats(hostname)

             # Store in InfluxDB
             point = Point("tailscale_connections")
                 .tag("hostname", hostname)
                 .tag("connection_type", conn_stats.get("connection_type", "unknown"))
                 .tag("relay_node", conn_stats.get("relay_node", "none"))
                 .field("latency_avg", ping_stats.get("avg", 0))
                 .field("latency_min", ping_stats.get("min", 0))
                 .field("latency_max", ping_stats.get("max", 0))
                 .field("tx_bytes", conn_stats.get("tx_bytes", 0))
                 .field("rx_bytes", conn_stats.get("rx_bytes", 0))

             write_api.write(bucket="analytics", record=point)

             logger.info(f"Connection metrics collected: {hostname}")
     ```

5. **Alertas avanzadas**
   - Integrar con Telegram (Sprint 18)
   - Alertas:
     ```python
     # Latency degradation
     if ping_stats["avg"] > 100:  # >100ms
         await telegram_alert.send_alert(
             f"⚠️ WARNING: High latency to {hostname}: {ping_stats['avg']:.1f}ms",
             severity="WARNING",
             topic=f"latency_{hostname}"
         )

     # Connection type changed (direct → relay)
     if conn_stats["connection_type"] == "relay":
         await telegram_alert.send_alert(
             f"⚠️ WARNING: {hostname} using DERP relay (not direct connection)",
             severity="WARNING",
             topic=f"relay_{hostname}"
         )
     ```

6. **API endpoints - Connection analytics**
   - Archivo: `api/routers/health_monitoring.py`
   - Nuevos endpoints:
     ```python
     @router.get("/health-monitoring/connection-stats/{hostname}")
     async def get_connection_stats(hostname: str):
         """Get detailed connection stats for node."""
         service = TailscaleHealthService()
         stats = service.get_connection_stats(hostname)
         ping = service.ping_peer(hostname)

         return {
             "hostname": hostname,
             "connection_stats": stats,
             "ping_stats": ping
         }

     @router.get("/health-monitoring/latency-history/{hostname}")
     async def get_latency_history(hostname: str, hours: int = 24):
         """Get latency history from InfluxDB."""
         query = f'''
             from(bucket: "analytics")
                 |> range(start: -{hours}h)
                 |> filter(fn: (r) => r["_measurement"] == "tailscale_connections")
                 |> filter(fn: (r) => r["hostname"] == "{hostname}")
                 |> filter(fn: (r) => r["_field"] == "latency_avg")
         '''

         result = query_api.query(query=query)

         history = []
         for table in result:
             for record in table.records:
                 history.append({
                     "timestamp": record.get_time().isoformat(),
                     "latency_ms": record.get_value()
                 })

         return {"hostname": hostname, "history": history}
     ```

7. **Dashboard VPN - Gráficas latency**
   - Archivo: `static/vpn.html`
   - Añadir sección:
     ```html
     <div class="latency-chart">
       <h3>Latency History (24h)</h3>
       <canvas id="latencyChart"></canvas>
     </div>
     ```
   - JavaScript fetch `/health-monitoring/latency-history/{hostname}`
   - Renderizar con Chart.js (ya disponible)

8. **Tests**
   - Archivo: `tests/unit/test_tailscale_logs.py`
   - Test casos:
     - ping_peer retorna latency stats
     - get_connection_stats retorna connection_type
     - Alert enviada si latency >100ms
     - Alert enviada si connection_type = relay
     - InfluxDB write con connection metrics

### Entregables

- [ ] `docker/tailscale-http-server.sh` (3 endpoints nuevos)
- [ ] `services/tailscale_health_service.py` (3 métodos nuevos)
- [ ] `tasks/health_monitoring_jobs.py` (job collect_connection_metrics)
- [ ] `api/routers/health_monitoring.py` (2 endpoints nuevos)
- [ ] `static/vpn.html` (latency chart)
- [ ] `tests/unit/test_tailscale_logs.py` (5 tests)
- [ ] InfluxDB measurement `tailscale_connections`

### Criterios de Aceptación

- [ ] Endpoint `/health-monitoring/connection-stats/{hostname}` funcional
- [ ] Endpoint `/health-monitoring/latency-history/{hostname}` retorna 24h data
- [ ] APScheduler job ejecuta cada 5min
- [ ] Alert enviada si latency >100ms
- [ ] Alert enviada si connection relay (no direct)
- [ ] Dashboard VPN muestra gráfica latency
- [ ] Tests passing (5/5)

---

## Fase 2: Structured Logging JSON (0.75 días)

### Objetivo

Cambiar logs plain text → JSON estructurado para aplicación + integrar logs Tailscale.

### Tareas

1. **Crear JSON formatter**
   - Archivo: `core/logging_config.py`
   - Clase `JSONFormatter`:
     ```python
     import json
     import logging
     from datetime import datetime

     class JSONFormatter(logging.Formatter):
         def format(self, record: logging.LogRecord) -> str:
             log_data = {
                 "timestamp": datetime.utcnow().isoformat(),
                 "level": record.levelname,
                 "logger": record.name,
                 "message": record.getMessage(),
                 "module": record.module,
                 "function": record.funcName,
                 "line": record.lineno
             }

             # Add user if available (Tailscale auth - Sprint 18)
             if hasattr(record, "user_login"):
                 log_data["user"] = record.user_login

             # Add exception if present
             if record.exc_info:
                 log_data["exception"] = self.formatException(record.exc_info)

             return json.dumps(log_data)
     ```

2. **Configurar JSON logging**
   - Modificar `core/logging_config.py`:
     ```python
     def setup_logging(json_format: bool = True):
         formatter = JSONFormatter() if json_format else logging.Formatter(...)
         # ... resto configuración
     ```

3. **Config env var**
   - `core/config.py`:
     ```python
     LOG_FORMAT_JSON: bool = Field(default=True)
     ```

4. **Endpoint búsqueda logs**
   - `api/routers/health.py`:
     ```python
     @router.get("/logs/search")
     async def search_logs(level: str = "ERROR", hours: int = 24, limit: int = 100):
         # Parse JSON logs from file
         # Return filtered results
     ```

5. **Tests**
   - `tests/unit/test_json_logging.py` (4 tests)

### Entregables

- [ ] `core/logging_config.py` JSONFormatter
- [ ] `api/routers/health.py` endpoint `/logs/search`
- [ ] `core/config.py` variable LOG_FORMAT_JSON
- [ ] `tests/unit/test_json_logging.py` (4 tests)

---

## Fase 3: Model Monitoring (0.75 días)

### Objetivo

Trackear Prophet MAE/RMSE en CSV + alertar si degradación >2x baseline.

### Tareas

1. **Crear tracker CSV**
   - `domain/ml/model_metrics_tracker.py`:
     ```python
     class ModelMetricsTracker:
         def log_metrics(self, model_name: str, metrics: dict):
             # Append to CSV

         def get_baseline(self, model_name: str, metric: str) -> float:
             # Return median value
     ```

2. **Integrar en Prophet**
   - `tasks/ml_jobs.py`:
     ```python
     tracker.log_metrics("prophet_price_forecast", {
         "mae": mae, "rmse": rmse, "r2": r2
     })

     if mae > baseline_mae * 2:
         # Alert Telegram
     ```

3. **API endpoint**
   - `api/routers/ml_predictions.py`:
     ```python
     @router.get("/models/metrics-history")
     async def get_metrics_history(model_name: str, limit: int = 100):
         # Return last N CSV entries
     ```

4. **Tests**
   - `tests/unit/test_model_metrics.py` (4 tests)

### Entregables

- [ ] `domain/ml/model_metrics_tracker.py`
- [ ] `tasks/ml_jobs.py` integrado
- [ ] `api/routers/ml_predictions.py` endpoint
- [ ] `tests/unit/test_model_metrics.py` (4 tests)
- [ ] `models/metrics_history.csv` generado

---

## Fase 4: Documentación (0.5 días)

### Tareas

1. **Docs nuevos**:
   - `docs/TAILSCALE_LOGS.md` - Tailscale analytics setup
   - `docs/ML_MONITORING.md` - Model metrics tracking

2. **Actualizar existentes**:
   - `docs/INFRASTRUCTURE.md` - JSON logging section
   - `CLAUDE.md` - Sprint 20

3. **Sprint retrospective**

### Entregables

- [ ] 2 docs nuevos
- [ ] 2 docs actualizados
- [ ] Sprint retrospective

---

## Métricas de Éxito

**Tailscale Logs**:
- [ ] 3 endpoints nuevos socat proxy
- [ ] Connection metrics en InfluxDB (latency, traffic, relay)
- [ ] Alertas latency >100ms
- [ ] Alertas connection relay
- [ ] Dashboard VPN con latency chart

**Structured Logging**:
- [ ] Logs JSON format
- [ ] Endpoint `/logs/search` funcional
- [ ] User context en logs (Tailscale auth)

**Model Monitoring**:
- [ ] Prophet metrics CSV
- [ ] Alert degradación MAE >2x
- [ ] Endpoint `/models/metrics-history`

**Testing**:
- [ ] Tests passing: 13 nuevos (5 tailscale + 4 logging + 4 metrics)

---

## Archivos Nuevos/Modificados

**Nuevos**:
- `domain/ml/model_metrics_tracker.py`
- `tests/unit/test_tailscale_logs.py`
- `tests/unit/test_json_logging.py`
- `tests/unit/test_model_metrics.py`
- `docs/TAILSCALE_LOGS.md`
- `docs/ML_MONITORING.md`
- `models/metrics_history.csv` (generado)

**Modificados**:
- `docker/tailscale-http-server.sh` (3 endpoints)
- `services/tailscale_health_service.py` (3 métodos)
- `tasks/health_monitoring_jobs.py` (job connection metrics)
- `tasks/ml_jobs.py` (Prophet tracking)
- `api/routers/health_monitoring.py` (2 endpoints)
- `api/routers/health.py` (logs search)
- `api/routers/ml_predictions.py` (metrics endpoint)
- `core/logging_config.py` (JSONFormatter)
- `static/vpn.html` (latency chart)
- `docs/INFRASTRUCTURE.md`
- `CLAUDE.md`

---

## Comandos Tailscale Útiles

**Ya implementados**:
```bash
tailscale status --json       # Node status
tailscale whois <ip>          # Node info
```

**Nuevos (Sprint 20)**:
```bash
tailscale netcheck --format=json   # Network diagnostics
tailscale ping --c 5 <host>        # Latency test
tailscale debug watch-ipn          # Connection debug
```

**Output ejemplo - netcheck**:
```json
{
  "UDP": true,
  "IPv6": false,
  "MappingVariesByDestIP": false,
  "HairPinning": true,
  "PreferredDERP": 9,
  "DERPLatency": {
    "9-fra": 0.023,
    "2-nyc": 0.089
  }
}
```

**Output ejemplo - ping**:
```
pong from chocolate-factory (100.x.x.x) via DERP(fra) in 23ms
pong from chocolate-factory (100.x.x.x) via [direct] in 12ms
```

---

## InfluxDB Schema - Tailscale Connections

**Measurement**: `tailscale_connections`

**Tags**:
- `hostname` (git, chocolate-factory-dev, chocolate-factory)
- `connection_type` (direct, relay)
- `relay_node` (fra, nyc, none)

**Fields**:
- `latency_avg` (float, milliseconds)
- `latency_min` (float)
- `latency_max` (float)
- `tx_bytes` (int, total transmitted)
- `rx_bytes` (int, total received)

**Queries útiles**:
```flux
// Latency trend last 24h
from(bucket: "analytics")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "tailscale_connections")
  |> filter(fn: (r) => r["hostname"] == "git")
  |> filter(fn: (r) => r["_field"] == "latency_avg")

// Connection type distribution
from(bucket: "analytics")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "tailscale_connections")
  |> group(columns: ["connection_type"])
  |> count()
```

---

## Dependencias

- socat (ya instalado en sidecar)
- httpx (ya instalado)
- Chart.js (ya disponible en static/)
- csv (built-in Python)
- json (built-in Python)

---

## Riesgos

1. **Ping timeout en socat**
   - Causa: `tailscale ping` tarda >10s
   - Solución: Timeout httpx aumentar a 15s

2. **JSON logs rompen parsers legacy**
   - Causa: Scripts bash esperan plain text
   - Solución: `LOG_FORMAT_JSON=false` en dev

3. **Latency alerts spam**
   - Causa: Conexión inestable
   - Solución: Rate limiting (ya en Sprint 18)

---

## Checklist Final Sprint 20

- [x] Fase 1: Tailscale logs (8 tasks) - COMPLETADO
- [x] Fase 2: JSON logging (5 tasks) - COMPLETADO (Nov 5, 2025)
- [ ] Fase 3: Model monitoring (4 tasks)
- [ ] Fase 4: Documentación (3 docs)
- [ ] Tests passing: 13/13 (actual: 11/11 Fase 2)
- [x] Connection metrics en InfluxDB (Fase 1)
- [ ] Latency chart en dashboard VPN
- [x] Logs JSON format (StructuredFormatter)
- [ ] Prophet metrics CSV tracking
- [ ] CLAUDE.md actualizado
- [ ] Sprint retrospective

---

## Fase 2 - Resumen Ejecución

**Fecha**: Nov 5, 2025
**Duración**: 1 día (incluyendo troubleshooting permisos)
**Tests**: 11/11 passing (100%)

### Implementación

Archivos:
- `docker/fastapi.Dockerfile`: +1 línea (chmod 775 /app/logs)
- `core/logging_config.py`: +4 líneas (user_login en StructuredFormatter)
- `core/config.py`: +1 línea (LOG_FORMAT_JSON: bool = False)
- `api/routers/health.py`: +97 líneas (GET /logs/search)
- `tests/unit/test_json_logging.py`: 207 líneas (11 tests unitarios)

### Issue Critical Resuelto

**Problema**: PermissionError en `/app/logs/fastapi.log` - Container restart loop
**Causa**: Bind mount con UID mismatch (host:1000 vs container:999)
**Fix**:
- Dockerfile: `chmod -R 775 /app/logs`
- Host: `chown -R 999:999 docker/services/fastapi/logs/`

### Verificación

- StructuredFormatter JSON logging funcional
- Endpoint `/logs/search` operacional (filtros: level, hours, limit, module)
- File logging escribiendo en `/app/logs/fastapi.log` (55KB generados)
- Container healthy
- Endpoint `/vpn` restored (307 redirect, antes 502)
- Tests: 11/11 passing
