# 🎯 SPRINT 13: Tailscale Observability - Enfoque Híbrido

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 MEDIA
> **Prerequisito**: Sprint 11-12 completados, Tailscale sidecar operacional
> **Duración estimada**: 2-3 días (12-16 horas)
> **Fecha inicio planeada**: 2025-10-21

---

## 📋 Objetivo

**Implementar observabilidad Tailscale con enfoque híbrido**: sistema práctico nativo 24/7 + MCP learning educacional.

### ¿Por qué Enfoque Híbrido?

**Problema**: Elegir entre utilidad práctica vs conocimiento MCP

**Solución**: Implementar ambos en fases
1. **Fase 1 (Práctico)**: Monitoring nativo + nginx logs → Dashboard 24/7
2. **Fase 2 (Educacional)**: MCP Tailscale → Aprender ecosistema MCP

**Resultado**: Observabilidad funcional + conocimiento MCP adquirido

---

## 📦 Arquitectura Propuesta

### Stack Completo

```
┌──────────────────────────────────────────┐
│  Fase 1: Sistema Nativo (Práctico)      │
├──────────────────────────────────────────┤
│                                          │
│  Tailscale CLI                           │
│  ├─ tailscale status --json              │
│  └─ tailscale whois <ip>                 │
│           ↓                              │
│  AnalyticsService                        │
│  ├─ Parse nginx logs                     │
│  ├─ Correlate w/ Tailscale CLI          │
│  └─ Store InfluxDB                       │
│           ↓                              │
│  Dashboard Widget (24/7)                 │
│  └─ Analytics última semana              │
│                                          │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Fase 2: MCP Learning (Educacional)     │
├──────────────────────────────────────────┤
│                                          │
│  Tailscale MCP Server                    │
│  ├─ @tailscale/mcp-server                │
│  └─ Requiere Claude Desktop              │
│           ↓                              │
│  Comparativa:                            │
│  ├─ MCP tools vs CLI nativo              │
│  ├─ Performance comparison               │
│  └─ Documentar aprendizajes              │
│           ↓                              │
│  Decisión Final:                         │
│  └─ Quedarse con solución preferida      │
│                                          │
└──────────────────────────────────────────┘
```

---

## 🎯 Fase 1: Sistema Nativo (Prioridad Alta)

### 1.1. Analytics Service

**Archivo**: `src/fastapi-app/services/tailscale_analytics_service.py`

```python
import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

class TailscaleAnalyticsService:
    """
    Observabilidad Tailscale usando comandos CLI nativos.
    No requiere API key, usa tailscale CLI ya instalado.
    """

    async def get_active_devices(self) -> List[Dict]:
        """
        Lista dispositivos conectados a la Tailnet.

        Command: tailscale status --json
        """
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)
        devices = []

        for peer in data.get("Peer", {}).values():
            if peer.get("Online", False):
                devices.append({
                    "hostname": peer.get("HostName"),
                    "ip": peer.get("TailscaleIPs", [])[0],
                    "os": peer.get("OS"),
                    "online": True,
                    "last_seen": peer.get("LastSeen")
                })

        return devices

    async def whois_ip(self, ip: str) -> Dict[str, Any]:
        """
        Identifica usuario/dispositivo por IP.

        Command: tailscale whois <ip>
        """
        result = subprocess.run(
            ["tailscale", "whois", ip],
            capture_output=True,
            text=True
        )

        # Parse output (formato: hostname\nuser@example.com)
        lines = result.stdout.split('\n')
        return {
            "hostname": lines[0] if len(lines) > 0 else None,
            "user": lines[1] if len(lines) > 1 else None,
            "ip": ip
        }

    async def parse_nginx_logs(self, hours: int = 24) -> List[Dict]:
        """
        Parse nginx access.log del sidecar Tailscale.

        Log format: 100.x.x.x - - [08/Oct/2025:14:32:15] "GET /dashboard" 200
        """
        log_file = Path("/logs/sidecar/access.log")

        if not log_file.exists():
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        access_logs = []

        with open(log_file, 'r') as f:
            for line in f:
                parsed = self._parse_nginx_line(line)
                if parsed and parsed["timestamp"] > cutoff:
                    # Enrich con Tailscale whois
                    user_info = await self.whois_ip(parsed["ip"])
                    parsed["user"] = user_info.get("user")
                    parsed["device"] = user_info.get("hostname")
                    access_logs.append(parsed)

        return access_logs

    def _parse_nginx_line(self, line: str) -> Dict:
        """Parse single nginx log line."""
        # Regex pattern para nginx log format
        pattern = r'(\d+\.\d+\.\d+\.\d+) .* \[(.+?)\] "(\w+) (.+?) HTTP.*?" (\d+)'
        match = re.match(pattern, line)

        if match:
            ip, timestamp_str, method, endpoint, status = match.groups()
            return {
                "ip": ip,
                "timestamp": datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S"),
                "method": method,
                "endpoint": endpoint,
                "status": int(status)
            }
        return None

    async def store_analytics(self, log: Dict):
        """Guarda analytics en InfluxDB para históricos."""
        point = Point("tailscale_access") \
            .tag("user", log.get("user", "unknown")) \
            .tag("device", log.get("device", "unknown")) \
            .tag("endpoint", log["endpoint"]) \
            .field("status", log["status"]) \
            .time(log["timestamp"])

        await self.influx_client.write(point)
```

