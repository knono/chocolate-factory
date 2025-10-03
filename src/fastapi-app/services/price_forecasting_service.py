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

        # Configuración Prophet
        self.prophet_config = {
            'yearly_seasonality': True,   # Patrones anuales
            'weekly_seasonality': True,   # Patrones semanales (lun-dom)
            'daily_seasonality': True,    # Patrones diarios (horas)
            'interval_width': 0.95,       # Intervalo confianza 95%
            'changepoint_prior_scale': 0.05,  # Flexibilidad en cambios de tendencia
            'seasonality_prior_scale': 10.0,  # Peso de estacionalidad
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

        # 3. Split train/test (temporal, no aleatorio)
        split_idx = int(len(df_prophet) * (1 - test_size))
        df_train = df_prophet[:split_idx].copy()
        df_test = df_prophet[split_idx:].copy()

        logger.info(f"📊 Split: {len(df_train)} train / {len(df_test)} test")

        try:
            # 4. Configurar y entrenar Prophet
            self.model = Prophet(**self.prophet_config)

            # Suprimir output verbose de Prophet
            import logging as prophet_logging
            prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

            self.model.fit(df_train)

            logger.info("✅ Modelo Prophet entrenado exitosamente")

            # 5. Validar con datos de test (backtesting)
            future_test = df_test[['ds']].copy()
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

            # 6. Guardar modelo
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
            # Crear dataframe de fechas futuras manualmente
            future_dates = pd.date_range(
                start=start_date,
                periods=168,
                freq='H'
            )

            future = pd.DataFrame({'ds': future_dates})

            # Predecir
            forecast = self.model.predict(future)

            # Formatear resultados
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
