# 🎯 SPRINT 11: Chatbot BI Conversacional - Claude Haiku API

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🔴 ALTA
> **Prerequisito**: Sprint 10 completado, API 30 endpoints operacionales
> **Duración estimada**: 1.5-2 días (8-12 horas)
> **Fecha inicio planeada**: 2025-10-10

---

## 📋 Objetivo

**Implementar chatbot BI conversacional** con acceso móvil que permita consultas en lenguaje natural sobre producción, precios energéticos y clima.

### ¿Por qué Chatbot en lugar de MCP?

**Problema real del usuario**:
- ✅ Acceso **móvil** (smartphone conectado a Tailnet)
- ✅ Consultas **conversacionales** simples
- ✅ Usuarios **no técnicos** (sin Claude Desktop)
- ✅ Sistema **100% autónomo** (sin Claude Code background)

**MCP vs Chatbot**:
```
❌ MCP Server:
   - Requiere Claude Desktop instalado
   - Solo acceso desktop
   - Dependencia Claude Code running
   - No apto para móvil

✅ Chatbot con Haiku API:
   - Totalmente independiente (FastAPI standalone)
   - Acceso universal (móvil/tablet/desktop via web)
   - Sin dependencias externas (solo API key)
   - Costo predecible (~€1.50-3/mes)
```

---

## 📦 Entregables

### 1. Context Builder Service (RAG Local)

**Archivo**: `src/fastapi-app/services/chatbot_context_service.py`

**Funcionalidad**: RAG local sin vector DB, usando keyword matching inteligente

```python
class ChatbotContextService:
    """
    Construye contexto relevante para Claude Haiku.
    NO usa embeddings, usa keyword matching simple.
    Optimizado para tokens (500-1500 tokens/pregunta).
    """

    async def build_context(self, question: str) -> str:
        """
        Selecciona endpoints relevantes basándose en keywords.

        Keywords detectados:
        - "cuándo", "producir", "ventanas" → optimal_windows
        - "precio", "energía", "costo" → price_forecast
        - "alerta", "problema" → predictive_alerts
        - "ahorro", "saving" → savings_tracking
        - Sin match → full_dashboard
        """
```

**Endpoints integrados** (30 disponibles, selección inteligente):
- `/dashboard/complete` - Estado actual (siempre incluido)
- `/insights/optimal-windows` - Ventanas óptimas 7 días
- `/predict/prices/weekly` - Forecast Prophet 168h
- `/insights/alerts` - Alertas predictivas
- `/insights/savings-tracking` - Tracking ahorros
- `/optimize/production/daily` - Plan optimizado 24h
- `/analysis/siar-summary` - Análisis histórico SIAR

**Optimización de tokens**:
- Context típico: 500-800 tokens (vs 5000 sin estructura)
- Ahorro: 6-10x vs proyecto mal diseñado
- Gracias a: Clean Architecture + Pydantic schemas

---

### 2. Chatbot Service (Claude Haiku API)

**Archivo**: `src/fastapi-app/services/chatbot_service.py`

**Stack técnico**:
```python
import anthropic  # SDK oficial Anthropic
from anthropic import Anthropic

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-3-5-haiku-20241022",  # Haiku (no Sonnet)
    max_tokens=300,  # Respuestas concisas
    system=system_prompt,
    messages=[{"role": "user", "content": f"..."}]
)
```

**¿Por qué Haiku y no Sonnet?**

| Criterio | Haiku | Sonnet 4 | ¿Necesitas Sonnet? |
|----------|-------|----------|-------------------|
| **Formateo datos estructurados** | ✅ Excelente | ✅ Excelente | ❌ No |
| **Razonamiento complejo** | Limitado | Excelente | ❌ No (contexto determinístico) |
| **Latencia** | ~1.5s | ~3-5s | ❌ Haiku más rápido |
| **Costo input** | $0.80/1M | $3.00/1M | ❌ 3.75x más caro |
| **Costo output** | $4.00/1M | $15.00/1M | ❌ 3.75x más caro |

