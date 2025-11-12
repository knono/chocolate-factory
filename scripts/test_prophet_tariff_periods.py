#!/usr/bin/env python3
"""
Prophet Test: Tariff Periods Explícitos
========================================

Compara:
- Baseline: is_peak_hour + is_valley_hour (genérico)
- Improved: is_P1_punta + is_P2_llano + is_P3_valle (tariff oficial RD 148/2021)

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
    """Features BASELINE (actual) - is_peak_hour + is_valley_hour"""
    df = df.copy()
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    # Baseline: peak/valley genérico
    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    holidays_es = [(1,1), (1,6), (5,1), (8,15), (10,12), (11,1), (12,6), (12,25)]
    df['is_holiday'] = df.apply(lambda r: 1 if (r['month'], r['day']) in holidays_es else 0, axis=1)
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

    return df


def add_features_tariff(df: pd.DataFrame) -> pd.DataFrame:
    """Features TARIFF PERIODS (RD 148/2021) - P1/P2/P3 oficial"""
    df = df.copy()
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    # Tariff periods oficiales España (RD 148/2021)
    # P1 Punta: 10-14h, 18-22h (lunes-viernes NO festivos)
    # P2 Llano: 8-10h, 14-18h, 22-24h (lunes-viernes NO festivos)
    # P3 Valle: 0-8h (todos los días) + fin de semana + festivos

    # Simplificado (sin festivos por ahora):
    df['is_P1_punta'] = (
        (df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21])) &
        (df['dayofweek'] < 5)  # Lunes-Viernes
    ).astype(int)

    df['is_P2_llano'] = (
        (df['hour'].isin([8, 9, 14, 15, 16, 17, 22, 23])) &
        (df['dayofweek'] < 5)  # Lunes-Viernes
    ).astype(int)

    df['is_P3_valle'] = (
        (df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7])) |  # Madrugada
        (df['dayofweek'].isin([5, 6]))  # Fin de semana
    ).astype(int)

    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    holidays_es = [(1,1), (1,6), (5,1), (8,15), (10,12), (11,1), (12,6), (12,25)]
    df['is_holiday'] = df.apply(lambda r: 1 if (r['month'], r['day']) in holidays_es else 0, axis=1)
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

    return df


def train_baseline(df_train: pd.DataFrame) -> Prophet:
    """Entrena modelo BASELINE (actual)"""
    logger.info("🔥 Training BASELINE (is_peak_hour + is_valley_hour)...")

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.08,
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


def train_tariff(df_train: pd.DataFrame) -> Prophet:
    """Entrena modelo TARIFF PERIODS (P1/P2/P3)"""
    logger.info("🔥 Training TARIFF PERIODS (is_P1_punta + is_P2_llano + is_P3_valle)...")

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.08,  # Mismo que baseline
        n_changepoints=25,
        seasonality_prior_scale=10.0,
        seasonality_mode='multiplicative'
    )

    model.add_country_holidays('ES')
    model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)

    # Tariff periods (prior_scale ajustados)
    model.add_regressor('is_P1_punta', prior_scale=0.12)   # Punta importante
    model.add_regressor('is_P2_llano', prior_scale=0.08)   # Llano neutral
    model.add_regressor('is_P3_valle', prior_scale=0.10)   # Valle importante

    model.add_regressor('is_weekend', prior_scale=0.06)
    model.add_regressor('is_holiday', prior_scale=0.08)
    model.add_regressor('is_winter', prior_scale=0.04)
    model.add_regressor('is_summer', prior_scale=0.04)

    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

    model.fit(df_train)
    logger.info("✅ TARIFF PERIODS trained")
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
    print("PROPHET TEST: TARIFF PERIODS (RD 148/2021)")
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

    # Tariff
    df_train_tariff = df_train[['timestamp', 'price']].copy()
    df_train_tariff.columns = ['ds', 'y']
    df_train_tariff = add_features_tariff(df_train_tariff)

    df_val_tariff = df_val[['timestamp', 'price']].copy()
    df_val_tariff.columns = ['ds', 'y']
    df_val_tariff = add_features_tariff(df_val_tariff)

    print(f"   ✅ Baseline features: is_peak_hour, is_valley_hour")
    print(f"   ✅ Tariff features:   is_P1_punta, is_P2_llano, is_P3_valle")
    print()

    # 3. Train models
    print("=" * 80)
    print("TRAINING")
    print("=" * 80)
    print()

    model_base = train_baseline(df_train_base)
    print()

    model_tariff = train_tariff(df_train_tariff)
    print()

    # 4. Evaluate
    print("=" * 80)
    print("EVALUATION (Walk-Forward Nov 1-10, 2025)")
    print("=" * 80)
    print()

    metrics_base = evaluate(model_base, df_val_base, "BASELINE")
    print()

    metrics_tariff = evaluate(model_tariff, df_val_tariff, "TARIFF PERIODS")
    print()

    # 5. Comparison
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()

    mae_diff = metrics_tariff['mae'] - metrics_base['mae']
    rmse_diff = metrics_tariff['rmse'] - metrics_base['rmse']
    r2_diff = metrics_tariff['r2'] - metrics_base['r2']
    cov_diff = metrics_tariff['coverage'] - metrics_base['coverage']

    print(f"{'Metric':<15} | {'Baseline':<15} | {'Tariff':<15} | {'Diff':<15} | Status")
    print("-" * 80)
    print(f"{'MAE':<15} | {metrics_base['mae']:<15.4f} | {metrics_tariff['mae']:<15.4f} | {mae_diff:<+15.4f} | {'✅' if mae_diff < 0 else '❌'}")
    print(f"{'RMSE':<15} | {metrics_base['rmse']:<15.4f} | {metrics_tariff['rmse']:<15.4f} | {rmse_diff:<+15.4f} | {'✅' if rmse_diff < 0 else '❌'}")
    print(f"{'R²':<15} | {metrics_base['r2']:<15.4f} | {metrics_tariff['r2']:<15.4f} | {r2_diff:<+15.4f} | {'✅' if r2_diff > 0 else '❌'}")
    print(f"{'Coverage 95%':<15} | {metrics_base['coverage']:<15.2%} | {metrics_tariff['coverage']:<15.2%} | {cov_diff:<+15.2%} | {'✅' if cov_diff > 0 else '❌'}")
    print()

    # 6. Decision
    print("=" * 80)
    print("DECISION")
    print("=" * 80)
    print()

    if r2_diff > 0.02:
        print(f"✅ TARIFF PERIODS SIGNIFICATIVAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Estructura tarifaria oficial mejora forecasting")
        print(f"   RECOMENDACIÓN: Implementar en producción")
    elif r2_diff > 0:
        print(f"⚠️  TARIFF PERIODS LIGERAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Mejora marginal, evaluar trade-off complejidad")
    else:
        print(f"❌ BASELINE MEJOR ({r2_diff:.4f} R²)")
        print(f"   Tariff periods NO mejoran forecasting")
        print(f"   RECOMENDACIÓN: Mantener baseline")

    print()


if __name__ == "__main__":
    asyncio.run(main())
