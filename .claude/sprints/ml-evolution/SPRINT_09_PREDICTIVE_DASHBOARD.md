# 🎯 SPRINT 09: Dashboard Predictivo Completo

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 ALTA
> **Prerequisito**: Sprints 06-08 completados
> **Estimación**: 6-8 horas

---

## 📋 Objetivo

Dashboard con **ventanas óptimas predichas**, análisis **desviaciones REE D-1 vs real**, alertas predictivas.

---

## 📦 Entregables

### 0. Rescate Funcionalidad Sprint 08
**Card "Análisis REE" eliminada** (v0.43.0 - redundante con Timeline Horaria).

**Funcionalidades a rescatar/mejorar**:
1. **BusinessLogicService** (ya implementado en Sprint 05)
   - Mantener lógica humanizada de recomendaciones
   - Ubicación actual: `services/business_logic_service.py`
   - Integrar en nuevos widgets (no en card independiente)

2. **Recomendaciones contextualizadas** → Integrar en Widget "Próximas Ventanas Óptimas"
   - Rescatar: Análisis momento energético actual
   - Rescatar: Oportunidad de ahorro vs promedio
   - Rescatar: Análisis por procesos (Conchado/Rolado/Templado)
   - **Mejora**: Usar Prophet para ventanas futuras, no solo momento actual

3. **Métricas eliminadas** (ahora redundantes):
   - ❌ Momento energético actual → Ya en Timeline Horaria (granularidad hora a hora)
   - ❌ Ranking precio actual → Ya en Timeline Horaria (posición vs 24h)
   - ❌ Proceso recomendado → Ya en Timeline Horaria (proceso activo por hora)

**Nueva arquitectura (Sprint 09)**:
- Widget único "Próximas Ventanas Óptimas" que agrega:
  - Recomendaciones BusinessLogicService
  - Predicciones Prophet 7 días
  - Contexto timeline horaria
  - Alertas predictivas

### 1. Widget "Próximas Ventanas Óptimas"
```
┌─────────────────────────────────────────┐
│  🟢 PRÓXIMAS VENTANAS ÓPTIMAS (7 DÍAS)  │
├─────────────────────────────────────────┤
│  Lun 00-06h: EXCELENTE (0.08€/kWh)     │
│    → Conchado intensivo 80kg            │
│    → Ahorro: 12€ vs producir en pico   │
│                                         │
│  Mar 02-05h: ÓPTIMA (0.06€/kWh)        │
│    → Premium + stock estratégico        │
│    → Ahorro: 18€ vs producir en pico   │
│                                         │
│  Jue 19-22h: ⚠️ EVITAR (0.32€/kWh)     │
│    → Solo completar lotes en curso      │
└─────────────────────────────────────────┘
```

### 2. Análisis Desviación REE D-1
```
┌──────────────────────────────────────┐
│  📊 REE D-1 vs REAL (ÚLTIMAS 24H)   │
├──────────────────────────────────────┤
│  Desviación Media: ±0.018 €/kWh     │
│  Accuracy Score: 87%                 │
│  Trend: ESTABLE                      │
│                                      │
│  ⚠️ Mayor desviación: 10-14h (pico) │
│  ✅ Más confiable: 00-06h (valle)   │
└──────────────────────────────────────┘
```

### 3. Alertas Predictivas
- [ ] "⚠️ Pico precio inminente: 19h hoy (0.34€/kWh predicho)"
- [ ] "🌡️ Ola calor próximos 3 días: Refrigeración preventiva"
- [ ] "💰 Ventana óptima abierta: Próximas 6h precios valle"

### 4. Comparativa Ahorro Real vs Planificado
```
┌────────────────────────────────┐
│  💰 AHORRO ENERGÉTICO SEMANAL  │
├────────────────────────────────┤
│  Plan Optimizado: 892€         │
│  Plan Baseline:   1,047€       │
│  Ahorro Real:     155€ (15%)   │
│                                │
│  Objetivo Mensual: 620€        │
│  Progreso: 25% (Semana 1/4)    │
└────────────────────────────────┘
```

---

## 🧪 Métricas de Éxito

- **Visualización**: Widgets claros y accionables
- **Actualización**: Tiempo real (auto-refresh 30s)
- **Precisión alertas**: > 90% (alertas útiles vs falsas alarmas)
- **Adoption**: Usuarios siguen recomendaciones > 70% del tiempo

---

## ✅ Checklist

- [ ] Widget ventanas óptimas (JavaScript)
- [ ] Análisis desviación REE D-1 (backend service)
- [ ] Sistema alertas predictivas (thresholds inteligentes)
- [ ] Comparativa ahorro (tracking real vs predicho)
- [ ] CSS responsive para nuevos widgets
- [ ] Integración con `/dashboard/complete`

---

**Próximo Sprint**: Sprint 10 - Consolidación y Limpieza
