# 🏗️ Infrastructure Sprints - Chocolate Factory

> **Objetivo**: Evolucionar infraestructura del proyecto con integración MCP, CI/CD local, y mejoras operacionales.

---

## 📋 Índice de Sprints

### Sprint 11: MCP Server - Chocolate Factory Integration ✨
**Estado**: 🔴 NO INICIADO
**Prioridad**: 🔴 ALTA
**Duración estimada**: 2-3 días (12-16 horas)
**Archivo**: [`SPRINT_11_MCP_SERVER.md`](./SPRINT_11_MCP_SERVER.md)

**Objetivo**: Implementar MCP (Model Context Protocol) server para exponer datos del proyecto como herramienta nativa para Claude Code.

**Entregables clave**:
- MCP server Python con 8-10 tools
- Integración con API FastAPI existente
- Configuración Claude Desktop
- Documentación y ejemplos de uso

**Valor**: Claude Code puede consultar datos de producción, precios, predicciones sin APIs HTTP manuales.

---

### Sprint 12: Forgejo Self-Hosted + CI/CD Local 🔐
**Estado**: 🔴 NO INICIADO
**Prioridad**: 🟡 MEDIA
**Duración estimada**: 1 semana (20-24 horas)
**Archivo**: [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)

**Objetivo**: Desplegar Forgejo self-hosted con CI/CD local, integrado con Tailscale para acceso seguro.

**Entregables clave**:
- Forgejo instance en Docker
- Gitea Actions runners
- Pipelines tests automatizados
- Docker registry privado
- Integración Tailscale

**Valor**: Control total sobre datos, CI/CD sin exponer GitHub, registry privado para imágenes Docker.

---

### Sprint 13: Tailscale Monitoring + Analytics MCP 📊
**Estado**: 🔴 NO INICIADO
**Prioridad**: 🟡 MEDIA-ALTA
**Duración estimada**: 3-4 días (16-20 horas)
**Archivo**: [`SPRINT_13_TAILSCALE_MONITORING.md`](./SPRINT_13_TAILSCALE_MONITORING.md)

**Objetivo**: Usar Tailscale MCP para analytics de usuarios + métricas sistema (más ligero que Prometheus/Grafana).

**Entregables**:
- Tailscale API integration
- Analytics service (access logs, usage stats)
- 3 MCP tools analytics custom
- Dashboard analytics widget
- System performance metrics

**Valor**: Saber quién usa el sistema, features populares, performance endpoints. Todo integrado con Claude Code vía MCP.

---

## 🎯 Estrategia de Ejecución

### Orden Recomendado

```
Sprint 11 (MCP Server) → Sprint 12 (Forgejo CI/CD) → Sprint 13 (Monitoring)
      ↓                        ↓                            ↓
  2-3 días                  1 semana                   1 semana
  Valor inmediato           Infraestructura            Nice-to-have
```

### Filosofía

1. **MCP primero**: Valor inmediato para desarrollo con Claude Code
2. **CI/CD después**: Tests automatizados + registry privado
3. **Monitoring opcional**: Cuando sistema esté en producción 24/7

---

## 📊 Comparativa Sprints

| Sprint | Complejidad | Valor Inmediato | Dependencias | Riesgo |
|--------|-------------|-----------------|--------------|--------|
| Sprint 11 (MCP) | Media | ⭐⭐⭐⭐⭐ | Ninguna | Bajo |
| Sprint 12 (Forgejo) | Alta | ⭐⭐⭐⭐ | Ninguna | Medio |
| Sprint 13 (Tailscale) | Media | ⭐⭐⭐⭐ | Sprint 11, Tailscale activo | Bajo |

---

## 🚀 Sprint 11 (MCP) - Vista Rápida

### ¿Por qué MCP primero?

- ✅ **Valor inmediato**: Claude Code puede consultar datos chocolate factory directamente
- ✅ **Bajo riesgo**: No modifica sistema existente, solo añade capa MCP
- ✅ **Rápido**: 2-3 días vs 1 semana para Forgejo
- ✅ **Prueba de concepto**: Si funciona bien, facilita otros sprints

### Ejemplo de uso MCP

```python
# Claude Code podrá hacer directamente:
User: "¿Cuál es el precio eléctrico actual?"
Claude: [usa tool mcp_get_current_price]
Response: 0.1234 €/kWh (periodo P2 - Llano)

User: "¿Qué ventanas óptimas tenemos esta semana?"
Claude: [usa tool mcp_get_optimal_windows]
Response: Lun 02-05h (0.06€), Mar 01-06h (0.07€)...
```

---

## 🔧 Sprint 12 (Forgejo) - Vista Rápida

### ¿Por qué Forgejo?

- ✅ **Control total**: Datos sensibles en tu infraestructura
- ✅ **CI/CD local**: Tests automatizados sin GitHub Actions
- ✅ **Registry privado**: Imágenes Docker sin Docker Hub
- ✅ **Tailscale ready**: Ya tienes sidecar configurado
- ✅ **Open source**: Forgejo es fork community-driven de Gitea

### Stack propuesto

```yaml
services:
  forgejo:          # Git server + UI
  gitea-runner:     # CI/CD runner
  docker-registry:  # Private registry
  tailscale:        # Secure access (reuse existing)
```

---

## 📝 Notas para Claude Code

### Al iniciar Sprint 11 (MCP)
1. Leer [`SPRINT_11_MCP_SERVER.md`](./SPRINT_11_MCP_SERVER.md)
2. Verificar endpoints disponibles: `curl http://localhost:8000/openapi.json`
3. Instalar dependencias MCP: `pip install mcp anthropic-mcp`
4. Crear directorio: `mkdir -p mcp-server/`

### Al iniciar Sprint 12 (Forgejo)
1. Leer [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)
2. Verificar Tailscale sidecar: `docker compose ps chocolate-factory`
3. Planificar volumenes persistentes
4. Generar SSH keys para git

---

## 🔄 Estado Actual del Proyecto

**Sprints ML Evolution**: ✅ 01-10 COMPLETADOS
**Clean Architecture**: ✅ Refactorizado (Oct 6, 2025)
**API Endpoints**: 30 disponibles
**Tailscale**: ✅ Sidecar activo
**Docker Compose**: ✅ 3 servicios running

**Próximo Sprint**: Sprint 11 - MCP Server
**Preparación**: Sistema estable, listo para extensión

---

**Última actualización**: 2025-10-08
**Autor**: Infrastructure Planning Team
**Versión**: 1.0
