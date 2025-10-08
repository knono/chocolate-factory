# 🎯 SPRINT 11: MCP Server - Chocolate Factory Integration

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🔴 ALTA
> **Prerequisito**: Sprint 10 completado, API 30 endpoints operacionales
> **Duración estimada**: 2-3 días (12-16 horas)
> **Fecha inicio planeada**: 2025-10-08

---

## 📋 Objetivo

**Implementar MCP (Model Context Protocol) server** para exponer datos de Chocolate Factory como herramienta nativa de Claude Code.

### ¿Qué es MCP?

MCP (Model Context Protocol) permite que Claude Code acceda a datos/funciones locales como "tools" nativos, sin necesidad de llamar APIs HTTP manualmente.

**Ejemplo**:
```
# Sin MCP (actual)
User: "¿Cuál es el precio REE actual?"
Claude: "Déjame consultar..." [hace curl http://localhost:8000/...]

# Con MCP (objetivo)
User: "¿Cuál es el precio REE actual?"
Claude: [usa tool get_current_price automáticamente]
Response: "0.1234 €/kWh (periodo P2)"
```

---

## 📦 Entregables

### 1. MCP Server Python (Core)

**Archivo**: `mcp-server/chocolate_factory_mcp.py`

**Tools a implementar** (8-10 herramientas):

#### Grupo A: Datos en Tiempo Real (3 tools)
1. **`get_current_price`**
   - Endpoint: `GET /ree/prices/latest`
   - Output: Precio actual €/kWh + periodo tarifario
   - Ejemplo: `{"price": 0.1234, "period": "P2", "timestamp": "..."}`

2. **`get_current_weather`**
   - Endpoint: `GET /weather/current`
   - Output: Temperatura, humedad, presión
   - Ejemplo: `{"temp": 22.5, "humidity": 55, "pressure": 1013}`

3. **`get_system_health`**
   - Endpoint: `GET /health`
   - Output: Estado servicios + última actualización
   - Ejemplo: `{"status": "healthy", "influxdb": "ok", "ree": "ok"}`

#### Grupo B: Predicciones ML (3 tools)
4. **`get_weekly_forecast`**
   - Endpoint: `GET /predict/prices/weekly`
   - Output: 168h predicciones Prophet
   - Ejemplo: `{"predictions": [{hour: 0, price: 0.08}, ...]}`

5. **`get_optimal_windows`**
   - Endpoint: `GET /insights/optimal-windows?days=7`
   - Output: Ventanas óptimas producción
   - Ejemplo: `{"windows": [{day: "Lun", hours: "02-05h", price: 0.06}]}`

6. **`get_production_recommendation`**
   - Endpoint: `POST /predict/production-recommendation`
   - Input: `{price, temp, humidity}`
   - Output: Recomendación (Optimal/Moderate/Reduced/Halt)

#### Grupo C: Análisis Histórico (3 tools)
7. **`get_siar_analysis`**
   - Endpoint: `GET /analysis/siar-summary`
   - Output: Correlaciones R², umbrales críticos
   - Ejemplo: `{"correlations": {"temp": 0.049}, "thresholds": {"p90": 28.8}}`

8. **`get_daily_optimization`**
   - Endpoint: `POST /optimize/production/daily`
   - Input: `{target_date, target_kg}`
   - Output: Plan 24h con timeline horaria

#### Grupo D: Alertas y Tracking (2 tools)
9. **`get_predictive_alerts`**
   - Endpoint: `GET /insights/alerts`
   - Output: Alertas activas (picos precio, clima extremo)
   - Ejemplo: `{"alerts": [{type: "price_spike", message: "..."}]}`

10. **`get_savings_tracking`**
    - Endpoint: `GET /insights/savings-tracking`
    - Output: Ahorro real vs baseline
    - Ejemplo: `{"daily_savings": 4.55, "weekly": 31.85}`

---

### 2. Configuración MCP

**Archivo**: `mcp-server/mcp_config.json`

```json
{
  "mcpServers": {
    "chocolate-factory": {
      "command": "python",
      "args": ["-m", "mcp-server.chocolate_factory_mcp"],
      "env": {
        "API_BASE_URL": "http://localhost:8000",
        "API_TIMEOUT": "30"
      }
    }
  }
}
```

