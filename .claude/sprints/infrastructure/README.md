# 🏗️ Infrastructure Sprints - Chocolate Factory

> **Objetivo**: Evolucionar infraestructura del proyecto con Chatbot BI conversacional, CI/CD local, y mejoras operacionales.

---

## 📋 Índice de Sprints

### Sprint 11: Chatbot BI Conversacional - Claude Haiku API ✅
**Estado**: ✅ COMPLETADO (2025-10-10)
**Prioridad**: 🔴 ALTA
**Duración real**: ~6 horas (vs 8-12h estimadas)
**Archivo**: [`SPRINT_11_CHATBOT_BI.md`](./SPRINT_11_CHATBOT_BI.md)

**Objetivo**: Implementar chatbot BI conversacional con acceso móvil que permita consultas en lenguaje natural sobre producción, precios energéticos y clima.

**Entregables completados**:
- ✅ Chatbot service con Claude Haiku API (193 líneas)
- ✅ RAG local con keyword matching 7 categorías (287 líneas)
- ✅ Widget conversacional integrado en dashboard
- ✅ 3 endpoints `/chat/*`: ask, stats, health
- ✅ Tests 100% passing (5/5 preguntas)
- ✅ Documentación completa (~800 líneas)

**Resultados**: Latencia 10-13s (50% reducción), costo €1.74-5.21/mes, tokens optimizados 600-1200 (6x mejor), rate limiting 20/min activo.

---

### Sprint 12: Forgejo Self-Hosted + CI/CD con Tres Nodos Tailscale 🔐
**Estado**: 🔴 NO INICIADO
**Prioridad**: 🟡 MEDIA
**Duración estimada**: 1.5-2 semanas (30-40 horas)
**Archivo**: [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)

**Objetivo**: Desplegar Forgejo self-hosted con CI/CD local + Docker Registry privado, integrado con **TRES nodos Tailscale** separados (git, desarrollo, producción).

**Entregables clave**:
- Forgejo instance en nodo Git/CI/CD dedicado
- Gitea Actions runners diferenciados (dev/prod)
- Pipelines CI/CD dual environment (develop/main)
- Docker registry privado
- Configuración ACLs Tailscale por nodo
- Entornos separados (docker-compose.dev.yml / docker-compose.prod.yml)
- Git remotes dobles (GitHub + Forgejo)

**Valor**: Control total sobre datos, aislamiento completo por nodo, CI/CD automatizado dual, seguridad mejorada con ACLs, escalabilidad independiente.

---

### Sprint 13: Tailscale Observability - Enfoque Híbrido 📊
**Estado**: 🔴 NO INICIADO
**Prioridad**: 🟡 MEDIA
**Duración estimada**: 2-3 días (12-16 horas)
**Archivo**: [`SPRINT_13_TAILSCALE_OBSERVABILITY.md`](./SPRINT_13_TAILSCALE_OBSERVABILITY.md)

**Objetivo**: Observabilidad Tailscale con enfoque híbrido: sistema nativo práctico 24/7 (Fase 1) + MCP learning educacional (Fase 2 opcional).

**Entregables Fase 1 (Práctico)**:
- Analytics service con CLI nativo (tailscale status, whois)
- Parser nginx logs + correlación Tailscale
- 3 endpoints API analytics
- Dashboard widget 24/7
- APScheduler job automático

**Entregables Fase 2 (Educacional - Opcional)**:
- Instalación Tailscale MCP (@tailscale/mcp-server)
- Comparativa MCP vs CLI nativo
- Documentación aprendizajes
- Decisión final: mantener o remover MCP

**Valor**: Observabilidad funcional autónoma + conocimiento ecosistema MCP (mejor de ambos mundos).

---

## 🎯 Estrategia de Ejecución

### Orden Recomendado

```
Sprint 11 (Chatbot BI) → Sprint 12 (Forgejo CI/CD) → Sprint 13 (Monitoring)
      ↓                        ↓                            ↓
  1.5-2 días               1 semana                   1 semana
  Valor inmediato          Infraestructura            Nice-to-have
```

### Filosofía

