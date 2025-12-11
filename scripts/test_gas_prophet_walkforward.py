#!/usr/bin/env python3
"""
Walk-Forward Validation: Prophet Baseline vs Prophet + Gas Feature
===================================================================

Usa EXACTAMENTE la misma configuración que el modelo de producción:
- Datos HORARIOS de InfluxDB (no diarios)
- Horizonte predicción: 168h (7 días)
- Features: is_peak_hour, is_valley_hour, is_weekend, etc.
- Prophet config: changepoint_prior=0.08, Fourier custom

Validación walk-forward:
- Train: ~3 meses de datos horarios
- Test: 168h (7 días) cada iteración
- Iteraciones: 10

Uso (inside Docker):
    python3 /app/scripts/test_gas_prophet_walkforward.py

Author: Gemini
Date: December 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import warnings

sys.path.insert(0, "/app")

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

# ==============================================================================
# PATHS
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAS_CSV = os.path.join(SCRIPT_DIR, "data", "gas_generation_36m.csv")

# ==============================================================================
# CONFIGURATION - SAME AS PRODUCTION
# ==============================================================================
TRAIN_HOURS = 90 * 24    # 90 días en horas (2160)
TEST_HOURS = 168         # 7 días = 168 horas (horizonte real)
N_ITERATIONS = 10        # Walk-forward iterations

# Prophet config from production
PROPHET_CONFIG = {
    'yearly_seasonality': False,
    'weekly_seasonality': False,
    'daily_seasonality': False,
    'interval_width': 0.95,
    'changepoint_prior_scale': 0.08,
    'n_changepoints': 25,
    'seasonality_prior_scale': 10.0,
    'seasonality_mode': 'multiplicative',
}

# ==============================================================================
# DATA LOADING
# ==============================================================================
def load_gas_data_hourly() -> pd.DataFrame:
    """Load gas generation CSV and expand to hourly (repeat daily value for each hour)."""
    logger.info(f"📥 Loading gas data and expanding to hourly...")
    
    if not os.path.exists(GAS_CSV):
        raise FileNotFoundError(f"Gas CSV not found: {GAS_CSV}")
    
    df = pd.read_csv(GAS_CSV, parse_dates=["date"])
    df = df.rename(columns={"date": "date", "gas_gen_mwh": "gas_gen"})
    
    # Expand daily to hourly (each day gets 24 rows with same gas value)
    hourly_records = []
    for _, row in df.iterrows():
        base_date = row["date"]
        for h in range(24):
            hourly_records.append({
                "ds": base_date + timedelta(hours=h),
                "gas_gen": row["gas_gen"]
            })
    
    hourly_df = pd.DataFrame(hourly_records)
    
    # Normalize gas generation
    hourly_df["gas_gen_scaled"] = (hourly_df["gas_gen"] - hourly_df["gas_gen"].min()) / \
                                   (hourly_df["gas_gen"].max() - hourly_df["gas_gen"].min())
    
    logger.info(f"✅ Loaded {len(hourly_df)} hourly gas records")
    return hourly_df

def load_pvpc_hourly() -> pd.DataFrame:
    """Load PVPC prices from InfluxDB (hourly)."""
    logger.info("📥 Loading PVPC hourly prices from InfluxDB...")
    
    from infrastructure.influxdb import get_influxdb_client
    
    influx = get_influxdb_client()
    
    query = '''
    from(bucket: "energy_data")
      |> range(start: -36mo)
      |> filter(fn: (r) => r["_measurement"] == "energy_prices")
      |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
      |> sort(columns: ["_time"])
    '''
    
    results = influx.query(query)
    
    records = []
    for record in results:
        records.append({
            "ds": record["time"].replace(tzinfo=None),
            "y": record["value"]
        })
    
    df = pd.DataFrame(records)
    df = df.drop_duplicates(subset=["ds"]).sort_values("ds").reset_index(drop=True)
    
    logger.info(f"✅ Loaded {len(df)} hourly price records")
    return df

def add_prophet_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add features exactly as production (from PriceForecastingService)."""
    df = df.copy()
    
    df['hour'] = df['ds'].dt.hour
    df['dayofweek'] = df['ds'].dt.dayofweek
    df['month'] = df['ds'].dt.month
    df['day'] = df['ds'].dt.day
    
    # Demand proxies (same as production)
    df['is_peak_hour'] = df['hour'].isin([10, 11, 12, 13, 18, 19, 20, 21]).astype(int)
    df['is_valley_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 5, 6, 7]).astype(int)
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    
    holidays_es = [(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 25)]
    df['is_holiday'] = df.apply(lambda row: 1 if (row['month'], row['day']) in holidays_es else 0, axis=1)
    
    df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)
    
    return df

