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

## Sprint 12: Forgejo Self-Hosted + CI/CD con Tres Nodos Tailscale

**Estado**: NO INICIADO
**Archivo**: [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)

Despliegue de Forgejo self-hosted con CI/CD local y Docker Registry privado. Arquitectura de tres nodos Tailscale separados para git, desarrollo y producción.

**Componentes**:
- Forgejo instance en nodo Git/CI/CD dedicado
- Gitea Actions runners diferenciados (dev/prod)
- Pipelines CI/CD dual environment (develop/main)
- Docker registry privado
- ACLs Tailscale por nodo
- Entornos separados (docker-compose.dev.yml / docker-compose.prod.yml)
- Git remotes duales (GitHub + Forgejo)

---

## Sprint 13: Tailscale Observability

**Estado**: NO INICIADO
**Archivo**: [`SPRINT_13_TAILSCALE_OBSERVABILITY.md`](./SPRINT_13_TAILSCALE_OBSERVABILITY.md)

Sistema de observabilidad para Tailscale con dos fases: implementación nativa funcional y exploración opcional de MCP.

**Fase 1**:
- Analytics service con CLI nativo (tailscale status, whois)
- Parser nginx logs con correlación Tailscale
- 3 endpoints API analytics
- Dashboard widget
- APScheduler job automático

**Fase 2 (Opcional)**:
- Instalación Tailscale MCP (@tailscale/mcp-server)
- Comparativa MCP vs CLI nativo
- Documentación técnica

## Orden de Ejecución

Sprint 11 (Chatbot BI) → Sprint 12 (Forgejo CI/CD) → Sprint 13 (Observability)

---

## Estado Actual del Proyecto

- Sprints ML Evolution: 01-09 completados
- Sprint 11 (Infrastructure): Completado
- Clean Architecture: Refactorizado (Oct 6, 2025)
- API Endpoints: 33 disponibles (incluye `/chat/*`)
- Tailscale: Sidecar activo
- Docker Compose: 3 servicios running

**Próximo**: Sprint 12 - Forgejo CI/CD

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

---

**Última actualización**: 2025-10-10
