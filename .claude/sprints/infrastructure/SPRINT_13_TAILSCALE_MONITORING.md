# 🎯 SPRINT 13: Tailscale Monitoring + Analytics MCP

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 MEDIA-ALTA
> **Prerequisito**: Sprint 11-12 completados, Tailscale sidecar operacional
> **Duración estimada**: 3-4 días (16-20 horas)
> **Fecha inicio planeada**: 2025-10-19

---

## 📋 Objetivo

**Usar Tailscale MCP** para monitorizar accesos, analytics de usuarios, y métricas de uso del sistema, sin necesidad de Prometheus/Grafana.

### ¿Por qué Tailscale MCP en lugar de Prometheus?

| Feature | Prometheus/Grafana | Tailscale MCP |
|---------|-------------------|---------------|
| **Setup** | Complejo (2 servicios) | Simple (ya tienes Tailscale) |
| **RAM** | ~500MB | ~50MB |
| **Acceso usuarios** | ❌ Manual | ✅ Nativo (Tailnet API) |
| **Integración Claude** | ❌ No | ✅ Tools MCP nativos |
| **Analytics Tailnet** | ❌ No disponible | ✅ Logs, conexiones, ACLs |
| **Costo** | Gratis pero complejo | Gratis y simple |

**Decisión**: Tailscale MCP + custom metrics endpoint es más ligero y se integra mejor con Claude Code.

---

## 📦 Entregables

### 1. Tailscale MCP Server Integration

