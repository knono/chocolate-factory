#!/usr/bin/env python3
"""
Prophet A/B Test: Climate Features vs Categorical Features
===========================================================

Compara dos modelos Prophet:
- Modelo A (Baseline): is_winter/is_summer (categórico)
- Modelo B (Improved): temperature/humidity (valores reales)

Estrategia clima hybrid:
1. Preferir OpenWeather/AEMET horaria (si disponible)
2. Fallback SIAR diaria broadcast (gaps o histórico)
3. Prediction: Climatología SIAR (promedio histórico día del año)

Validación walk-forward:
- Train: hasta Oct 31, 2025
- Test: Nov 1-10, 2025 (datos no vistos)

Output:
- Comparación R², MAE, RMSE, Coverage
- Report markdown con conclusiones
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
from datetime import datetime, timedelta
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


async def extract_climate_hybrid(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Extrae clima con estrategia hybrid:
    1. OpenWeather/AEMET horaria (prioridad)
    2. SIAR diaria broadcast (fallback)

    Returns:
        DataFrame con: timestamp (hourly), temperature, humidity, source
    """
    from services.data_ingestion import DataIngestionService

    logger.info(f"📊 Extracting climate data: {start_date.date()} → {end_date.date()}")

    async with DataIngestionService() as service:
        query_api = service.client.query_api()

        # 1. Intentar OpenWeather/AEMET horaria (bucket energy_data)
        start_rfc = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_rfc = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        weather_query = f'''
            from(bucket: "{service.config.bucket}")
            |> range(start: {start_rfc}, stop: {end_rfc})
            |> filter(fn: (r) => r._measurement == "weather_data")
            |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
            |> sort(columns: ["_time"])
        '''

        logger.info("🔍 Querying OpenWeather/AEMET hourly...")
        tables = query_api.query(weather_query)

        weather_hourly = []
        for table in tables:
            for record in table.records:
                weather_hourly.append({
                    'timestamp': record.get_time(),
                    'field': record.get_field(),
                    'value': record.get_value(),
                    'source': 'openweather_hourly'
                })

        df_hourly = pd.DataFrame(weather_hourly)
        logger.info(f"✅ OpenWeather/AEMET: {len(df_hourly)} records")

        # 2. Extraer SIAR diaria (bucket siar_historical)
        siar_query = f'''
            from(bucket: "siar_historical")
            |> range(start: {start_rfc}, stop: {end_rfc})
            |> filter(fn: (r) => r._measurement == "siar_weather")
            |> filter(fn: (r) => r._field == "temperatura_media" or r._field == "humedad_relativa_media")
            |> sort(columns: ["_time"])
        '''

        logger.info("🔍 Querying SIAR daily...")
        tables = query_api.query(siar_query)

        siar_daily = []
        for table in tables:
            for record in table.records:
                field_name = record.get_field()
                if 'temperatura' in field_name.lower():
                    field_name = 'temperature'
                elif 'humedad' in field_name.lower():
                    field_name = 'humidity'

                siar_daily.append({
                    'date': record.get_time().date(),
                    'field': field_name,
                    'value': record.get_value(),
                    'source': 'siar_daily'
                })

        df_siar_daily = pd.DataFrame(siar_daily)
        logger.info(f"✅ SIAR daily: {len(df_siar_daily)} records")

        # 3. Merge strategy: Hourly priority, SIAR broadcast fallback
        if not df_hourly.empty:
            # Pivot hourly data
            df_hourly['timestamp'] = pd.to_datetime(df_hourly['timestamp']).dt.tz_localize(None)
            df_hourly_pivot = df_hourly.pivot_table(
                index='timestamp',
                columns='field',
                values='value',
                aggfunc='mean'
            ).reset_index()

            df_hourly_pivot.columns.name = None
            logger.info(f"✅ Hourly pivoted: {len(df_hourly_pivot)} timestamps")
        else:
            df_hourly_pivot = pd.DataFrame()

        if not df_siar_daily.empty:
            # Pivot SIAR daily
            df_siar_pivot = df_siar_daily.pivot_table(
                index='date',
                columns='field',
                values='value',
                aggfunc='mean'
            ).reset_index()

            df_siar_pivot.columns.name = None

            # Broadcast SIAR daily to hourly (24 repetitions per day)
            siar_broadcast = []
            for _, row in df_siar_pivot.iterrows():
                date = row['date']
                for hour in range(24):
                    timestamp = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour)
                    siar_broadcast.append({
                        'timestamp': timestamp,
                        'temperature': row.get('temperature', np.nan),
                        'humidity': row.get('humidity', np.nan),
                        'source': 'siar_broadcast'
                    })

            df_siar_broadcast = pd.DataFrame(siar_broadcast)
            logger.info(f"✅ SIAR broadcast: {len(df_siar_broadcast)} hourly timestamps")
        else:
            df_siar_broadcast = pd.DataFrame()

        # 4. Merge: prioritize hourly, fill gaps with SIAR broadcast
        if not df_hourly_pivot.empty and not df_siar_broadcast.empty:
            merged = pd.merge(
                df_hourly_pivot,
                df_siar_broadcast,
                on='timestamp',
                how='outer',
                suffixes=('_hourly', '_siar')
            )

            # Priority: hourly > siar
            merged['temperature'] = merged.get('temperature_hourly', merged.get('temperature')).fillna(
                merged.get('temperature_siar')
            )
            merged['humidity'] = merged.get('humidity_hourly', merged.get('humidity')).fillna(
                merged.get('humidity_siar')
            )

            # Determine source
            merged['source'] = 'openweather_hourly'
            merged.loc[merged['temperature_hourly'].isna(), 'source'] = 'siar_broadcast'

            result = merged[['timestamp', 'temperature', 'humidity', 'source']].copy()
        elif not df_hourly_pivot.empty:
            result = df_hourly_pivot[['timestamp', 'temperature', 'humidity']].copy()
            result['source'] = 'openweather_hourly'
        elif not df_siar_broadcast.empty:
            result = df_siar_broadcast[['timestamp', 'temperature', 'humidity', 'source']].copy()
        else:
            result = pd.DataFrame(columns=['timestamp', 'temperature', 'humidity', 'source'])

        # Fill remaining NaNs with forward/backward fill
        result = result.sort_values('timestamp')
        result['temperature'] = result['temperature'].fillna(method='ffill').fillna(method='bfill')
        result['humidity'] = result['humidity'].fillna(method='ffill').fillna(method='bfill')

        # Log source distribution
        if not result.empty and 'source' in result.columns:
            source_counts = result['source'].value_counts()
            logger.info(f"📊 Climate sources: {source_counts.to_dict()}")

        logger.info(f"✅ Final climate data: {len(result)} hourly records")
        return result


