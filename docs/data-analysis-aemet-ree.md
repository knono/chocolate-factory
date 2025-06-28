# Análisis de Patrones de Datos: AEMET y REE

**Fecha de análisis**: 27 de junio de 2025  
**Autor**: TFM Chocolate Factory Project  
**Estado**: Hallazgos críticos para modelado MLflow

## Resumen Ejecutivo

Durante la implementación de las APIs de AEMET y REE se han identificado patrones de datos críticos que impactan directamente en la estrategia de modelado de Machine Learning y optimización energética de la fábrica de chocolate.

## Hallazgos Principales

### 1. REE (Red Eléctrica de España) - Datos Energéticos

**✅ Comportamiento Excelente**
- **Cobertura temporal**: 24 horas completas (00:00-23:00)
- **Frecuencia**: Datos cada hora sin interrupciones
- **Fiabilidad**: ⭐⭐⭐⭐⭐ Datos en tiempo real extremadamente precisos
- **Ejemplo real**: 142.6 €/MWh a las 13:00, 77.33 €/MWh a las 14:00

### 2. AEMET - Datos Meteorológicos (Estación Linares 5279X)

#### Observaciones Reales - Patrón Crítico Identificado

**⚠️ Limitación Temporal Significativa**
- **Cobertura**: Solo 00:00-07:00 (8 registros por día)
- **Gap crítico**: Sin datos reales 08:00-23:00
- **Impacto**: Ausencia de datos durante horario productivo principal

**Patrón de temperaturas observado (27/06/2025)**:
```
00:00 → 28.5°C  |  04:00 → 23.9°C
01:00 → 27.6°C  |  05:00 → 22.8°C ← Temperatura mínima
02:00 → 26.8°C  |  06:00 → 23.4°C
03:00 → 24.8°C  |  07:00 → 25.6°C ← Último registro
                  08:00-23:00 → NO HAY DATOS
```

#### Discrepancias en Condiciones Extremas

**Caso de estudio - Ola de calor 27/06/2025**:
- **AEMET (07:00)**: 25.6°C
- **Observación real (13:00)**: ~35°C
- **Predicción local**: Máxima 39°C
- **Discrepancia**: 10°C de diferencia

### 3. Predicción AEMET vs Observación

**API de Predicción Horaria Disponible**:
- **Endpoint**: `prediccion/especifica/municipio/horaria/23055`
- **Cobertura**: 48 horas de predicción
- **Resolución**: Datos cada hora
- **Estado**: ✅ Funcional con datos actualizados (09:40 AM)

## Implicaciones para MLflow y Modelado

### Estrategia de Features Híbrida Recomendada

```python
# FEATURES ENERGÉTICOS (REE) - Cobertura completa 24h
ree_price_eur_kwh          # Precio electricidad por hora
ree_demand_mw              # Demanda energética nacional  
tariff_period              # P1-P6 según horario
renewable_percentage       # % energía renovable

# FEATURES METEOROLÓGICOS - Enfoque híbrido
# 00:00-07:00: Datos reales AEMET
temp_observed             # Temperatura observada (madrugada)
humidity_observed         # Humedad observada (madrugada)

# 08:00-23:00: Predicción AEMET + validación externa
temp_predicted            # Predicción horaria AEMET
temp_validated            # Cross-validation con OpenWeatherMap
humidity_predicted        # Predicción horaria AEMET

# FEATURES DERIVADOS
chocolate_production_index    # Índice óptimo producción
heat_stress_factor           # Factor estrés térmico
energy_optimization_score    # Combinación precio + clima
```

### Sincronización Temporal

**Desafío identificado**:
- REE: Datos cada hora 24/7 ✅
- AEMET observación: Solo 8 horas/día ⚠️
- AEMET predicción: 48 horas horizonte ✅

**Solución propuesta**:
1. **Backbone REE**: Usar timestamps REE como referencia principal
2. **Interpolación AEMET**: Algoritmos para gap 08:00-23:00
3. **Validación cruzada**: OpenWeatherMap para condiciones extremas
4. **Features lag**: Usar última observación AEMET válida

## Recomendaciones Técnicas

### Para Desarrollo Inmediato

1. **Implementar interpolación temporal** entre 07:00 y 00:00 siguiente día
2. **Integrar API predicción AEMET** para horario diurno
3. **Sistema de alertas** cuando discrepancia > 5°C entre fuentes
4. **Feature engineering** para manejar datos faltantes

### Para Siguiente Iteración

1. **OpenWeatherMap como segunda fuente** para validación
2. **Modelo de detección de anomalías** meteorológicas
3. **Correlación avanzada** REE-clima para optimización
4. **Dashboard de calidad de datos** en tiempo real

## Conclusiones

Los hallazgos revelan una **arquitectura de datos asimétrica** donde:

- **REE proporciona datos perfectos** para optimización energética
- **AEMET requiere estrategia híbrida** (observación + predicción)
- **El gap temporal 08:00-23:00 es crítico** para producción de chocolate
- **La validación cruzada es esencial** durante eventos meteorológicos extremos

Esta asimetría no es un problema sino una **característica del dominio** que debe ser modelada explícitamente en la arquitectura de ML, proporcionando una oportunidad para **diferenciación técnica** en el TFM.

## Próximos Pasos

1. ✅ **Completado**: Integración básica AEMET + REE
2. 🚧 **En desarrollo**: Sistema híbrido observación/predicción
3. 📋 **Planificado**: OpenWeatherMap integration
4. 📋 **Planificado**: Modelos MLflow con features híbridos

---

**Nota técnica**: Este análisis se basa en datos reales capturados el 27/06/2025 durante condiciones de ola de calor extrema en Andalucía, proporcionando un caso de estudio ideal para validar la robustez del sistema en condiciones adversas.