**Tu caso de uso**: 90% preguntas son **lookups simples** (precio actual, cuándo producir, alertas). Haiku es perfecto para formatear datos estructurados.

**System prompt especializado**:
```
Eres un asistente especializado en la Chocolate Factory de Linares.

Rol:
- Responder sobre producción, precios energéticos, clima
- Recomendar ventanas óptimas de producción
- Explicar alertas y métricas
- Ser conciso (máximo 3-4 frases por respuesta)
- Usar emojis relevantes (⚡💰🌡️🏭)

Contexto técnico:
- Sistema ML con Prophet forecasting (168h)
- 88k registros SIAR históricos (2000-2025)
- 42k registros REE precios (2022-2025)
- Optimización horaria con periodos tarifarios P1/P2/P3

IMPORTANTE: Responde SOLO basándote en el CONTEXTO proporcionado.
```

---

### 3. API Endpoint

**Archivo**: `src/fastapi-app/api/routers/chatbot.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chatbot"])

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    tokens: dict  # {"input": int, "output": int}
    latency_ms: int
    cost_usd: float

@router.post("/ask", response_model=ChatResponse)
async def ask_chatbot(request: ChatRequest):
    """
    Endpoint conversacional para consultas BI.

    Ejemplos:
    - "¿Cuándo debo producir mañana?"
    - "¿Por qué el precio está alto ahora?"
    - "¿Cuánto ahorramos esta semana?"
    - "¿Hay alertas activas?"
    """
    chatbot = ChatbotService()
    response = await chatbot.ask(request.question)
    return ChatResponse(**response)
```

**Rate limiting** (protección costos):
```python
from fastapi_limiter.depends import RateLimiter

@router.post("/ask")
@limiter.limit("20/minute")  # Max 20 preguntas/minuto
async def ask_chatbot(request: ChatRequest):
    ...
```

---

### 4. UI Móvil Responsive

**Archivo**: `static/chat.html`

**Características**:
- 📱 **Mobile-first design** (iOS/Android optimizado)
- 💬 **Interfaz chat nativa** (burbujas usuario/asistente)
- ⚡ **Real-time typing indicator** (UX feedback)
- 🎨 **Gradient background** (matching dashboard)
- ♿ **Accesible** (input grande, botones táctiles)

**Preguntas rápidas sugeridas**:
```html
<div class="quick-questions">
    <button onclick="askQuick('¿Cuándo debo producir hoy?')">
        🏭 ¿Cuándo producir?
    </button>
    <button onclick="askQuick('¿Cuál es el precio actual?')">
        ⚡ Precio actual
    </button>
    <button onclick="askQuick('¿Hay alertas?')">
        🚨 Ver alertas
    </button>
    <button onclick="askQuick('Ahorro esta semana')">
        💰 Ahorro semanal
    </button>
</div>
```

**Screenshot mockup**:
```
┌─────────────────────────────┐
│ 🍫 Chocolate Factory Chatbot│
├─────────────────────────────┤
│                             │
│  👋 ¡Hola! Soy tu          │
│  asistente...              │
│                             │
│            ¿Cuándo debo    │
│            producir hoy?   │
│                             │
│  ✅ Te recomiendo:         │
│  - 02:00-05:00h (0.06€)   │
│  - 13:00-15:00h (0.08€)   │
│                             │
├─────────────────────────────┤
│ [Escribe tu pregunta...] 📤│
└─────────────────────────────┘
```

---

### 5. Integración Tailscale (Nginx Sidecar)

**Archivo**: `docker/services/nginx/nginx.conf`

**Añadir ruta `/chat/*`**:
```nginx
# Chat endpoint
location /chat/ {
    proxy_pass http://chocolate_factory_brain:8000/chat/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}

# Static chat UI
location /chat {
    proxy_pass http://chocolate_factory_brain:8000/static/chat.html;
}
```

**Acceso remoto**:
- Dashboard: `https://tu-tailnet.ts.net/`
- Chatbot: `https://tu-tailnet.ts.net/chat`

---

### 6. Environment Variables

**Archivo**: `.env.example`

