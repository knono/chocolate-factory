# 🎯 SPRINT 08: Optimización Horaria Inteligente

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 ALTA
> **Prerequisito**: Sprint 06 + Sprint 07 completados
> **Estimación**: 8-10 horas

---

## 📋 Objetivo

Modelo de **planificación horaria 24h** basado en:
- Predicciones REE (Sprint 06)
- Predicciones clima (Sprint 07)
- Estado planta actual
- Constraints de negocio (conchado, templado, etc.)

---

## 📦 Entregables

### 1. Motor Optimización
- [ ] `services/hourly_optimizer_service.py`
- [ ] Algoritmo optimización (Linear Programming o Genetic Algorithm)
- [ ] Input: Predicciones REE + clima + estado planta
- [ ] Output: Plan horario 24h (qué, cuándo, cuánto)

### 2. Planificador Procesos
```python
Plan horario 24h:
- 00-06h: Conchado 80kg (valle, 0.08€/kWh)
- 06-10h: Templado 40kg (llano, 0.15€/kWh)
- 10-14h: Mezcla 60kg (pico, evitar conchado)
- ...
```

### 3. Cálculo Ahorro
- [ ] Función `calculate_savings(plan_optimized vs plan_baseline)`
- [ ] Métrica: Ahorro €/día esperado
- [ ] Comparativa: Plan manual vs plan optimizado

### 4. Recomendaciones Contextualizadas
- [ ] Por proceso: "Conchado óptimo: 02-05h (ahorro 0.18€/kg)"
- [ ] Por día: "Mejor día producción premium: Martes (condiciones ideales)"
- [ ] Por semana: "Ventana óptima: Lun 00h - Mar 06h (valle + clima óptimo)"

---

## 🧪 Métricas de Éxito

- **Ahorro energético**: > 15% vs baseline
- **Feasibility**: 100% planes factibles (respetan constraints)
- **Adoption**: Dashboard muestra plan claro y accionable
- **ROI**: Ahorro €/mes cuantificable

---

## ✅ Checklist

- [ ] Implementar motor optimización (scipy.optimize o similar)
- [ ] Definir constraints producción (capacidad, tiempos, etc.)
- [ ] API `/optimize/production/daily`
- [ ] Integrar con BusinessLogicService
- [ ] Dashboard: Widget "Plan Optimizado 24h"
- [ ] Calcular y mostrar ahorro estimado

---

**Próximo Sprint**: Sprint 09 - Dashboard Predictivo