async def calculate_climatology(siar_start_year: int = 2000) -> pd.DataFrame:
    """
    Calcula climatología SIAR: promedio histórico por día del año.

    Returns:
        DataFrame con: day_of_year, avg_temperature, avg_humidity
    """
    from services.data_ingestion import DataIngestionService

    logger.info(f"📊 Calculating SIAR climatology ({siar_start_year}-2025)...")

    async with DataIngestionService() as service:
        query_api = service.client.query_api()

        siar_query = f'''
            from(bucket: "siar_historical")
            |> range(start: {siar_start_year}-01-01T00:00:00Z)
            |> filter(fn: (r) => r._measurement == "siar_weather")
            |> filter(fn: (r) => r._field == "temperatura_media" or r._field == "humedad_relativa_media")
        '''

        tables = query_api.query(siar_query)

        siar_data = []
        for table in tables:
            for record in table.records:
                field_name = record.get_field()
                if 'temperatura' in field_name.lower():
                    field_name = 'temperature'
                elif 'humedad' in field_name.lower():
                    field_name = 'humidity'

                timestamp = record.get_time()
                siar_data.append({
                    'date': timestamp.date(),
                    'day_of_year': timestamp.timetuple().tm_yday,
                    'field': field_name,
                    'value': record.get_value()
                })

        df_siar = pd.DataFrame(siar_data)

        # Pivot
        df_pivot = df_siar.pivot_table(
            index=['date', 'day_of_year'],
            columns='field',
            values='value',
            aggfunc='mean'
        ).reset_index()

        # Group by day_of_year (promedio todos los años)
        climatology = df_pivot.groupby('day_of_year').agg({
            'temperature': 'mean',
            'humidity': 'mean'
        }).reset_index()

        climatology.columns = ['day_of_year', 'avg_temperature', 'avg_humidity']

        logger.info(f"✅ Climatology calculated: {len(climatology)} days (1-366)")
        logger.info(f"   Temp range: {climatology['avg_temperature'].min():.1f} - {climatology['avg_temperature'].max():.1f} °C")
        logger.info(f"   Humidity range: {climatology['avg_humidity'].min():.1f} - {climatology['avg_humidity'].max():.1f} %")

        return climatology


