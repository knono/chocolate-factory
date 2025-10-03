# 🎯 SPRINT 06: Predicción de Precios REE

> **Estado**: 🟡 EN PROGRESO
> **Prioridad**: 🔴 CRÍTICA
> **Fecha Inicio**: 2025-10-03
> **Estimación**: 8-10 horas desarrollo + 2 horas testing

---

## 📋 Resumen Ejecutivo

### Problema Actual
El **heatmap semanal** muestra datos históricos o estáticos, NO predicciones reales. Los 42,578 registros REE (2022-2025) están infrautilizados.

### Solución Sprint 06
Implementar modelo **LSTM o Prophet** para predecir precios REE próximas **168 horas** (7 días) y poblar el heatmap con predicciones reales.

### Impacto Esperado
- ✅ Heatmap pasa de decorativo → **herramienta de planificación real**
- ✅ Planificación semanal basada en datos predictivos
- ✅ ROI medible (ahorro energético cuantificable)

---

## 🎯 Objetivos del Sprint

### Objetivo Principal
Implementar sistema de predicción de precios REE con precisión MAE < 0.02 €/kWh.

### Objetivos Secundarios
1. Integrar predicciones con heatmap dashboard
2. Generar intervalos de confianza (95%)
3. API REST para consumo de predicciones
4. Almacenamiento predicciones en InfluxDB

---

## 📦 Entregables

### Entregable 1: Modelo Predictivo
- [ ] **Archivo**: `src/fastapi-app/services/price_forecasting_service.py`
- [ ] **Modelo**: LSTM (TensorFlow/Keras) o Prophet (Facebook)
- [ ] **Métricas objetivo**:
  - MAE < 0.02 €/kWh
  - RMSE < 0.03 €/kWh
  - R² > 0.85
- [ ] **Horizonte**: 168 horas (7 días)
- [ ] **Actualización**: Cada hora (APScheduler)

### Entregable 2: API Endpoints
- [ ] `GET /predict/prices/weekly` → Predicción 7 días
  - Response: `[{hour, predicted_price, confidence_lower, confidence_upper}]`
- [ ] `GET /predict/prices/hourly?hours=24` → Predicción configurable
- [ ] `GET /models/price-forecast/status` → Estado modelo
- [ ] `POST /models/price-forecast/train` → Reentrenamiento manual

### Entregable 3: Integración Dashboard
- [ ] **Heatmap actualizado** con predicciones reales
- [ ] **Color coding**:
  - 🟢 Verde: < 0.12 €/kWh (ÓPTIMO)
  - 🟡 Amarillo: 0.12-0.20 €/kWh (NORMAL)
  - 🟠 Naranja: 0.20-0.30 €/kWh (ALTO)
  - 🔴 Rojo: > 0.30 €/kWh (MUY ALTO)
- [ ] **Tooltip mejorado**: Precio predicho ± intervalo confianza

### Entregable 4: Almacenamiento InfluxDB
- [ ] **Bucket**: `energy_data` (existente)
- [ ] **Measurement**: `price_predictions`
- [ ] **Fields**: `predicted_price`, `confidence_lower`, `confidence_upper`
- [ ] **Tags**: `model_version`, `forecast_horizon`, `created_at`

### Entregable 5: APScheduler Job
- [ ] **Job**: `update_price_forecasts`
- [ ] **Frecuencia**: Cada hora (cron: `0 * * * *`)
- [ ] **Acción**: Generar predicciones 168h y almacenar en InfluxDB

---

## 🛠️ Implementación Técnica

### Opción A: Prophet (Recomendado para MVP)

**Ventajas**:
- ✅ Manejo automático de estacionalidad
- ✅ Robusto con datos faltantes
- ✅ Intervalos de confianza nativos
- ✅ Menos hiperparámetros

**Desventajas**:
- ❌ Menos flexible que LSTM
- ❌ No captura dependencias complejas