---

### 1.2. API Endpoints

**Archivo**: `src/fastapi-app/api/routers/analytics.py`

```python
from fastapi import APIRouter, Query
from services.tailscale_analytics_service import TailscaleAnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/devices")
async def get_active_devices():
    """
    Lista dispositivos activos en Tailnet.

    Uses: tailscale status --json
    """
    service = TailscaleAnalyticsService()
    devices = await service.get_active_devices()

    return {
        "devices": devices,
        "total": len(devices)
    }

@router.get("/access-logs")
async def get_access_logs(hours: int = Query(default=24, ge=1, le=168)):
    """
    Access logs últimas N horas con usuario Tailscale identificado.

    Uses: nginx logs + tailscale whois
    """
    service = TailscaleAnalyticsService()
    logs = await service.parse_nginx_logs(hours=hours)

    # Analytics summary
    unique_users = len(set(log["user"] for log in logs if log["user"]))
    unique_devices = len(set(log["device"] for log in logs if log["device"]))

    return {
        "logs": logs,
        "summary": {
            "total_requests": len(logs),
            "unique_users": unique_users,
            "unique_devices": unique_devices,
            "period_hours": hours
        }
    }

@router.get("/dashboard-usage")
async def get_dashboard_usage(days: int = Query(default=7, ge=1, le=30)):
    """
    Métricas de uso dashboard desde InfluxDB.

    Returns:
    - Most viewed endpoints
    - Peak hours
    - User sessions
    """
    # Query InfluxDB metrics
    query = f"""
    from(bucket: "analytics")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "tailscale_access")
      |> group(columns: ["endpoint"])
      |> count()
    """

    # Process results...
    return {
        "most_viewed_endpoints": [...],
        "peak_hours": [...],
        "active_users": [...]
    }
```

---

### 1.3. Dashboard Widget

**Archivo**: `static/js/components/analytics-widget.js`