**Usar**: [Tailscale MCP Server oficial](https://github.com/tailscale/tailscale-mcp)

**Tools disponibles nativos**:
- `tailscale_list_devices` - Dispositivos en tu Tailnet
- `tailscale_get_device` - Info detallada dispositivo
- `tailscale_get_status` - Estado conexión Tailscale
- `tailscale_who_is` - Identificar usuario por IP

**Configuración**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "chocolate-factory": {
      "command": "python",
      "args": ["/ruta/mcp-server/chocolate_factory_mcp.py"]
    },
    "tailscale": {
      "command": "npx",
      "args": ["-y", "@tailscale/mcp-server"],
      "env": {
        "TAILSCALE_API_KEY": "${TAILSCALE_API_KEY}",
        "TAILNET": "your-tailnet.ts.net"
      }
    }
  }
}
```

---

### 2. Custom Analytics Endpoint (FastAPI)

**Archivo**: `src/fastapi-app/api/routers/analytics.py`

**Endpoints nuevos**:

#### `GET /analytics/access-logs`
Logs de acceso al dashboard vía Tailnet

```python
@router.get("/analytics/access-logs")
async def get_access_logs(
    hours: int = Query(default=24, ge=1, le=168),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get access logs from Tailscale + nginx logs.

    Returns:
    - timestamp: cuando accedieron
    - user: usuario Tailscale (email)
    - device: nombre dispositivo
    - endpoint: ruta accedida
    - response_time_ms: tiempo respuesta
    """
    return await service.get_access_logs(hours=hours)
```

**Output ejemplo**:
```json
{
  "logs": [
    {
      "timestamp": "2025-10-08T14:32:15Z",
      "user": "user@example.com",
      "device": "user-laptop",
      "ip": "100.x.x.x",
      "endpoint": "/dashboard",
      "method": "GET",
      "status": 200,
      "response_time_ms": 42
    }
  ],
  "summary": {
    "total_requests": 1247,
    "unique_users": 3,
    "unique_devices": 5,
    "avg_response_time_ms": 38
  }
}
```

---

#### `GET /analytics/dashboard-usage`
Métricas de uso del dashboard

```python
@router.get("/analytics/dashboard-usage")
async def get_dashboard_usage(
    days: int = Query(default=7, ge=1, le=30)
):
    """
    Dashboard usage metrics from InfluxDB + Tailscale.

    Returns:
    - most_viewed_cards: tarjetas dashboard más vistas
    - peak_hours: horas con más accesos
    - user_sessions: sesiones por usuario
    - api_calls: endpoints más usados
    """
```

**Output ejemplo**:
```json
{
  "most_viewed_cards": [
    {"card": "Sistema", "views": 342},
    {"card": "Pronóstico Semanal", "views": 289},
    {"card": "Dashboard Predictivo", "views": 156}
  ],
  "peak_hours": [
    {"hour": 10, "requests": 89},
    {"hour": 15, "requests": 67}
  ],
  "user_sessions": [
    {
      "user": "user@example.com",
      "sessions": 45,
      "total_time_hours": 12.3,
      "favorite_features": ["Prophet forecast", "SIAR analysis"]
    }
  ],
  "api_calls_by_endpoint": [
    {"/dashboard/complete": 1204},
    {"/insights/optimal-windows": 356},
    {"/predict/prices/weekly": 234}
  ]
}
```

---

#### `GET /analytics/system-health-history`
Histórico salud sistema (InfluxDB metrics)

```python
@router.get("/analytics/system-health-history")
async def get_system_health_history(days: int = 7):
    """
    System health metrics over time.

    Returns:
    - uptime_percentage: % tiempo online
    - api_response_times: latencias por endpoint
    - influxdb_query_times: performance queries
    - error_rate: tasa errores por endpoint
    """
```

---

### 3. Analytics Service (Backend)

**Archivo**: `src/fastapi-app/services/analytics_service.py`

**Funcionalidades**:

#### Parsear nginx logs (Tailscale sidecar)
```python
async def parse_nginx_logs(self, hours: int = 24) -> List[AccessLog]:
    """
    Parse nginx access.log from Tailscale sidecar.

    Format: 100.x.x.x - - [08/Oct/2025:14:32:15] "GET /dashboard HTTP/1.1" 200 1234
    """
    log_file = Path("/logs/sidecar/access.log")
    # Parse logs + enrich with Tailscale API (user info)
```

#### Correlación Tailscale API
```python
async def enrich_with_tailscale_data(self, ip: str) -> TailscaleUser:
    """
    Use Tailscale API to get user info from IP.

    API: https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices
    """
    # Match IP → device → user email
```

#### Métricas custom en InfluxDB
```python
async def store_access_metric(self, log: AccessLog):
    """
    Store access log in InfluxDB for time-series analysis.

    Measurement: api_access
    Tags: user, device, endpoint, method
    Fields: response_time_ms, status_code
    """
    point = Point("api_access") \
        .tag("user", log.user) \
        .tag("endpoint", log.endpoint) \
        .field("response_time_ms", log.response_time_ms)

    await influxdb.write(point)
```

---

### 4. Tailscale MCP Tools (Custom Chocolate Factory)

**Archivo**: `mcp-server/tools/tailscale.py`

**Añadir a MCP server chocolate_factory_mcp.py**:

#### Tool: `get_active_users`
```python
async def get_active_users() -> Dict[str, Any]:
    """
    Get currently active users on Tailnet accessing chocolate factory.

    Uses:
    - Tailscale API: list devices online
    - Nginx logs: filter IPs accessing dashboard last 5 min

    Returns:
    {
      "active_users": [
        {
          "email": "user@example.com",
          "device": "user-laptop",
          "last_seen": "2 min ago",
          "current_page": "/dashboard"
        }
      ],
      "total_active": 1
    }
    """
```

#### Tool: `get_usage_stats`
```python
async def get_usage_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get Chocolate Factory usage statistics.

    Combines:
    - Tailscale access logs
    - InfluxDB metrics
    - API endpoint usage

    Returns:
    {
      "period_days": 7,
      "total_sessions": 156,
      "unique_users": 3,
      "most_active_user": "user@example.com",
      "top_features": [
        "Prophet forecast (234 accesos)",
        "SIAR analysis (156 accesos)"
      ],
      "avg_session_duration_min": 8.5
    }
    """
```

#### Tool: `get_system_performance`
```python
async def get_system_performance() -> Dict[str, Any]:
    """
    Get system performance metrics.

    Returns:
    {
      "uptime_last_7d": "99.8%",
      "avg_api_response_ms": 42,
      "slowest_endpoints": [
        {"/optimize/production/daily": "892ms"},
        {"/analysis/siar-summary": "234ms"}
      ],
      "error_rate": "0.02%",
      "influxdb_status": "healthy",
      "data_freshness": "2 min ago"
    }
    """
```

---

### 5. Dashboard Analytics Widget

**Archivo**: `static/js/components/analytics-widget.js`

**Nueva tarjeta dashboard**: "📊 Analytics Última Semana"

```html
<div class="card analytics-card">
  <h3>📊 Analytics Última Semana</h3>

  <div class="metric">
    <span class="label">Sesiones totales:</span>
    <span class="value">156</span>
  </div>

  <div class="metric">
    <span class="label">Usuarios únicos:</span>
    <span class="value">3</span>
  </div>

  <div class="chart">
    <!-- Chart.js: accesos por día última semana -->
    <canvas id="accessChart"></canvas>
  </div>

  <div class="top-features">
    <h4>Features más usadas:</h4>
    <ul>
      <li>🔮 Prophet Forecast (234 accesos)</li>
      <li>📊 SIAR Analysis (156 accesos)</li>
      <li>⚡ Optimal Windows (89 accesos)</li>
    </ul>
  </div>
</div>
```

---

### 6. Tailscale API Integration

**Archivo**: `src/fastapi-app/infrastructure/external_apis/tailscale_client.py`

```python
import httpx
from typing import List, Dict, Any

class TailscaleClient:
    """
    Client para Tailscale API v2.

    Docs: https://tailscale.com/api
    """

    def __init__(self):
        self.api_key = os.getenv("TAILSCALE_API_KEY")
        self.tailnet = os.getenv("TAILNET", "your-tailnet.ts.net")
        self.base_url = "https://api.tailscale.com/api/v2"

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}"
            },
            timeout=30.0
        )

    async def list_devices(self) -> List[Dict[str, Any]]:
        """List all devices in Tailnet."""
        response = await self.client.get(
            f"{self.base_url}/tailnet/{self.tailnet}/devices"
        )
        return response.json()["devices"]

    async def get_device_by_ip(self, ip: str) -> Dict[str, Any]:
        """Get device info by IP address."""
        devices = await self.list_devices()
        for device in devices:
            if ip in device.get("addresses", []):
                return device
        return None

    async def whois(self, ip: str) -> Dict[str, Any]:
        """
        Get user info for IP address.

        Returns:
        {
          "user": "user@example.com",
          "device": "user-laptop",
          "online": true,
          "last_seen": "2025-10-08T14:32:15Z"
        }
        """
        response = await self.client.get(
            f"{self.base_url}/tailnet/{self.tailnet}/whois?addr={ip}"
        )
        return response.json()
