# Instrucciones para Claude Code - Chocolate Factory System

> **ATENCIÓN CLAUDE**: Lee este documento completamente antes de hacer cualquier sugerencia o cambio en el código.

## 📚 Estructura de Documentación

Este proyecto sigue una estructura específica de documentación en `.claude/`. **SIEMPRE consulta estos archivos antes de proponer cambios:**

```
.claude/
├── architecture.md          # 🏗️ Infraestructura técnica CONFIRMADA
├── instructions.md          # 📋 Este archivo
├── commands/               # 🔧 Comandos y scripts operacionales
├── context/               # 📊 Contexto de negocio y producción
├── hooks/                # 🪝 Scripts ejecutables
├── rules/                # 📏 Reglas de negocio y seguridad
└── settings*.json        # ⚙️ Configuraciones del proyecto
```

## 🎯 Prioridades y Principios

### 1. **NUNCA cambiar el stack tecnológico**
   - ✅ USA: FastAPI + HTML/JS Vanilla + InfluxDB + Docker
   - ❌ NO sugieras: React, Vue, PostgreSQL, MongoDB, etc.
   - Ver: `.claude/architecture.md` para detalles completos

### 2. **Contexto de negocio es crítico**
   - Somos una fábrica de chocolate REAL en Linares, Jaén
   - La producción NUNCA se detiene (excepto emergencias documentadas)
   - Los costos energéticos son factor clave en España
   - Ver: `.claude/context/business/` para detalles

### 3. **Seguridad y datos sensibles**
   - NUNCA expongas API keys o tokens en código
   - Sigue las reglas en `.claude/rules/security-sensitive-data.md`
   - Usa variables de entorno para credenciales

## 📁 Guía de Archivos Clave

### `/commands/` - Scripts Operacionales
```bash
backfill.md         # Proceso completo de recuperación de datos
quick-backfill.md   # Backfill rápido para gaps pequeños
security-check.md   # Verificación de seguridad del sistema
README.md          # Documentación de comandos disponibles
```
**Uso**: Consultar antes de sugerir nuevos scripts o modificar procesos de datos.

### `/context/` - Conocimiento del Dominio

#### `/context/business/` - Negocio
```yaml
cost_structure.yaml      # Estructura de costos real de producción
production-targets.md    # Objetivos y métricas de producción
shift_schedule.yaml      # Turnos y horarios de fábrica
```

#### `/context/production/` - Producción
```yaml
energy-consumption.md         # Patrones de consumo energético
machinery.md                  # Especificaciones de maquinaria
production_constraints.yaml   # Limitaciones físicas y operativas
production-process.md         # Proceso completo de fabricación
```

**IMPORTANTE**: Estos archivos contienen la realidad operacional. Úsalos para:
- Validar que las sugerencias sean factibles
- Entender limitaciones físicas reales
- Proponer optimizaciones realistas

### `/hooks/` - Scripts Ejecutables
```bash
backfill.sh         # Script shell para backfill automático
quick-backfill.sh   # Versión rápida del backfill
security-check.sh   # Auditoría de seguridad
```
**Nota**: Estos son scripts bash que se ejecutan directamente. Mantén compatibilidad.

### `/rules/` - Reglas de Negocio y Seguridad
```markdown
production_rules.md           # Reglas operacionales de producción
security-sensitive-data.md   # Manejo de datos sensibles
siar-etl-solution.md         # Solución ETL para datos SIAR
business-logic-suggestions.md # Lógica para sistema de recomendaciones
```

## 🚀 Flujo de Trabajo Recomendado

### Antes de proponer cualquier cambio:

1. **Revisa la arquitectura**
   ```bash
   cat .claude/architecture.md
   ```

2. **Entiende el contexto de negocio**
   ```bash
   ls -la .claude/context/business/
   ls -la .claude/context/production/
   ```

3. **Verifica las reglas aplicables**
   ```bash
   grep -r "NUNCA\|SIEMPRE\|CRÍTICO" .claude/rules/
   ```

4. **Consulta comandos existentes**
   ```bash
   cat .claude/commands/README.md
   ```

## 💻 Patrones de Código Establecidos

### Backend (FastAPI)
```python
# Ubicación: src/fastapi-app/
# Patrón: Servicios + Routers + Models

# ✅ CORRECTO
from services.influx_service import InfluxDBService
from services.energy_service import EnergyDataIngestion

# ❌ INCORRECTO - No uses ORMs SQL
from sqlalchemy import create_engine  # NO!
```

