# Infrastructure Sprints

## Sprint 11: Chatbot BI Conversacional

**Estado**: COMPLETADO (2025-10-10)
**Archivo**: [`SPRINT_11_CHATBOT_BI.md`](./SPRINT_11_CHATBOT_BI.md)

Chatbot conversacional con Claude Haiku. RAG local (keyword matching), 3 endpoints, rate limiting.

**Código**:
- chatbot_context_service.py (524 líneas)
- chatbot_service.py (198 líneas)
- chatbot.py router (237 líneas)

**Características**: Queries sobre producción/precios/clima, responses 300 tokens max, latencia 10-13s, in-memory stats

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

## Sprint 13: Health Monitoring (Pivoted from Analytics)

**Estado**: COMPLETADO (2025-10-21, Pivotado 18:00)
**Archivo**: [`SPRINT_13_TAILSCALE_OBSERVABILITY.md`](./SPRINT_13_TAILSCALE_OBSERVABILITY.md)

Sistema de health monitoring para nodos Tailscale con métricas útiles y accionables. **Pivote Crítico**: Analytics inicial NO aportaba valor → Reenfocado a health monitoring basado en feedback usuario.

**Implementación Completada (Post-Pivote)**:
- TailscaleHealthService con health checks (316 líneas, enfocado)
- HTTP proxy server en sidecar (`socat` puerto 8765) - mantenido de implementación inicial
- 5 endpoints `/health-monitoring/*` (summary, critical, alerts, nodes, uptime)
- 3 APScheduler jobs (métricas cada 5 min, critical check cada 2 min, status log hourly)
- Uptime tracking en InfluxDB + alertas proactivas nodos críticos
- Clasificación nodos: production/development/git (3 críticos, 100% healthy)

**Archivos Eliminados (sin valor)**:
- VPN dashboard (`/vpn`, 632 líneas HTML/CSS/JS)
- parse_nginx_logs() y endpoints analytics sin contexto

**Arquitectura Final (Health Monitoring)**:
- Seguridad: Zero Docker socket exposure (mantenido)
- Valor: Métricas accionables (uptime %, health %, alertas proactivas)
- Autonomía: 100% APScheduler 24/7
- Patrón: HTTP proxy + InfluxDB historical tracking

## Orden de Ejecución

Sprint 11 (Chatbot BI) → Sprint 12 (Forgejo CI/CD) → Sprint 13 (Health Monitoring)

---

---

## Sprint 16: Documentation Integrity & Transparency

**Estado**: IN PROGRESS (2025-10-30)
**Archivo**: [`SPRINT_16_INTEGRITY_TRANSPARENCY.md`](./SPRINT_16_INTEGRITY_TRANSPARENCY.md)

Corrección de documentación que no refleja realidad del código.

**Objetivos**:
- Eliminar claims falsos (ML R² 0.963 circular, endpoints inexistentes)
- Etiquetar valores hardcoded (ROI 1,661€, métricas Prophet)
- Limpiar obsoleto (MLflow, frecuencias entrenamiento incorrectas)
- Añadir disclaimers (limitations, security, test coverage 19%)

**Effort**: ~8 horas (3 días)

---

## Sprint 17: Test Coverage + Business Rules

**Estado**: COMPLETADO (2025-10-30)
**Archivo**: [`SPRINT_17_ROBUSTNESS.md`](./SPRINT_17_ROBUSTNESS.md)

**Fase 1 - Test Coverage:**
- Coverage: 19% → 32%
- Tests: 102 → 134
- Código: +880 líneas
- Coverage servicios: backfill 53%, gap_detector 66%

**Fase 2 - Business Rules:**
- machinery_specs.md: creado (98 líneas)
- production_rules.md: expandido
- optimization_rules.md: creado (113 líneas)

---

## Estado Actual del Proyecto

- Sprints ML Evolution: 01-10 completados
- Sprints Infrastructure: 11-17 completados
- Clean Architecture: refactorizado (Oct 6-29, 2025)
- API Endpoints: 45 (12 routers)
- Tailscale: 3 nodos (git, dev, prod)
- CI/CD: pipeline con rollback
- Tests: 134 (91 passing, 11 E2E failing)
- Coverage: 32%
- APScheduler: 7 jobs

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