```

---

## 📝 Plan de Implementación

### Fase 1: Tailscale API Setup (2-3 horas)

- [ ] Generar Tailscale API key: https://login.tailscale.com/admin/settings/keys
- [ ] Añadir `TAILSCALE_API_KEY` a `.env`
- [ ] Implementar `tailscale_client.py`
- [ ] Test: listar dispositivos Tailnet
- [ ] Test: whois para IP conocida

### Fase 2: Analytics Service (4-5 horas)

- [ ] Crear `services/analytics_service.py`
- [ ] Implementar `parse_nginx_logs()`
- [ ] Implementar `enrich_with_tailscale_data()`
- [ ] Implementar `store_access_metric()` (InfluxDB)
- [ ] Tests unitarios

### Fase 3: Analytics API Endpoints (3-4 horas)

- [ ] Crear `api/routers/analytics.py`
- [ ] Endpoint `GET /analytics/access-logs`
- [ ] Endpoint `GET /analytics/dashboard-usage`
- [ ] Endpoint `GET /analytics/system-health-history`
- [ ] Registrar router en `main.py`

### Fase 4: Tailscale MCP Integration (2-3 horas)

- [ ] Instalar Tailscale MCP: `npx -y @tailscale/mcp-server`
- [ ] Configurar `claude_desktop_config.json`
- [ ] Añadir custom tools a `mcp-server/tools/tailscale.py`
- [ ] Test tools en Claude Code

### Fase 5: Dashboard Analytics Widget (3-4 horas)

- [ ] Crear `static/js/components/analytics-widget.js`
- [ ] Integrar Chart.js para gráficos
- [ ] Añadir widget a dashboard principal
- [ ] Estilos CSS

### Fase 6: Nginx Logs Persistence (1-2 horas)

- [ ] Bind mount logs sidecar: `./logs/sidecar:/var/log/nginx`
- [ ] Configurar log rotation (evitar disco lleno)
- [ ] Test parseo logs después restart

### Fase 7: Documentación (1-2 horas)

- [ ] `docs/TAILSCALE_MONITORING.md`
- [ ] Ejemplos uso MCP tools
- [ ] Dashboard analytics screenshots
- [ ] Actualizar CLAUDE.md

---

## 🧪 Criterios de Éxito

### Tests Funcionales

1. **Test Tailscale API**:
   ```bash
   curl -H "Authorization: Bearer ${TAILSCALE_API_KEY}" \
     https://api.tailscale.com/api/v2/tailnet/your-tailnet.ts.net/devices
   # Expected: lista dispositivos Tailnet
   ```

2. **Test Analytics Endpoint**:
   ```bash
   curl http://localhost:8000/analytics/access-logs?hours=24
   # Expected: logs acceso con usuarios Tailscale
   ```

3. **Test MCP Tool**:
   ```
   User (en Claude Code): "¿Quién está usando el dashboard ahora?"
   Claude: [usa tool get_active_users]
   Response: "1 usuario activo: user@example.com desde user-laptop"
   ```

4. **Test Dashboard Widget**:
   - Abrir http://localhost:8000/dashboard
   - Verificar widget "Analytics" muestra datos
   - Chart.js renderiza gráfico accesos

### Métricas de Éxito

- ✅ Tailscale API conectada y funcional
- ✅ Analytics service parsea nginx logs
- ✅ 3 endpoints analytics operacionales
- ✅ 3 MCP tools Tailscale funcionando
- ✅ Dashboard widget renderiza correctamente
- ✅ Logs persisten entre reinicios

---

## 🚧 Problemas Potenciales

### Problema 1: Tailscale API rate limiting

**Síntomas**: HTTP 429 "Too Many Requests"

**Solución**:
```python
# Cachear respuestas Tailscale API
from functools import lru_cache