---

### 3. Integración Claude Desktop

**Archivo**: `~/.config/Claude/claude_desktop_config.json` (Linux/Mac)

```json
{
  "mcpServers": {
    "chocolate-factory": {
      "command": "python",
      "args": ["/ruta/proyecto/mcp-server/chocolate_factory_mcp.py"],
      "env": {
        "PYTHONPATH": "/ruta/proyecto"
      }
    }
  }
}
```

---

### 4. Tests Integración

**Archivo**: `mcp-server/test_mcp_tools.py`

```python
import pytest
from chocolate_factory_mcp import ChocolateFactoryMCP

@pytest.mark.asyncio
async def test_get_current_price():
    mcp = ChocolateFactoryMCP()
    result = await mcp.get_current_price()
    assert "price" in result
    assert result["price"] > 0

@pytest.mark.asyncio
async def test_get_optimal_windows():
    mcp = ChocolateFactoryMCP()
    result = await mcp.get_optimal_windows(days=7)
    assert "windows" in result
    assert len(result["windows"]) > 0
```

---

### 5. Documentación Uso

**Archivo**: `docs/MCP_INTEGRATION.md`

**Contenido**:
- Instalación MCP server
- Configuración Claude Desktop
- Lista de tools disponibles
- Ejemplos de uso con Claude Code
- Troubleshooting común

---

## 🛠️ Stack Técnico

### Dependencias Python

```toml
# pyproject.toml (añadir)
[project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",           # MCP SDK
    "anthropic-mcp>=0.1.0", # Anthropic MCP client
    "httpx>=0.27.0",        # HTTP client async
    "pydantic>=2.0.0",      # Ya existe
]
```

### Arquitectura MCP Server

```
mcp-server/
├── chocolate_factory_mcp.py  # Main MCP server
├── tools/
│   ├── __init__.py
│   ├── realtime.py           # get_current_price, get_weather
│   ├── predictions.py        # get_weekly_forecast, get_optimal_windows
│   ├── analysis.py           # get_siar_analysis, get_daily_optimization
│   └── alerts.py             # get_predictive_alerts, get_savings_tracking
├── client/
│   └── api_client.py         # HTTP client wrapper para FastAPI
├── schemas/
│   └── mcp_responses.py      # Pydantic schemas para MCP responses
├── test_mcp_tools.py         # Tests
└── README.md                 # Documentación
```

---

## 📝 Plan de Implementación

### Fase 1: Setup Básico (2-3 horas)

- [ ] Crear directorio `mcp-server/`
- [ ] Instalar dependencias: `pip install mcp anthropic-mcp httpx`
- [ ] Crear estructura de archivos
- [ ] Implementar `api_client.py` (wrapper HTTP para FastAPI)
- [ ] Test conexión: `curl http://localhost:8000/health`

### Fase 2: Implementar Tools Grupo A (2-3 horas)

- [ ] `get_current_price()` → `/ree/prices/latest`
- [ ] `get_current_weather()` → `/weather/current`
- [ ] `get_system_health()` → `/health`
- [ ] Tests unitarios para cada tool

### Fase 3: Implementar Tools Grupo B (3-4 horas)

- [ ] `get_weekly_forecast()` → `/predict/prices/weekly`
- [ ] `get_optimal_windows()` → `/insights/optimal-windows`
- [ ] `get_production_recommendation()` → `/predict/production-recommendation`
- [ ] Tests integración con API real

### Fase 4: Implementar Tools Grupo C+D (2-3 horas)

- [ ] `get_siar_analysis()` → `/analysis/siar-summary`
- [ ] `get_daily_optimization()` → `/optimize/production/daily`
- [ ] `get_predictive_alerts()` → `/insights/alerts`
- [ ] `get_savings_tracking()` → `/insights/savings-tracking`

### Fase 5: Integración Claude Desktop (2-3 horas)

- [ ] Configurar `claude_desktop_config.json`
- [ ] Reiniciar Claude Desktop
- [ ] Verificar tools disponibles en Claude Code
- [ ] Pruebas end-to-end con prompts reales

### Fase 6: Documentación (1-2 horas)

- [ ] Escribir `docs/MCP_INTEGRATION.md`
- [ ] Añadir ejemplos de uso
- [ ] Documentar troubleshooting
- [ ] Actualizar CLAUDE.md