**Código base**:
```python
from prophet import Prophet
import pandas as pd

class PriceForecastingService:
    def __init__(self):
        self.model = None

    async def train_model(self, historical_data: pd.DataFrame):
        """
        Entrenar modelo Prophet con datos históricos REE
        """
        # Formato Prophet: 'ds' (datetime), 'y' (valor)
        df_prophet = historical_data[['timestamp', 'price_eur_kwh']].copy()
        df_prophet.columns = ['ds', 'y']

        # Configurar modelo
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            interval_width=0.95  # 95% intervalo confianza
        )

        # Entrenar
        model.fit(df_prophet)
        self.model = model

        # Guardar modelo
        with open('/app/models/price_forecast_prophet.pkl', 'wb') as f:
            pickle.dump(model, f)

    async def predict_weekly(self) -> List[Dict]:
        """
        Predecir próximas 168 horas
        """
        if not self.model:
            await self.load_model()

        # Generar futuro dataframe
        future = self.model.make_future_dataframe(periods=168, freq='H')

        # Predecir
        forecast = self.model.predict(future)

        # Últimas 168 horas (forecast incluye histórico)
        predictions = forecast.tail(168)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

        return predictions.to_dict('records')
```

---

### Opción B: LSTM (TensorFlow)

**Ventajas**:
- ✅ Captura dependencias temporales complejas
- ✅ Mejor para patrones no lineales
- ✅ Escalable a múltiples features

**Desventajas**:
- ❌ Más complejo de entrenar
- ❌ Requiere más datos y tunning
- ❌ Intervalos de confianza no nativos

**Código base**:
```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

class PriceForecastingServiceLSTM:
    def __init__(self, lookback=168):
        self.lookback = lookback  # 7 días histórico
        self.model = None

    def create_sequences(self, data, lookback):
        """Crear secuencias para LSTM"""
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i:i+lookback])
            y.append(data[i+lookback])
        return np.array(X), np.array(y)

    async def train_model(self, historical_data: pd.DataFrame):
        """Entrenar LSTM"""
        prices = historical_data['price_eur_kwh'].values

        # Normalizar
        scaler = StandardScaler()
        prices_scaled = scaler.fit_transform(prices.reshape(-1, 1))

        # Crear secuencias
        X, y = self.create_sequences(prices_scaled, self.lookback)

        # Split train/test
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Modelo
        model = Sequential([
            LSTM(50, activation='relu', return_sequences=True, input_shape=(self.lookback, 1)),
            Dropout(0.2),
            LSTM(50, activation='relu'),
            Dropout(0.2),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mse', metrics=['mae'])

        # Entrenar
        model.fit(X_train, y_train, epochs=50, batch_size=32,
                  validation_data=(X_test, y_test), verbose=1)

        self.model = model
        model.save('/app/models/price_forecast_lstm.h5')
```

---

## 📊 Métricas de Éxito

### Métricas Técnicas
| Métrica | Objetivo | Crítico |
|---|---|---|
| MAE | < 0.02 €/kWh | < 0.03 €/kWh |
| RMSE | < 0.03 €/kWh | < 0.05 €/kWh |
| R² Score | > 0.85 | > 0.75 |
| Tiempo predicción | < 5 segundos | < 10 segundos |
| Cobertura intervalo 95% | > 90% | > 80% |

### Métricas de Negocio
- **Ahorro energético**: Comparar costos planificando con predicciones vs sin ellas
- **Accuracy decisiones**: % de recomendaciones correctas vs incorrectas
- **Adopción usuario**: % de veces que se sigue recomendación del sistema

---

## 🗂️ Estructura de Archivos

```
src/fastapi-app/services/
├── price_forecasting_service.py    # ✅ NUEVO - Servicio predicción
└── enhanced_ml_service.py           # Modificar para integrar

models/
├── price_forecast_prophet.pkl       # ✅ NUEVO - Modelo Prophet
└── price_forecast_scaler.pkl        # ✅ NUEVO - Scaler (si LSTM)

src/fastapi-app/
└── main.py                          # Añadir endpoints + APScheduler job
```

---

## 🔄 Integración APScheduler

```python
# En main.py
from services.price_forecasting_service import PriceForecastingService

price_forecast_service = PriceForecastingService()

@scheduler.scheduled_job('cron', hour='*', id='update_price_forecasts')
async def update_price_forecasts():
    """
    Actualizar predicciones de precios cada hora
    """
    try:
        logger.info("🔮 Actualizando predicciones de precios...")

        # Generar predicciones
        predictions = await price_forecast_service.predict_weekly()

        # Almacenar en InfluxDB
        async with DataIngestionService() as service:
            for pred in predictions:
                point = (
                    Point("price_predictions")
                    .tag("model_version", "prophet_v1")
                    .tag("forecast_horizon", "168h")
                    .field("predicted_price", pred['yhat'])
                    .field("confidence_lower", pred['yhat_lower'])
                    .field("confidence_upper", pred['yhat_upper'])
                    .time(pred['ds'])
                )
                await service.write_point(point)

        logger.info(f"✅ {len(predictions)} predicciones almacenadas")

    except Exception as e:
        logger.error(f"❌ Error actualizando predicciones: {e}")
```