def add_prophet_features_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade features Prophet BASELINE (categóricas).

    Features:
    - Temporales: hour, dayofweek, month
    - Demanda: is_peak_hour, is_valley_hour, is_business_hour
    - Calendario: is_weekend, is_holiday
    - Estacionales: is_winter, is_summer (CATEGÓRICO)
    """
    df = df.copy()

    # Temporal
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    # Demand proxies
    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

    # Calendar
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

    holidays_es = [
        (1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 25)
    ]
    df['is_holiday'] = df.apply(
        lambda row: 1 if (row['month'], row['day']) in holidays_es else 0,
        axis=1
    )

    # Seasonality (CATEGÓRICO - BASELINE)
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)

    return df


def add_prophet_features_improved(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade features Prophet IMPROVED (clima real).

    Features:
    - Temporales: hour, dayofweek, month (igual baseline)
    - Demanda: is_peak_hour, is_valley_hour (igual baseline)
    - Calendario: is_weekend, is_holiday (igual baseline)
    - Clima: temperature, humidity (VALORES REALES - IMPROVED)
    """
    df = df.copy()

    # Temporal
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day

    # Demand proxies
    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)

    # Calendar
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

    holidays_es = [
        (1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 25)
    ]
    df['is_holiday'] = df.apply(
        lambda row: 1 if (row['month'], row['day']) in holidays_es else 0,
        axis=1
    )

    # Clima (VALORES REALES - ya vienen en df desde merge)
    # temperature, humidity ya están en el dataframe

    return df


def train_model_baseline(df_train: pd.DataFrame) -> Prophet:
    """
    Entrena modelo Prophet BASELINE con features categóricas.
    """
    logger.info("🔥 Training BASELINE model (is_winter/is_summer)...")

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

    # Fourier seasonality
    model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)

    # Regressors
    model.add_regressor('is_peak_hour', prior_scale=0.10)
    model.add_regressor('is_valley_hour', prior_scale=0.08)
    model.add_regressor('is_weekend', prior_scale=0.06)
    model.add_regressor('is_holiday', prior_scale=0.08)
    model.add_regressor('is_winter', prior_scale=0.04)  # CATEGÓRICO
    model.add_regressor('is_summer', prior_scale=0.04)  # CATEGÓRICO

    # Suprimir logs Prophet
    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

    model.fit(df_train)

    logger.info("✅ BASELINE model trained")
    return model


def train_model_improved(df_train: pd.DataFrame) -> Prophet:
    """
    Entrena modelo Prophet IMPROVED con features clima reales.
    """
    logger.info("🔥 Training IMPROVED model (temperature/humidity)...")

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

    # Fourier seasonality (igual baseline)
    model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)

    # Regressors (CAMBIO: temperature/humidity en vez de is_winter/is_summer)
    model.add_regressor('is_peak_hour', prior_scale=0.10)
    model.add_regressor('is_valley_hour', prior_scale=0.08)
    model.add_regressor('is_weekend', prior_scale=0.06)
    model.add_regressor('is_holiday', prior_scale=0.08)

    # CLIMA REAL (nuevo)
    model.add_regressor('temperature', prior_scale=0.08)  # °C
    model.add_regressor('humidity', prior_scale=0.06)     # %

    # Suprimir logs Prophet
    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

    model.fit(df_train)

    logger.info("✅ IMPROVED model trained")
    return model