---

## 🧪 Criterios de Éxito

### Tests Funcionales

1. **Test conexión básica**:
   ```bash
   python -m mcp-server.chocolate_factory_mcp --test
   # Expected: "MCP server initialized successfully"
   ```

2. **Test tool individual**:
   ```python
   result = await mcp.get_current_price()
   assert result["status"] == "success"
   assert "price" in result
   ```

3. **Test integración Claude**:
   - Abrir Claude Code
   - Prompt: "¿Cuál es el precio eléctrico actual?"
   - Verificar que Claude usa tool `get_current_price` automáticamente
   - Response debe incluir precio real del sistema

### Métricas de Éxito

- ✅ 10/10 tools implementados y funcionando
- ✅ Tests coverage > 80%
- ✅ Tiempo respuesta MCP < 2s por tool
- ✅ Claude Code reconoce todos los tools
- ✅ Documentación completa

---

## 🚧 Problemas Potenciales

### Problema 1: Claude Desktop no reconoce MCP server

**Síntomas**: Tools no aparecen en Claude Code

**Solución**:
```bash
# 1. Verificar configuración
cat ~/.config/Claude/claude_desktop_config.json

# 2. Verificar permisos
chmod +x mcp-server/chocolate_factory_mcp.py

# 3. Reiniciar Claude Desktop completamente
killall "Claude Desktop"
open -a "Claude Desktop"
```

### Problema 2: Timeout en llamadas API

**Síntomas**: Tools fallan con timeout

**Solución**:
```python
# Aumentar timeout en api_client.py
client = httpx.AsyncClient(timeout=30.0)  # Default: 5s
```

### Problema 3: API no accesible desde MCP

**Síntomas**: Connection refused

**Solución**:
```bash
# Verificar API running
curl http://localhost:8000/health

# Verificar firewall
sudo ufw allow 8000/tcp
```

---

## 📊 Valor del Sprint 11

### Beneficios Inmediatos

1. **Productividad Claude Code**: Consultas directas sin curl manual
2. **Experiencia natural**: Claude accede a datos como "memoria nativa"
3. **Reutilizable**: MCP server puede usarse en otros proyectos
4. **Extensible**: Añadir nuevos tools es trivial (1 función nueva)

### Casos de Uso Reales

```
# Caso 1: Planificación producción
User: "¿Cuándo debo producir esta semana?"
Claude: [usa get_optimal_windows + get_weekly_forecast]
Response: "Te recomiendo Lunes 02-05h (0.06€/kWh) y Miércoles 01-06h (0.07€/kWh)"

# Caso 2: Análisis en tiempo real
User: "¿Es buen momento para producir ahora?"
Claude: [usa get_current_price + get_current_weather + get_production_recommendation]
Response: "Sí. Precio 0.09€ (P3-Valle), 22°C temperatura óptima. Recomendación: OPTIMAL"

# Caso 3: Troubleshooting
User: "¿Por qué el sistema no ingiere datos?"
Claude: [usa get_system_health + get_predictive_alerts]
Response: "Sistema healthy. Sin alertas activas. Última ingesta: hace 2 min"
```

---

## 🔄 Próximos Pasos después Sprint 11

### Si Sprint 11 es éxito → Sprint 12 (Forgejo CI/CD)
- Usar Forgejo para versionar MCP server
- CI/CD tests automatizados para tools
- Registry privado para imágenes Docker

### Extensiones Futuras MCP
- Tool `execute_optimization` (ejecutar plan recomendado)
- Tool `send_notification` (alertas a Telegram/Discord)
- Tool `export_report` (generar PDF con análisis)

---

## 📚 Referencias

- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **Anthropic MCP SDK**: https://github.com/anthropics/anthropic-sdk-python
- **FastAPI OpenAPI**: http://localhost:8000/docs
- **Chocolate Factory API**: `docs/API_REFERENCE.md`

---

**Fecha creación**: 2025-10-08
**Autor**: Infrastructure Sprint Planning
**Versión**: 1.0
**Sprint anterior**: Sprint 10 - Consolidación (✅ COMPLETADO)
**Sprint siguiente**: Sprint 12 - Forgejo CI/CD (planeado)
