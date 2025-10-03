# 🎯 SPRINT 07: Series Temporales SIAR

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 ALTA
> **Prerequisito**: Sprint 06 completado
> **Estimación**: 6-8 horas

---

## 📋 Objetivo

Activar uso de **88,935 registros SIAR** (2000-2025) para:
1. Predicción condiciones climáticas 7 días
2. Análisis correlación temperatura/humedad → eficiencia producción
3. Detección patrones estacionales (verano crítico)

---

## 📦 Entregables

### 1. Servicio Predicción Climática
- [ ] `services/weather_forecasting_service.py`
- [ ] Modelo Prophet para temperatura/humedad (7 días)
- [ ] Integración datos SIAR históricos

### 2. Análisis Correlación
- [ ] Correlación temp/humidity → chocolate_production_index
- [ ] Identificar thresholds críticos (verano > 35°C)
- [ ] Función `calculate_weather_impact_score(temp, humidity)`

### 3. Detección Estacionalidad
- [ ] Patrones mensuales (Jun-Ago crítico)
- [ ] Ajuste costos estacionales automático
- [ ] Alertas predictivas "Próxima ola de calor en 3 días"

### 4. Integración ML Costos
- [ ] Añadir features climáticas predichas a `enhanced_ml_service.py`
- [ ] Reentrenar modelos con features SIAR
- [ ] API `/predict/weather-impact?days=7`

---

## 🧪 Métricas de Éxito

- **Temperatura**: MAE < 2°C (predicción 7 días)
- **Humedad**: MAE < 5% (predicción 7 días)
- **Correlación detectada**: R² > 0.6 (temp → eficiencia)
- **Alertas estacionales**: 95% accuracy (verano detectado)

---

## ✅ Checklist

- [ ] Extraer datos SIAR completos (88,935 registros)
- [ ] Entrenar modelo Prophet clima (temp + humidity)
- [ ] Calcular correlaciones históricas
- [ ] Integrar predicciones con modelo costos
- [ ] Dashboard: Widget "Próximas condiciones climáticas"
- [ ] APScheduler: Job predicción clima (cada 6h)

---

**Próximo Sprint**: Sprint 08 - Optimización Horaria
