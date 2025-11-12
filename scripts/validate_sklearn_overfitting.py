#!/usr/bin/env python3
"""
Sklearn Models Overfitting Validation
======================================

Entrena modelos sklearn y valida overfitting con:
- R² train vs test
- 5-fold cross-validation
- Feature importance
"""

import asyncio
import sys
import os
sys.path.insert(0, '/home/nono/Downloads/chocolate-factory/src/fastapi-app')
os.environ.setdefault('INFLUXDB_URL', 'http://localhost:8086')
os.environ.setdefault('INFLUXDB_TOKEN', 'chocolate-factory-influxdb-token')
os.environ.setdefault('INFLUXDB_ORG', 'chocolate-factory')
os.environ.setdefault('INFLUXDB_BUCKET', 'energy_data')

from domain.ml.direct_ml import DirectMLService


async def main():
    print("=" * 80)
    print("SKLEARN MODELS - OVERFITTING VALIDATION")
    print("=" * 80)
    print()

    # Train models with validation
    print("🔥 Training models with cross-validation...")
    print()

    service = DirectMLService()
    results = await service.train_models()

    if not results.get('success'):
        print(f"❌ Training failed: {results.get('error')}")
        return

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE - CHECK LOGS ABOVE FOR:")
    print("=" * 80)
    print("  1. R² Train vs Test (overfitting if diff > 0.10)")
    print("  2. Cross-validation scores (stability check)")
    print("  3. Feature importance (top predictors)")
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    # Energy model summary
    if 'energy_model' in results:
        em = results['energy_model']
        print()
        print("📊 ENERGY MODEL (RandomForestRegressor)")
        r2_train = em.get('r2_train', 0)
        r2_test = em.get('r2_test', 0)
        r2_diff = em.get('r2_diff', 0)
        cv_mean = em.get('cv_r2_mean', 0)
        cv_std = em.get('cv_r2_std', 0)

        print(f"   R² Train:  {r2_train:.4f}")
        print(f"   R² Test:   {r2_test:.4f}")
        print(f"   R² Diff:   {r2_diff:.4f}")
        print(f"   CV Mean:   {cv_mean:.4f} ± {cv_std:.4f}")

        overfitting = em.get('overfitting_detected', False)
        status = "⚠️  OVERFITTING DETECTED" if overfitting else "✅ No overfitting"
        print(f"   Status:    {status}")

    # Production model summary
    if 'production_model' in results:
        pm = results['production_model']
        print()
        print("📊 PRODUCTION MODEL (RandomForestClassifier)")
        acc_train = pm.get('accuracy_train', 0)
        acc_test = pm.get('accuracy_test', 0)
        acc_diff = pm.get('accuracy_diff', 0)
        cv_mean = pm.get('cv_accuracy_mean', 0)
        cv_std = pm.get('cv_accuracy_std', 0)

        print(f"   Acc Train: {acc_train:.4f}")
        print(f"   Acc Test:  {acc_test:.4f}")
        print(f"   Acc Diff:  {acc_diff:.4f}")
        print(f"   CV Mean:   {cv_mean:.4f} ± {cv_std:.4f}")

        overfitting = pm.get('overfitting_detected', False)
        status = "⚠️  OVERFITTING DETECTED" if overfitting else "✅ No overfitting"
        print(f"   Status:    {status}")

    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    energy_ok = not results.get('energy_model', {}).get('overfitting_detected', False)
    prod_ok = not results.get('production_model', {}).get('overfitting_detected', False)

    if energy_ok and prod_ok:
        print("✅ BOTH MODELS: No overfitting detected - models generalize well")
    elif energy_ok or prod_ok:
        print("⚠️  PARTIAL OVERFITTING: One model shows overfitting")
    else:
        print("❌ CRITICAL: Both models show overfitting - increase regularization")

    print()


if __name__ == "__main__":
    asyncio.run(main())
