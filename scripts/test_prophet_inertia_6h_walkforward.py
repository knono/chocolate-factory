"""
Validación Walk-Forward: Prophet + Inercia 3h vs 6h
====================================================
Compara ambas ventanas de inercia para determinar la mejor configuración.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sklearn.metrics import mean_absolute_error, r2_score

async def walk_forward_validation_compare():
    from services.data_ingestion import DataIngestionService
    from services.price_forecasting_service import PriceForecastingService

    print("="*70)
    print("WALK-FORWARD VALIDATION: Prophet + Inercia 3h vs 6h")
    print("="*70)

    # 1. Obtener datos reales de los últimos 7 días
    async with DataIngestionService() as service:
        query = '''
            from(bucket: "energy_data")
            |> range(start: -7d)
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
                    'price_real': record.get_value()
                })

        df_real = pd.DataFrame(data)
        df_real['timestamp'] = pd.to_datetime(df_real['timestamp'])
        df_real = df_real.sort_values('timestamp').drop_duplicates('timestamp')
        df_real['hour'] = df_real['timestamp'].dt.hour
        df_real['date'] = df_real['timestamp'].dt.date

    print(f"Datos: {len(df_real)} registros, {df_real['date'].nunique()} días")
    print(f"Rango: {df_real['timestamp'].min()} → {df_real['timestamp'].max()}")
    print(f"Precio medio: {df_real['price_real'].mean():.4f} €/kWh")
    print(f"Precio range: {df_real['price_real'].min():.4f} - {df_real['price_real'].max():.4f} €/kWh")

    # 2. Obtener predicciones Prophet (patrón base por hora)
    forecast_service = PriceForecastingService()
    predictions_raw = await forecast_service.predict_hours(hours=168)
    df_prophet = pd.DataFrame(predictions_raw)
    df_prophet['timestamp'] = pd.to_datetime(df_prophet['timestamp'])
    df_prophet['hour'] = df_prophet['timestamp'].dt.hour

    # Crear lookup de predicción Prophet por hora
    prophet_by_hour = df_prophet.groupby('hour')['predicted_price'].mean().to_dict()
    prophet_mean = np.mean(list(prophet_by_hour.values()))

    # 3. Walk-forward con múltiples ventanas
    windows = [3, 6, 9, 12]  # Probar diferentes ventanas
    results_by_window = {}

    dates = sorted(df_real['date'].unique())[1:]  # Saltar primer día

    for window in windows:
        all_predictions = []

        for test_date in dates:
            df_day = df_real[df_real['date'] == test_date].copy()

            for _, row in df_day.iterrows():
                current_ts = row['timestamp']
                current_hour = row['hour']

                # Solo usar datos ANTERIORES (walk-forward)
                past_data = df_real[
                    (df_real['timestamp'] < current_ts) &
                    (df_real['timestamp'] >= current_ts - timedelta(hours=window))
                ]

                if len(past_data) < 2:
                    continue

                past_mean = past_data['price_real'].mean()
                prophet_pred = prophet_by_hour.get(current_hour, prophet_mean)

                # Corrección por inercia
                correction = past_mean - prophet_mean
                corrected_pred = prophet_pred + correction

                all_predictions.append({
                    'timestamp': current_ts,
                    'hour': current_hour,
                    'price_real': row['price_real'],
                    'prophet_original': prophet_pred,
                    'prophet_corrected': corrected_pred,
                    'past_mean': past_mean,
                    'correction': correction
                })

        df_results = pd.DataFrame(all_predictions)

        if len(df_results) > 0:
            y_true = df_results['price_real'].values
            y_pred_orig = df_results['prophet_original'].values
            y_pred_corr = df_results['prophet_corrected'].values

            mae_orig = mean_absolute_error(y_true, y_pred_orig)
            mae_corr = mean_absolute_error(y_true, y_pred_corr)
            r2_orig = r2_score(y_true, y_pred_orig)
            r2_corr = r2_score(y_true, y_pred_corr)

            improvement = (mae_orig - mae_corr) / mae_orig * 100

            results_by_window[window] = {
                'n_predictions': len(df_results),
                'mae_original': mae_orig,
                'mae_corrected': mae_corr,
                'r2_original': r2_orig,
                'r2_corrected': r2_corr,
                'improvement_pct': improvement,
                'df': df_results
            }

    # 4. Mostrar comparación
    print(f"\n{'='*70}")
    print(f"COMPARACIÓN DE VENTANAS DE INERCIA")
    print(f"{'='*70}")
    print(f"{'Ventana':<10} {'N':<8} {'MAE Orig':<12} {'MAE Corr':<12} {'Mejora':<10} {'R² Corr':<10}")
    print(f"{'-'*65}")

    best_window = None
    best_mae = float('inf')

    for window, res in sorted(results_by_window.items()):
        print(f"{window}h{'':<7} {res['n_predictions']:<8} {res['mae_original']:<12.4f} {res['mae_corrected']:<12.4f} {res['improvement_pct']:+.1f}%{'':<5} {res['r2_corrected']:<10.4f}")
        if res['mae_corrected'] < best_mae:
            best_mae = res['mae_corrected']
            best_window = window

    print(f"\n{'='*70}")
    print(f"MEJOR VENTANA: {best_window}h (MAE={best_mae:.4f})")
    print(f"{'='*70}")

    # 5. Detalles de la mejor ventana por día
    if best_window in results_by_window:
        print(f"\nDetalle por día (ventana {best_window}h):")
        df_best = results_by_window[best_window]['df']
        df_best['date'] = pd.to_datetime(df_best['timestamp']).dt.date

        for date in sorted(df_best['date'].unique()):
            df_day = df_best[df_best['date'] == date]
            mae_d_orig = mean_absolute_error(df_day['price_real'], df_day['prophet_original'])
            mae_d_corr = mean_absolute_error(df_day['price_real'], df_day['prophet_corrected'])
            r2_d = r2_score(df_day['price_real'], df_day['prophet_corrected']) if len(df_day) > 1 else 0
            imp_d = (mae_d_orig - mae_d_corr) / mae_d_orig * 100 if mae_d_orig > 0 else 0
            print(f"  {date}: MAE {mae_d_orig:.4f} → {mae_d_corr:.4f} ({imp_d:+.1f}%), R²={r2_d:.3f}")

    # 6. Comparación 3h vs 6h específica
    print(f"\n{'='*70}")
    print(f"COMPARACIÓN DIRECTA: 3h vs 6h")
    print(f"{'='*70}")

    if 3 in results_by_window and 6 in results_by_window:
        r3 = results_by_window[3]
        r6 = results_by_window[6]

        mae_diff = r6['mae_corrected'] - r3['mae_corrected']
        r2_diff = r6['r2_corrected'] - r3['r2_corrected']

        print(f"Inercia 3h: MAE={r3['mae_corrected']:.4f}, R²={r3['r2_corrected']:.4f}")
        print(f"Inercia 6h: MAE={r6['mae_corrected']:.4f}, R²={r6['r2_corrected']:.4f}")
        print(f"Diferencia: MAE {mae_diff:+.4f}, R² {r2_diff:+.4f}")

        if r6['mae_corrected'] < r3['mae_corrected']:
            print(f"\n✅ RECOMENDACIÓN: Usar inercia 6h (MAE {abs(mae_diff):.4f} mejor)")
        else:
            print(f"\n⚠️ RECOMENDACIÓN: Mantener inercia 3h (MAE {abs(mae_diff):.4f} mejor)")

    return results_by_window

if __name__ == "__main__":
    result = asyncio.run(walk_forward_validation_compare())
    print(f"\n{'='*70}")
    print("VALIDACIÓN COMPLETADA")
    print(f"{'='*70}")