@lru_cache(ttl=300)  # 5 min cache
async def list_devices():
    return await tailscale_client.list_devices()
```

### Problema 2: Nginx logs no accesibles

**Síntomas**: Permission denied al leer `/logs/sidecar/access.log`

**Solución**:
```bash
# Ajustar permisos bind mount
chmod -R 755 logs/sidecar/
chown -R 1000:1000 logs/sidecar/
```

### Problema 3: Claude Code no reconoce Tailscale MCP

**Síntomas**: Tools no aparecen

**Solución**:
```bash
# Verificar npx funciona
npx -y @tailscale/mcp-server --version

# Verificar API key
echo $TAILSCALE_API_KEY

# Reiniciar Claude Desktop
```

---

## 📊 Valor del Sprint 13

### Beneficios vs Prometheus/Grafana

| Feature | Prometheus/Grafana | Tailscale MCP |
|---------|-------------------|---------------|
| **Setup time** | 6-8h | 3-4h |
| **RAM usage** | +500MB | +50MB |
| **User analytics** | ❌ Manual | ✅ Automático |
| **Claude integration** | ❌ No | ✅ Nativo |
| **Mantainability** | Alta (2 servicios) | Baja (API externa) |

### Casos de Uso Reales

#### Caso 1: Monitorizar acceso dashboard
```
User (Claude Code): "¿Quién está usando el sistema?"
Claude: [usa get_active_users]
Response: "2 usuarios activos:
- user@example.com (user-laptop) - viendo /dashboard
- user2@example.com (iphone) - viendo /insights/optimal-windows"
```

#### Caso 2: Analizar features más usadas
```
User: "¿Qué features son más populares?"
Claude: [usa get_usage_stats]
Response: "Última semana (156 sesiones):
1. Prophet Forecast - 234 accesos
2. SIAR Analysis - 156 accesos
3. Optimal Windows - 89 accesos

