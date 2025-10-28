# SPRINT 13: Tailscale Health Monitoring

**Status**: COMPLETED
**Date**: Oct 21, 2025
**Duration**: 8 hours

---

## Objective

Monitor Tailscale node status (online/offline, uptime). 24/7 autonomous operation.

---

## Implementation

### HTTP Proxy (Sidecar)

**File**: `docker/tailscale-http-server.sh`

socat TCP listener on localhost:8765 exposes Tailscale CLI via HTTP:
- `GET /status` → `tailscale status --json`
- `GET /whois/<ip>` → `tailscale whois <ip>`

Integration:
- Installed in `docker/tailscale-sidecar.Dockerfile`
- Launched in `docker/tailscale-start.sh`

### Backend Services

**TailscaleHealthService** (`services/tailscale_health_service.py`, 315 lines)

Methods:
- `get_tailscale_status()` - HTTP GET http://chocolate-factory:8765/status
- `get_nodes_health()` - Parse peers, classify by hostname
- `store_health_metrics(nodes)` - Write Point to InfluxDB bucket "analytics"
- `calculate_uptime(hostname, hours=24)` - Query InfluxDB uptime %

**HealthLogsService** (`services/health_logs_service.py`, 221 lines)

Methods:
- `generate_event_logs()` - Create logs from current state
- `filter_logs(severity, event_type)` - Filter by criteria
- `paginate_logs(page, per_page=20)` - Paginate results

### API Endpoints

**File**: `api/routers/health_monitoring.py` (269 lines)

Endpoints:
```
GET /health-monitoring/summary
  → {total_nodes, online_nodes, offline_nodes, critical_nodes: {health_percentage}}

GET /health-monitoring/nodes?project_only=true
  → [{hostname, ip, online, node_type, os, last_seen, uptime_24h}, ...]
  → project_only=true: 3 critical nodes only
  → project_only=false: all nodes

GET /health-monitoring/critical
  → {git, dev, prod} status

GET /health-monitoring/alerts
  → Active alerts (nodes offline >2 min)

GET /health-monitoring/logs?page=1&severity=&event_type=
  → Paginated event logs (20/page)
  → Filters: severity (ok|warning|critical), event_type (all|health_check|node_online|node_offline|alert)
```

### APScheduler Jobs

**File**: `tasks/health_monitoring_jobs.py` (124 lines)

Jobs registered in `scheduler_config.py`:

1. `collect_health_metrics()` - Every 5 min
   - Fetch status via socat
   - Write Point records to InfluxDB ("analytics" bucket)
   - Measurement: `tailscale_health`
   - Tags: hostname, node_type, os
   - Fields: online (0/1), ip, latency_ms

2. `check_critical_nodes()` - Every 2 min
   - Check if any critical node offline
   - Log ERROR for production node down
   - Log WARNING for other critical nodes down

3. `log_health_status()` - Every hour
   - Log aggregated health report

### InfluxDB Storage

**Bucket**: analytics

**Measurement**: tailscale_health

**Data**:
```
Point("tailscale_health")
  .tag("hostname", "git")
  .tag("node_type", "production|development|git|other")
  .tag("os", "Linux|Darwin|Windows")
  .field("online", 1 or 0)
  .field("ip", "100.x.x.x")
```

Query example (uptime 24h):
```flux
from(bucket: "analytics")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "tailscale_health")
  |> filter(fn: (r) => r["hostname"] == "git")
  |> filter(fn: (r) => r["_field"] == "online")
  |> mean()
```

### Critical Nodes Classification

Automatic detection by hostname:
- "git" → node_type = "git"
- "dev" → node_type = "development"
- "chocolate-factory" (without "dev") → node_type = "production"
- Other → node_type = "other"

Monitored nodes:
- git (Forgejo)
- chocolate-factory-dev (Development)
- chocolate-factory (Production)

### Dashboard

**File**: `static/vpn.html` (7.4 KB)

Access:
- Local: http://localhost:8000/vpn
- Via Tailnet: https://<TAILSCALE_DOMAIN_GIT>/vpn (proxied through git sidecar)

Shows:
- Health summary
- Critical nodes grid
- Node details table
- Event logs with pagination

---

## Security with socat

**Problem**: Access Tailscale CLI without Docker socket or subprocess in FastAPI.

**Solution**: HTTP proxy in isolated sidecar.

**How it works**:
1. socat listens on localhost:8765 (sidecar container only)
2. For each request, forks process and runs handler shell script
3. Handler executes: `tailscale status --json` or `tailscale whois <ip>`
4. Returns HTTP response
5. FastAPI makes standard HTTP request via httpx.Client
6. No subprocess in FastAPI, no Docker socket, no shell injection risk

**Benefits**:
- Process isolation (CLI runs in sidecar, not FastAPI)
- No Docker socket exposure
- No subprocess in FastAPI process memory
- Read-only (no write capability)

---

## Files Created/Modified

Backend:
- `services/tailscale_health_service.py` (315 lines)
- `services/health_logs_service.py` (221 lines)
- `api/routers/health_monitoring.py` (269 lines)
- `tasks/health_monitoring_jobs.py` (124 lines)

Infrastructure:
- `docker/tailscale-http-server.sh` (48 lines)
- Integration: `docker/tailscale-sidecar.Dockerfile`, `docker/tailscale-start.sh`

Frontend:
- `static/vpn.html` (7.4 KB)

Configuration:
- `api/routers/__init__.py` (export router)
- `tasks/scheduler_config.py` (register jobs)
- `docker-compose.override.yml` (shared volume tailscale_state)

---

## Limitations

- Event logs generated from current state (no true history)
- Uptime calculation requires accumulated InfluxDB data
- No persistent alert storage (memory-only during job run)

---

**Version**: 3.0 (Implementation documented)
**Created**: Oct 21, 2025
**Updated**: Oct 28, 2025
