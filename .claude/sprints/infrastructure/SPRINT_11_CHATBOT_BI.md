# SPRINT 11: Chatbot BI Conversacional

**Status**: COMPLETED
**Date**: 2025-10-10
**Archivos**: chatbot_service.py (198 líneas), chatbot_context_service.py (524 líneas), chatbot.py router (237 líneas)

## Objetivo

Chatbot conversacional con Claude API para consultas sobre producción, precios y clima. Acceso mobile via Tailnet.

## Implementación

### 1. Context Service (RAG local)
`src/fastapi-app/services/chatbot_context_service.py`

- Keyword matching (sin vector DB)
- Detecta categorías: optimal_windows, price_forecast, alerts, savings, production_plan, analysis
- Ejecuta llamadas paralelas con `asyncio.gather()` para optimizar latencia
- Contexto: 500-1500 tokens/pregunta
- Endpoints integrados: `/dashboard/complete`, `/insights/*`, `/predict/*`, `/optimize/*`, `/analysis/*`

### 2. Chatbot Service
`src/fastapi-app/services/chatbot_service.py`

- Cliente Anthropic (Claude Haiku 4.5)
- Max 300 tokens respuesta
- System prompt: respuestas concisas (3-4 frases), basadas en contexto, sin inventar datos
- Error handling: APIError, APITimeoutError
- Cost tracking automático

### 3. Endpoints
`src/fastapi-app/api/routers/chatbot.py`

```
POST /chat/ask      - Pregunta (max 500 caracteres)
GET /chat/stats     - Métricas (tokens, latencia, costo)
GET /chat/health    - Status servicio
```

Rate limiting: 20 req/min (slowapi)

### 4. UI Integration
`static/js/chatbot.js`, `static/index.html`

- Widget conversacional en dashboard
- Chat bubbles (usuario/asistente)
- 4 botones rápidos
- Stats footer
- Responsive mobile

### 5. Config
`.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
CHATBOT_MODEL=claude-haiku-4-5
CHATBOT_MAX_TOKENS=300
CHATBOT_RATE_LIMIT=20
```

## Decisiones Técnicas

- **Haiku vs Sonnet**: Haiku suficiente (queries simples, 4-5x más rápido, 3x más barato)
- **Keyword matching vs embeddings**: Sin vector DB, simple y rápido
- **Parallel API calls**: asyncio.gather() reduce latencia ~80%
- **In-memory stats**: No persistencia (reset en reinicio contenedor)
- **Single-turn queries**: Sin conversación multi-vuelta

## Testing

5 preguntas (100% passing):
- "¿Cuál es el precio actual?"
- "¿Cuándo debo producir hoy?"
- "¿Hay alertas?"
- "¿Cuánto ahorramos esta semana?"
- "¿Cuál es el mejor momento para producir?"

Latencia: 10-13s (incluye context building + API)

```bash
curl -X POST http://localhost:8000/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuándo debo producir hoy?"}'

curl http://localhost:8000/chat/stats
```

## Limitaciones Actuales

1. Stats en memoria (no persisten)
2. Single-turn (sin historial conversación)
3. Rate limiting por sesión (no por usuario)
4. Latencia 10-13s aceptable para mobile
