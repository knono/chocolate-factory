# 🧠 ML Evolution Sprints - Chocolate Factory

> **Objetivo**: Evolucionar de modelos sintéticos a ML predictivo real usando series temporales históricas (88,935 registros SIAR + 42,578 registros REE).

## 📋 Índice de Sprints

### ✅ Sprints Base Completados (Sprint 01-05)
- **Sprint 01-02**: Migración arquitectura monolítica → microservicios
- **Sprint 03**: Service Layer + Repositories pattern
- **Sprint 04**: SIAR ETL + 25 años datos históricos
- **Sprint 05**: Dashboard unificado + Business Logic Service

---

## 🚀 ML Evolution Sprints (Sprint 06-10)

### ✅ Sprint 06: Predicción de Precios REE (COMPLETADO)
**Estado**: ✅ **COMPLETADO** (3 de Octubre, 2025)
**Archivo**: [`SPRINT_06_PRICE_FORECASTING.md`](./SPRINT_06_PRICE_FORECASTING.md)

**Objetivo**: Implementar modelo Prophet para predecir precios REE próximas 168h (7 días).

**Entregables Completados**:
- ✅ Modelo Prophet operacional (prophet 1.1.7)
- ✅ Heatmap poblado con predicciones reales (no simuladas)
- ✅ API `/predict/prices/weekly` + `/predict/prices/hourly`
- ✅ Intervalos de confianza 95%
- ✅ Métricas: MAE 0.033 €/kWh, R² 0.49, Coverage 88.3%
- ✅ Dashboard integration con tooltips Safari/Chrome/Brave
- ✅ APScheduler job: predicciones horarias automáticas

**Impacto**: Heatmap ahora muestra predicciones Prophet reales. Sistema de forecasting operacional.

---

### 🔵 Sprint 07: Series Temporales SIAR
**Estado**: 🔴 NO INICIADO
**Archivo**: [`SPRINT_07_SIAR_TIMESERIES.md`](./SPRINT_07_SIAR_TIMESERIES.md)

**Objetivo**: Activar uso de 88,935 registros SIAR para predicción climática y patrones estacionales.

**Entregables**:
- ✅ Análisis correlación temperatura/humedad → eficiencia producción
- ✅ Detección patrones estacionales (verano crítico)
- ✅ Predicción condiciones ambientales 7 días
- ✅ Integración con modelo costos

**Impacto**: Predicción climática → Planificación meteorológica anticipada.

---

### 🔵 Sprint 08: Optimización Horaria Inteligente
**Estado**: 🔴 NO INICIADO
**Archivo**: [`SPRINT_08_HOURLY_OPTIMIZATION.md`](./SPRINT_08_HOURLY_OPTIMIZATION.md)

**Objetivo**: Modelo de planificación horaria 24h basado en predicciones REE + clima + estado planta.

**Entregables**:
- ✅ Motor de optimización horaria
- ✅ Plan recomendado 24h (qué producir, cuándo, cuánto)
- ✅ Cálculo ahorro energético estimado
- ✅ Recomendaciones contextualizadas por proceso (conchado, templado, etc.)

**Impacto**: Planificación automática vs recomendaciones genéricas.

---

### 🔵 Sprint 09: Dashboard Predictivo Completo
**Estado**: 🔴 NO INICIADO
**Archivo**: [`SPRINT_09_PREDICTIVE_DASHBOARD.md`](./SPRINT_09_PREDICTIVE_DASHBOARD.md)

**Objetivo**: Dashboard con ventanas óptimas predichas, análisis de desviaciones REE D-1 vs real.

**Entregables**:
- ✅ Widget "Próximas ventanas óptimas" (7 días)
- ✅ Análisis desviación REE D-1 vs precios reales
- ✅ Alertas predictivas (picos de precio inminentes)
- ✅ Comparativa ahorro real vs planificado

**Impacto**: Dashboard predictivo funcional para toma de decisiones.

---