### Frontend (HTML + JS Vanilla)
```javascript
// Ubicación: Embebido en HTMLResponse o static/
// Patrón: Fetch API + DOM Manipulation

// ✅ CORRECTO
fetch('/dashboard/complete')
  .then(res => res.json())
  .then(data => updateDashboard(data));

// ❌ INCORRECTO - No uses frameworks
import React from 'react';  // NO!
```

### Base de Datos (InfluxDB)
```python
# Ubicación: services/influx_service.py
# Patrón: Time series con measurements y tags

# ✅ CORRECTO
point = Point("energy_prices") \
    .tag("source", "REE") \
    .field("price_eur_kwh", value) \
    .time(timestamp)

# ❌ INCORRECTO - No SQL
cursor.execute("INSERT INTO prices...")  # NO!
```

## 🔄 Procesos Críticos

### 1. Ingesta de Datos Energéticos
- **Fuente**: REE API (Red Eléctrica España)
- **Frecuencia**: Cada hora
- **Backfill**: Ver `.claude/commands/backfill.md`
- **Validación**: Precios entre 0.01 - 0.80 €/kWh

### 2. Sistema de Recomendaciones
- **Reglas**: `.claude/rules/business-logic-suggestions.md`
- **Thresholds**: Basados en realidad española
- **Output**: NUNCA sugerir parada total
- **Formato**: Mensajes accionables para operadores

### 3. Predicciones ML
- **Modelos**: Pickled en `./models/`
- **Reentrenamiento**: Semanal con 30 días de datos
- **Métricas**: MAE < 0.02 €/kWh para energía
- **Fallback**: Si falla ML, usar reglas determinísticas

## ⚠️ Errores Comunes a Evitar

### ❌ NO HAGAS ESTO:
```python
# 1. No cambies la base de datos
import psycopg2  # NO! Usamos InfluxDB

# 2. No añadas frameworks frontend
npm install react  # NO! Usamos Vanilla JS

# 3. No ignores el contexto de negocio
if price > 0.30:
    return "DETENER PRODUCCIÓN"  # NO! Nunca parar

# 4. No hardcodees credenciales
api_key = "sk-1234567890"  # NO! Usa .env

# 5. No asumas ubicación diferente
# Estamos en Linares, Jaén, España - NO en USA
```

### ✅ HAZ ESTO EN SU LUGAR:
```python
# 1. Usa InfluxDB para time series
from influxdb_client import InfluxDBClient

# 2. JavaScript vanilla para frontend
document.getElementById('dashboard').innerHTML = data;

# 3. Optimiza sin detener
if price > 0.30:
    return "REDUCIR A 70% CAPACIDAD"

# 4. Variables de entorno
api_key = os.getenv('AEMET_API_KEY')

# 5. Contexto español
timezone = "Europe/Madrid"
currency = "EUR"
```

## 📊 Métricas de Éxito

Las sugerencias de código deben optimizar para:

1. **Disponibilidad**: >99.5% uptime del sistema
2. **Eficiencia energética**: Reducir costo/kg chocolate
3. **Calidad de predicción**: MAE <5% en predicciones
4. **Tiempo de respuesta**: Dashboard <2s carga
5. **Mantenibilidad**: Código simple, sin dependencias innecesarias

## 🔐 Checklist de Seguridad

Antes de cualquier commit:

- [ ] No hay API keys en el código
- [ ] Variables sensibles en `.env`
- [ ] Endpoints no exponen data sensible
- [ ] Logs no contienen passwords/tokens
- [ ] Docker images no incluyen `.env`

## 📞 Contacto y Escalación

Si necesitas clarificación sobre:
- **Reglas de negocio**: Consulta `.claude/context/business/`
- **Limitaciones técnicas**: Ver `.claude/architecture.md`
- **Procesos de producción**: Lee `.claude/context/production/`
- **Seguridad**: Revisa `.claude/rules/security-sensitive-data.md`

## 🎯 Resumen Ejecutivo para Claude

1. **Stack fijo**: FastAPI + HTML/JS + InfluxDB + Docker
2. **Contexto**: Fábrica real de chocolate en España
3. **Prioridad**: Producción continua y eficiencia energética
4. **Seguridad**: Nunca expongas credenciales
5. **Documentación**: Siempre consulta `.claude/` antes de proponer

---

**RECUERDA**: Este sistema está en producción en una fábrica real. Las sugerencias deben ser prácticas, probadas y alineadas con la realidad operacional documentada en `.claude/`.