```bash
# Claude API (obligatorio para chatbot)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

# Chatbot settings (opcional)
CHATBOT_MAX_TOKENS=300          # Max tokens respuesta
CHATBOT_MODEL=claude-3-5-haiku-20241022
CHATBOT_RATE_LIMIT=20           # Requests/minuto
```

**Obtener API Key** (5 minutos):
1. Ir a https://console.anthropic.com/
2. Crear cuenta (si no tienes)
3. "API Keys" → "Create Key"
4. Copiar: `sk-ant-api03-xxxxxxxxxxxxx`
5. Añadir a `.env`

**Crédito inicial**: $5 gratis (~1,600 preguntas de prueba)

---

### 7. Monitoring & Cost Tracking

**Endpoint adicional**: `GET /chat/stats`

```python
@router.get("/stats")
async def get_chatbot_stats():
    """
    Estadísticas de uso del chatbot.

    Returns:
        {
            "total_questions": 1247,
            "total_tokens_input": 1_245_000,
            "total_tokens_output": 187_000,
            "total_cost_usd": 2.74,
            "avg_latency_ms": 1534,
            "questions_today": 42
        }
    """
```

**Dashboard widget** (futuro Sprint 12):
```html
<div class="card">
    <h3>💬 Chatbot Usage</h3>
    <div>Preguntas hoy: <strong id="chatbot-questions">42</strong></div>
    <div>Costo mes: <strong id="chatbot-cost">€2.74</strong></div>
    <div>Latencia promedio: <strong id="chatbot-latency">1.5s</strong></div>
</div>
```

---

## 🛠️ Stack Técnico

### Dependencias Python

```toml
# pyproject.toml (añadir)
[project.dependencies]
anthropic = "^0.40.0"      # Claude API SDK
httpx = "^0.27.0"          # Async HTTP (ya existe)
fastapi-limiter = "^0.1.6" # Rate limiting

[project.optional-dependencies]
chatbot = [
    "anthropic>=0.40.0",
    "fastapi-limiter>=0.1.6",
]
```

**Instalación**:
```bash
cd src/fastapi-app
pip install anthropic fastapi-limiter
```

---

### Arquitectura Chatbot Service

```
src/fastapi-app/
├── services/
│   ├── chatbot_context_service.py   # RAG local (keyword matching)
│   └── chatbot_service.py           # Claude Haiku API integration
├── api/routers/
│   └── chatbot.py                   # /chat/ask endpoint
├── core/
│   └── config.py                    # ANTHROPIC_API_KEY setting
└── static/
    └── chat.html                    # UI móvil responsive
```

---

## 📝 Plan de Implementación

### Fase 1: Setup Básico (1-2 horas)

