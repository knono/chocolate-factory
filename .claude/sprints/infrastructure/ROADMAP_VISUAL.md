# 🗺️ Roadmap Visual - Infrastructure Sprints

**Estado Actual**: ✅ Sprint 10 COMPLETADO (ML Evolution finalizado)
**Próximo Sprint**: 🎯 Sprint 11 - MCP Server

---

## 📊 Timeline Visual

```
════════════════════════════════════════════════════════════════════════
                    CHOCOLATE FACTORY - INFRASTRUCTURE ROADMAP
════════════════════════════════════════════════════════════════════════

┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Sprint 10  │────▶│  Sprint 11   │────▶│  Sprint 12   │────▶│  Sprint 13   │
│Consolidación│     │  MCP Server  │     │Forgejo CI/CD │     │Tailscale MCP │
│             │     │              │     │              │     │  Analytics   │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      ✅                   🔴                    🔴                    🔴
  COMPLETADO            PLANEADO              PLANEADO             PLANEADO

  Oct 6, 2025         Oct 8-10, 2025       Oct 11-18, 2025      Oct 19-22, 2025

    1 día               2-3 días              1 semana             3-4 días
════════════════════════════════════════════════════════════════════════
```

---

## 🎯 Sprint 11: MCP Server (2-3 días)

### Objetivo
Exponer datos Chocolate Factory como tools MCP nativos para Claude Code



**10 Tools MCP**: Realtime (3) + Predictions (3) + Analysis (2) + Alerts (2)

---

## 🏗️ Sprint 12: Forgejo CI/CD (1 semana)

### Objetivo
Desplegar Forgejo self-hosted + CI/CD + Docker Registry + Tailscale



**Stack**: Forgejo + Gitea Actions + Docker Registry + Tailscale sidecar integration

---

## 📊 Sprint 13: Tailscale Monitoring (3-4 días) ✨

### Objetivo
Analytics de usuarios + métricas sistema usando **Tailscale MCP** (más ligero que Prometheus)



### ¿Por qué Tailscale MCP en lugar de Prometheus?

| Feature | Prometheus + Grafana | Tailscale MCP |
|---------|---------------------|---------------|
| **Setup** | 6-8h (complejo) | 3-4h (simple) |
| **RAM** | +500MB | +50MB |
| **User analytics** | ❌ No disponible | ✅ Nativo |
| **Claude integration** | ❌ Manual | ✅ Tools MCP |
| **Mantenimiento** | Alto (2 servicios) | Bajo (API externa) |

### Arquitectura Sprint 13
```
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE (Client)                      │
│  User: "¿Quién está usando el dashboard?"                   │
└───────────────────────────┬─────────────────────────────────┘
                            │ MCP Protocol
                  ┌─────────┴──────────┐
                  │                    │
         ┌────────▼─────────┐  ┌──────▼──────────────┐
         │ Chocolate Factory│  │  Tailscale MCP      │
         │   MCP Server     │  │  (official)         │
         │  (13 tools)      │  │  (4 tools nativas)  │
         └────────┬─────────┘  └──────┬──────────────┘
                  │                    │
                  └──────────┬─────────┘
                             │
              ┌──────────────┴────────────────┐
              │                               │
     ┌────────▼────────┐         ┌───────────▼──────────┐
     │  FastAPI API    │         │  Tailscale API       │
     │  /analytics/*   │         │  api.tailscale.com   │
     │  3 endpoints    │         │  whois, devices      │
     └────────┬────────┘         └──────────────────────┘
              │
     ┌────────▼────────┐
     │  nginx logs     │  ← access.log parsing
     │  Tailscale      │     + user correlation
     │  sidecar        │
     └─────────────────┘
```

### 3 Nuevos Endpoints Analytics

#### 1. `GET /analytics/access-logs`
```json
{
  "logs": [
    {
      "user": "user@example.com",
      "device": "user-laptop",
      "endpoint": "/dashboard",
      "timestamp": "2025-10-08T14:32:15Z"
    }
  ],
  "summary": {
    "unique_users": 3,
    "total_requests": 1247
  }
}
```

