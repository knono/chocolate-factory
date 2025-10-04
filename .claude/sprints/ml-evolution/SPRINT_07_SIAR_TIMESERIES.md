# 🎯 SPRINT 07: Análisis Histórico SIAR (REVISADO)

> **Estado**: 🟡 EN PROGRESO
> **Prioridad**: 🟡 ALTA
> **Prerequisito**: Sprint 06 completado
> **Estimación**: 4-6 horas
> **Fecha Inicio**: 2025-10-04

---

## 🔄 REVISIÓN DEL ENFOQUE

### ❌ Enfoque Original (Incorrecto)
- Predicción climática con Prophet (REDUNDANTE - AEMET ya lo hace)
- Entrenar modelos para predecir temperatura/humedad futura

### ✅ Enfoque Corregido (Realista)
- **Análisis histórico** de 88,935 registros SIAR (2000-2025)
- **Correlaciones basadas en evidencia** de 25 años
- **Integración** predicciones AEMET + contexto histórico SIAR
- **Recomendaciones inteligentes** basadas en datos reales

---

## 📋 Objetivo Revisado

Usar **88,935 registros SIAR** (2000-2025) para:
1. **Análisis correlación histórica**: temp/humedad → eficiencia producción chocolate (25 años evidencia)
2. **Detección patrones estacionales**: verano crítico, primavera óptima (datos reales)
3. **Umbrales basados en evidencia**: ¿A qué temperatura falló la producción históricamente?
4. **Contexto para predicciones AEMET**: "Mañana 32°C" + "A 32°C históricamente producción cayó 15%"

---

## 📦 Entregables Revisados

### 1. Servicio Análisis Histórico SIAR
- [ ] `services/siar_analysis_service.py`
- [ ] Análisis correlación temperatura → eficiencia producción (25 años)
- [ ] Análisis correlación humedad → calidad templado chocolate
- [ ] Detección umbrales críticos basados en datos reales

### 2. Patrones Estacionales con Evidencia
- [ ] Estadísticas mensuales (Jun-Ago: ¿cuántos días críticos reales?)
- [ ] Identificar mejores/peores meses para producción (datos, no asunciones)
- [ ] Función `get_seasonal_production_efficiency(month)`

### 3. Integración AEMET + SIAR
- [ ] Predicciones AEMET (7 días) + Contexto histórico SIAR
- [ ] Recomendaciones: "Mañana 30°C → En 2015 a 30°C reducimos 10% producción"
- [ ] Función `contextualize_aemet_forecast_with_siar_history()`

### 4. API Endpoints de Análisis Histórico
- [ ] `GET /analysis/weather-correlation` - Correlaciones históricas
- [ ] `GET /analysis/seasonal-patterns` - Patrones estacionales
- [ ] `GET /analysis/critical-thresholds` - Umbrales basados en evidencia
- [ ] `GET /forecast/aemet-contextualized` - AEMET + contexto SIAR

---

## 🧪 Métricas de Éxito Revisadas

- **Correlación temperatura → eficiencia**: R² > 0.6 (25 años datos)
- **Correlación humedad → calidad**: R² > 0.5 (25 años datos)
- **Patrones estacionales detectados**: 12 meses analizados
- **Umbrales críticos identificados**: 3+ umbrales basados en percentiles históricos
- **Integración AEMET**: 100% predicciones contextualizadas con historia

---

## ✅ Checklist Revisado

### Fase 1: Análisis Histórico SIAR (2-3h)
- [ ] Extraer datos SIAR completos (88,935 registros)
- [ ] Calcular correlaciones temp → eficiencia (25 años)
- [ ] Calcular correlaciones humidity → calidad templado
- [ ] Detectar umbrales críticos (percentil 90, 95, 99)
- [ ] Análisis estacional (estadísticas por mes)

### Fase 2: Integración AEMET + SIAR (1-2h)
- [ ] Crear función contexto histórico para predicciones AEMET
- [ ] Integrar con `enhanced_ml_service.py`
- [ ] API endpoints análisis histórico
- [ ] Recomendaciones contextualizadas

### Fase 3: Dashboard + Documentación (1h)
- [ ] Widget dashboard: "Contexto Climático Histórico"
- [ ] Mostrar correlaciones y patrones
- [ ] Actualizar documentación (CLAUDE.md, README.md)
- [ ] Tests básicos de correlaciones

---

## 🎯 Ejemplo de Flujo Corregido

### ❌ Flujo Original (Redundante)
```
SIAR histórico → Prophet → Predicción 7 días
                    ↓
            (Redundante con AEMET)
```

### ✅ Flujo Corregido (Inteligente)
```
AEMET API → "Mañana 32°C, 75% humedad"
    ↓
SIAR histórico (25 años) → "A 32°C, producción cayó 12% (evidencia 2010-2023)"
    ↓
Recomendación inteligente → "REDUCIR producción 15% mañana (basado en 87 días similares)"
```

---

## 📊 Valor Real del Sprint 07

| Componente | Antes | Después Sprint 07 | Ganancia |
|---|---|---|---|
| **Predicciones clima** | AEMET API (ya existe) | AEMET API (sin cambios) | 0% |
| **Contexto histórico** | 0% (ignorado) | 100% (25 años evidencia) | **+100%** |
| **Umbrales críticos** | Asumidos (35°C) | Basados en datos reales | **+80%** |
| **Correlaciones** | 0% | R² >0.6 demostrado | **+100%** |
| **Recomendaciones** | Genéricas | Contextualizadas con historia | **+70%** |

---

## 🔧 Archivos a Crear/Modificar

### Crear
- `src/fastapi-app/services/siar_analysis_service.py` (Nuevo)

### Modificar
- `src/fastapi-app/main.py` (Añadir endpoints análisis)
- `src/fastapi-app/services/enhanced_ml_service.py` (Integrar contexto SIAR)
- `src/fastapi-app/services/dashboard.py` (Widget contexto histórico)

### Eliminar
- ~~`services/weather_forecasting_service.py`~~ (Redundante - ELIMINAR)

---

## 🚫 Lo que NO Haremos

- ❌ Predicción climática con Prophet (AEMET ya lo hace)
- ❌ Entrenar modelos ML para predecir temperatura futura
- ❌ Duplicar funcionalidad AEMET
- ❌ APScheduler job predicción clima (redundante)

---

## ✅ Lo que SÍ Haremos

- ✅ Análisis correlación histórica (25 años evidencia)
- ✅ Detección patrones estacionales con datos reales
- ✅ Umbrales críticos basados en percentiles históricos
- ✅ Contextualizar predicciones AEMET con historia SIAR
- ✅ Recomendaciones inteligentes basadas en evidencia

---

**Próximo Sprint**: Sprint 08 - Optimización Horaria
**Última Actualización**: 2025-10-04 (Enfoque corregido)
