#!/usr/bin/env python3
"""
Prophet Test: Ventana de Entrenamiento Óptima
==============================================
Compara: 36, 24, 18, 12, 9, 6 meses de datos de entrenamiento.
"""

import asyncio
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.metrics import mean_absolute_error, r2_score
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

# Suprimir logs
import logging
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)


async def run_comparison():
    from services.data_ingestion import DataIngestionService

    print("="*70)
    print("COMPARACIÓN VENTANAS DE ENTRENAMIENTO PROPHET")
    print("="*70)

    # 1. Extraer todos los datos disponibles (37 meses)
    async with DataIngestionService() as service:
        query = '''
            from(bucket: "energy_data")
            |> range(start: -37mo)
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
                    'ds': record.get_time(),
                    'y': record.get_value()
                })

    df_all = pd.DataFrame(data)
    df_all['ds'] = pd.to_datetime(df_all['ds']).dt.tz_localize(None)
    df_all = df_all.sort_values('ds').drop_duplicates('ds')

    print(f"📊 Datos totales: {len(df_all)} registros")
    print(f"   Rango: {df_all['ds'].min().date()} → {df_all['ds'].max().date()}")

    # Agregar features
    df_all['hour'] = df_all['ds'].dt.hour
    df_all['dayofweek'] = df_all['ds'].dt.dayofweek
    df_all['month'] = df_all['ds'].dt.month
    df_all['day'] = df_all['ds'].dt.day
    df_all['is_peak_hour'] = df_all['hour'].isin([10,11,12,13,18,19,20,21]).astype(int)
    df_all['is_valley_hour'] = df_all['hour'].isin([0,1,2,3,4,5,6,7]).astype(int)
    df_all['is_weekend'] = df_all['dayofweek'].isin([5,6]).astype(int)
    df_all['is_winter'] = df_all['month'].isin([12,1,2]).astype(int)
    df_all['is_summer'] = df_all['month'].isin([6,7,8]).astype(int)
    holidays_es = [(1,1),(1,6),(5,1),(8,15),(10,12),(11,1),(12,6),(12,25)]
    df_all['is_holiday'] = df_all.apply(lambda r: 1 if (r['month'], r['day']) in holidays_es else 0, axis=1)

    # Definir test set (últimos 7 días)
    max_date = df_all['ds'].max()
    test_start = max_date - timedelta(days=7)
    df_test = df_all[df_all['ds'] > test_start].copy()

    print(f"📊 Test set: {len(df_test)} registros (últimos 7 días)")

    # Ventanas a probar
    windows_months = [36, 24, 18, 12, 9, 6]
    results = []

    for months in windows_months:
        print(f"\n{'='*50}")
        print(f"VENTANA: {months} meses")
        print(f"{'='*50}")

        # Filtrar datos de entrenamiento
        train_end = test_start - timedelta(hours=1)
        train_start = train_end - timedelta(days=months * 30)
        df_train = df_all[(df_all['ds'] >= train_start) & (df_all['ds'] <= train_end)].copy()

        print(f"   Train: {len(df_train)} registros ({df_train['ds'].min().date()} → {df_train['ds'].max().date()})")

        if len(df_train) < 500:
            print(f"   ⚠️ Pocos datos, saltando...")
            continue

        try:
            # Entrenar Prophet
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.08,
                n_changepoints=25,
                seasonality_prior_scale=10.0,
                seasonality_mode='multiplicative',
            )
            model.add_seasonality(name='daily', period=1, fourier_order=8, prior_scale=12.0)
            model.add_seasonality(name='weekly', period=7, fourier_order=5, prior_scale=10.0)
            model.add_seasonality(name='yearly', period=365.25, fourier_order=8, prior_scale=8.0)
            model.add_regressor('is_peak_hour', prior_scale=0.10)
            model.add_regressor('is_valley_hour', prior_scale=0.08)
            model.add_regressor('is_weekend', prior_scale=0.06)
            model.add_regressor('is_holiday', prior_scale=0.08)
            model.add_regressor('is_winter', prior_scale=0.04)
            model.add_regressor('is_summer', prior_scale=0.04)

            model.fit(df_train)

            # Predecir test
            regressor_cols = ['ds', 'is_peak_hour', 'is_valley_hour', 'is_weekend',
                              'is_holiday', 'is_winter', 'is_summer']
            forecast = model.predict(df_test[regressor_cols].copy())

            # Métricas Prophet solo
            y_true = df_test['y'].values
            y_pred = forecast['yhat'].values
            mae_prophet = mean_absolute_error(y_true, y_pred)
            r2_prophet = r2_score(y_true, y_pred)

            # Métricas con corrección inercia 3h (walk-forward)
            prophet_by_hour = forecast.groupby(forecast['ds'].dt.hour)['yhat'].mean().to_dict()
            prophet_mean = forecast['yhat'].mean()

            predictions = []
            for idx, row in df_test.iterrows():
                current_ts = row['ds']
                current_hour = current_ts.hour

                # Últimas 3h (de datos reales, no de test)
                past_mask = (df_all['ds'] < current_ts) & (df_all['ds'] >= current_ts - timedelta(hours=3))
                past_data = df_all[past_mask]

                if len(past_data) < 2:
                    continue

                past_mean = past_data['y'].mean()
                prophet_pred = prophet_by_hour.get(current_hour, prophet_mean)
                correction = past_mean - prophet_mean
                corrected_pred = prophet_pred + correction

                predictions.append({
                    'real': row['y'],
                    'corrected': corrected_pred
                })

            df_pred = pd.DataFrame(predictions)
            mae_corrected = mean_absolute_error(df_pred['real'], df_pred['corrected'])
            r2_corrected = r2_score(df_pred['real'], df_pred['corrected'])
            improvement = (mae_prophet - mae_corrected) / mae_prophet * 100

            print(f"   Prophet solo:    MAE={mae_prophet:.4f}, R²={r2_prophet:.4f}")
            print(f"   Prophet+Inercia: MAE={mae_corrected:.4f}, R²={r2_corrected:.4f} ({improvement:+.1f}%)")

            results.append({
                'months': months,
                'train_samples': len(df_train),
                'mae_prophet': mae_prophet,
                'r2_prophet': r2_prophet,
                'mae_corrected': mae_corrected,
                'r2_corrected': r2_corrected,
                'improvement': improvement
            })

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Tabla final
    print("\n" + "="*70)
    print("TABLA COMPARATIVA FINAL")
    print("="*70)
    print(f"{'Ventana':<10} {'Train':<8} {'MAE Proph':<12} {'R² Proph':<10} {'MAE+Iner':<12} {'R²+Iner':<10}")
    print("-"*70)

    best = None
    for r in results:
        print(f"{r['months']}m{'':<7} {r['train_samples']:<8} {r['mae_prophet']:<12.4f} {r['r2_prophet']:<10.4f} {r['mae_corrected']:<12.4f} {r['r2_corrected']:<10.4f}")
        if best is None or r['mae_corrected'] < best['mae_corrected']:
            best = r

    if best:
        print("\n" + "="*70)
        print(f"MEJOR: {best['months']} meses (MAE+Inercia={best['mae_corrected']:.4f}, R²={best['r2_corrected']:.4f})")

        # Comparar con 36 meses
        actual_36 = next((r for r in results if r['months'] == 36), None)
        if actual_36 and best['months'] != 36:
            mae_diff = actual_36['mae_corrected'] - best['mae_corrected']
            r2_diff = best['r2_corrected'] - actual_36['r2_corrected']
            pct_better = mae_diff / actual_36['mae_corrected'] * 100
            print(f"\nvs 36 meses: MAE {mae_diff:+.4f} ({pct_better:+.1f}%), R² {r2_diff:+.4f}")

            if pct_better > 5:
                print(f"\n✅ RECOMENDACIÓN: Cambiar a {best['months']} meses")
            else:
                print(f"\n⚠️ Diferencia <5%, mantener 36 meses por estabilidad")
        print("="*70)

    return results

if __name__ == "__main__":
    asyncio.run(run_comparison())
