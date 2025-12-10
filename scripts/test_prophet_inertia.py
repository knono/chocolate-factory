"""
Test 2: Feature de Inercia de Precios
=====================================
Usar precio real de las últimas horas como "ancla" para corregir Prophet.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

async def test_inertia_correction():
    from services.data_ingestion import DataIngestionService
    from services.price_forecasting_service import PriceForecastingService
    
    print("="*60)
    print("TEST 2: Prophet + Inercia (últimas N horas)")
    print("="*60)
    
    # 1. Obtener datos reales de los últimos 3 días
    async with DataIngestionService() as service:
        query = '''
            from(bucket: "energy_data")
            |> range(start: -3d)
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
        
    print(f"📊 Datos reales: {len(df_real)} registros")
    
    # 2. Separar datos
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    df_today = df_real[df_real['timestamp'] >= today_start].copy()
    
    if len(df_today) < 5:
        print("❌ Insuficientes datos de hoy para validar")
        return
    
    # 3. Obtener predicciones Prophet
    forecast_service = PriceForecastingService()
    predictions_raw = await forecast_service.predict_hours(hours=24)
    df_prophet = pd.DataFrame(predictions_raw)
    df_prophet['timestamp'] = pd.to_datetime(df_prophet['timestamp'])
    df_prophet['hour'] = df_prophet['timestamp'].dt.hour
    
    # 4. Probar diferentes ventanas de inercia
    windows = [3, 6, 12]
    results = {}
    
    for window in windows:
        print(f"\n🔧 Probando ventana de {window} horas...")
        
        df_test = df_today.copy()
        df_test['hour'] = df_test['timestamp'].dt.hour
        
        corrections = []
        
        for idx, row in df_test.iterrows():
            current_hour = row['hour']
            current_ts = row['timestamp']
            
            # Obtener últimas N horas reales
            past_window = df_real[
                (df_real['timestamp'] < current_ts) & 
                (df_real['timestamp'] >= current_ts - timedelta(hours=window))
            ]
            
            if len(past_window) < 2:
                # Fallback a media global
                past_mean = df_real['price_real'].mean()
            else:
                past_mean = past_window['price_real'].mean()
            
            # Obtener predicción Prophet para esa hora (basado en patrón histórico)
            # Buscar predicción con misma hora
            prophet_pred = df_prophet[df_prophet['hour'] == current_hour]['predicted_price'].values
            if len(prophet_pred) == 0:
                prophet_pred = df_prophet['predicted_price'].mean()
            else:
                prophet_pred = prophet_pred[0]
            
            # Corrección adaptativa: Prophet + (nivel_reciente - nivel_prophet_histórico)
            prophet_historical_mean = df_prophet['predicted_price'].mean()
            correction = past_mean - prophet_historical_mean
            
            corrected_price = prophet_pred + correction
            
            corrections.append({
                'hour': current_hour,
                'price_real': row['price_real'],
                'prophet_original': prophet_pred,
                'past_mean': past_mean,
                'correction': correction,
                'prophet_corrected': corrected_price
            })
        
        df_corrections = pd.DataFrame(corrections)
        
        # Calcular métricas
        y_true = df_corrections['price_real'].values
        y_pred_original = df_corrections['prophet_original'].values
        y_pred_corrected = df_corrections['prophet_corrected'].values
        
        mae_original = mean_absolute_error(y_true, y_pred_original)
        mae_corrected = mean_absolute_error(y_true, y_pred_corrected)
        
        r2_original = r2_score(y_true, y_pred_original)
        r2_corrected = r2_score(y_true, y_pred_corrected)
        
        improvement = (mae_original - mae_corrected) / mae_original * 100
        
        results[window] = {
            'mae_original': mae_original,
            'mae_corrected': mae_corrected,
            'r2_original': r2_original,
            'r2_corrected': r2_corrected,
            'improvement': improvement,
            'df': df_corrections
        }
        
        print(f"   MAE Original: {mae_original:.4f}")
        print(f"   MAE Corregido: {mae_corrected:.4f}")
        print(f"   Mejora: {improvement:+.1f}%")
        print(f"   R² Original: {r2_original:.4f}")
        print(f"   R² Corregido: {r2_corrected:.4f}")
    
    # 5. Encontrar mejor ventana
    best_window = max(results.keys(), key=lambda w: results[w]['improvement'])
    best_result = results[best_window]
    
    print(f"\n{'='*60}")
    print(f"📊 MEJOR RESULTADO: Ventana de {best_window} horas")
    print(f"{'='*60}")
    print(f"   MAE: {best_result['mae_original']:.4f} → {best_result['mae_corrected']:.4f} ({best_result['improvement']:+.1f}%)")
    print(f"   R²:  {best_result['r2_original']:.4f} → {best_result['r2_corrected']:.4f}")
    
    # Mostrar detalle
    print(f"\n📋 Detalle por hora (ventana {best_window}h):")
    print(f"   {'Hora':<6} {'Real':<10} {'Prophet':<10} {'Corregido':<10} {'Err Orig':<10} {'Err Corr':<10}")
    for _, row in best_result['df'].iterrows():
        err_orig = row['prophet_original'] - row['price_real']
        err_corr = row['prophet_corrected'] - row['price_real']
        print(f"   {int(row['hour']):02d}:00  {row['price_real']:<10.4f} {row['prophet_original']:<10.4f} {row['prophet_corrected']:<10.4f} {err_orig:<+10.4f} {err_corr:<+10.4f}")
    
    return best_result, best_window

if __name__ == "__main__":
    result, window = asyncio.run(test_inertia_correction())
    if result:
        print(f"\n{'='*60}")
        print(f"✅ TEST 2 COMPLETADO")
        print(f"   Mejor ventana: {window} horas")
        print(f"   Mejora MAE: {result['improvement']:.1f}%")
        print(f"{'='*60}")
