# Infrastructure Sprints

## Sprint 11: Chatbot BI Conversacional - Claude Haiku API

**Estado**: COMPLETADO (2025-10-10)
**Archivo**: [`SPRINT_11_CHATBOT_BI.md`](./SPRINT_11_CHATBOT_BI.md)

Chatbot conversacional integrado en dashboard para consultas en lenguaje natural sobre producción, precios energéticos y clima. Implementa RAG local con keyword matching, 3 endpoints `/chat/*` (ask, stats, health), y rate limiting.

**Implementación**:
- Chatbot service con Claude Haiku API (193 líneas)
- RAG local con keyword matching 7 categorías (287 líneas)
- Widget conversacional integrado en dashboard
- Tests: 5/5 preguntas
- Latencia: 10-13s
- Context: 600-1200 tokens/consulta
- Costo: €1.74-5.21/mes

---

## Sprint 12: Forgejo Self-Hosted + CI/CD + Testing Suite

**Estado**: COMPLETADO (2025-10-20, Fases 1-11)
**Archivo**: [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)

Despliegue de Forgejo self-hosted con CI/CD local, Docker Registry privado y suite completa de tests automatizados. Arquitectura de tres nodos Tailscale separados para git, desarrollo y producción.

**Implementación Completa**:
- Forgejo instance en nodo Git/CI/CD dedicado
- Gitea Actions runners diferenciados (dev/prod)
- Pipelines CI/CD dual environment (develop/main)
- Docker registry privado
- SOPS secrets management
- Testing suite: 102 tests (66 unit/integration/ML + 36 E2E)
- Smoke tests integrados en pipeline (post-deploy validation)
- Automatic rollback on test failures
- Entornos separados (docker-compose.dev.yml / docker-compose.prod.yml)
- Git remotes duales (GitHub + Forgejo)

---

## Sprint 13: Tailscale Observability (HTTP Proxy)

**Estado**: COMPLETADO (2025-10-21)
**Archivo**: [`SPRINT_13_TAILSCALE_OBSERVABILITY.md`](./SPRINT_13_TAILSCALE_OBSERVABILITY.md)

Sistema de observabilidad Tailscale usando HTTP proxy para monitoring autónomo 24/7 y seguridad mejorada. Decisión técnica: HTTP proxy en sidecar (descartados MCP/Skills por falta de autonomía, subprocess CLI por seguridad).

**Implementación Completada**:
- TailscaleAnalyticsService con `httpx` (HTTP client, 455 líneas)
- HTTP proxy server en sidecar (`socat` en puerto 8765, 48 líneas)
- 4 endpoints `/analytics/*` (devices, quota-status, access-logs, dashboard-usage)
- Dashboard VPN completo (`/vpn` → `static/vpn.html`, 176+215+241 líneas)
- 2 APScheduler jobs (analytics cada 15 min, status log cada hora)
- Clasificación dispositivos (own/shared/external) + tracking quota (0/3 usuarios)

**Arquitectura Final (Opción A - HTTP Proxy)**:
- Seguridad: Zero Docker socket exposure (vs subprocess que requería socket mount)
- Latencia: <100ms HTTP proxy (vs +1.5s MCP overhead)
- Autonomía: 100% APScheduler 24/7 (vs MCP/Skills requieren sesión activa)
- Patrón: HTTP estándar contenedor-a-contenedor (consistente con arquitectura)

## Orden de Ejecución

Sprint 11 (Chatbot BI) → Sprint 12 (Forgejo CI/CD) → Sprint 13 (Tailscale Observability)

---

## Estado Actual del Proyecto

- Sprints ML Evolution: 01-10 completados
- Sprint 11 (Infrastructure): Completado
- Sprint 12 (CI/CD + Testing): Completado (Fases 1-11)
- Sprint 13 (Observability): Completado (HTTP Proxy)
- Clean Architecture: Refactorizado (Oct 6, 2025)
- API Endpoints: 37 disponibles (incluye `/chat/*` + `/analytics/*`)
- Tailscale: 3 nodos activos (git, dev, prod) + observability
- CI/CD: Pipeline automatizado con rollback
- Tests: 102 tests (100% passing)
- APScheduler: 13 jobs automatizados (incluye analytics)

**Próximos Sprints**: TBD

---

## Notas de Configuración

### Sprint 11 (Chatbot BI)
1. Obtener API Key: https://console.anthropic.com/
2. Añadir `ANTHROPIC_API_KEY` a `.env`
3. Instalar: `pip install anthropic fastapi-limiter`

### Sprint 12 (Forgejo)
1. Verificar Tailscale sidecar: `docker compose ps chocolate-factory`
2. Planificar volumenes persistentes
3. Generar SSH keys para git

### Sprint 13 (Tailscale Observability)
1. Verificar Tailscale CLI instalado en host: `tailscale version`
2. Crear directorio logs: `mkdir -p ./logs/sidecar && chmod 755 ./logs/sidecar`
3. Verificar nginx logs sidecar: `tail -f ./logs/sidecar/access.log`

---

**Última actualización**: 2025-10-21