def create_prophet_model(with_gas: bool = False):
    """Create Prophet model with production config."""
    from prophet import Prophet
    
    model = Prophet(**PROPHET_CONFIG)
    model.add_country_holidays('ES')
    
    # Custom seasonality (same as production)
    model.add_seasonality(name='daily', period=1, fourier_order=10, prior_scale=13.0)
    model.add_seasonality(name='weekly', period=7, fourier_order=6, prior_scale=11.0)
    model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=9.0)
    
    # Regressors
    model.add_regressor('is_peak_hour', prior_scale=0.12)
    model.add_regressor('is_valley_hour', prior_scale=0.09)
    model.add_regressor('is_weekend', prior_scale=0.07)
    model.add_regressor('is_holiday', prior_scale=0.09)
    model.add_regressor('is_winter', prior_scale=0.05)
    model.add_regressor('is_summer', prior_scale=0.05)
    
    if with_gas:
        model.add_regressor('gas_gen_scaled', prior_scale=0.10)
    
    return model

# ==============================================================================
# WALK-FORWARD VALIDATION
# ==============================================================================
def walk_forward_validation(merged_df: pd.DataFrame):
    """Perform walk-forward with 168h horizon (production config)."""
    
    logger.info("\n" + "=" * 70)
    logger.info("🔬 WALK-FORWARD VALIDATION (Production Config)")
    logger.info("=" * 70)
    logger.info(f"Config: Train={TRAIN_HOURS}h (~{TRAIN_HOURS//24}d), Test={TEST_HOURS}h (7d), Iterations={N_ITERATIONS}")
    
    total_hours_needed = TRAIN_HOURS + (TEST_HOURS * N_ITERATIONS)
    if len(merged_df) < total_hours_needed:
        logger.error(f"❌ Not enough data. Need {total_hours_needed}, have {len(merged_df)}")
        return
    
    start_idx = len(merged_df) - total_hours_needed
    
    results_a = []  # Baseline
    results_b = []  # + Gas
    
    feature_cols = ['is_peak_hour', 'is_valley_hour', 'is_weekend', 'is_holiday', 'is_winter', 'is_summer']
    
    for i in range(N_ITERATIONS):
        iter_start = start_idx + (i * TEST_HOURS)
        train_end = iter_start + TRAIN_HOURS
        test_end = train_end + TEST_HOURS
        
        train = merged_df.iloc[iter_start:train_end].copy()
        test = merged_df.iloc[train_end:test_end].copy()
        
        if len(test) < TEST_HOURS:
            logger.warning(f"⚠️ Iteration {i+1}: Not enough test data, skipping")
            continue
        
        train_start_date = train["ds"].min().strftime("%Y-%m-%d")
        test_start_date = test["ds"].min().strftime("%Y-%m-%d")
        test_end_date = test["ds"].max().strftime("%Y-%m-%d")
        
        logger.info(f"\n📊 Iteration {i+1}/{N_ITERATIONS}: Train→{train_start_date}, Test {test_start_date} → {test_end_date}")
        
        # --- Model A: Baseline ---
        model_a = create_prophet_model(with_gas=False)
        model_a.fit(train[["ds", "y"] + feature_cols])
        
        future_a = test[["ds"] + feature_cols].copy()
        forecast_a = model_a.predict(future_a)
        
        mae_a = np.mean(np.abs(test["y"].values - forecast_a["yhat"].values))
        ss_res_a = np.sum((test["y"].values - forecast_a["yhat"].values) ** 2)
        ss_tot_a = np.sum((test["y"].values - test["y"].mean()) ** 2)
        r2_a = 1 - (ss_res_a / ss_tot_a) if ss_tot_a > 0 else 0
        
        results_a.append({"iteration": i+1, "mae": mae_a, "r2": r2_a, "test_start": test_start_date})
        
        # --- Model B: + Gas ---
        model_b = create_prophet_model(with_gas=True)
        model_b.fit(train[["ds", "y"] + feature_cols + ["gas_gen_scaled"]])
        
        future_b = test[["ds"] + feature_cols + ["gas_gen_scaled"]].copy()
        forecast_b = model_b.predict(future_b)
        
        mae_b = np.mean(np.abs(test["y"].values - forecast_b["yhat"].values))
        ss_res_b = np.sum((test["y"].values - forecast_b["yhat"].values) ** 2)
        ss_tot_b = np.sum((test["y"].values - test["y"].mean()) ** 2)
        r2_b = 1 - (ss_res_b / ss_tot_b) if ss_tot_b > 0 else 0
        
        results_b.append({"iteration": i+1, "mae": mae_b, "r2": r2_b, "test_start": test_start_date})
        
        improvement = (mae_a - mae_b) / mae_a * 100 if mae_a > 0 else 0
        logger.info(f"   MAE: {mae_a:.4f} → {mae_b:.4f} ({improvement:+.1f}%) | R²: {r2_a:.3f} → {r2_b:.3f}")
    
    # ==============================================================================
    # AGGREGATE RESULTS
    # ==============================================================================
    logger.info("\n" + "=" * 70)
    logger.info("📊 WALK-FORWARD VALIDATION SUMMARY")
    logger.info("=" * 70)
    
    df_a = pd.DataFrame(results_a)
    df_b = pd.DataFrame(results_b)
    
    avg_mae_a = df_a["mae"].mean()
    std_mae_a = df_a["mae"].std()
    avg_mae_b = df_b["mae"].mean()
    std_mae_b = df_b["mae"].std()
    
    avg_r2_a = df_a["r2"].mean()
    avg_r2_b = df_b["r2"].mean()
    
    total_improvement = (avg_mae_a - avg_mae_b) / avg_mae_a * 100 if avg_mae_a > 0 else 0
    r2_improvement = avg_r2_b - avg_r2_a
    wins_b = sum(1 for a, b in zip(df_a["mae"], df_b["mae"]) if b < a)
    
    logger.info("")
    logger.info(f"{'Model':<20} {'Avg MAE':<12} {'Std MAE':<12} {'Avg R²':<12}")
    logger.info("-" * 60)
    logger.info(f"{'Baseline':<20} {avg_mae_a:.4f}       {std_mae_a:.4f}       {avg_r2_a:.4f}")
    logger.info(f"{'+ Gas Feature':<20} {avg_mae_b:.4f}       {std_mae_b:.4f}       {avg_r2_b:.4f}")
    logger.info("")
    logger.info(f"MAE Improvement: {total_improvement:+.1f}%")
    logger.info(f"R² Improvement:  {r2_improvement:+.4f} ({r2_improvement*100:+.2f} pp)")
    logger.info(f"Gas Wins: {wins_b}/{N_ITERATIONS} iterations ({wins_b/N_ITERATIONS*100:.0f}%)")
    
    # Statistical test
    from scipy import stats
    t_stat, p_value = stats.ttest_rel(df_a["mae"], df_b["mae"])
    
    logger.info("")
    logger.info(f"Paired t-test: t={t_stat:.3f}, p-value={p_value:.4f}")
    
    if p_value < 0.05 and avg_mae_b < avg_mae_a:
        logger.info("✅ Difference is STATISTICALLY SIGNIFICANT (p < 0.05)")
    elif avg_mae_b < avg_mae_a:
        logger.info("⚠️ Gas feature improves but NOT statistically significant")
    else:
        logger.info("❌ Gas feature does NOT improve the model")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ Walk-Forward Validation Complete")
    logger.info("=" * 70)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    logger.info("=" * 70)
    logger.info("Walk-Forward: Prophet + Gas (Production Config, Hourly Data)")
    logger.info("=" * 70)
    
    gas_df = load_gas_data_hourly()
    price_df = load_pvpc_hourly()
    
    # Add features
    price_df = add_prophet_features(price_df)
    
    # Merge on hour
    merged = pd.merge(price_df, gas_df[["ds", "gas_gen", "gas_gen_scaled"]], on="ds", how="inner")
    merged = merged.sort_values("ds").reset_index(drop=True)
    
    logger.info(f"📊 Merged dataset: {len(merged)} hourly samples")
    logger.info(f"   Range: {merged['ds'].min()} → {merged['ds'].max()}")
    
    walk_forward_validation(merged)
    
    return 0

if __name__ == "__main__":
    exit(main())