Usuario más activo: user@example.com (45 sesiones)"
```

#### Caso 3: Detectar problemas performance
```
User: "¿Hay algún endpoint lento?"
Claude: [usa get_system_performance]
Response: "Sistema healthy (99.8% uptime), pero endpoints lentos:
- /optimize/production/daily: 892ms (recomendar caché)
- /analysis/siar-summary: 234ms (aceptable)"
```

---

## 🔄 Integración con Sprint 11-12

### MCP Server Consolidado

Después Sprint 13, tendrás **2 MCP servers**:

```json
{
  "mcpServers": {
    "chocolate-factory": {
      // 10 tools datos producción (Sprint 11)
      // + 3 tools analytics (Sprint 13)
      "command": "python",
      "args": ["mcp-server/chocolate_factory_mcp.py"]
    },
    "tailscale": {
      // Tools nativos Tailscale
      "command": "npx",
      "args": ["-y", "@tailscale/mcp-server"]
    }
  }
}
```

**Total tools disponibles en Claude Code**: 10 (producción) + 3 (analytics) + 4 (Tailscale) = **17 tools**

### CI/CD Pipeline para Analytics

```yaml
# .forgejo/workflows/test-analytics.yml
name: Test Analytics Service

on:
  push:
    paths:
      - 'src/fastapi-app/services/analytics_service.py'
      - 'src/fastapi-app/api/routers/analytics.py'

jobs:
  test-analytics:
    steps:
      - name: Test Tailscale client
        run: pytest tests/test_tailscale_client.py

      - name: Test analytics endpoints
        run: pytest tests/test_analytics_api.py

      - name: Validate nginx log parsing
        run: python scripts/validate_log_parser.py
```

---

## 📚 Referencias

- **Tailscale API**: https://tailscale.com/api
- **Tailscale MCP**: https://github.com/tailscale/tailscale-mcp
- **Chart.js**: https://www.chartjs.org/docs/
- **nginx logs format**: http://nginx.org/en/docs/http/ngx_http_log_module.html

---

## 🚀 Próximos Pasos después Sprint 13

### Extensiones Futuras

1. **Alerting automático vía MCP**:
   ```python
   # Tool: send_alert si system unhealthy
   await send_telegram_alert("Sistema caído - uptime 85%")
   ```

2. **Exportar reports PDF**:
   ```python
   # Tool: generate_monthly_report
   pdf = await generate_report(month="october")
   # → Analytics mensual automático
   ```

3. **A/B testing dashboard features**:
   ```python
   # Trackear qué widgets miran más usuarios
   # → Priorizar desarrollo features populares
   ```

---

**Fecha creación**: 2025-10-08
**Autor**: Infrastructure Sprint Planning
**Versión**: 1.0 (actualizado con Tailscale MCP)
**Sprint anterior**: Sprint 12 - Forgejo CI/CD
**Mejora clave**: Tailscale MCP en lugar de Prometheus/Grafana (más ligero, mejor integración)
