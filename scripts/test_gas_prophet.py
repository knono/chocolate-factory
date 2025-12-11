#!/usr/bin/env python3
"""
Test Prophet Model with Gas Generation Feature
==============================================

Compara el modelo Prophet actual (sin gas) vs modelo con gas_gen_mwh
como feature adicional.

Requisitos:
- scripts/data/gas_generation_36m.csv (ejecutar download_gas_historical.py)
- Acceso a InfluxDB para precios PVPC

Uso (inside Docker):
    python3 /app/scripts/test_gas_prophet.py

Uso (host con venv):
    python3 scripts/test_gas_prophet.py

Author: Gemini
Date: December 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add app path for Docker execution
sys.path.insert(0, "/app")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# PATHS
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAS_CSV = os.path.join(SCRIPT_DIR, "data", "gas_generation_36m.csv")

# ==============================================================================
# STEP 1: Load Gas Generation Data
# ==============================================================================
def load_gas_data() -> pd.DataFrame:
    """Load gas generation CSV."""
    logger.info(f"📥 Loading gas data from {GAS_CSV}")
    
    if not os.path.exists(GAS_CSV):
        raise FileNotFoundError(f"Gas CSV not found: {GAS_CSV}\nRun: python3 scripts/download_gas_historical.py")
    
    df = pd.read_csv(GAS_CSV, parse_dates=["date"])
    df = df.rename(columns={"date": "ds", "gas_gen_mwh": "gas_gen"})
    
    # Normalize gas generation (scale to 0-1 range for Prophet)
    df["gas_gen_scaled"] = (df["gas_gen"] - df["gas_gen"].min()) / (df["gas_gen"].max() - df["gas_gen"].min())
    
    logger.info(f"✅ Loaded {len(df)} gas records ({df['ds'].min().date()} to {df['ds'].max().date()})")
    
    return df[["ds", "gas_gen", "gas_gen_scaled"]]

# ==============================================================================
# STEP 2: Load PVPC Prices from InfluxDB
# ==============================================================================
def load_pvpc_prices() -> pd.DataFrame:
    """Load PVPC prices from InfluxDB."""
    logger.info("📥 Loading PVPC prices from InfluxDB...")
    
    try:
        from infrastructure.influxdb import get_influxdb_client
        from core.config import settings
        
        influx = get_influxdb_client()
        
        # Query 36 months of prices, aggregated daily
        query = '''
        from(bucket: "energy_data")
          |> range(start: -36mo)
          |> filter(fn: (r) => r["_measurement"] == "energy_prices")
          |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
          |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
          |> yield(name: "daily_avg")
        '''
        
        results = influx.query(query)
        
        if not results:
            raise Exception("No PVPC data found in InfluxDB")
        
        # Convert to DataFrame
        records = []
        for record in results:
            records.append({
                "ds": record["time"].replace(tzinfo=None).date(),
                "y": record["value"]
            })
        
        df = pd.DataFrame(records)
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.groupby("ds")["y"].mean().reset_index()
        
        logger.info(f"✅ Loaded {len(df)} price records")
        
        return df
        
    except ImportError:
        logger.warning("⚠️ Cannot import InfluxDB client (not in Docker?)")
        logger.info("   Using synthetic price data for testing")
        return generate_synthetic_prices()

def generate_synthetic_prices() -> pd.DataFrame:
    """Generate synthetic price data for testing outside Docker."""
    logger.info("🔧 Generating synthetic PVPC prices...")
    
    # Create dates matching gas data range
    dates = pd.date_range(start="2022-12-01", end="2025-12-11", freq="D")
    
    # Synthetic prices with seasonality
    np.random.seed(42)
    base = 0.15  # Base price €/kWh
    seasonal = 0.05 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)  # Yearly cycle
    noise = np.random.normal(0, 0.03, len(dates))
    
    prices = base + seasonal + noise
    prices = np.clip(prices, 0.05, 0.40)  # Realistic bounds
    
    df = pd.DataFrame({"ds": dates, "y": prices})
    logger.info(f"✅ Generated {len(df)} synthetic price records")
    
    return df

# ==============================================================================
# STEP 3: Calculate Correlation
# ==============================================================================
def calculate_correlation(gas_df: pd.DataFrame, price_df: pd.DataFrame) -> float:
    """Calculate Pearson correlation between gas generation and prices."""
    logger.info("📊 Calculating correlation...")
    
    # Merge on date
    merged = pd.merge(gas_df, price_df, on="ds", how="inner")
    
    if len(merged) < 30:
        logger.warning(f"⚠️ Only {len(merged)} overlapping records")
        return 0.0
    
    correlation = merged["gas_gen"].corr(merged["y"])
    
    logger.info(f"✅ Correlation (Gas vs Price): r = {correlation:.4f}")
    logger.info(f"   Overlapping records: {len(merged)}")
    
    return correlation

# ==============================================================================
# STEP 4: Train Prophet Models (with and without gas)
# ==============================================================================
def train_and_compare_models(gas_df: pd.DataFrame, price_df: pd.DataFrame):
    """Train Prophet with and without gas feature, compare metrics."""
    logger.info("\n" + "=" * 60)
    logger.info("🔬 Training Prophet Models (A/B Comparison)")
    logger.info("=" * 60)
    
    try:
        from prophet import Prophet
    except ImportError:
        logger.error("❌ Prophet not installed. Run inside Docker or install prophet.")
        return
    
    # Merge data
    merged = pd.merge(gas_df, price_df, on="ds", how="inner")
    merged = merged.sort_values("ds").reset_index(drop=True)
    
    logger.info(f"📊 Total samples: {len(merged)}")
    
    # Train/Test split (last 30 days as test)
    split_date = merged["ds"].max() - timedelta(days=30)
    train = merged[merged["ds"] <= split_date].copy()
    test = merged[merged["ds"] > split_date].copy()
    
    logger.info(f"   Train: {len(train)} samples (up to {split_date.date()})")
    logger.info(f"   Test: {len(test)} samples")
    
    if len(test) < 7:
        logger.warning("⚠️ Not enough test data, using last 14 days")
        split_date = merged["ds"].max() - timedelta(days=14)
        train = merged[merged["ds"] <= split_date].copy()
        test = merged[merged["ds"] > split_date].copy()
    
    # ------------------------------------------------------------------
    # Model A: Baseline (no gas)
    # ------------------------------------------------------------------
    logger.info("\n📈 Model A: Baseline Prophet (no gas)...")
    
    model_a = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.08
    )
    
    model_a.fit(train[["ds", "y"]])
    
    forecast_a = model_a.predict(test[["ds"]])
    
    mae_a = np.mean(np.abs(test["y"].values - forecast_a["yhat"].values))
    rmse_a = np.sqrt(np.mean((test["y"].values - forecast_a["yhat"].values) ** 2))
    
    # R² calculation
    ss_res_a = np.sum((test["y"].values - forecast_a["yhat"].values) ** 2)
    ss_tot_a = np.sum((test["y"].values - test["y"].mean()) ** 2)
    r2_a = 1 - (ss_res_a / ss_tot_a) if ss_tot_a > 0 else 0
    
    logger.info(f"   MAE:  {mae_a:.6f} €/kWh")
    logger.info(f"   RMSE: {rmse_a:.6f} €/kWh")
    logger.info(f"   R²:   {r2_a:.4f}")
    
    # ------------------------------------------------------------------
    # Model B: With Gas Regressor
    # ------------------------------------------------------------------
    logger.info("\n📈 Model B: Prophet + Gas Feature...")
    
    model_b = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.08
    )
    
    # Add gas as regressor
    model_b.add_regressor("gas_gen_scaled")
    
    model_b.fit(train[["ds", "y", "gas_gen_scaled"]])
    
    test_b = test[["ds", "gas_gen_scaled"]].copy()
    forecast_b = model_b.predict(test_b)
    
    mae_b = np.mean(np.abs(test["y"].values - forecast_b["yhat"].values))
    rmse_b = np.sqrt(np.mean((test["y"].values - forecast_b["yhat"].values) ** 2))
    
    ss_res_b = np.sum((test["y"].values - forecast_b["yhat"].values) ** 2)
    ss_tot_b = np.sum((test["y"].values - test["y"].mean()) ** 2)
    r2_b = 1 - (ss_res_b / ss_tot_b) if ss_tot_b > 0 else 0
    
    logger.info(f"   MAE:  {mae_b:.6f} €/kWh")
    logger.info(f"   RMSE: {rmse_b:.6f} €/kWh")
    logger.info(f"   R²:   {r2_b:.4f}")
    
    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("📊 COMPARISON RESULTS")
    logger.info("=" * 60)
    
    mae_improvement = (mae_a - mae_b) / mae_a * 100
    r2_improvement = (r2_b - r2_a) * 100  # In percentage points
    
    logger.info(f"                    Baseline    + Gas      Change")
    logger.info(f"MAE (€/kWh):        {mae_a:.6f}   {mae_b:.6f}   {mae_improvement:+.1f}%")
    logger.info(f"R²:                 {r2_a:.4f}      {r2_b:.4f}      {r2_improvement:+.1f} pp")
    
    if mae_b < mae_a:
        logger.info("\n✅ Gas feature IMPROVES the model!")
        logger.info(f"   Recommendation: Add gas generation as regressor")
    else:
        logger.info("\n⚠️ Gas feature does NOT improve the model")
        logger.info(f"   Recommendation: Do not add gas feature")

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    logger.info("=" * 60)
    logger.info("Test: Gas Generation as Prophet Feature")
    logger.info("=" * 60)
    
    # Step 1: Load gas data
    try:
        gas_df = load_gas_data()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    
    # Step 2: Load PVPC prices
    price_df = load_pvpc_prices()
    
    # Step 3: Calculate correlation
    correlation = calculate_correlation(gas_df, price_df)
    
    if abs(correlation) < 0.1:
        logger.warning(f"⚠️ Very weak correlation ({correlation:.4f})")
        logger.info("   Gas generation may not be useful as a feature")
    elif abs(correlation) < 0.3:
        logger.info(f"ℹ️ Weak correlation ({correlation:.4f})")
        logger.info("   Gas generation might provide marginal improvement")
    else:
        logger.info(f"✅ Moderate/Strong correlation ({correlation:.4f})")
        logger.info("   Gas generation is a good candidate feature")
    
    # Step 4: Train and compare models
    train_and_compare_models(gas_df, price_df)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Test Complete")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