1. **Chatbot BI primero**: Acceso móvil universal + consultas conversacionales
2. **CI/CD después**: Tests automatizados + registry privado
3. **Monitoring opcional**: Cuando sistema esté en producción 24/7

---

## 📊 Comparativa Sprints

| Sprint | Complejidad | Valor Inmediato | Dependencias | Riesgo | Costo/mes | Estado |
|--------|-------------|-----------------|--------------|--------|-----------|--------|
| Sprint 11 (Chatbot) | Media | ⭐⭐⭐⭐⭐ | Ninguna | Bajo | ~€2 | ✅ COMPLETADO |
| Sprint 12 (Forgejo 3 nodos) | Muy Alta | ⭐⭐⭐⭐⭐ | Ninguna | Medio-Alto | €0 | 🔴 Pendiente |
| Sprint 13 (Observability) | Media | ⭐⭐⭐⭐ | Tailscale activo | Bajo | €0 | 🔴 Pendiente |

---

## 🚀 Sprint 11 (Chatbot BI) - Vista Rápida

### ¿Por qué Chatbot en lugar de MCP?

**Problema real del usuario**:
- ✅ Acceso **móvil** (smartphone conectado a Tailnet)
- ✅ Consultas **conversacionales** simples
- ✅ Usuarios **no técnicos** (sin Claude Desktop)
- ✅ Sistema **100% autónomo** (sin Claude Code background)

**Ventajas Chatbot vs MCP**:
- ✅ **Acceso universal**: Móvil, tablet, desktop (MCP solo desktop)
- ✅ **Independiente**: FastAPI standalone (MCP requiere Claude Desktop)
- ✅ **Costo predecible**: ~€1.50-3/mes con Haiku (MCP: €0 pero limitado)
- ✅ **Escalable**: Multi-usuario (MCP: 1 usuario)

### Ejemplo de uso Chatbot

```
📱 Usuario desde móvil (Tailnet):
User: "¿Cuándo debo producir hoy?"
Chatbot: "✅ Ventanas óptimas hoy:
- 02:00-05:00h (0.06€/kWh - Valle P3)
- 14:00-16:00h (0.09€/kWh - Llano P2)
Recomiendo madrugada para máximo ahorro."

Time to answer: ~1.5s
Cost: €0.001
```

### Optimización de Costos

**Tu arquitectura Clean Architecture ahorra 6-10x tokens**:
- Context típico: 600 tokens (vs 5,000 proyecto mal diseñado)
- Ahorro mensual: ~€10/mes gracias a buena estructura
- Costo real: ~€1.50-3/mes (50-150 preguntas/día)

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

### Al iniciar Sprint 11 (Chatbot BI)
1. Leer [`SPRINT_11_CHATBOT_BI.md`](./SPRINT_11_CHATBOT_BI.md)
2. Obtener API Key: https://console.anthropic.com/ → "API Keys" → "Create Key"
3. Añadir `ANTHROPIC_API_KEY` a `.env`
4. Instalar dependencias: `pip install anthropic fastapi-limiter`
5. Verificar endpoints disponibles: `curl http://localhost:8000/openapi.json`

### Al iniciar Sprint 12 (Forgejo)
1. Leer [`SPRINT_12_FORGEJO_CICD.md`](./SPRINT_12_FORGEJO_CICD.md)
2. Verificar Tailscale sidecar: `docker compose ps chocolate-factory`
3. Planificar volumenes persistentes
4. Generar SSH keys para git

---

## 🔄 Estado Actual del Proyecto

**Sprints ML Evolution**: ✅ 01-09 COMPLETADOS
**Sprint 11 (Infrastructure)**: ✅ COMPLETADO (Chatbot BI)
**Clean Architecture**: ✅ Refactorizado (Oct 6, 2025)
**API Endpoints**: 33 disponibles (añadidos `/chat/*`)
**Tailscale**: ✅ Sidecar activo
**Docker Compose**: ✅ 3 servicios running

**Próximo Sprint**: Sprint 12 - Forgejo CI/CD (opcional)
**Preparación**: Sistema estable con chatbot BI operacional

---

**Última actualización**: 2025-10-10
**Autor**: Infrastructure Planning Team
**Versión**: 2.0 (Actualizado con enfoque Chatbot BI)