def evaluate_model(model: Prophet, df_test: pd.DataFrame, model_name: str) -> dict:
    """Evalúa modelo en test set"""
    logger.info(f"📊 Evaluating {model_name}...")

    # Predict
    forecast = model.predict(df_test)

    # Metrics
    y_true = df_test['y'].values
    y_pred = forecast['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # Coverage
    lower = forecast['yhat_lower'].values
    upper = forecast['yhat_upper'].values
    coverage = np.mean((y_true >= lower) & (y_true <= upper))

    metrics = {
        'model_name': model_name,
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'coverage': coverage,
        'samples': len(y_true)
    }

    logger.info(f"  MAE:     {mae:.4f} €/kWh")
    logger.info(f"  RMSE:    {rmse:.4f} €/kWh")
    logger.info(f"  R²:      {r2:.4f}")
    logger.info(f"  Coverage: {coverage:.2%}")

    return metrics


async def main():
    print("=" * 80)
    print("PROPHET A/B TEST: CLIMATE FEATURES")
    print("=" * 80)
    print()

    # 1. Extract REE data (train hasta Oct 31, test Nov 1-10)
    print("📊 Step 1: Extracting REE data...")
    train_cutoff = "2025-11-01T00:00:00Z"
    df_ree_train = await extract_ree_data(train_cutoff)

    val_start = datetime(2025, 11, 1)
    val_end = datetime(2025, 11, 11)
    df_ree_val = await extract_ree_data("2025-11-11T00:00:00Z")
    df_ree_val = df_ree_val[df_ree_val['timestamp'] >= val_start]

    print(f"   ✅ Train: {len(df_ree_train)} records ({df_ree_train['timestamp'].min().date()} → {df_ree_train['timestamp'].max().date()})")
    print(f"   ✅ Val: {len(df_ree_val)} records ({df_ree_val['timestamp'].min().date()} → {df_ree_val['timestamp'].max().date()})")
    print()

    # 2. Extract climate data (hybrid strategy)
    print("📊 Step 2: Extracting climate data (hybrid)...")
    train_start = df_ree_train['timestamp'].min()
    train_end = df_ree_train['timestamp'].max()

    df_climate_train = await extract_climate_hybrid(train_start, train_end)
    df_climate_val = await extract_climate_hybrid(val_start, val_end)

    print(f"   ✅ Climate train: {len(df_climate_train)} records")
    print(f"   ✅ Climate val: {len(df_climate_val)} records")
    print()

    # 3. Calculate climatology for fallback
    print("📊 Step 3: Calculating SIAR climatology...")
    try:
        climatology = await calculate_climatology(siar_start_year=2000)
        print(f"   ✅ Climatology: {len(climatology)} days")
    except Exception as e:
        logger.warning(f"⚠️  SIAR climatology failed: {e}")
        logger.warning("   Using simple fallback (mean values)")
        climatology = pd.DataFrame({
            'day_of_year': range(1, 367),
            'avg_temperature': [20.0] * 366,  # Fallback: 20°C constant
            'avg_humidity': [60.0] * 366       # Fallback: 60% constant
        })
        print(f"   ⚠️  Using fallback climatology (20°C, 60%)")
    print()

    # 4. Merge REE + Climate (train)
    print("📊 Step 4: Merging REE + Climate (train)...")
    df_train = pd.merge(df_ree_train, df_climate_train, on='timestamp', how='left')

    # Fill missing climate with climatology
    df_train['day_of_year'] = df_train['timestamp'].dt.dayofyear
    df_train = df_train.merge(climatology, on='day_of_year', how='left')
    df_train['temperature'] = df_train['temperature'].fillna(df_train['avg_temperature'])
    df_train['humidity'] = df_train['humidity'].fillna(df_train['avg_humidity'])

    print(f"   ✅ Merged train: {len(df_train)} records")
    print(f"   📊 Temperature: {df_train['temperature'].min():.1f} - {df_train['temperature'].max():.1f} °C")
    print(f"   📊 Humidity: {df_train['humidity'].min():.1f} - {df_train['humidity'].max():.1f} %")
    print()

    # 5. Merge REE + Climate (validation)
    print("📊 Step 5: Merging REE + Climate (validation)...")
    df_val = pd.merge(df_ree_val, df_climate_val, on='timestamp', how='left')

    # Fill missing climate with climatology
    df_val['day_of_year'] = df_val['timestamp'].dt.dayofyear
    df_val = df_val.merge(climatology, on='day_of_year', how='left')
    df_val['temperature'] = df_val['temperature'].fillna(df_val['avg_temperature'])
    df_val['humidity'] = df_val['humidity'].fillna(df_val['avg_humidity'])

    print(f"   ✅ Merged val: {len(df_val)} records")
    print()

    # 6. Prepare Prophet format
    print("📊 Step 6: Preparing Prophet format...")

    # Baseline
    df_train_baseline = df_train[['timestamp', 'price']].copy()
    df_train_baseline.columns = ['ds', 'y']
    df_train_baseline = add_prophet_features_baseline(df_train_baseline)

    df_val_baseline = df_val[['timestamp', 'price']].copy()
    df_val_baseline.columns = ['ds', 'y']
    df_val_baseline = add_prophet_features_baseline(df_val_baseline)

    # Improved
    df_train_improved = df_train[['timestamp', 'price', 'temperature', 'humidity']].copy()
    df_train_improved.columns = ['ds', 'y', 'temperature', 'humidity']
    df_train_improved = add_prophet_features_improved(df_train_improved)

    df_val_improved = df_val[['timestamp', 'price', 'temperature', 'humidity']].copy()
    df_val_improved.columns = ['ds', 'y', 'temperature', 'humidity']
    df_val_improved = add_prophet_features_improved(df_val_improved)

    print(f"   ✅ Baseline features: {list(df_train_baseline.columns)}")
    print(f"   ✅ Improved features: {list(df_train_improved.columns)}")
    print()

    # 7. Train models
    print("=" * 80)
    print("TRAINING MODELS")
    print("=" * 80)
    print()

    model_baseline = train_model_baseline(df_train_baseline)
    print()

    model_improved = train_model_improved(df_train_improved)
    print()

    # 8. Evaluate models
    print("=" * 80)
    print("EVALUATION (Walk-Forward Nov 1-10, 2025)")
    print("=" * 80)
    print()

    metrics_baseline = evaluate_model(model_baseline, df_val_baseline, "BASELINE (is_winter/summer)")
    print()

    metrics_improved = evaluate_model(model_improved, df_val_improved, "IMPROVED (temperature/humidity)")
    print()

    # 9. Comparison
    print("=" * 80)
    print("A/B COMPARISON")
    print("=" * 80)
    print()
    print(f"{'Metric':<15} | {'Baseline':<15} | {'Improved':<15} | {'Diff':<15} | Status")
    print("-" * 80)

    mae_diff = metrics_improved['mae'] - metrics_baseline['mae']
    mae_status = "✅ Mejor" if mae_diff < 0 else "❌ Peor"
    print(f"{'MAE':<15} | {metrics_baseline['mae']:<15.4f} | {metrics_improved['mae']:<15.4f} | {mae_diff:<+15.4f} | {mae_status}")

    rmse_diff = metrics_improved['rmse'] - metrics_baseline['rmse']
    rmse_status = "✅ Mejor" if rmse_diff < 0 else "❌ Peor"
    print(f"{'RMSE':<15} | {metrics_baseline['rmse']:<15.4f} | {metrics_improved['rmse']:<15.4f} | {rmse_diff:<+15.4f} | {rmse_status}")

    r2_diff = metrics_improved['r2'] - metrics_baseline['r2']
    r2_status = "✅ Mejor" if r2_diff > 0 else "❌ Peor"
    print(f"{'R²':<15} | {metrics_baseline['r2']:<15.4f} | {metrics_improved['r2']:<15.4f} | {r2_diff:<+15.4f} | {r2_status}")

    cov_diff = metrics_improved['coverage'] - metrics_baseline['coverage']
    cov_status = "✅ Mejor" if cov_diff > 0 else "❌ Peor"
    print(f"{'Coverage 95%':<15} | {metrics_baseline['coverage']:<15.2%} | {metrics_improved['coverage']:<15.2%} | {cov_diff:<+15.2%} | {cov_status}")

    print()

    # 10. Interpretation
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print()

    if r2_diff > 0.02:  # Mejora >2%
        print(f"✅ IMPROVED model es SIGNIFICATIVAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Clima real (temperature/humidity) mejora forecasting vs categorías estacionales")
        print(f"   RECOMENDACIÓN: Implementar modelo IMPROVED en producción")
    elif r2_diff > 0:
        print(f"⚠️  IMPROVED model es LIGERAMENTE MEJOR (+{r2_diff:.4f} R²)")
        print(f"   Mejora marginal, evaluar trade-off complejidad vs ganancia")
        print(f"   RECOMENDACIÓN: A/B testing en producción antes de decidir")
    else:
        print(f"❌ BASELINE model es MEJOR ({r2_diff:.4f} R²)")
        print(f"   Clima real NO mejora forecasting, categorías estacionales suficientes")
        print(f"   RECOMENDACIÓN: Mantener modelo BASELINE actual")

    print()

    # 11. Save report
    report_path = "/home/nono/Downloads/chocolate-factory/docs/PROPHET_AB_TEST_REPORT.md"
    with open(report_path, 'w') as f:
        f.write("# Prophet A/B Test Report: Climate Features\n\n")
        f.write(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Validation**: Walk-forward Nov 1-10, 2025 ({metrics_baseline['samples']} samples)\n\n")

        f.write("## Modelos comparados\n\n")
        f.write("### Baseline (Actual)\n")
        f.write("- Features categóricas: `is_winter`, `is_summer`\n")
        f.write("- Exógenas: is_peak_hour, is_valley_hour, is_weekend, is_holiday\n")
        f.write("- Fourier: daily=8, weekly=5, yearly=8\n\n")

        f.write("### Improved (Propuesto)\n")
        f.write("- Features clima real: `temperature` (°C), `humidity` (%)\n")
        f.write("- Estrategia: Hybrid (OpenWeather horaria + SIAR broadcast)\n")
        f.write("- Exógenas: is_peak_hour, is_valley_hour, is_weekend, is_holiday (igual baseline)\n")
        f.write("- Fourier: daily=8, weekly=5, yearly=8 (igual baseline)\n\n")

        f.write("## Resultados\n\n")
        f.write("| Métrica | Baseline | Improved | Diff | Status |\n")
        f.write("|---------|----------|----------|------|--------|\n")
        f.write(f"| MAE | {metrics_baseline['mae']:.4f} | {metrics_improved['mae']:.4f} | {mae_diff:+.4f} | {mae_status} |\n")
        f.write(f"| RMSE | {metrics_baseline['rmse']:.4f} | {metrics_improved['rmse']:.4f} | {rmse_diff:+.4f} | {rmse_status} |\n")
        f.write(f"| R² | {metrics_baseline['r2']:.4f} | {metrics_improved['r2']:.4f} | {r2_diff:+.4f} | {r2_status} |\n")
        f.write(f"| Coverage 95% | {metrics_baseline['coverage']:.2%} | {metrics_improved['coverage']:.2%} | {cov_diff:+.2%} | {cov_status} |\n\n")

        f.write("## Conclusión\n\n")
        if r2_diff > 0.02:
            f.write(f"✅ **IMPROVED model SIGNIFICATIVAMENTE MEJOR** (+{r2_diff:.4f} R²)\n\n")
            f.write("Recomendación: Implementar en producción.\n")
        elif r2_diff > 0:
            f.write(f"⚠️ **IMPROVED model LIGERAMENTE MEJOR** (+{r2_diff:.4f} R²)\n\n")
            f.write("Recomendación: A/B testing en producción.\n")
        else:
            f.write(f"❌ **BASELINE model MEJOR** ({r2_diff:.4f} R²)\n\n")
            f.write("Recomendación: Mantener modelo actual.\n")

    print(f"📄 Report saved: {report_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
