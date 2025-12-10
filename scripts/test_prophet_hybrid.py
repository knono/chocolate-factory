"""
Test 1: Modelo Híbrido Prophet + Corrección D-1
================================================
Prophet predice la forma de la curva, corregimos con el nivel de ayer.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

async def test_hybrid_correction():
    from services.data_ingestion import DataIngestionService
    from services.price_forecasting_service import PriceForecastingService
    
    print("="*60)
    print("TEST 1: Prophet + Corrección D-1")
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
    print(f"   Rango: {df_real['timestamp'].min()} → {df_real['timestamp'].max()}")
    
    # 2. Separar: ayer (para calibrar) y hoy (para validar)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    
    df_yesterday = df_real[(df_real['timestamp'] >= yesterday_start) & (df_real['timestamp'] < today_start)]
    df_today = df_real[df_real['timestamp'] >= today_start]
    
    print(f"\n📅 Ayer: {len(df_yesterday)} registros, media={df_yesterday['price_real'].mean():.4f}")
    print(f"📅 Hoy: {len(df_today)} registros, media={df_today['price_real'].mean():.4f}")
    
    if len(df_today) < 5:
        print("❌ Insuficientes datos de hoy para validar")
        return
    
    # 3. Obtener predicciones Prophet para hoy
    forecast_service = PriceForecastingService()
    
    # Simular predicciones para las horas de hoy
    predictions_raw = await forecast_service.predict_hours(hours=24)
    
    df_prophet = pd.DataFrame(predictions_raw)
    df_prophet['timestamp'] = pd.to_datetime(df_prophet['timestamp'])
    
    # 4. Calcular corrección D-1
    yesterday_mean = df_yesterday['price_real'].mean()
    prophet_baseline = df_prophet['predicted_price'].mean()
    correction_factor = yesterday_mean - prophet_baseline
    
    print(f"\n🔧 Corrección D-1:")
    print(f"   Media ayer (real): {yesterday_mean:.4f}")
    print(f"   Media Prophet: {prophet_baseline:.4f}")
    print(f"   Factor corrección: {correction_factor:+.4f}")
    
    # 5. Aplicar corrección
    df_prophet['predicted_corrected'] = df_prophet['predicted_price'] + correction_factor
    
    # 6. Merge con datos reales de hoy
    df_today['hour'] = df_today['timestamp'].dt.hour
    df_prophet['hour'] = df_prophet['timestamp'].dt.hour
    
    df_merged = pd.merge(df_today, df_prophet[['hour', 'predicted_price', 'predicted_corrected']], 
                         on='hour', how='inner')
    
    print(f"\n📊 Comparación ({len(df_merged)} horas):")
    print("-"*60)
    
    # 7. Calcular métricas
    y_true = df_merged['price_real'].values
    y_pred_original = df_merged['predicted_price'].values
    y_pred_corrected = df_merged['predicted_corrected'].values
    
    mae_original = mean_absolute_error(y_true, y_pred_original)
    mae_corrected = mean_absolute_error(y_true, y_pred_corrected)
    
    r2_original = r2_score(y_true, y_pred_original)
    r2_corrected = r2_score(y_true, y_pred_corrected)
    
    print(f"\n📈 RESULTADOS:")
    print(f"   {'Métrica':<20} {'Original':<15} {'Corregido':<15} {'Mejora':<10}")
    print(f"   {'-'*60}")
    print(f"   {'MAE (€/kWh)':<20} {mae_original:<15.4f} {mae_corrected:<15.4f} {((mae_original-mae_corrected)/mae_original*100):+.1f}%")
    print(f"   {'R²':<20} {r2_original:<15.4f} {r2_corrected:<15.4f} {(r2_corrected-r2_original):+.4f}")
    
    # Mostrar algunas predicciones
    print(f"\n📋 Detalle por hora:")
    print(f"   {'Hora':<6} {'Real':<10} {'Prophet':<10} {'Corregido':<10} {'Error Orig':<12} {'Error Corr':<12}")
    for _, row in df_merged.iterrows():
        err_orig = row['predicted_price'] - row['price_real']
        err_corr = row['predicted_corrected'] - row['price_real']
        print(f"   {int(row['hour']):02d}:00  {row['price_real']:<10.4f} {row['predicted_price']:<10.4f} {row['predicted_corrected']:<10.4f} {err_orig:<+12.4f} {err_corr:<+12.4f}")
    
    return {
        'mae_original': mae_original,
        'mae_corrected': mae_corrected,
        'r2_original': r2_original,
        'r2_corrected': r2_corrected,
        'correction_factor': correction_factor,
        'improvement_mae': (mae_original - mae_corrected) / mae_original * 100
    }

if __name__ == "__main__":
    result = asyncio.run(test_hybrid_correction())
    if result:
        print(f"\n{'='*60}")
        print(f"✅ TEST 1 COMPLETADO")
        print(f"   Mejora MAE: {result['improvement_mae']:.1f}%")
        print(f"{'='*60}")
