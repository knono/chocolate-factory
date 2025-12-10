"""
Validación Walk-Forward: Prophet + Inercia 3h
=============================================
Simula predicción día a día para validar que no hay data leakage.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sklearn.metrics import mean_absolute_error, r2_score

async def walk_forward_validation():
    from services.data_ingestion import DataIngestionService
    from services.price_forecasting_service import PriceForecastingService
    
    print("="*60)
    print("WALK-FORWARD VALIDATION: Prophet + Inercia 3h")
    print("="*60)
    
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
    
    # 2. Obtener predicciones Prophet (patrón base por hora)
    forecast_service = PriceForecastingService()
    predictions_raw = await forecast_service.predict_hours(hours=168)
    df_prophet = pd.DataFrame(predictions_raw)
    df_prophet['timestamp'] = pd.to_datetime(df_prophet['timestamp'])
    df_prophet['hour'] = df_prophet['timestamp'].dt.hour
    
    # Crear lookup de predicción Prophet por hora
    prophet_by_hour = df_prophet.groupby('hour')['predicted_price'].mean().to_dict()
    
    # 3. Walk-forward: para cada hora, predecir usando solo datos pasados
    window = 3  # horas
    all_predictions = []
    
    dates = sorted(df_real['date'].unique())[1:]  # Saltar primer día (necesita historia)
    
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
            prophet_pred = prophet_by_hour.get(current_hour, df_prophet['predicted_price'].mean())
            prophet_mean = np.mean(list(prophet_by_hour.values()))
            
            # Corrección
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
    
    # 4. Calcular métricas globales
    y_true = df_results['price_real'].values
    y_pred_orig = df_results['prophet_original'].values
    y_pred_corr = df_results['prophet_corrected'].values
    
    mae_orig = mean_absolute_error(y_true, y_pred_orig)
    mae_corr = mean_absolute_error(y_true, y_pred_corr)
    r2_orig = r2_score(y_true, y_pred_orig)
    r2_corr = r2_score(y_true, y_pred_corr)
    
    improvement = (mae_orig - mae_corr) / mae_orig * 100
    
    print(f"\n{'='*60}")
    print(f"RESULTADOS WALK-FORWARD ({len(df_results)} predicciones)")
    print(f"{'='*60}")
    print(f"{'Métrica':<15} {'Original':<12} {'Corregido':<12} {'Cambio':<10}")
    print(f"{'-'*50}")
    print(f"{'MAE':<15} {mae_orig:<12.4f} {mae_corr:<12.4f} {improvement:+.1f}%")
    print(f"{'R²':<15} {r2_orig:<12.4f} {r2_corr:<12.4f} {r2_corr-r2_orig:+.4f}")
    
    # 5. Métricas por día
    print(f"\nPor día:")
    df_results['date'] = pd.to_datetime(df_results['timestamp']).dt.date
    for date in sorted(df_results['date'].unique()):
        df_day = df_results[df_results['date'] == date]
        mae_d_orig = mean_absolute_error(df_day['price_real'], df_day['prophet_original'])
        mae_d_corr = mean_absolute_error(df_day['price_real'], df_day['prophet_corrected'])
        imp_d = (mae_d_orig - mae_d_corr) / mae_d_orig * 100
        print(f"  {date}: MAE {mae_d_orig:.4f} → {mae_d_corr:.4f} ({imp_d:+.1f}%)")
    
    return {
        'n_predictions': len(df_results),
        'mae_original': mae_orig,
        'mae_corrected': mae_corr,
        'r2_original': r2_orig,
        'r2_corrected': r2_corr,
        'improvement_pct': improvement
    }

if __name__ == "__main__":
    result = asyncio.run(walk_forward_validation())
    print(f"\n{'='*60}")
    if result['improvement_pct'] > 0:
        print(f"VALIDACIÓN EXITOSA: +{result['improvement_pct']:.1f}% mejora MAE")
    else:
        print(f"VALIDACIÓN FALLIDA: {result['improvement_pct']:.1f}% cambio MAE")
    print(f"{'='*60}")
