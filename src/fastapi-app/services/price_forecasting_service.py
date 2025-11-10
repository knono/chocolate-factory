"""
Price Forecasting Service - Sprint 06
=====================================

Servicio de predicción de precios REE usando Prophet (Facebook).
Genera pronósticos de 168 horas (7 días) con intervalos de confianza.

Funcionalidades:
- Extracción de datos históricos REE desde InfluxDB
- Entrenamiento modelo Prophet con estacionalidad automática
- Predicción 7 días con intervalos de confianza 95%
- Almacenamiento predicciones en InfluxDB
- Backtesting para validación de métricas

Objetivo Sprint 06: MAE < 0.02 €/kWh
"""

import pickle
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from influxdb_client import Point

from .data_ingestion import DataIngestionService
from domain.ml.model_metrics_tracker import ModelMetricsTracker

logger = logging.getLogger(__name__)


class PriceForecastingService:
    """
    Servicio de predicción de precios REE usando Prophet.

    Attributes:
        models_dir: Directorio para almacenar modelos entrenados
        model: Modelo Prophet entrenado (None si no entrenado)
        last_training: Timestamp del último entrenamiento
        metrics: Métricas del modelo actual (MAE, RMSE, R²)
    """

    def __init__(self, models_dir: str = "/app/models/forecasting"):
        """
        Inicializa el servicio de predicción de precios.

        Args:
            models_dir: Ruta donde almacenar modelos Prophet
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.model: Optional[Prophet] = None
        self.last_training: Optional[datetime] = None
        self.metrics: Dict[str, float] = {}

        # Initialize metrics tracker (Sprint 20)
        self.metrics_tracker = ModelMetricsTracker()

        # Configuración Prophet (optimizada para R² = 0.48, balance generalización/complejidad)
        self.prophet_config = {
            # Seasonality configuration (disabled default, use custom Fourier)
            'yearly_seasonality': False,    # Custom Fourier order instead
            'weekly_seasonality': False,    # Custom Fourier order instead
            'daily_seasonality': False,     # Custom Fourier order instead

            # Confidence interval
            'interval_width': 0.95,         # 95% confidence intervals

            # Changepoints: balance entre flexibilidad y generalización
            'changepoint_prior_scale': 0.08,  # Sweet spot
            'n_changepoints': 25,             # Sweet spot

            # Seasonality: balance fino
            'seasonality_prior_scale': 10.0,  # Sweet spot

            # Smoothing
            'seasonality_mode': 'multiplicative',  # Better for price variations
        }

        # Intentar cargar modelo existente
        self._load_latest_model()

    async def extract_ree_historical_data(self, months_back: int = 12) -> pd.DataFrame:
        """
        Extrae datos históricos de precios REE desde InfluxDB.

        Args:
            months_back: Meses de historia a extraer (default: 12 meses)

        Returns:
            DataFrame con columnas: timestamp, price_eur_kwh
        """
        logger.info(f"📊 Extrayendo datos REE: {months_back} meses")

        async with DataIngestionService() as service:
            # Query para extraer precios REE
            query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{months_back}mo)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"])
            '''

            try:
                query_api = service.client.query_api()
                tables = query_api.query(query)

                # Procesar datos
                data = []
                for table in tables:
                    for record in table.records:
                        data.append({
                            'timestamp': record.get_time(),
                            'price_eur_kwh': record.get_value()
                        })

                df = pd.DataFrame(data)

                if df.empty:
                    logger.error("❌ No se encontraron datos REE en InfluxDB")
                    return pd.DataFrame()

                # Eliminar duplicados y ordenar
                df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')

                logger.info(f"✅ Extraídos {len(df)} registros REE ({df['timestamp'].min()} → {df['timestamp'].max()})")
                logger.info(f"📈 Rango precios: {df['price_eur_kwh'].min():.4f} - {df['price_eur_kwh'].max():.4f} €/kWh")

                return df

            except Exception as e:
                logger.error(f"❌ Error extrayendo datos REE: {e}")
                return pd.DataFrame()

    def prepare_prophet_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara datos en formato Prophet (ds, y).

        Args:
            df: DataFrame con columnas timestamp, price_eur_kwh

        Returns:
            DataFrame con columnas: ds (datetime), y (float)
        """
        if df.empty:
            return pd.DataFrame()

        # Formato Prophet: 'ds' (datetime) y 'y' (valor a predecir)
        prophet_df = df[['timestamp', 'price_eur_kwh']].copy()
        prophet_df.columns = ['ds', 'y']

        # Asegurar que ds es datetime sin timezone (Prophet requirement)
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds']).dt.tz_localize(None)

        # Eliminar NaN
        prophet_df = prophet_df.dropna()

        logger.info(f"✅ Datos preparados para Prophet: {len(prophet_df)} registros")

        return prophet_df

    def _add_prophet_features(self, df: pd.DataFrame, include_lags: bool = False) -> pd.DataFrame:
        """
        Agrega features exógenas avanzadas: lags, Fourier, holidays, demanda proxy.

        Args:
            df: DataFrame con columnas ds, y (optional)
            include_lags: Si True, calcula lags (solo para training, no prediction)

        Returns:
            DataFrame con features adicionales
        """
        df = df.copy()

        # Extract temporal features
        df['hour'] = df['ds'].dt.hour
        df['dayofweek'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['day'] = df['ds'].dt.day
        df['quarter'] = df['ds'].dt.quarter

        # === DEMAND PROXIES ===
        # Horas pico de demanda eléctrica española (10-13, 18-21)
        df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)

        # Horas valle (madrugada 0-7)
        df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

        # Horas laborables vs no laborables
        df['is_business_hour'] = (
            (df['dayofweek'] < 5) &  # Lunes-Viernes
            (df['hour'] >= 8) &       # 8:00-20:00
            (df['hour'] <= 20)
        ).astype(int)

        # === HOLIDAYS Y WEEKENDS ===
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

        # Festividades españoles fijas (mes, día)
        holidays_es = [
            (1, 1),    # Año Nuevo
            (1, 6),    # Reyes
            (5, 1),    # Día del Trabajo
            (8, 15),   # Asunción
            (10, 12),  # Hispanidad
            (11, 1),   # Todos los Santos
            (12, 6),   # Constitución
            (12, 25),  # Navidad
        ]

        df['is_holiday'] = df.apply(
            lambda row: 1 if (row['month'], row['day']) in holidays_es else 0,
            axis=1
        )

        # === SEASONALITY PROXIES ===
        # Estaciones (mayor demanda en invierno/verano por calefacción/AC)
        df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
        df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

        # === AUTOREGRESSIVE LAGS (solo para training) ===
        if include_lags and 'y' in df.columns:
            # Lags importantes para precios eléctricos
            df['price_lag_24h'] = df['y'].shift(24)    # Mismo momento día anterior
            df['price_lag_168h'] = df['y'].shift(168)  # Mismo momento semana anterior
            df['price_lag_1h'] = df['y'].shift(1)      # Hora anterior

            # Rolling statistics (última semana)
            df['price_rolling_mean_24h'] = df['y'].shift(1).rolling(window=24, min_periods=1).mean()
            df['price_rolling_std_24h'] = df['y'].shift(1).rolling(window=24, min_periods=1).std()

            # Rellenar NaNs en lags (primeros registros)
            lag_cols = ['price_lag_24h', 'price_lag_168h', 'price_lag_1h',
                       'price_rolling_mean_24h', 'price_rolling_std_24h']
            for col in lag_cols:
                df[col] = df[col].fillna(df['y'].mean())

        return df

    async def train_model(self, months_back: int = 12, test_size: float = 0.2) -> Dict[str, Any]:
        """
        Entrena modelo Prophet con datos históricos REE.

        Args:
            months_back: Meses de historia para entrenar (default: 12)
            test_size: Proporción datos para testing (default: 20%)

        Returns:
            Diccionario con métricas de entrenamiento y validación
        """
        logger.info("🤖 Iniciando entrenamiento modelo Prophet...")

        # 1. Extraer datos históricos
        df_raw = await self.extract_ree_historical_data(months_back=months_back)

        if df_raw.empty:
            return {"success": False, "error": "No hay datos históricos disponibles"}

        # 2. Preparar datos formato Prophet
        df_prophet = self.prepare_prophet_data(df_raw)

        if len(df_prophet) < 100:
            logger.warning(f"⚠️ Datos insuficientes para entrenamiento: {len(df_prophet)} registros")
            return {"success": False, "error": f"Datos insuficientes: {len(df_prophet)} registros (mínimo 100)"}

        # 2b. Agregar features exógenas simples (holidays, demanda proxy, NO lags)
        df_prophet = self._add_prophet_features(df_prophet, include_lags=False)
        logger.info("✅ Features exógenas simples: holidays, peak hours (sin lags para evitar overfitting)")

        # 3. Split train/test (temporal, no aleatorio)
        split_idx = int(len(df_prophet) * (1 - test_size))
        df_train = df_prophet[:split_idx].copy()
        df_test = df_prophet[split_idx:].copy()

        logger.info(f"📊 Split: {len(df_train)} train / {len(df_test)} test")

        try:
            # 4. Configurar y entrenar Prophet con custom seasonality
            self.model = Prophet(**self.prophet_config)

            # Agregar country holidays españoles (mejora estacionalidad)
            self.model.add_country_holidays('ES')

            # === CUSTOM FOURIER SEASONALITY (optimizado para R² = 0.48) ===
            # Daily: orden 8 (sweet spot - generaliza bien)
            self.model.add_seasonality(
                name='daily',
                period=1,
                fourier_order=8,
                prior_scale=12.0
            )

            # Weekly: orden 5 (sweet spot - generaliza bien)
            self.model.add_seasonality(
                name='weekly',
                period=7,
                fourier_order=5,
                prior_scale=10.0
            )

            # Yearly: orden 8 (sweet spot)
            self.model.add_seasonality(
                name='yearly',
                period=365.25,
                fourier_order=8,
                prior_scale=8.0
            )

            # === REGRESSORES EXÓGENOS (optimizados para R² = 0.48) ===
            # Demand proxies (sweet spot)
            self.model.add_regressor('is_peak_hour', prior_scale=0.10)
            self.model.add_regressor('is_valley_hour', prior_scale=0.08)

            # Holidays & weekends
            self.model.add_regressor('is_weekend', prior_scale=0.06)
            self.model.add_regressor('is_holiday', prior_scale=0.08)

            # Seasonality proxies
            self.model.add_regressor('is_winter', prior_scale=0.04)
            self.model.add_regressor('is_summer', prior_scale=0.04)

            # NO lags autoregressivos (causan overfitting temporal)

            # Suprimir output verbose de Prophet
            import logging as prophet_logging
            prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

            self.model.fit(df_train)

            logger.info("✅ Modelo Prophet entrenado exitosamente")

            # 5. Validar con datos de test (backtesting)
            # Seleccionar columnas de regressores (sin lags)
            regressor_cols = [
                'ds', 'is_peak_hour', 'is_valley_hour',
                'is_weekend', 'is_holiday', 'is_winter', 'is_summer'
            ]
            future_test = df_test[regressor_cols].copy()
            forecast_test = self.model.predict(future_test)

            # Calcular métricas
            y_true = df_test['y'].values
            y_pred = forecast_test['yhat'].values

            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            r2 = r2_score(y_true, y_pred)

            # Cobertura intervalo de confianza
            lower = forecast_test['yhat_lower'].values
            upper = forecast_test['yhat_upper'].values
            coverage = np.mean((y_true >= lower) & (y_true <= upper))

            self.metrics = {
                'mae': mae,
                'rmse': rmse,
                'r2': r2,
                'coverage_95': coverage,
                'train_samples': len(df_train),
                'test_samples': len(df_test),
            }

            logger.info(f"📊 Métricas modelo:")
            logger.info(f"   MAE: {mae:.4f} €/kWh (objetivo: <0.02)")
            logger.info(f"   RMSE: {rmse:.4f} €/kWh (objetivo: <0.03)")
            logger.info(f"   R²: {r2:.4f} (objetivo: >0.85)")
            logger.info(f"   Coverage 95%: {coverage:.2%} (objetivo: >90%)")

            # 6. Log metrics to CSV tracker (Sprint 20)
            training_duration = (datetime.now() - datetime.now()).total_seconds()  # Placeholder
            self.metrics_tracker.log_metrics(
                model_name="prophet_price_forecast",
                metrics={
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2),
                    "samples": len(df_train),
                    "duration_seconds": training_duration
                },
                notes="scheduled_retrain" if hasattr(self, '_scheduled_run') else "manual_train"
            )

            # 7. Guardar modelo
            self.last_training = datetime.now()
            self._save_model()

            # 7. Resultado (convertir numpy types a Python nativos)
            result = {
                "success": True,
                "metrics": {
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2),
                    "coverage_95": float(coverage),
                    "train_samples": int(len(df_train)),
                    "test_samples": int(len(df_test)),
                },
                "last_training": self.last_training.isoformat(),
                "model_file": str(self.models_dir / "prophet_latest.pkl"),
                "meets_objectives": {
                    "mae_ok": bool(mae < 0.02),
                    "rmse_ok": bool(rmse < 0.03),
                    "r2_ok": bool(r2 > 0.85),
                    "coverage_ok": bool(coverage > 0.90),
                }
            }

            return result

        except Exception as e:
            logger.error(f"❌ Error entrenando modelo: {e}")
            return {"success": False, "error": str(e)}

    async def _get_historical_prices_for_lags(self, reference_date: datetime) -> pd.Series:
        """
        Obtiene precios históricos desde InfluxDB para calcular lags en predicción.

        Args:
            reference_date: Fecha de referencia (ahora)

        Returns:
            Series con precios históricos indexados por timestamp
        """
        async with DataIngestionService() as service:
            # Extraer última semana de datos reales (necesario para lags)
            query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -200h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"])
            '''

            try:
                query_api = service.client.query_api()
                tables = query_api.query(query)

                data = []
                for table in tables:
                    for record in table.records:
                        data.append({
                            'timestamp': record.get_time(),
                            'price': record.get_value()
                        })

                df = pd.DataFrame(data)
                if df.empty:
                    logger.warning("⚠️ No hay datos históricos para lags, usando media")
                    return pd.Series([0.165], index=[reference_date])  # Fallback

                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
                df = df.set_index('timestamp').sort_index()

                return df['price']

            except Exception as e:
                logger.error(f"❌ Error obteniendo históricos para lags: {e}")
                return pd.Series([0.165], index=[reference_date])

    async def predict_weekly(self, start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Genera predicción de precios para próximas 168 horas (7 días).

        Args:
            start_date: Fecha de inicio para predicciones (default: ahora)

        Returns:
            Lista de diccionarios con: timestamp, predicted_price, confidence_lower, confidence_upper
        """
        if not self.model:
            logger.warning("⚠️ Modelo no entrenado, intentando cargar...")
            if not self._load_latest_model():
                raise ValueError("No hay modelo disponible. Ejecutar train_model() primero.")

        # Si no se especifica fecha, usar ahora
        if start_date is None:
            start_date = datetime.now().replace(minute=0, second=0, microsecond=0)

        logger.info(f"🔮 Generando predicción 168 horas desde {start_date.isoformat()}...")

        try:
            # 1. Crear dataframe de fechas futuras
            future_dates = pd.date_range(
                start=start_date,
                periods=168,
                freq='H'
            )

            future = pd.DataFrame({'ds': future_dates})

            # 2. Agregar features exógenas (sin lags)
            future = self._add_prophet_features(future, include_lags=False)

            logger.info("✅ Features exógenas agregadas (sin lags)")

            # 3. Predecir con modelo Prophet
            forecast = self.model.predict(future)

            # 4. Formatear resultados
            predictions = []
            for _, row in forecast.iterrows():
                predictions.append({
                    'timestamp': row['ds'].isoformat(),
                    'predicted_price': round(row['yhat'], 4),
                    'confidence_lower': round(row['yhat_lower'], 4),
                    'confidence_upper': round(row['yhat_upper'], 4),
                })

            logger.info(f"✅ {len(predictions)} predicciones generadas")
            logger.info(f"📈 Rango predicho: {min(p['predicted_price'] for p in predictions):.4f} - {max(p['predicted_price'] for p in predictions):.4f} €/kWh")

            return predictions

        except Exception as e:
            logger.error(f"❌ Error generando predicciones: {e}")
            raise

    async def predict_hours(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Genera predicción de precios para N horas específicas.

        Args:
            hours: Número de horas a predecir (default: 24)

        Returns:
            Lista de predicciones
        """
        if hours < 1 or hours > 168:
            raise ValueError("hours debe estar entre 1 y 168")

        # Generar predicción completa y tomar primeras N horas
        full_predictions = await self.predict_weekly()
        return full_predictions[:hours]

    async def store_predictions_influxdb(self, predictions: List[Dict[str, Any]]) -> bool:
        """
        Almacena predicciones en InfluxDB.

        Args:
            predictions: Lista de predicciones generadas

        Returns:
            True si almacenamiento exitoso
        """
        logger.info(f"💾 Almacenando {len(predictions)} predicciones en InfluxDB...")

        async with DataIngestionService() as service:
            try:
                points = []
                model_version = self.last_training.strftime("%Y%m%d_%H%M%S") if self.last_training else "unknown"

                for pred in predictions:
                    point = (
                        Point("price_predictions")
                        .tag("model_type", "prophet")
                        .tag("model_version", model_version)
                        .tag("forecast_horizon", "168h")
                        .field("predicted_price", pred['predicted_price'])
                        .field("confidence_lower", pred['confidence_lower'])
                        .field("confidence_upper", pred['confidence_upper'])
                        .time(pred['timestamp'])
                    )
                    points.append(point)

                # Escribir en batch
                write_api = service.client.write_api()
                write_api.write(bucket=service.config.bucket, record=points)

                logger.info(f"✅ Predicciones almacenadas exitosamente")
                return True

            except Exception as e:
                logger.error(f"❌ Error almacenando predicciones: {e}")
                return False

    def get_model_status(self) -> Dict[str, Any]:
        """
        Obtiene estado actual del modelo.

        Returns:
            Diccionario con información del modelo
        """
        return {
            "model_loaded": self.model is not None,
            "last_training": self.last_training.isoformat() if self.last_training else None,
            "metrics": self.metrics,
            "model_file": str(self.models_dir / "prophet_latest.pkl"),
            "prophet_config": self.prophet_config,
        }

    def _save_model(self):
        """Guarda modelo Prophet en disco"""
        try:
            model_path = self.models_dir / "prophet_latest.pkl"

            model_data = {
                'model': self.model,
                'last_training': self.last_training,
                'metrics': self.metrics,
                'config': self.prophet_config,
            }

            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"💾 Modelo guardado: {model_path}")

        except Exception as e:
            logger.error(f"❌ Error guardando modelo: {e}")

    def _load_latest_model(self) -> bool:
        """
        Carga último modelo Prophet entrenado.

        Returns:
            True si carga exitosa
        """
        try:
            model_path = self.models_dir / "prophet_latest.pkl"

            if not model_path.exists():
                logger.info("ℹ️ No hay modelo previo disponible")
                return False

            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.last_training = model_data['last_training']
            self.metrics = model_data.get('metrics', {})

            logger.info(f"✅ Modelo cargado (entrenado: {self.last_training})")
            return True

        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {e}")
            return False


# Factory function
def get_price_forecasting_service() -> PriceForecastingService:
    """Obtiene instancia del servicio de predicción de precios"""
    return PriceForecastingService()
