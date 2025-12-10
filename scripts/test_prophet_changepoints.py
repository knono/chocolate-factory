#!/usr/bin/env python3
"""
Prophet Test: Changepoints Flexibles + Volatilidad
===================================================

Compara:
- Baseline: changepoint_prior_scale=0.08 (conservador)
- Improved: changepoint_prior_scale=0.12 + volatility feature (sin lags directos)

Validación walk-forward: Nov 1-10, 2025
"""

import asyncio
import sys
import os
sys.path.insert(0, '/home/nono/Downloads/chocolate-factory/src/fastapi-app')
os.environ.setdefault('INFLUXDB_URL', 'http://localhost:8086')
os.environ.setdefault('INFLUXDB_TOKEN', 'chocolate-factory-influxdb-token')
os.environ.setdefault('INFLUXDB_ORG', 'chocolate-factory')
os.environ.setdefault('INFLUXDB_BUCKET', 'energy_data')

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from prophet import Prophet
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_ree_data(end_date: str) -> pd.DataFrame:
    """Extrae datos REE hasta end_date (exclusive)"""
    from services.data_ingestion import DataIngestionService

    async with DataIngestionService() as service:
        query = f'''
            from(bucket: "{service.config.bucket}")
            |> range(start: -36mo, stop: {end_date})
            |> filter(fn: (r) => r._measurement == "energy_prices")
            |> filter(fn: (r) => r._field == "price_eur_kwh")
            |> sort(columns: ["_time"])
        '''

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
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
        return df.sort_values('timestamp')


def add_features_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Features BASELINE (sin volatilidad)"""
    df = df.copy()
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    holidays_es = [(1,1), (1,6), (5,1), (8,15), (10,12), (11,1), (12,6), (12,25)]
    df['is_holiday'] = df.apply(lambda r: 1 if (r['month'], r['day']) in holidays_es else 0, axis=1)
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

    return df


def add_features_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Features VOLATILITY (con rolling std sin lags directos)

    IMPORTANTE: Calcula volatilidad sobre valores PASADOS sin usar y actual
    para evitar data leakage.
    """
    df = df.copy()
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    holidays_es = [(1,1), (1,6), (5,1), (8,15), (10,12), (11,1), (12,6), (12,25)]
    df['is_holiday'] = df.apply(lambda r: 1 if (r['month'], r['day']) in holidays_es else 0, axis=1)
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

    # Volatility feature (rolling std últimos 7 días, SIN incluir valor actual)
    if 'y' in df.columns:
        # Training: usar y (precio real)
        df['price_volatility_7d'] = df['y'].shift(1).rolling(window=168, min_periods=24).std()
        df['price_volatility_7d'] = df['price_volatility_7d'].fillna(df['price_volatility_7d'].mean())
    else:
        # Prediction: sin y disponible, usar valor constante (media histórica)
        # Esto es una limitación: en producción usaríamos volatilidad calculada desde InfluxDB
        df['price_volatility_7d'] = 0.05  # Valor medio típico (~5 cent/kWh std)

    # Binary: alta volatilidad (>threshold)
    volatility_threshold = 0.06  # 6 cent/kWh std
    df['is_high_volatility'] = (df['price_volatility_7d'] > volatility_threshold).astype(int)

    return df


def train_baseline(df_train: pd.DataFrame) -> Prophet:
    """Entrena modelo BASELINE (changepoint_prior_scale=0.08)"""
    logger.info("🔥 Training BASELINE (changepoint_prior_scale=0.08)...")

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.08,  # Conservador
        n_changepoints=25,
        seasonality_prior_scale=10.0,
        seasonality_mode='multiplicative'
    )

    model.add_country_holidays('ES')
    model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)

    model.add_regressor('is_peak_hour', prior_scale=0.10)
    model.add_regressor('is_valley_hour', prior_scale=0.08)
    model.add_regressor('is_weekend', prior_scale=0.06)
    model.add_regressor('is_holiday', prior_scale=0.08)
    model.add_regressor('is_winter', prior_scale=0.04)
    model.add_regressor('is_summer', prior_scale=0.04)

    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

    model.fit(df_train)
    logger.info("✅ BASELINE trained")
    return model


def train_changepoints(df_train: pd.DataFrame) -> Prophet:
    """Entrena modelo CHANGEPOINTS (changepoint_prior_scale=0.12 + volatility)"""
    logger.info("🔥 Training CHANGEPOINTS (changepoint_prior_scale=0.12 + volatility)...")

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.12,  # Más flexible (+50% vs baseline)
        n_changepoints=25,
        seasonality_prior_scale=10.0,
        seasonality_mode='multiplicative'
    )

    model.add_country_holidays('ES')
    model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)

    model.add_regressor('is_peak_hour', prior_scale=0.10)
    model.add_regressor('is_valley_hour', prior_scale=0.08)
    model.add_regressor('is_weekend', prior_scale=0.06)
    model.add_regressor('is_holiday', prior_scale=0.08)
    model.add_regressor('is_winter', prior_scale=0.04)
    model.add_regressor('is_summer', prior_scale=0.04)

    # Nuevas features volatilidad
    model.add_regressor('price_volatility_7d', prior_scale=0.05)     # Volatilidad continua
    model.add_regressor('is_high_volatility', prior_scale=0.08)      # Volatilidad binaria

    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

    model.fit(df_train)
    logger.info("✅ CHANGEPOINTS trained")
    return model