---

## 🧪 Plan de Testing

### Test 1: Precisión Histórica (Backtesting)
```python
async def test_forecast_accuracy():
    """
    Test de precisión usando últimas 2 semanas como test set
    """
    # 1. Entrenar con datos hasta hace 2 semanas
    # 2. Predecir esas 2 semanas
    # 3. Comparar con datos reales
    # 4. Calcular MAE, RMSE, R²
    assert mae < 0.02, "MAE fuera de objetivo"
```

### Test 2: Intervalos de Confianza
```python
async def test_confidence_intervals():
    """
    Verificar que 95% de valores reales caen en intervalo 95%
    """
    # Generar 100 predicciones con intervalos
    # Comparar con valores reales
    coverage = sum(lower <= real <= upper) / len(predictions)
    assert coverage > 0.90, "Cobertura insuficiente"
```

### Test 3: Performance
```python
async def test_prediction_performance():
    """
    Verificar tiempo de predicción
    """
    start = time.time()
    predictions = await service.predict_weekly()
    duration = time.time() - start
    assert duration < 5.0, "Predicción demasiado lenta"
```

---

## 🐛 Problemas Esperados y Soluciones

### Problema 1: Datos faltantes en series temporales
**Solución**: Prophet maneja automáticamente, LSTM requiere interpolación.

### Problema 2: Overfitting
**Solución**: Cross-validation temporal, regularización, early stopping.

### Problema 3: Cambios de distribución (concept drift)
**Solución**: Reentrenamiento mensual, monitoreo de métricas en producción.

---

## ✅ Checklist de Completitud

### Desarrollo
- [ ] Implementar `PriceForecastingService` (Prophet o LSTM)
- [ ] Crear endpoints API (`/predict/prices/*`)
- [ ] Integrar con APScheduler (job cada hora)
- [ ] Almacenamiento InfluxDB predicciones
- [ ] Actualizar heatmap dashboard con predicciones

### Testing
- [ ] Backtesting con datos históricos (MAE < 0.02)
- [ ] Test intervalos de confianza (coverage > 90%)
- [ ] Test performance (< 5 segundos)
- [ ] Test integración dashboard (visualización correcta)

### Documentación
- [ ] Docstrings en código
- [ ] Actualizar `CLAUDE.md` con nuevos endpoints
- [ ] Actualizar `architecture.md` con servicio predicción
- [ ] Añadir ejemplo uso API en README

### Despliegue
- [ ] Verificar dependencias (`prophet` o `tensorflow` en requirements.txt)
- [ ] Entrenar modelo inicial con datos completos
- [ ] Verificar job APScheduler ejecutándose
- [ ] Monitorear logs primera semana

---

## 📝 Decisiones de Diseño

### Decisión 1: Prophet vs LSTM
**Elegido**: Prophet (MVP rápido, intervalos nativos)
**Razón**: Más simple, robusto, suficiente para Sprint 06. LSTM para Sprint 08 si necesario.

### Decisión 2: Frecuencia actualización
**Elegido**: Cada hora
**Razón**: Balance entre freshness y carga computacional.

### Decisión 3: Horizonte predicción
**Elegido**: 168 horas (7 días)
**Razón**: Alineado con heatmap semanal del dashboard.

---

## 🔗 Dependencias

### Sprint Anterior
- ✅ Sprint 05: Dashboard base funcionando
- ✅ Sprint 04: Datos REE históricos completos

### Sprint Siguiente
- Sprint 07: Integración clima para predicción combinada

---

## 📅 Timeline Estimado

| Fase | Duración | Acumulado |
|---|---|---|
| Setup + investigación Prophet/LSTM | 2h | 2h |
| Implementación servicio predicción | 4h | 6h |
| Integración dashboard + API | 2h | 8h |
| Testing y ajuste hiperparámetros | 2h | 10h |
| Documentación y despliegue | 1h | 11h |

---

**Estado**: 🟡 PENDIENTE
**Próximo paso**: Decidir Prophet vs LSTM e implementar `PriceForecastingService`

**Última actualización**: 2025-10-03