### 🔵 Sprint 10: Consolidación y Limpieza
**Estado**: 🔴 NO INICIADO
**Archivo**: [`SPRINT_10_CONSOLIDATION.md`](./SPRINT_10_CONSOLIDATION.md)

**Objetivo**: Unificar servicios ML, eliminar código legacy, documentación final.

**Entregables**:
- ✅ Unificación: `direct_ml.py` + `enhanced_ml_service.py` + `ml_models.py` → 1 servicio
- ✅ Limpieza modelos sintéticos obsoletos
- ✅ Tests automatizados predicciones
- ✅ Documentación técnica completa
- ✅ Métricas ROI (ahorro energético demostrable)

**Impacto**: Sistema ML limpio, mantenible, y con valor medible.

---

## 📊 Valor Actual vs Potencial

| Componente | Valor Sprint 05 | Valor Sprint 10 | Ganancia |
|---|---|---|---|
| **Datos SIAR** | 0% (no usados) | 80% (predicción clima) | +80% |
| **Datos REE** | 20% (viz) | 90% (predicción) | +70% |
| **Modelos ML** | 30% (sintético) | 95% (time series) | +65% |
| **Heatmap** | 10% (estático) | 85% (predictivo) | +75% |
| **Recomendaciones** | 40% (reglas fijas) | 75% (contextualizadas) | +35% |

---

## 🎯 Estrategia de Ejecución

### Filosofía de Sprints
1. **Sin interrupción de servicio**: Cada sprint añade funcionalidad sin romper existente
2. **Entregables mínimos viables**: Al final de cada sprint, sistema 100% funcional
3. **Documentación continua**: `.claude/sprints/` mantiene contexto entre sesiones
4. **Limpieza progresiva**: Eliminar legacy solo cuando nuevo código probado

### Workflow por Sprint
```
1. Leer SPRINT_XX.md → Entender objetivos
2. Implementar entregables incrementalmente
3. Actualizar SPRINT_XX.md con progreso
4. Al completar: Marcar ✅ COMPLETADO
5. Actualizar README.md (este archivo)
6. Mover a siguiente sprint
```

### Criterios de Completitud
Cada sprint se considera **COMPLETADO** cuando:
- ✅ Todos los entregables implementados y probados
- ✅ Sistema funciona sin errores
- ✅ Documentación actualizada
- ✅ Métricas de éxito alcanzadas
- ✅ Sin deuda técnica crítica

---

## 📝 Notas para Claude Code

### Al iniciar sesión
1. **Leer este README** para contexto general
2. **Identificar sprint activo** (buscar estado 🟡 PENDIENTE)
3. **Abrir SPRINT_XX.md correspondiente** para detalles
4. **Revisar checklist** de tareas pendientes

### Durante desarrollo
1. **Actualizar estado** en SPRINT_XX.md (checkboxes `- [ ]` → `- [x]`)
2. **Documentar problemas** en sección "Problemas Encontrados"
3. **Registrar decisiones** en "Decisiones de Diseño"

### Al completar sprint
1. **Marcar sprint como ✅ COMPLETADO** en este README
2. **Actualizar CLAUDE.md** si hay cambios arquitectura
3. **Eliminar archivos legacy** si aplicable
4. **Crear commit descriptivo**:
   ```bash
   git commit -m "✅ SPRINT XX - [Título Sprint] COMPLETADO"
   ```

---

## 🔄 Estado Actual del Proyecto

**Sprint Activo**: Sprint 06 - Predicción de Precios REE
**Fecha Inicio**: 2025-10-03
**Completitud Total**: Sprint 05/10 (50% base arquitectura, 0% ML evolution)

**Próximos Pasos**:
1. Leer [`SPRINT_06_PRICE_FORECASTING.md`](./SPRINT_06_PRICE_FORECASTING.md)
2. Implementar modelo predictivo precios LSTM/Prophet
3. Integrar con heatmap dashboard
4. Validar métricas y marcar completado

---

**Última actualización**: 2025-10-03
**Autor**: Sistema ML Evolution
**Versión**: 1.0
