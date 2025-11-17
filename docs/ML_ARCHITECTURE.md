# ML Architecture - Chocolate Factory

**Fecha**: 20 de Octubre, 2025 (Actualizado: 28 de Octubre, 2025)
**Versión**: 1.1
**Estado**: ✅ Producción

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Servicios ML Actuales](#servicios-ml-actuales)
4. [Modelos Implementados](#modelos-implementados)
5. [Feature Engineering Pipeline](#feature-engineering-pipeline)
6. [Flujo de Entrenamiento](#flujo-de-entrenamiento)
7. [Flujo de Predicción](#flujo-de-predicción)
8. [Almacenamiento de Modelos](#almacenamiento-de-modelos)
9. [Métricas y Evaluación](#métricas-y-evaluación)
10. [Integración con Dashboard](#integración-con-dashboard)

---

## Resumen Ejecutivo

El sistema ML de Chocolate Factory integra **3 tipos de modelos** para optimización energética y predicción de producción:

1. **Prophet** - Predicción de precios REE (168 horas)
2. **sklearn RandomForest** - Optimización energética (regresión)
3. **sklearn RandomForest** - Recomendación de producción (clasificación)

**Estado Actual**:
- ✅ 3 servicios ML en producción (no unificados)
- ✅ Feature engineering automático
- ✅ Entrenamiento automático: sklearn 30min, Prophet 24h (7 APScheduler jobs total)
- ✅ Predicciones integradas en dashboard
- ✅ ROI tracking: 11,045€/año (valle-prioritized vs baseline, 35.7% ahorro)

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────┤
│  InfluxDB:                                                      │
│  - energy_prices (REE API, 42,578 registros 2022-2025)        │
│  - weather_data (AEMET + OpenWeatherMap, híbrido 24/7)        │
│  - siar_historical (88,935 registros 2000-2025)               │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              FEATURE ENGINEERING LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  DirectMLService.engineer_features():                           │
│  - Basic features: hour, day_of_week                            │
│  - Weather features: temperature, humidity                      │
│  - Target generation (supervised learning):                     │
│    * energy_optimization_score (0-100)                          │
│    * production_class (Optimal/Moderate/Reduced/Halt)           │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ML MODELS (3 tipos)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   PROPHET    │  │  SKLEARN RF  │  │  SKLEARN RF  │         │
│  │              │  │              │  │              │         │
│  │ Predicción   │  │ Optimización │  │ Clasificación│         │
│  │ Precios REE  │  │  Energética  │  │  Producción  │         │
│  │              │  │              │  │              │         │
│  │ 168h ahead   │  │ Score 0-100  │  │ 4 clases     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PREDICTION SERVICES                            │
├─────────────────────────────────────────────────────────────────┤
│  - PriceForecastingService (Prophet)                            │
│  - DirectMLService (sklearn energy + production)                │
│  - PredictiveInsightsService (insights layer)                   │
│  - HourlyOptimizerService (optimization layer)                  │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD & API                              │
├─────────────────────────────────────────────────────────────────┤
│  - /dashboard/complete (JSON data)                              │
│  - /insights/* (4 endpoints)                                    │
│  - /optimize/production/daily (hourly timeline)                 │
│  - /predict/prices/weekly (Prophet forecast)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Servicios ML Actuales

### 1. `direct_ml.py` - Sklearn Models (PRINCIPAL)

**Ubicación**: `src/fastapi-app/services/direct_ml.py`
**Estado**: ✅ **EN USO - PRODUCCIÓN**
**Responsabilidad**: Modelos sklearn para optimización y clasificación

**Modelos**:
- `energy_model`: RandomForestRegressor (score 0-100)
- `production_model`: RandomForestClassifier (4 clases)

**Features**:
- Feature engineering con targets supervisados
- Entrenamiento automático cada 30 min
- Versionado de modelos con timestamp
- Métricas: R², MAE, RMSE, accuracy

**Endpoints asociados**:
- `/models/train` (entrenamiento manual)
- `/models/status-direct` (estado + métricas)
- `/predict/energy-optimization` (predicción score 0-100)
- `/predict/production-recommendation` (predicción clase)

**UPDATE OCT 28**: CRITICAL BUG FIX
- Métodos predicción usaban 3 features, modelo entrenado con 5
- FIXED: `predict_energy_optimization()` y `predict_production_recommendation()` ahora usan 5 features
- Agregado temperature y humidity a ambos métodos (línea 915-923, 970-978)
- **Impacto**: Endpoints `/predict/*` ahora funciona correctamente. BUG CRÍTICO RESUELTO.

---

### 2. `enhanced_ml_service.py` - Advanced Features (LEGACY)

**Ubicación**: `src/fastapi-app/services/enhanced_ml_service.py`
**Estado**: ⚠️ **NO USADO - LEGACY**
**Responsabilidad**: Features avanzadas (no integradas)

**Características**:
- Advanced feature engineering (13+ features)
- Temporal patterns, seasonality
- External factor integration

**Estado**: Código legacy, NO se usa en producción actual. **NO borrar** por si se necesita en futuro (código de referencia).

---

### 3. `ml_models.py` - Old Implementation (LEGACY)

**Ubicación**: `src/fastapi-app/services/ml_models.py`
**Estado**: ⚠️ **NO USADO - LEGACY**
**Responsabilidad**: Implementación antigua de modelos

**Estado**: Código legacy, reemplazado por `direct_ml.py`. **NO borrar** por compatibilidad histórica.

---

### 4. `price_forecasting_service.py` - Prophet Models (PRODUCCIÓN)

**Ubicación**: `src/fastapi-app/services/price_forecasting_service.py`
**Estado**: ✅ **EN USO - PRODUCCIÓN**
**Responsabilidad**: Predicción precios REE con Prophet

**Modelo**:
- Prophet (Facebook/Meta)
- 168h forecast (7 días)
- Intervalos confianza 95%

**Métricas**:
- MAE: 0.033 €/kWh
- RMSE: 0.042 €/kWh
- R²: 0.49
- Coverage: 88.3%

**Endpoints asociados**:
- `/predict/prices/weekly` (7 días completos)
- `/predict/prices/hourly?hours=N` (1-168h configurable)
- `/predict/prices/train` (entrenamiento manual)
- `/predict/prices/status` (métricas)

**UPDATE OCT 28**: Agregadas variables exógenas (holidays españoles, demanda proxy)
- Nuevo método `_add_prophet_features()`: is_peak_hour, is_weekend, is_holiday
- Integrado `add_country_holidays('ES')`
- Regressores: is_peak_hour (prior 0.1), is_weekend (prior 0.05), is_holiday (prior 0.1)
- **Impacto esperado**: R² 0.49 → 0.55-0.65, MAE 0.033 → 0.027-0.030

---

## Modelos Implementados

### Prophet - Predicción de Precios REE

**Tipo**: Time series forecasting
**Framework**: Prophet 1.1.7
**Objetivo**: Predecir precios electricidad española (PVPC)

**Arquitectura**:
```python
# Model configuration
model = Prophet(
    seasonality_mode='multiplicative',
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=True
)
```

**Input**:
- Datos históricos REE (42,578 registros)
- Timestamp + precio €/kWh

**Output**:
- 168 predicciones horarias (7 días)
- Intervalos confianza (yhat_lower, yhat_upper)
- Timestamp ISO format

**Entrenamiento**:
- Automático: APScheduler job cada 24h
- Manual: POST `/predict/prices/train`

**Storage**: `/app/models/price_forecast_prophet_YYYYMMDD_HHMMSS.pkl`

---

### RandomForest Regressor - Energy Optimization

**Tipo**: Supervised regression
**Framework**: sklearn RandomForestRegressor
**Objetivo**: Score optimización energética (0-100)

**Arquitectura**:
```python
RandomForestRegressor(
    n_estimators=50,
    random_state=42
)
```

**Features** (10):
- Base (5): price_eur_kwh, hour, day_of_week, temperature, humidity
- Machinery (5): machine_power_kw, machine_thermal_efficiency, machine_humidity_efficiency, estimated_cost_eur, tariff_multiplier

**Target**: `energy_optimization_score` (physics-based)

**Output**: Score 0-100 (mayor = mejor momento para producir)

**Métricas (Nov 12, 2025)**:
- R² test: **0.983** (train: 0.996, diff: 0.013)
- Cross-validation 5-fold: 0.982 ± 0.003
- Training samples: 497
- Test samples: 125
- Overfitting: NO (diff < 0.10 threshold)

**Entrenamiento**:
- Automático: Cada 30 minutos
- Manual: POST `/predict/train`

**Storage**: `/app/models/energy_optimization_YYYYMMDD_HHMMSS.pkl`

---

### RandomForest Classifier - Production Recommendation

**Tipo**: Supervised classification (4 clases)
**Framework**: sklearn RandomForestClassifier
**Objetivo**: Recomendar nivel de producción

**Arquitectura**:
```python
RandomForestClassifier(
    n_estimators=50,
    random_state=42
)
```

**Features**: Same 10 features as energy model (5 base + 5 machinery-specific)

**Target**: `production_class` (physics-based suitability score)

**Classes** (4):
1. **Optimal**: suitability ≥ 75 (alta eficiencia térmica/humedad + bajo precio)
2. **Moderate**: 55 ≤ suitability < 75 (condiciones aceptables)
3. **Reduced**: 35 ≤ suitability < 55 (baja eficiencia o alto precio)
4. **Halt**: suitability < 35 (condiciones adversas)

**Output**: Clase + probabilidades

**Métricas (Nov 12, 2025)**:
- Accuracy test: **0.928** (train: 0.998, diff: 0.070)
- Cross-validation 5-fold: 0.947 ± 0.026
- Training samples: 497
- Test samples: 125
- Classes: 4 (Optimal, Moderate, Reduced, Halt)
- Overfitting: NO (diff < 0.15 threshold)

**Entrenamiento**:
- Automático: Cada 30 minutos (junto con energy model)
- Manual: POST `/predict/train`

**Storage**: `/app/models/production_classifier_YYYYMMDD_HHMMSS.pkl`

---

## Feature Engineering Pipeline

**Ubicación**: `DirectMLService.engineer_features()` (`domain/ml/direct_ml.py:401-501`)

### Feature Set (10 features total)

#### Base Features (5)
```python
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
df['temperature']  # From weather data (AEMET/OpenWeatherMap)
df['humidity']     # From weather data
df['price_eur_kwh'] # From REE API
```

#### Machinery-Specific Features (5)
**Source**: `domain/machinery/specs.py` - Real equipment specifications

```python
# Determine active process by hour (heuristic)
df['active_process'] = determine_active_process(hour)
# Returns: Conchado (0-6h), Refinado (6-10h), Templado (10-14h), Mezclado (14-24h)

# Machine specifications
df['machine_power_kw']        # 30-48 kW depending on process
df['machine_thermal_efficiency'] = max(0, 100 - |temp - optimal_temp| × 5)
df['machine_humidity_efficiency'] = max(0, 100 - |humidity - optimal_humidity| × 2)
df['estimated_cost_eur'] = (power_kw × duration_hours) × price_eur_kwh
df['tariff_multiplier']       # P1=1.3, P2=1.0, P3=0.8
```

**Process Specifications**:
| Process | Power | Duration | Optimal Temp | Optimal Humidity |
|---------|-------|----------|--------------|------------------|
| Conchado | 48 kW | 5h | 40-50°C | 50% |
| Refinado | 42 kW | 4h | 30-40°C | 55% |
| Templado | 36 kW | 2h | 28-32°C | 60% |
| Mezclado | 30 kW | 1h | 20-30°C | 50% |

---

### Target Calculation (Physics-Based)

#### Energy Optimization Score (0-100)
**Formula**:
```python
score = (100 - price_normalized) × 0.4 +          # 40% price weight
        machine_thermal_efficiency × 0.35 +       # 35% thermal efficiency
        machine_humidity_efficiency × 0.15 +      # 15% humidity efficiency
        ((tariff_multiplier - 1) × -50 + 50) × 0.1 # 10% tariff weight
```

**Key improvement**: Replaced synthetic noise with real thermal/humidity efficiency from machinery specs.

---

#### Production Recommendation (Optimal/Moderate/Reduced/Halt)
**Formula**:
```python
suitability = machine_thermal_efficiency × 0.45 +  # 45% thermal
              machine_humidity_efficiency × 0.25 +  # 25% humidity
              (100 - price_normalized) × 0.30      # 30% price

# Tariff adjustment for valle periods
if tariff_period == 'P3_Valle':
    suitability *= tariff_multiplier

# Classification
if suitability >= 75: class = "Optimal"
elif suitability >= 55: class = "Moderate"
elif suitability >= 35: class = "Reduced"
else: class = "Halt"
```

**Key improvement**: Classification based on real machine efficiency instead of arbitrary thresholds.

---

### Validation

| Aspect | Status | Details |
|--------|--------|---------|
| Based on real data | ✅ | REE prices, weather, machinery specs |
| Physics-based | ✅ | Thermal/humidity efficiency from equipment |
| Reproducible | ✅ | No random noise, deterministic calculations |
| Business-validated | ✅ | Specifications from `.claude/rules/machinery_specs.md` |

---

## Flujo de Entrenamiento

### Entrenamiento Automático (APScheduler)

**Frecuencia**:
- Prophet: Cada 24 horas (entrenamiento diario)
- sklearn models: Cada 30 minutos

**Trigger**: `tasks/scheduler_config.py`

```python
scheduler.add_job(
    train_ml_models_job,
    'interval',
    minutes=30,
    id='train_ml_models'
)
```

---

### Flujo de Entrenamiento sklearn

```
1. Extract data from InfluxDB
   └─> use_all_data=True (todos los datos disponibles)

2. Feature Engineering
   └─> engineer_features(df)
       ├─> Basic: hour, day_of_week
       ├─> Weather: temperature, humidity (si disponibles)
       └─> Targets: energy_score, production_class

3. Prepare features
   └─> feature_columns = [price, hour, day_of_week, temp?, hum?]
   └─> Clean NaNs: dropna + fillna(mean)

4. Train Energy Model (Regressor)
   ├─> Split 80/20 train/test
   ├─> RandomForestRegressor(n_estimators=50)
   ├─> Fit on X_train, y_energy
   ├─> Evaluate R² on X_test
   └─> Save model with timestamp

5. Train Production Model (Classifier)
   ├─> Filter rows with production_class
   ├─> Split 80/20 stratified
   ├─> RandomForestClassifier(n_estimators=50)
   ├─> Fit on X_train, y_production
   ├─> Evaluate accuracy on X_test
   └─> Save model with timestamp

6. Update registry
   └─> /app/models/model_registry.json
```

**Mínimo samples**: 10 registros (por modelo)

---

### Flujo de Entrenamiento Prophet

```
1. Extract historical REE prices
   └─> Query InfluxDB: last 30 days minimum

2. Prepare DataFrame
   └─> Columns: ds (timestamp), y (price)

3. Train Prophet model
   ├─> seasonality_mode='multiplicative'
   ├─> yearly, weekly, daily seasonality
   └─> fit(df)

4. Evaluate on test set
   ├─> Split last 20% as test
   ├─> Predict on test dates
   └─> Calculate MAE, RMSE, R², coverage

5. Save model
   └─> /app/models/price_forecast_prophet_YYYYMMDD_HHMMSS.pkl

6. Update metrics
   └─> Store in model_registry.json
```

---

## Flujo de Predicción

### Predicción en Tiempo Real

**Endpoints**:
- `POST /predict/energy-optimization` (sklearn energy)
- `POST /predict/production-recommendation` (sklearn production)
- `GET /predict/prices/weekly` (Prophet)

---

### Ejemplo: Energy Optimization

**Request**:
```json
POST /predict/energy-optimization
{
  "price_eur_kwh": 0.15,
  "temperature": 22,
  "humidity": 55
}
```

**Process**:
```
1. Load latest energy model
   └─> /app/models/latest/energy_optimization.pkl

2. Engineer features
   ├─> hour = current_hour
   ├─> day_of_week = current_day
   └─> [price, hour, day_of_week, temp, hum]

3. Predict
   └─> score = model.predict(features)

4. Return
   └─> {"energy_optimization_score": 78.5}
```

---

### Ejemplo: Prophet Price Forecast

**Request**:
```json
GET /predict/prices/weekly
```

**Process**:
```
1. Load latest Prophet model
   └─> /app/models/latest/price_forecast_prophet.pkl

2. Create future dataframe
   └─> 168 hourly timestamps (7 days)

3. Predict
   └─> forecast = model.predict(future)

4. Extract results
   ├─> predicted_price (yhat)
   ├─> confidence_lower (yhat_lower)
   └─> confidence_upper (yhat_upper)

5. Return JSON array
   └─> [{hour, price, lower, upper}, ...]
```

---

## Almacenamiento de Modelos

### Estructura de Directorios

```
/app/models/
├── latest/                                    # Symlinks a modelos activos
│   ├── energy_optimization.pkl               → ../energy_optimization_20251020_143022.pkl
│   ├── production_classifier.pkl             → ../production_classifier_20251020_143022.pkl
│   └── price_forecast_prophet.pkl            → ../price_forecast_prophet_20251019_183045.pkl
│
├── energy_optimization_20251020_143022.pkl   # Versionado con timestamp
├── energy_optimization_20251019_120015.pkl   # Versión anterior
├── production_classifier_20251020_143022.pkl
├── production_classifier_20251019_120015.pkl
├── price_forecast_prophet_20251019_183045.pkl
├── price_forecast_prophet_20251018_150032.pkl
│
└── model_registry.json                        # Metadatos de todos los modelos
```

---

### model_registry.json

**Ejemplo**:
```json
{
  "energy_optimization": {
    "latest": {
      "timestamp": "20251020_143022",
      "path": "/app/models/energy_optimization_20251020_143022.pkl",
      "metrics": {
        "r2_score": 0.8923,
        "training_samples": 1024,
        "test_samples": 256
      },
      "created_at": "2025-10-20T14:30:22Z"
    },
    "versions": [
      {
        "timestamp": "20251020_143022",
        "metrics": {"r2_score": 0.8923}
      },
      {
        "timestamp": "20251019_120015",
        "metrics": {"r2_score": 0.8756}
      }
    ]
  },
  "production_classifier": {
    "latest": {
      "timestamp": "20251020_143022",
      "path": "/app/models/production_classifier_20251020_143022.pkl",
      "metrics": {
        "accuracy": 0.9234,
        "training_samples": 1024,
        "test_samples": 256,
        "classes": ["Optimal", "Moderate", "Reduced", "Halt"]
      },
      "created_at": "2025-10-20T14:30:22Z"
    }
  },
  "price_forecast_prophet": {
    "latest": {
      "timestamp": "20251019_183045",
      "path": "/app/models/price_forecast_prophet_20251019_183045.pkl",
      "metrics": {
        "mae": 0.033,
        "rmse": 0.042,
        "r2": 0.49,
        "coverage": 0.883
      },
      "created_at": "2025-10-19T18:30:45Z"
    }
  }
}
```

---

## Métricas y Evaluación

### Prophet Price Forecasting

| Métrica | Valor Actual | Objetivo | Estado |
|---------|-------------|----------|--------|
| MAE | 0.033 €/kWh | < 0.05 | ✅ |
| RMSE | 0.042 €/kWh | < 0.06 | ✅ |
| R² | 0.49 | > 0.40 | ✅ |
| Coverage 95% | 88.3% | > 85% | ✅ |

#### Experimentos de Optimización Prophet (Nov 12, 2025)

Se probaron **3 variantes** para mejorar baseline (R² 0.4932). Todos empeoraron rendimiento:

**1. Clima Real (temperature/humidity)**
- **Objetivo**: Usar valores reales clima vs categóricos (is_winter/summer)
- **Features**: temperature (°C), humidity (%)
- **Estrategia**: Hybrid (OpenWeather horaria + SIAR broadcast)
- **Resultado**: R² 0.4906 (-0.0026, -0.26%)
- **Causa**: Coverage limitado (5%), correlación débil clima-precios
- **Script**: `test_prophet_climate_ab.py`

**2. Tariff Periods Explícitos (P1/P2/P3)**
- **Objetivo**: Usar estructura tarifaria oficial (RD 148/2021) vs is_peak/valley
- **Features**: is_P1_punta, is_P2_llano, is_P3_valle
- **Resultado**: R² 0.3222 (-0.1711, -17.11%)
- **Causa**: Overfitting estructura regulatoria, multicolinealidad categórica
- **Script**: `test_prophet_tariff_periods.py`

**3. Changepoints + Volatility**
- **Objetivo**: Mayor flexibilidad (changepoint_prior_scale 0.12) + volatilidad
- **Features**: + price_volatility_7d, is_high_volatility
- **Resultado**: R² 0.3141 (-0.1791, -17.91%)
- **Causa**: Overfitting, volatilidad ya capturada por Fourier
- **Script**: `test_prophet_changepoints.py`

**Conclusión**: Baseline actual óptimo. Features simples (is_peak_hour, is_valley_hour, is_winter, is_summer) generalizan mejor que features elaboradas. Complejidad adicional causa overfitting.

**Principio validado**: "Less is more" en ML para series temporales volátiles.

---

### sklearn Energy Optimization (Nov 12, 2025)

| Métrica | Valor Actual | Objetivo | Estado |
|---------|-------------|----------|--------|
| R² test | **0.983** | > 0.80 | ✅ |
| R² train | 0.996 | - | ✅ |
| R² diff | 0.013 | < 0.10 | ✅ No overfitting |
| CV 5-fold | 0.982 ± 0.003 | Stable | ✅ |
| Training samples | 497 | > 100 | ✅ |
| Test samples | 125 | > 20 | ✅ |
| Features | 10 (5 base + 5 machinery) | - | ✅ |

**Validation**: `scripts/validate_sklearn_overfitting.py`

---

### sklearn Production Classifier (Nov 12, 2025)

| Métrica | Valor Actual | Objetivo | Estado |
|---------|-------------|----------|--------|
| Accuracy test | **0.928** | > 0.80 | ✅ |
| Accuracy train | 0.998 | - | ✅ |
| Accuracy diff | 0.070 | < 0.15 | ✅ No overfitting |
| CV 5-fold | 0.947 ± 0.026 | Stable | ✅ |
| Training samples | 497 | > 100 | ✅ |
| Test samples | 125 | > 20 | ✅ |
| Classes | 4 (Optimal/Moderate/Reduced/Halt) | 4 | ✅ |

**Validation**: `scripts/validate_sklearn_overfitting.py`

---

### Scripts de Validación

**Prophet Walk-Forward Validation**:
```bash
docker exec chocolate_factory_brain python /app/scripts/validate_prophet_walkforward.py
```
- Train: Data hasta Oct 31, 2025
- Test: Nov 1-10, 2025 (unseen data)
- Output: MAE, RMSE, R², Coverage 95%
- Location: `scripts/validate_prophet_walkforward.py`

**sklearn Overfitting Detection**:
```bash
docker exec chocolate_factory_brain python /app/scripts/validate_sklearn_overfitting.py
```
- Train/test split: 80/20
- Cross-validation: 5-fold KFold
- Metrics: R² train vs test, CV mean ± std
- Overfitting thresholds: R² diff > 0.10, Acc diff > 0.15
- Location: `scripts/validate_sklearn_overfitting.py`
- Code: `domain/ml/direct_ml.py:824-912` (energy), `931-1012` (production)

---

## Integración con Dashboard

### Endpoints ML en Dashboard

**Dashboard completo**:
```
GET /dashboard/complete
```

**Incluye**:
- Prophet predictions (next 7 days)
- Energy optimization score (current)
- Production recommendation (current)
- SIAR historical context
- Hourly optimization plan (24h)

---

### Insights Dashboard (Sprint 09)

**Endpoints**:
```
GET /insights/optimal-windows       # 7 días ventanas óptimas (Prophet)
GET /insights/ree-deviation         # REE D-1 vs Real (accuracy 87.5%)
GET /insights/predictive-alerts     # Alertas (picos, clima extremo)
GET /insights/savings-tracking      # ROI tracking (11,045€/año valle-prioritized)
```

**Trazabilidad ROI**:
```
Frontend Dashboard
  ↓
GET /insights/savings-tracking (routers/insights.py)
  ↓
PredictiveInsightsService.get_savings_tracking()
  ↓
Cálculos:
  - Diario: 30.26€ ahorro/día
  - Mensual: 908€/mes
  - Anual: 11,045€/año
```

---

### Hourly Optimization (Sprint 08)

**Endpoint**:
```
POST /optimize/production/daily
```

**Incluye**:
- Plan optimizado 24h (qué producir, cuándo)
- Timeline horaria (precio Prophet/hora + periodo tarifario P1/P2/P3)
- Ahorro estimado vs baseline (85.33% savings)
- Batches recomendados por proceso

---

## Testing

### Tests Implementados (Sprint 12)

**Total**: 66 tests (100% pasando)

**ML Tests**:
```
tests/ml/
├── test_prophet_model.py              # 6 tests Prophet
│   ├── test_prophet_model_training
│   ├── test_prophet_7day_prediction
│   ├── test_prophet_confidence_intervals
│   ├── test_prophet_mae_threshold
│   ├── test_prophet_handles_missing_data
│   └── test_prophet_serialization
│
└── test_sklearn_models.py             # 6 tests sklearn
    ├── test_energy_optimization_model_training
    ├── test_production_recommendation_classifier
    ├── test_feature_engineering_13_features
    ├── test_model_accuracy_threshold
    ├── test_model_persistence_pickle
    └── test_model_trainer_validation_metrics
```

**Coverage**: 19% (baseline establecido Sprint 12)

**CI/CD**: Tests se ejecutan automáticamente en Forgejo Actions (`.gitea/workflows/ci-cd-dual.yml`)

---

## Roadmap Futuro

### Sprint 10 - Consolidación (Opcional)

**Pendiente**:
- [ ] Unificar 3 servicios ML → 1 servicio (bajo demanda)
- [ ] Aumentar coverage a 25-30%
- [ ] Backtesting Prophet con datos históricos

**No pendiente** (ya cubierto):
- ✅ Tests automatizados (Sprint 12)
- ✅ CI/CD configurado (Sprint 12)
- ✅ ROI tracking (Sprint 09)
- ✅ Feature engineering documentado (este documento)

---

### Mejoras Potenciales

1. **Modelos avanzados**:
   - LSTM para precios REE
   - XGBoost para optimización
   - Ensemble models

2. **Features adicionales**:
   - Días festivos
   - Eventos especiales
   - Precios combustibles

3. **Online learning**:
   - Actualización incremental de modelos
   - Detección de drift

4. **Explicabilidad**:
   - SHAP values
   - Feature importance visualization

---

## ⚠️ Limitaciones y Disclaimers

### Limitaciones de ML

**Energy Scoring (sklearn)**:
- ❌ **No es ML predictivo**: Usa reglas de negocio determinísticas
- ❌ **Métricas circulares**: R² alto porque predice su propia fórmula
- ✅ **Útil para**: Scoring en tiempo real basado en reglas validadas
- ⚠️ **No usar para**: Predicciones futuras, forecasting, o análisis de tendencias

**Prophet Price Forecasting**:
- ✅ **ML real**: Modelo entrenado con datos históricos
- ⚠️ **R² = 0.49**: Solo explica 49% de la varianza (51% sin explicar)
- ⚠️ **MAE = 0.033 €/kWh**: Error promedio ~3.3 céntimos por predicción
- ⚠️ **Métricas estáticas**: Última medición 24-Oct-2025, no se actualizan dinámicamente
- ❌ **Sin drift detection**: No hay monitoreo de degradación del modelo
- ❌ **Sin A/B testing**: No hay validación de mejoras en producción

### Limitaciones de Testing

**Cobertura de Tests**:
- ⚠️ **32% coverage** (Sprint 17): 68% del código sin testear
- ✅ **134 tests**: 123 passing, 11 E2E failing (performance/resilience)
- ❌ **Recomendado**: 40%+ coverage para producción con confianza
- ⚠️ **Áreas sin cobertura**: Error handling, edge cases, failure scenarios

### Limitaciones de Seguridad

**Modelo de Seguridad**:
- ✅ **Network-level**: Tailscale VPN zero-trust mesh (WireGuard encrypted)
- ❌ **Application-level**: Sin autenticación/autorización en API endpoints
- ❌ **Rate limiting**: Global per-endpoint, no per-user
- ⚠️ **Modelo de despliegue**: Solo para infraestructura privada con seguridad a nivel de red
- ❌ **No exponer**: A internet público sin autenticación adicional

**Control de Acceso**:
- ✅ Localhost: Acceso completo (desarrollo)
- ✅ Tailscale network: Acceso completo (solo dispositivos autorizados)
- ❌ Internet público: Sin acceso (no expuesto)

### Limitaciones de Observabilidad

**Monitoreo**:
- ✅ **Health checks**: Disponibilidad de servicios
- ❌ **Performance monitoring**: No implementado
- ❌ **Alerting**: No hay sistema de alertas (Discord/Telegram/email)
- ❌ **Logs centralizados**: Logs recolectados pero no analizados
- ⚠️ **Adecuado para**: Desarrollo, demos, despliegues privados pequeños

**Métricas ROI**:
- ⚠️ **11,045€/año**: Estimación valle-prioritized (35.7% ahorro vs baseline), **NO medición real**
- ✅ **Data volumes**: Verificables desde InfluxDB (42k REE, 88k SIAR - Oct 2025)
- ❌ **Ahorro real**: No medido en producción real

### Recomendaciones para Producción

**Para uso en producción real se requiere**:
1. ✅ Aumentar test coverage a 40%+
2. ✅ Implementar autenticación/autorización en API
3. ✅ Añadir drift detection en modelos ML
4. ✅ Implementar sistema de alertas
5. ✅ Centralizar y analizar logs
6. ✅ Añadir performance monitoring
7. ✅ Validar ROI con datos reales de producción

---

## Referencias

- **Sprint 06**: Prophet Price Forecasting (`.claude/sprints/ml-evolution/SPRINT_06_PRICE_FORECASTING.md`)
- **Sprint 07**: SIAR Historical Analysis (`.claude/sprints/ml-evolution/SPRINT_07_SIAR_TIMESERIES.md`)
- **Sprint 08**: Hourly Optimization (`.claude/sprints/ml-evolution/SPRINT_08_HOURLY_OPTIMIZATION.md`)
- **Sprint 09**: Predictive Dashboard (`.claude/sprints/ml-evolution/SPRINT_09_PREDICTIVE_DASHBOARD.md`)
- **Sprint 12**: Testing Suite (`.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`)
- **Sprint 16**: Documentation Integrity (`.claude/sprints/infrastructure/SPRINT_16_INTEGRITY_TRANSPARENCY.md`)

---

**Última actualización**: 2025-10-30
**Versión**: 1.1
**Autor**: ML Architecture Documentation - Sprint 10, Updated Sprint 16