def evaluate(model: Prophet, df_test: pd.DataFrame, name: str) -> dict:
    """Evalúa modelo"""
    logger.info(f"📊 Evaluating {name}...")

    forecast = model.predict(df_test)
    y_true = df_test['y'].values
    y_pred = forecast['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    lower = forecast['yhat_lower'].values
    upper = forecast['yhat_upper'].values
    coverage = np.mean((y_true >= lower) & (y_true <= upper))

    logger.info(f"  MAE:     {mae:.4f} €/kWh")
    logger.info(f"  RMSE:    {rmse:.4f} €/kWh")
    logger.info(f"  R²:      {r2:.4f}")
    logger.info(f"  Coverage: {coverage:.2%}")

    return {'name': name, 'mae': mae, 'rmse': rmse, 'r2': r2, 'coverage': coverage}


async def main():
    print("=" * 80)
    print("PROPHET TEST: CHANGEPOINTS FLEXIBLES + VOLATILIDAD")
    print("=" * 80)
    print()

    # 1. Extract data
    print("📊 Extracting REE data...")
    train_cutoff = "2025-11-01T00:00:00Z"
    df_train = await extract_ree_data(train_cutoff)

    val_start = datetime(2025, 11, 1)
    df_val = await extract_ree_data("2025-11-11T00:00:00Z")
    df_val = df_val[df_val['timestamp'] >= val_start]

    print(f"   ✅ Train: {len(df_train)} records")
    print(f"   ✅ Val:   {len(df_val)} records")
    print()

    # 2. Prepare Prophet format
    print("📊 Preparing features...")

    # Baseline
    df_train_base = df_train[['timestamp', 'price']].copy()
    df_train_base.columns = ['ds', 'y']
    df_train_base = add_features_baseline(df_train_base)

    df_val_base = df_val[['timestamp', 'price']].copy()
    df_val_base.columns = ['ds', 'y']
    df_val_base = add_features_baseline(df_val_base)

    # Changepoints + Volatility
    df_train_cp = df_train[['timestamp', 'price']].copy()
    df_train_cp.columns = ['ds', 'y']
    df_train_cp = add_features_volatility(df_train_cp)

    df_val_cp = df_val[['timestamp', 'price']].copy()
    df_val_cp.columns = ['ds', 'y']
    df_val_cp = add_features_volatility(df_val_cp)

    print(f"   ✅ Baseline: changepoint_prior_scale=0.08, no volatility")
    print(f"   ✅ Improved: changepoint_prior_scale=0.12, + price_volatility_7d, + is_high_volatility")
    print()

    # 3. Train models
    print("=" * 80)
    print("TRAINING")
    print("=" * 80)
    print()

    model_base = train_baseline(df_train_base)
    print()

    model_cp = train_changepoints(df_train_cp)
    print()

    # 4. Evaluate
    print("=" * 80)
    print("EVALUATION (Walk-Forward Nov 1-10, 2025)")
    print("=" * 80)
    print()

    metrics_base = evaluate(model_base, df_val_base, "BASELINE")
    print()

    metrics_cp = evaluate(model_cp, df_val_cp, "CHANGEPOINTS+VOLATILITY")
    print()

    # 5. Comparison
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()

    mae_diff = metrics_cp['mae'] - metrics_base['mae']
    rmse_diff = metrics_cp['rmse'] - metrics_base['rmse']
    r2_diff = metrics_cp['r2'] - metrics_base['r2']
    cov_diff = metrics_cp['coverage'] - metrics_base['coverage']

    print(f"{'Metric':<15} | {'Baseline':<15} | {'Changepoints':<15} | {'Diff':<15} | Status")
    print("-" * 85)
    print(f"{'MAE':<15} | {metrics_base['mae']:<15.4f} | {metrics_cp['mae']:<15.4f} | {mae_diff:<+15.4f} | {'✅' if mae_diff < 0 else '❌'}")
    print(f"{'RMSE':<15} | {metrics_base['rmse']:<15.4f} | {metrics_cp['rmse']:<15.4f} | {rmse_diff:<+15.4f} | {'✅' if rmse_diff < 0 else '❌'}")
    print(f"{'R²':<15} | {metrics_base['r2']:<15.4f} | {metrics_cp['r2']:<15.4f} | {r2_diff:<+15.4f} | {'✅' if r2_diff > 0 else '❌'}")
    print(f"{'Coverage 95%':<15} | {metrics_base['coverage']:<15.2%} | {metrics_cp['coverage']:<15.2%} | {cov_diff:<+15.2%} | {'✅' if cov_diff > 0 else '❌'}")
    print()

    # 6. Decision
    print("=" * 80)
    print("DECISION")
    print("=" * 80)
    print()

    if r2_diff > 0.02:
        print(f"✅ CHANGEPOINTS+VOLATILITY SIGNIFICATIVAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Changepoints flexibles + volatilidad mejoran forecasting")
        print(f"   RECOMENDACIÓN: Implementar en producción")
    elif r2_diff > 0:
        print(f"⚠️  CHANGEPOINTS+VOLATILITY LIGERAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Mejora marginal, evaluar trade-off complejidad")
    else:
        print(f"❌ BASELINE MEJOR ({r2_diff:.4f} R²)")
        print(f"   Changepoints flexibles NO mejoran forecasting")
        print(f"   RECOMENDACIÓN: Mantener baseline")

    print()


if __name__ == "__main__":
    asyncio.run(main())
