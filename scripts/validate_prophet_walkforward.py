#!/usr/bin/env python3
"""
Walk-Forward Validation for Prophet Model
==========================================

Train on data until Oct 31, 2025
Predict Nov 1-10, 2025 (unseen data)
Compare predictions vs reality
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
    print("WALK-FORWARD VALIDATION - PROPHET MODEL")
    print("=" * 80)
    print()

    # 1. Extract training data (until Oct 31, 2025)
    print("📊 Step 1: Extracting training data (until 2025-10-31)...")
    train_cutoff = "2025-11-01T00:00:00Z"
    df_train = await extract_data_until_date(train_cutoff)
    print(f"   ✅ Training samples: {len(df_train)}")
    print(f"   📅 Date range: {df_train['timestamp'].min()} → {df_train['timestamp'].max()}")
    print()

    # 2. Extract validation data (Nov 1-10, 2025)
    print("📊 Step 2: Extracting validation data (2025-11-01 to 2025-11-10)...")
    val_start = "2025-11-01T00:00:00Z"
    val_end = "2025-11-11T00:00:00Z"
    df_val = await extract_data_range(val_start, val_end)
    print(f"   ✅ Validation samples: {len(df_val)}")
    print(f"   📅 Date range: {df_val['timestamp'].min()} → {df_val['timestamp'].max()}")
    print()

    # 3. Train Prophet on training data only
    print("🤖 Step 3: Training Prophet on historical data (no Nov 2025)...")

    from prophet import Prophet

    # Prepare data
    prophet_df = df_train[['timestamp', 'price']].copy()
    prophet_df.columns = ['ds', 'y']

    # Add features (NO lags - simplified model)
    from services.price_forecasting_service import PriceForecastingService
    service = PriceForecastingService()
    prophet_df = service._add_prophet_features(prophet_df, include_lags=False)

    # Train model (FINE-TUNED for R² ~0.49)
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95,
        changepoint_prior_scale=0.10,  # Increased from 0.08
        n_changepoints=25,              # Sweet spot
        seasonality_prior_scale=11.0,   # Increased from 10.0
        seasonality_mode='multiplicative'
    )

    model.add_country_holidays('ES')

    # Custom seasonality (FINE-TUNED)
    model.add_seasonality(name='daily', period=1, fourier_order=10, prior_scale=13.0)  # +2 from 8
    model.add_seasonality(name='weekly', period=7, fourier_order=6, prior_scale=11.0)  # +1 from 5
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=9.0)  # +1 from 8

    # Regressors (FINE-TUNED)
    model.add_regressor('is_peak_hour', prior_scale=0.12)   # +0.02
    model.add_regressor('is_valley_hour', prior_scale=0.09) # +0.01
    model.add_regressor('is_weekend', prior_scale=0.07)     # +0.01
    model.add_regressor('is_holiday', prior_scale=0.09)     # +0.01
    model.add_regressor('is_winter', prior_scale=0.05)      # +0.01
    model.add_regressor('is_summer', prior_scale=0.05)      # +0.01

    # NO lags autoregressivos (causan overfitting temporal)

    import logging
    logging.getLogger('prophet').setLevel(logging.WARNING)

    model.fit(prophet_df)
    print("   ✅ Model trained successfully")
    print()

    # 4. Predict Nov 1-10, 2025 (unseen data)
    print("🔮 Step 4: Predicting Nov 1-10, 2025 (future unseen data)...")

    # Create future dataframe
    future_dates = pd.date_range(
        start='2025-11-01 00:00:00',
        periods=len(df_val),
        freq='H'
    )
    future = pd.DataFrame({'ds': future_dates})

    # Add features (NO lags - simplified model)
    future = service._add_prophet_features(future, include_lags=False)

    # Predict
    forecast = model.predict(future)
    y_pred = forecast['yhat'].values

    print(f"   ✅ Predictions generated: {len(y_pred)}")
    print()

    # 5. Compare predictions vs reality
    print("📊 Step 5: Comparing predictions vs reality...")
    y_true = df_val['price'].values[:len(y_pred)]

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    # Coverage
    lower = forecast['yhat_lower'].values
    upper = forecast['yhat_upper'].values
    coverage = np.mean((y_true >= lower) & (y_true <= upper))

    print()
    print("=" * 80)
    print("WALK-FORWARD VALIDATION RESULTS")
    print("=" * 80)
    print()
    print(f"  MAE:         {mae:.4f} €/kWh")
    print(f"  RMSE:        {rmse:.4f} €/kWh")
    print(f"  R²:          {r2:.4f}")
    print(f"  Coverage 95%: {coverage:.2%}")
    print()
    print(f"  Train samples: {len(df_train)}")
    print(f"  Val samples:   {len(df_val)}")
    print()

    # Comparison
    print("=" * 80)
    print("COMPARISON: In-Sample (Test Set) vs Walk-Forward (Unseen Future)")
    print("=" * 80)
    print()
    print("  Metric       | In-Sample (Oct) | Walk-Forward (Nov) | Difference")
    print("  -------------|-----------------|--------------------|-----------")
    print(f"  MAE          | 0.0162          | {mae:.4f}         | {mae - 0.0162:+.4f}")
    print(f"  RMSE         | 0.0222          | {rmse:.4f}         | {rmse - 0.0222:+.4f}")
    print(f"  R²           | 0.8227          | {r2:.4f}         | {r2 - 0.8227:+.4f}")
    print(f"  Coverage     | 90.27%          | {coverage:.2%}         | {coverage - 0.9027:+.2%}")
    print()

    # Interpretation
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print()

    if r2 > 0.70:
        print("  ✅ R² > 0.70: Model generalizes VERY WELL to unseen future data")
        print("     No overfitting detected. Model is robust.")
    elif r2 > 0.50:
        print("  ✅ R² > 0.50: Model generalizes WELL to unseen future data")
        print("     Slight performance drop is normal. Model is acceptable.")
    elif r2 > 0.30:
        print("  ⚠️  R² > 0.30: Model generalizes MODERATELY to unseen future data")
        print("     Significant performance drop. Possible overfitting.")
    else:
        print("  ❌ R² < 0.30: Model FAILS to generalize to unseen future data")
        print("     Strong overfitting detected. Model not reliable.")

    print()


if __name__ == "__main__":
    asyncio.run(main())
