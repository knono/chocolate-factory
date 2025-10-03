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