- [ ] Obtener API Key de Anthropic (https://console.anthropic.com/)
- [ ] Instalar dependencias: `pip install anthropic fastapi-limiter`
- [ ] Añadir `ANTHROPIC_API_KEY` a `.env`
- [ ] Actualizar `core/config.py` con nueva setting
- [ ] Test conexión Claude API:
  ```python
  from anthropic import Anthropic
  client = Anthropic(api_key="sk-ant-...")
  message = client.messages.create(
      model="claude-3-5-haiku-20241022",
      max_tokens=100,
      messages=[{"role": "user", "content": "Test"}]
  )
  print(message.content[0].text)
  ```

### Fase 2: Context Builder (2-3 horas)

- [ ] Crear `services/chatbot_context_service.py`
- [ ] Implementar keyword matching logic:
  - [ ] `_get_current_status()` - Siempre incluido
  - [ ] `_get_optimal_windows()` - Keywords: cuándo, producir, ventanas
  - [ ] `_get_price_forecast()` - Keywords: precio, energía, costo
  - [ ] `_get_alerts()` - Keywords: alerta, problema, warning
  - [ ] `_get_savings()` - Keywords: ahorro, saving, comparar
  - [ ] `_get_full_dashboard()` - Fallback sin match
- [ ] Tests unitarios: verificar context < 2000 tokens

### Fase 3: Chatbot Service (2-3 horas)

- [ ] Crear `services/chatbot_service.py`
- [ ] Implementar `ask()` method:
  - [ ] Build context con `ChatbotContextService`
  - [ ] Call Claude Haiku API
  - [ ] Calcular latency y cost
  - [ ] Return response con metadata
- [ ] Definir system prompt especializado
- [ ] Error handling (API timeout, invalid key)
- [ ] Tests integración con mock Anthropic API

### Fase 4: API Endpoint (1-2 horas)

- [ ] Crear `api/routers/chatbot.py`
- [ ] Implementar `POST /chat/ask`:
  - [ ] Request schema: `ChatRequest(question: str)`
  - [ ] Response schema: `ChatResponse(answer, tokens, latency, cost)`
  - [ ] Rate limiting: 20 requests/minute
  - [ ] Error handling HTTP
- [ ] Registrar router en `main.py`
- [ ] Test endpoint con `curl`:
  ```bash
  curl -X POST http://localhost:8000/chat/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "¿Cuál es el precio actual?"}'
  ```

### Fase 5: UI Móvil (2-3 horas)

- [ ] Crear `static/chat.html`
- [ ] Implementar chat interface:
  - [ ] Header con título
  - [ ] Container mensajes scrollable
  - [ ] Input + botón enviar
  - [ ] Burbujas user/assistant
  - [ ] Typing indicator
  - [ ] Quick questions buttons
- [ ] CSS responsive (mobile-first)
- [ ] JavaScript fetch API:
  - [ ] `sendMessage()` function
  - [ ] `addMessage()` function
  - [ ] Enter key to send
- [ ] Test en móvil (Chrome DevTools responsive)

### Fase 6: Integración Tailscale (1 hora)

- [ ] Actualizar `docker/services/nginx/nginx.conf`:
  - [ ] Añadir `location /chat/` proxy
  - [ ] Añadir `location /chat` redirect a static
- [ ] Rebuild Tailscale sidecar:
  ```bash
  docker compose build chocolate-factory
  docker compose up -d chocolate-factory
  ```
- [ ] Test acceso remoto: `https://tu-tailnet.ts.net/chat`

### Fase 7: Monitoring & Docs (1-2 horas)

- [ ] Implementar `GET /chat/stats` endpoint
- [ ] Log tokens/cost a InfluxDB (futuro dashboard)
- [ ] Escribir `docs/CHATBOT_BI.md`:
  - [ ] Setup API Key
  - [ ] Ejemplos de preguntas
  - [ ] Costos estimados
  - [ ] Troubleshooting
- [ ] Actualizar `CLAUDE.md` con Sprint 11 completado
- [ ] Actualizar `.env.example` con `ANTHROPIC_API_KEY`

---

## 🧪 Criterios de Éxito

### Tests Funcionales

1. **Test Context Builder**:
   ```python
   context = await context_service.build_context("¿Cuándo producir?")
   assert "PRÓXIMAS VENTANAS ÓPTIMAS" in context
   assert len(context) < 2000  # tokens optimizados
   ```

2. **Test Chatbot Service**:
   ```python
   response = await chatbot.ask("¿Cuál es el precio actual?")
   assert "answer" in response
   assert response["tokens"]["input"] < 1000
   assert response["latency_ms"] < 3000  # < 3s
   ```

3. **Test API Endpoint**:
   ```bash
   curl -X POST http://localhost:8000/chat/ask \
     -d '{"question": "¿Hay alertas?"}' | jq
   # Expected: {"answer": "...", "tokens": {...}, ...}
   ```

4. **Test UI Móvil**:
   - [ ] Abrir `http://localhost:8000/static/chat.html` en Chrome mobile
   - [ ] Escribir pregunta: "¿Cuándo producir?"
   - [ ] Verificar respuesta en < 3s
   - [ ] Verificar burbujas chat responsive

5. **Test Tailscale Remoto**:
   - [ ] Abrir smartphone
   - [ ] Conectar a Tailnet
   - [ ] Ir a `https://tu-tailnet.ts.net/chat`
   - [ ] Hacer pregunta desde móvil
   - [ ] Verificar respuesta correcta

### Métricas de Éxito

- ✅ Chatbot responde < 3s (latencia aceptable)
- ✅ Context < 2000 tokens/pregunta (optimizado)
- ✅ Costo < €3/mes con 50 preguntas/día (predecible)
- ✅ Acceso móvil funcional via Tailnet (universal)
- ✅ 0 dependencias Claude Code (100% autónomo)
- ✅ UI responsive mobile-first (UX excelente)
- ✅ Rate limiting activo (protección costos)

---

## 💰 Análisis de Costos

### Costo por Pregunta (Haiku)

**Ejemplo pregunta típica**:
```
User: "¿Cuándo debo producir mañana?"

Context:
- Current status: 100 tokens
- Optimal windows: 300 tokens
- Price forecast: 200 tokens
Total input: 600 tokens

Response:
"✅ Te recomiendo producir mañana en dos ventanas:
- 02:00-05:00h (precio 0.06€/kWh - Valle P3)
- 13:00-15:00h (precio 0.08€/kWh - Llano P2)
La ventana de madrugada ofrece mayor ahorro."
Total output: 150 tokens

Cost calculation:
Input: 600 × $0.80/1M = $0.00048
Output: 150 × $4.00/1M = $0.00060
TOTAL: $0.00108 (~€0.001 por pregunta)
```

### Uso Mensual Proyectado

**Escenario conservador** (50 preguntas/día):
```
50 preguntas/día × 30 días = 1,500 preguntas/mes

Input: 600 tokens × 1,500 = 900k tokens
Output: 150 tokens × 1,500 = 225k tokens

Costo input: 900k × $0.80/1M = $0.72
Costo output: 225k × $4.00/1M = $0.90
──────────────────────────────────────
TOTAL: $1.62/mes (~€1.51/mes)
```

**Escenario intensivo** (150 preguntas/día):
```
150 preguntas/día × 30 días = 4,500 preguntas/mes

Input: 600 tokens × 4,500 = 2.7M tokens
Output: 150 tokens × 4,500 = 675k tokens

Costo input: 2.7M × $0.80/1M = $2.16
Costo output: 675k × $4.00/1M = $2.70
──────────────────────────────────────
TOTAL: $4.86/mes (~€4.54/mes)
```

**Conclusión**: Incluso con uso intensivo, costo < €5/mes (muy asequible)

### Optimización Tokens (Tu Arquitectura)

**Gracias a Clean Architecture + Pydantic schemas**:

| Aspecto | Proyecto mal diseñado | Tu proyecto | Ahorro |
|---------|----------------------|-------------|--------|
| **Context por pregunta** | 5,000 tokens | 600 tokens | 8.3x |
| **Response verboso** | 400 tokens | 150 tokens | 2.7x |
| **Costo/pregunta** | $0.008 | $0.001 | 8x |
| **Costo/mes (50q/día)** | €11.20 | €1.51 | 7.4x |

**Tu ahorro real**: ~€10/mes gracias a buena estructura del proyecto

---

## 🚧 Problemas Potenciales

### Problema 1: API Key inválida o sin crédito

**Síntomas**: Error 401 Unauthorized o 429 Rate Limit

**Solución**:
```bash
# 1. Verificar API key en .env
echo $ANTHROPIC_API_KEY

# 2. Verificar crédito restante
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"

# 3. Añadir crédito en console.anthropic.com/settings/billing
```

### Problema 2: Latencia alta (> 5s)

**Síntomas**: Chatbot responde muy lento

**Causas y soluciones**:
```python
# Causa 1: Context demasiado grande
# Fix: Reducir tokens en context_service.py
context = await self._get_compact_context(question)  # < 1000 tokens

# Causa 2: Timeout httpx bajo
# Fix: Aumentar timeout
client = httpx.AsyncClient(timeout=30.0)

# Causa 3: Network issues
# Fix: Retry logic con tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_claude_api(self, ...):
    ...
```

### Problema 3: Costos inesperados

**Síntomas**: Gasto > €10/mes

**Protecciones**:
```python
# 1. Rate limiting estricto
@router.post("/chat/ask")
@limiter.limit("10/minute")  # Reducir a 10/min
async def ask_chatbot(...):
    ...

# 2. Daily spending cap
daily_cost = await get_daily_cost()
if daily_cost > 0.50:  # Max $0.50/día
    raise HTTPException(429, "Daily spending limit reached")

# 3. Max tokens per question
if len(question) > 200:
    raise HTTPException(400, "Question too long (max 200 chars)")
```

### Problema 4: Respuestas incorrectas (alucinaciones)

**Síntomas**: Chatbot inventa datos

**Mitigación**:
```python
# System prompt claro
system_prompt = """
IMPORTANTE: Responde SOLO basándote en el CONTEXTO proporcionado.
Si no hay información suficiente, di: "No tengo datos suficientes para responder eso."
NUNCA inventes precios, fechas o métricas.
"""

# Validación respuesta
if "no tengo datos" in response.lower():
    # OK, chatbot admite no saber
    pass
elif not contains_contextual_data(response, context):
    # Warning: respuesta sospechosa
    logger.warning(f"Possible hallucination: {response}")
```

---

## 📊 Valor del Sprint 11

### Beneficios Inmediatos

1. **Acceso móvil universal**: Consultas desde smartphone (Tailnet)
2. **100% autónomo**: Sin dependencias Claude Code/Desktop
3. **Costo predecible**: ~€1.50-3/mes (muy bajo)
4. **UX natural**: Conversación en lenguaje natural
5. **Escalable**: Puede crecer a más features sin reescribir

### Casos de Uso Reales

**Caso 1: Planificación rápida (desde móvil)**
```
User: "¿Cuándo debo producir hoy?"
Chatbot: "✅ Ventanas óptimas hoy:
- 02:00-05:00h (0.06€/kWh - Valle P3)
- 14:00-16:00h (0.09€/kWh - Llano P2)
Recomiendo madrugada para máximo ahorro."

Time to answer: ~1.5s
Cost: €0.001
```

**Caso 2: Análisis en tiempo real**
```
User: "¿Es buen momento para producir ahora?"
Chatbot: "⚡ Precio actual: 0.15€/kWh (P1-Punta)
🌡️ Temperatura: 28°C (por encima óptimo)
⚠️ Recomendación: ESPERA. Mejor producir en 3h (precio 0.08€)"

Time to answer: ~2s
Cost: €0.0012
```

**Caso 3: Troubleshooting**
```
User: "¿Por qué hay una alerta?"
Chatbot: "🚨 Alertas activas (2):
1. Pico precio previsto mañana 18-21h (0.28€/kWh)
2. Temperatura alta próximas 48h (32°C P95)
Recomiendo ajustar plan producción."

Time to answer: ~1.8s
Cost: €0.0011
```

**Caso 4: Comparativas**
```
User: "¿Cuánto ahorramos esta semana?"
Chatbot: "💰 Ahorro semanal: 31.85€
📊 Comparativa:
- Baseline (horario fijo): 156.40€
- Optimizado (Prophet ML): 124.55€
- Ahorro: 20.4%
¡Vas muy bien! 🎉"

Time to answer: ~1.6s
Cost: €0.001
```

### ROI del Sprint

**Inversión**:
- Desarrollo: 8-12 horas (1.5-2 días)
- Costo operacional: ~€2/mes

**Beneficios**:
- ✅ Acceso móvil a BI (antes: solo desktop)
- ✅ Consultas 10x más rápidas (vs navegar dashboard)
- ✅ Decisiones informadas en tiempo real
- ✅ UX mejorada para usuarios no técnicos
- ✅ Extensible a notificaciones Telegram/WhatsApp (futuro)

---

## 🔄 Próximos Pasos después Sprint 11

### Sprint 12: Forgejo CI/CD (planeado)
- Tests automatizados para chatbot
- CI/CD para validar responses
- Registry privado para imágenes Docker

### Extensiones Futuras Chatbot

**Fase 2 (opcional)**:
- [ ] **Prompt caching** (Anthropic): Reducir costos 10x
- [ ] **Historial conversación**: Context multi-turn
- [ ] **Voice input**: Speech-to-text (Web Speech API)
- [ ] **Notificaciones push**: Telegram/WhatsApp bot
- [ ] **Modo híbrido**: Haiku (simple) + Sonnet (complejo)
- [ ] **Multi-idioma**: Inglés, español, catalán

**Fase 3 (avanzado)**:
- [ ] **Actions execution**: "Ejecuta plan optimizado para mañana"
- [ ] **Report generation**: "Genera PDF análisis semanal"
- [ ] **Proactive alerts**: "Avísame si precio > 0.20€"

---

## 📚 Referencias

- **Anthropic API Docs**: https://docs.anthropic.com/en/api/
- **Claude Haiku**: https://docs.anthropic.com/en/docs/about-claude/models#model-recommendations
- **Prompt Caching**: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- **FastAPI WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/ (futuro streaming)
- **Chocolate Factory API**: `docs/API_REFERENCE.md`

---

## 📝 Checklist Completitud

### Desarrollo Core
- [ ] `services/chatbot_context_service.py` implementado
- [ ] `services/chatbot_service.py` con Haiku API
- [ ] `api/routers/chatbot.py` con endpoints
- [ ] Tests unitarios + integración passing

### UI/UX
- [ ] `static/chat.html` responsive mobile-first
- [ ] Quick questions buttons funcionales
- [ ] Typing indicator implementado
- [ ] CSS optimizado para móvil

### Infraestructura
- [ ] `ANTHROPIC_API_KEY` en `.env`
- [ ] Nginx sidecar configurado (`/chat/*`)
- [ ] Rate limiting activo (20/min)
- [ ] Monitoring `/chat/stats` endpoint

### Documentación
- [ ] `docs/CHATBOT_BI.md` creado
- [ ] `.env.example` actualizado
- [ ] `CLAUDE.md` actualizado con Sprint 11
- [ ] README.md con ejemplos de uso

### Testing
- [ ] Test local: `http://localhost:8000/static/chat.html`
- [ ] Test Tailnet: `https://tu-tailnet.ts.net/chat`
- [ ] Test móvil: iPhone/Android real
- [ ] Test costos: Verificar < €0.002/pregunta

---

## 🎉 Criterio de Finalización

Sprint 11 se considera **COMPLETADO** cuando:
- ✅ Chatbot responde correctamente a 10 preguntas tipo
- ✅ Acceso móvil funcional via Tailnet
- ✅ Latencia < 3s (95th percentile)
- ✅ Costo < €3/mes con uso normal (50q/día)
- ✅ UI responsive en móvil iOS/Android
- ✅ Documentación completa publicada
- ✅ Sistema 100% autónomo (sin Claude Code)

---

**Fecha creación**: 2025-10-10
**Autor**: Infrastructure Sprint Planning (Revisión v2.0)
**Versión**: 2.0 (Chatbot BI + Haiku API)
**Sprint anterior**: Sprint 10 - Consolidación (✅ COMPLETADO)
**Sprint siguiente**: Sprint 12 - Forgejo CI/CD (planeado)

---

## 🔄 Changelog v2.0

**Cambios vs v1.0 (MCP Server)**:
- ❌ **Eliminado**: MCP server implementation (dependencia Claude Desktop)
- ✅ **Añadido**: Chatbot BI con Claude Haiku API (100% autónomo)
- ✅ **Añadido**: RAG local con keyword matching (sin vector DB)
- ✅ **Añadido**: UI móvil responsive (`static/chat.html`)
- ✅ **Añadido**: Análisis costos detallado (€1.50-3/mes)
- ✅ **Añadido**: Integración Tailscale para acceso remoto
- ⚡ **Reducido**: Duración 2-3 días → 1.5-2 días (más simple)
- 💰 **Optimizado**: Tokens 6-10x menos vs proyecto mal diseñado

**Justificación cambio**: Problema real del usuario es acceso móvil conversacional, no integración desktop MCP.