```javascript
async function renderAnalyticsWidget() {
    const response = await fetch('/analytics/access-logs?hours=168');
    const data = await response.json();

    const container = document.getElementById('analytics-widget');

    container.innerHTML = `
        <div class="card analytics-card">
            <h3>📊 Analytics Última Semana</h3>

            <div class="metrics-grid">
                <div class="metric">
                    <span class="label">Accesos Totales:</span>
                    <span class="value">${data.summary.total_requests}</span>
                </div>

                <div class="metric">
                    <span class="label">Usuarios Únicos:</span>
                    <span class="value">${data.summary.unique_users}</span>
                </div>

                <div class="metric">
                    <span class="label">Dispositivos:</span>
                    <span class="value">${data.summary.unique_devices}</span>
                </div>
            </div>

            <div class="recent-activity">
                <h4>Actividad Reciente:</h4>
                <ul>
                    ${data.logs.slice(0, 5).map(log => `
                        <li>
                            <strong>${log.user || 'Unknown'}</strong>
                            (${log.device || 'Unknown'})
                            → ${log.endpoint}
                            <span class="timestamp">${formatTime(log.timestamp)}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        </div>
    `;
}

// Refresh cada 5 minutos
setInterval(renderAnalyticsWidget, 300000);
```

**Añadir a `static/index.html`**:
```html
<!-- Analytics Widget -->
<div id="analytics-widget"></div>
<script src="js/components/analytics-widget.js"></script>
```

---

### 1.4. APScheduler Job

**Archivo**: `src/fastapi-app/tasks/analytics_jobs.py`

```python
async def collect_analytics():
    """
    Job APScheduler: Recolectar analytics cada 15 minutos.

    - Parse nginx logs
    - Enrich con Tailscale CLI
    - Store InfluxDB
    """
    service = TailscaleAnalyticsService()
    logs = await service.parse_nginx_logs(hours=1)  # Última hora

    for log in logs:
        await service.store_analytics(log)

    logger.info(f"Analytics collected: {len(logs)} accesses")

# Registrar en scheduler_config.py
scheduler.add_job(
    collect_analytics,
    trigger="interval",
    minutes=15,
    id="analytics_collection",
    name="Tailscale Analytics Collection"
)
```

---

## 🎓 Fase 2: MCP Learning (Opcional Educacional)

### 2.1. Instalación Tailscale MCP

**Setup**:
```bash
# 1. Generar API key Tailscale
# https://login.tailscale.com/admin/settings/keys

# 2. Añadir a .env
TAILSCALE_API_KEY=tskey-api-xxxxx
TAILNET=your-tailnet.ts.net

# 3. Configurar Claude Desktop
cat ~/.config/Claude/claude_desktop_config.json
```

**Config**:
```json
{
  "mcpServers": {
    "tailscale": {
      "command": "npx",
      "args": ["-y", "@tailscale/mcp-server"],
      "env": {
        "TAILSCALE_API_KEY": "${TAILSCALE_API_KEY}",
        "TAILNET": "${TAILNET}"
      }
    }
  }
}
```

---

### 2.2. Tools MCP Disponibles

**Nativos de @tailscale/mcp-server**:

1. **`tailscale_list_devices`**
   - Lista dispositivos Tailnet
   - Equivalente CLI: `tailscale status --json`

2. **`tailscale_get_device`**
   - Info detallada dispositivo
   - Equivalente CLI: `tailscale status <hostname>`

3. **`tailscale_whois`**
   - Identificar usuario por IP
   - Equivalente CLI: `tailscale whois <ip>`

4. **`tailscale_get_status`**
   - Estado conexión Tailscale
   - Equivalente CLI: `tailscale status`

---

### 2.3. Ejercicio Comparativo

**Objetivo**: Comparar MCP vs CLI nativo

**Test 1: Listar dispositivos**
```bash
# CLI nativo
time tailscale status --json

# MCP (en Claude Code)
User: "¿Qué dispositivos están en la Tailnet?"
Claude: [usa tailscale_list_devices]
# → Medir latencia respuesta
```

**Test 2: Identificar usuario**
```bash
# CLI nativo
time tailscale whois 100.x.x.x

# MCP
User: "¿Quién es 100.x.x.x?"
Claude: [usa tailscale_whois]
# → Comparar resultados
```

**Documentar**:
```markdown
## Comparativa MCP vs CLI

| Operación | CLI Nativo | MCP Tailscale | Diferencia |
|-----------|------------|---------------|------------|
| List devices | 0.2s | 1.5s | +1.3s (overhead) |
| Whois IP | 0.1s | 1.2s | +1.1s |
| Accesibilidad | Terminal | Claude Code | MCP más natural |
| Autonomía | ✅ 24/7 | ❌ Solo con Claude Desktop | CLI mejor para automation |

**Conclusión**:
- CLI nativo: Mejor para sistema autónomo 24/7
- MCP: Mejor para consultas ad-hoc conversacionales
```

---

## 📝 Plan de Implementación

### Fase 1: Sistema Nativo (8-10 horas) - PRIORIDAD

- [ ] **(2h)** Crear `services/tailscale_analytics_service.py`
  - [ ] Implementar `get_active_devices()` (CLI)
  - [ ] Implementar `whois_ip()` (CLI)
  - [ ] Implementar `parse_nginx_logs()`
  - [ ] Implementar `store_analytics()` (InfluxDB)

- [ ] **(2h)** Crear `api/routers/analytics.py`
  - [ ] Endpoint `GET /analytics/devices`
  - [ ] Endpoint `GET /analytics/access-logs`
  - [ ] Endpoint `GET /analytics/dashboard-usage`

- [ ] **(2h)** Dashboard widget
  - [ ] Crear `static/js/components/analytics-widget.js`
  - [ ] Integrar en `index.html`
  - [ ] CSS styling

- [ ] **(1h)** APScheduler job
  - [ ] Job `collect_analytics()` cada 15 min
  - [ ] Test recolección datos

- [ ] **(1h)** Nginx logs persistence
  - [ ] Bind mount: `./logs/sidecar:/var/log/nginx`
  - [ ] Test parseo logs

### Fase 2: MCP Learning (4-6 horas) - OPCIONAL

- [ ] **(1h)** Setup Tailscale MCP
  - [ ] Generar API key
  - [ ] Configurar `claude_desktop_config.json`
  - [ ] Test tools en Claude Code

- [ ] **(2h)** Ejercicio comparativo
  - [ ] Test 1: List devices (CLI vs MCP)
  - [ ] Test 2: Whois (CLI vs MCP)
  - [ ] Test 3: Latencia comparison
  - [ ] Documentar resultados

- [ ] **(1-2h)** Documentación aprendizajes
  - [ ] `docs/MCP_TAILSCALE_LEARNING.md`
  - [ ] Pros/cons cada enfoque
  - [ ] Recomendación final

- [ ] **(opcional)** Decisión mantener o remover MCP
  - Si útil: Mantener ambos
  - Si no: Documentar y remover MCP setup

---

## 🧪 Criterios de Éxito

### Fase 1 (Obligatorio)

- ✅ **3 endpoints analytics** operacionales
- ✅ **Dashboard widget** muestra datos reales
- ✅ **APScheduler job** recolecta cada 15 min
- ✅ **Nginx logs** persisten entre reinicios
- ✅ **InfluxDB** guarda históricos analytics

### Fase 2 (Opcional)

- ✅ **Tailscale MCP** instalado y funcional
- ✅ **4 tools MCP** funcionan en Claude Code
- ✅ **Comparativa** documentada (CLI vs MCP)
- ✅ **Decisión final** tomada y documentada

---

## 💰 Análisis Comparativo

### Soluciones Disponibles

| Solución | Setup | RAM | Autonomía | Integración Claude | Costo |
|----------|-------|-----|-----------|-------------------|-------|
| **Prometheus/Grafana** | 6-8h | +500MB | ✅ 24/7 | ❌ No | €0 |
| **Tailscale MCP** | 2h | +10MB | ❌ Solo con Claude Desktop | ✅ Nativo | €0 |
| **CLI Nativo (Híbrido)** | 4h | +5MB | ✅ 24/7 | ⚠️ Indirecto (via API) | €0 |

**Recomendación**: CLI Nativo (Fase 1) + MCP Learning (Fase 2 opcional)

---

## 🚧 Problemas Potenciales

### Problema 1: Nginx logs no accesibles

**Síntomas**: Permission denied al leer `/logs/sidecar/access.log`

**Solución**:
```bash
# Crear directorio bind mount
mkdir -p ./logs/sidecar

# Ajustar permisos
chmod -R 755 ./logs/sidecar/

# Actualizar docker-compose.yml
volumes:
  - ./logs/sidecar:/var/log/nginx:rw
```

### Problema 2: Tailscale CLI no funciona en container

**Síntomas**: `tailscale: command not found`

**Solución**:
```dockerfile
# Dockerfile FastAPI
RUN curl -fsSL https://tailscale.com/install.sh | sh

# O ejecutar desde host
# y compartir socket /var/run/tailscale/tailscaled.sock
```

### Problema 3: MCP Tailscale requiere API key

**Síntomas**: "TAILSCALE_API_KEY not set"

**Solución**:
```bash
# 1. Generar key en Tailscale admin
https://login.tailscale.com/admin/settings/keys

# 2. Añadir a .env
TAILSCALE_API_KEY=tskey-api-xxxxx

# 3. Verificar en config
cat ~/.config/Claude/claude_desktop_config.json | grep TAILSCALE
```

---

## 📊 Valor del Sprint 13

### Beneficios Inmediatos (Fase 1)

1. **Observabilidad 24/7**: Saber quién usa el sistema
2. **Dashboard analytics**: Métricas visuales históricas
3. **Autonomous monitoring**: APScheduler automático
4. **Zero dependencies**: Solo CLI nativo + nginx logs
5. **InfluxDB integration**: Históricos para análisis

### Beneficios Educacionales (Fase 2)

1. **Aprender MCP externo**: Experiencia real con third-party MCP
2. **Comparativa práctica**: Entender trade-offs MCP vs nativo
3. **Conocimiento ecosistema**: Preparación para futuros MCPs
4. **Decisión informada**: Elegir mejor solución basado en datos

---

## 📚 Referencias

### Fase 1 (Nativo)
- **Tailscale CLI**: https://tailscale.com/kb/1080/cli
- **nginx logs**: http://nginx.org/en/docs/http/ngx_http_log_module.html
- **InfluxDB Python**: https://influxdb-client.readthedocs.io/

### Fase 2 (MCP)
- **Tailscale MCP**: https://github.com/tailscale/tailscale-mcp
- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **Anthropic MCP**: https://docs.anthropic.com/en/docs/mcp

---

## 🔄 Próximos Pasos

**Después Fase 1**:
- Dashboard analytics operacional 24/7
- Decisión: ¿Continuar con Fase 2 MCP?

**Después Fase 2 (si se hace)**:
- Comparativa documentada
- Elegir mantener MCP o solo nativo
- Actualizar CLAUDE.md con decisión

**Extensiones Futuras**:
- Alerting automático (Telegram/Discord)
- Exportar reports PDF mensuales
- A/B testing dashboard features

---

**Fecha creación**: 2025-10-10
**Autor**: Infrastructure Sprint Planning
**Versión**: 2.0 (Enfoque Híbrido: Nativo + MCP Learning)
**Sprint anterior**: Sprint 12 - Forgejo CI/CD
**Mejora clave**: Práctico (24/7) + Educacional (MCP) en lugar de solo MCP