#### 2. `GET /analytics/dashboard-usage`
```json
{
  "most_viewed_cards": [
    {"card": "Pronóstico Semanal", "views": 289},
    {"card": "Dashboard Predictivo", "views": 156}
  ],
  "user_sessions": [
    {
      "user": "user@example.com",
      "sessions": 45,
      "favorite_features": ["Prophet forecast", "SIAR analysis"]
    }
  ]
}
```

#### 3. `GET /analytics/system-health-history`
```json
{
  "uptime_last_7d": "99.8%",
  "avg_api_response_ms": 42,
  "slowest_endpoints": [
    {"/optimize/production/daily": "892ms"}
  ]
}
```

### 3 Custom MCP Tools (Analytics)

**Tool 1**: `get_active_users()`
- Quién usa el sistema ahora mismo
- Tailscale API + nginx logs últimos 5 min

**Tool 2**: `get_usage_stats(days=7)`
- Features más usadas
- Sesiones por usuario
- Tiempo promedio sesión

**Tool 3**: `get_system_performance()`
- Uptime 7 días
- Endpoints lentos
- Tasa errores

### Dashboard Widget
```
┌────────────────────────────────────────┐
│  📊 Analytics Última Semana            │
├────────────────────────────────────────┤
│  Sesiones totales: 156                 │
│  Usuarios únicos: 3                    │
│                                        │
│  [Chart.js: accesos por día]          │
│                                        │
│  Features más usadas:                  │
│  🔮 Prophet Forecast (234)             │
│  📊 SIAR Analysis (156)                │
│  ⚡ Optimal Windows (89)               │
└────────────────────────────────────────┘
```

### Casos de Uso Reales

#### Caso 1: Monitorizar acceso
```
User: "¿Quién está usando el dashboard?"
Claude: [usa get_active_users]
Response: "2 usuarios activos:
- user@example.com (user-laptop) → /dashboard
- user2@example.com (iphone) → /insights"
```

#### Caso 2: Features populares
```
User: "¿Qué features son más populares?"
Claude: [usa get_usage_stats]
Response: "Top 3 última semana:
1. Prophet Forecast - 234 accesos
2. SIAR Analysis - 156 accesos
3. Optimal Windows - 89 accesos"
```

#### Caso 3: Detectar lentitud
```
User: "¿Hay endpoints lentos?"
Claude: [usa get_system_performance]
Response: "Sistema 99.8% uptime, pero lentos:
- /optimize/production/daily: 892ms ⚠️
- /analysis/siar-summary: 234ms ✅"
```







## 🔄 Stack Completo Post-Sprint 13

```
┌────────────────────────────────────────────────────────────────┐
│                         USER (Tailnet)                         │
│  Claude Code + Tailscale MCP + your-hostname.your-tailnet.ts.net       │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────────────┐
│                    MCP LAYER (17 tools)                        │
│  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │ Chocolate Factory    │  │ Tailscale MCP (official)     │  │
│  │ - 10 tools producción│  │ - whois, devices, status     │  │
│  │ - 3 tools analytics  │  │ - 4 tools nativas            │  │
│  └──────────────────────┘  └──────────────────────────────┘  │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────────────┐
│                     APPLICATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   FastAPI    │  │   Forgejo    │  │  Analytics   │        │
│  │   30 API     │  │   Git + CI   │  │  Service     │        │
│  │   endpoints  │  │   Pipelines  │  │  Tailscale   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────────────┐
│                     INFRASTRUCTURE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   InfluxDB   │  │Docker Registry│  │  Tailscale   │        │
│  │   Time series│  │   Private    │  │   Sidecar    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

**Total componentes**:
- 17 MCP tools (13 custom + 4 Tailscale nativas)
- 33 API endpoints (30 existentes + 3 analytics)
- 6 servicios Docker (FastAPI, InfluxDB, Forgejo, Runner, Registry, Tailscale)


**Fecha creación**: 2025-10-08
**Última actualización**: 2025-10-08 (actualizado Sprint 13 con Tailscale MCP)
