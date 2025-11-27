#!/usr/bin/env python3
"""
Walk-Forward Validation for Prophet Model - DYNAMIC DATES
=========================================================

Train on data until N days ago
Predict last N days (truly unseen data)
Compare predictions vs reality
"""

import asyncio
import sys
import os
sys.path.insert(0, '/app')
os.environ.setdefault('INFLUXDB_URL', 'http://chocolate_factory_storage:8086')
os.environ.setdefault('INFLUXDB_TOKEN', 'chocolate-factory-influxdb-token')
os.environ.setdefault('INFLUXDB_ORG', 'chocolate-factory')
os.environ.setdefault('INFLUXDB_BUCKET', 'energy_data')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from services.data_ingestion import DataIngestionService


async def extract_data_until_date(end_date: str):
    """Extract REE data from InfluxDB until end_date (exclusive)"""

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


async def extract_data_range(start_date: str, end_date: str):
    """Extract REE data for specific date range"""

    async with DataIngestionService() as service:
        query = f'''
            from(bucket: "{service.config.bucket}")
            |> range(start: {start_date}, stop: {end_date})
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
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
        return df.sort_values('timestamp') if not df.empty else df


async def main():
    print("=" * 80)
    print("WALK-FORWARD VALIDATION - PROPHET MODEL (DYNAMIC)")
    print("=" * 80)
    print()

    # Calculate dynamic dates
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    validation_days = 10
    
    val_end = now
    val_start = now - timedelta(days=validation_days)
    train_cutoff = val_start
    
    print(f"🗓️  TODAY: {now.date()}")
    print(f"📊 TRAIN: Until {train_cutoff.date()} (exclusive)")
    print(f"🔮 VALIDATE: {val_start.date()} to {val_end.date()} (last {validation_days} days)")
    print()

    # 1. Extract training data
    print(f"📊 Step 1: Extracting training data (until {train_cutoff.date()})...")
    train_cutoff_str = train_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    df_train = await extract_data_until_date(train_cutoff_str)
    print(f"   ✅ Training samples: {len(df_train)}")
    print(f"   📅 Date range: {df_train['timestamp'].min()} → {df_train['timestamp'].max()}")
    print()

    # 2. Extract validation data
    print(f"📊 Step 2: Extracting validation data ({val_start.date()} to {val_end.date()})...")
    val_start_str = val_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    val_end_str = val_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    df_val = await extract_data_range(val_start_str, val_end_str)
    print(f"   ✅ Validation samples: {len(df_val)}")
    if len(df_val) > 0:
        print(f"   📅 Date range: {df_val['timestamp'].min()} → {df_val['timestamp'].max()}")
    print()

    if len(df_val) == 0:
        print("❌ ERROR: No validation data found!")
        return

    # 3. Train Prophet on training data only
    print("🤖 Step 3: Training Prophet on historical data (no validation period)...")

    from prophet import Prophet

    # Prepare data
    prophet_df = df_train[['timestamp', 'price']].copy()
    prophet_df.columns = ['ds', 'y']

    # Add features (NO lags - simplified model)
    from services.price_forecasting_service import PriceForecastingService
    service = PriceForecastingService()
    prophet_df = service._add_prophet_features(prophet_df, include_lags=False)

    # Train model (current configuration)
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.08,
        n_changepoints=25,
        seasonality_prior_scale=10.0,
    )

    # Add seasonalities
    model.add_seasonality(name='daily', period=1, fourier_order=8)
    model.add_seasonality(name='weekly', period=7, fourier_order=5)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8)

    # Add regressors
    model.add_regressor('is_peak_hour')
    model.add_regressor('is_valley_hour')
    model.add_regressor('is_winter')
    model.add_regressor('is_summer')

    model.fit(prophet_df)
    print("   ✅ Model trained successfully")
    print()

    # 4. Predict validation period
    print(f"🔮 Step 4: Predicting {val_start.date()} to {val_end.date()} (unseen data)...")
    
    # Create future dataframe
    future = model.make_future_dataframe(periods=validation_days * 24, freq='h')
    future = service._add_prophet_features(future, include_lags=False)
    
    # Predict
    forecast = model.predict(future)
    
    # Filter to validation period only (convert to tz-naive for comparison)
    val_start_naive = val_start.replace(tzinfo=None)
    val_end_naive = val_end.replace(tzinfo=None)
    forecast_val = forecast[forecast['ds'] >= val_start_naive]
    forecast_val = forecast_val[forecast_val['ds'] < val_end_naive]
    
    print(f"   ✅ Predictions generated: {len(forecast_val)}")
    print()

    # 5. Compare predictions vs reality
    print("📊 Step 5: Comparing predictions vs reality...")
    print()

    # Merge predictions with actual values
    df_val = df_val.rename(columns={'timestamp': 'ds', 'price': 'actual'})
    comparison = pd.merge(df_val, forecast_val[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='inner')
    
    if len(comparison) == 0:
        print("❌ ERROR: No matching timestamps between predictions and actual data!")
        return

    # Calculate metrics
    y_true = comparison['actual'].values
    y_pred = comparison['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # Coverage calculation
    within_interval = ((comparison['actual'] >= comparison['yhat_lower']) & 
                      (comparison['actual'] <= comparison['yhat_upper'])).sum()
    coverage = (within_interval / len(comparison)) * 100

    print("=" * 80)
    print("WALK-FORWARD VALIDATION RESULTS (TRULY UNSEEN DATA)")
    print("=" * 80)
    print()
    print(f"  MAE:         {mae:.4f} €/kWh")
    print(f"  RMSE:        {rmse:.4f} €/kWh")
    print(f"  R²:          {r2:.4f}")
    print(f"  Coverage 95%: {coverage:.2f}%")
    print()
    print(f"  Train samples: {len(df_train)}")
    print(f"  Val samples:   {len(comparison)}")
    print(f"  Val period:    {val_start.date()} to {val_end.date()}")
    print()

    # Interpretation
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print()
    if r2 >= 0.50:
        print(f"  ✅ R² >= 0.50: Model generalizes WELL to unseen future data")
    elif r2 >= 0.40:
        print(f"  ⚠️  R² >= 0.40: Model generalizes ACCEPTABLY")
    elif r2 >= 0.30:
        print(f"  ⚠️  R² >= 0.30: Model generalizes POORLY")
    else:
        print(f"  ❌ R² < 0.30: Model FAILS to generalize to unseen future data")
        print(f"     Strong overfitting detected. Model not reliable.")
    print()

    if coverage >= 90:
        print(f"  ✅ Coverage >= 90%: Confidence intervals are well-calibrated")
    else:
        print(f"  ⚠️  Coverage < 90%: Confidence intervals need adjustment")
    print()

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
