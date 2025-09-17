# Quick Start: Datos Históricos con Sistema SIAR

## Cuándo Usar Esta Guía

Usa esta alternativa cuando:
- ❌ La API AEMET histórica falla
- ❌ `historical_weather_records < 1000` en `/init/status`
- ❌ El sistema reporta `weather_data: insufficient`

## Pasos de Implementación

### 1. Verificar el Problema
```bash
# Comprobar estado actual
curl -s "http://localhost:8000/init/status" | jq '.status.historical_weather_records'

# Si devuelve < 1000, necesitas esta solución
```

### 2. Obtener Datos de Sistema SIAR

#### Opción A: Datos Completos (Recomendado)
1. Visitar [Sistema SIAR](https://Sistema SIAR/Aemethistorico/Descargahistorico.html)
2. Descargar base de datos completa (3.50€)
3. Extraer CSV para estación 5279X (Linares, Jaén)

#### Opción B: Datos Sintéticos (Testing)
El sistema puede generar datos de prueba automáticamente.

### 3. Ejecutar ETL

#### Método Simple (Datos Sintéticos)
```bash
# Ejecutar ETL con datos de prueba
curl -X POST "http://localhost:8000/init/datosclima/etl?station_id=5279X&years=3"
```

#### Método Completo (Datos Reales)
```bash
# 1. Copiar CSV al contenedor
docker cp linares_5279X.csv chocolate_factory_brain:/tmp/weather_data.csv

# 2. Ejecutar ETL personalizado
docker exec chocolate_factory_brain python -c "
from services.datosclima_etl import DatosClimaETL
import asyncio

async def run_etl():
    etl = DatosClimaETL()
    stats = await etl.process_csv_file('/tmp/weather_data.csv', '5279X')
    print(f'Processed: {stats.successful_writes} records')

asyncio.run(run_etl())
"
```

### 4. Verificar Resultados

```bash
# Verificar crecimiento de datos
du -sh docker/services/influxdb/data/engine/

# Verificar conteos actualizados
curl -s "http://localhost:8000/init/status" | jq '.status.historical_weather_records'

# Verificación completa
curl -s "http://localhost:8000/influxdb/verify?hours=8760" | jq '.total_records'
```

### 5. Validación Final

```bash
# Ejecutar script de verificación
./data_verification.sh

# Resultado esperado:
# ✅ Weather Data: Substantial (1000+ records)
# ✅ Data ingestion working - Ready for MLflow
```

## Ejemplo de Ejecución Exitosa

```bash
$ curl -X POST "http://localhost:8000/init/datosclima/etl?station_id=5279X&years=3"

{
  "🏭": "TFM Chocolate Factory - DatosClima ETL",
  "status": "✅ ETL Completed",
  "data_source": "Sistema SIAR",
  "station": "5279X - Linares, Jaén",
  "processing_results": {
    "total_records": 1000,
    "successful_writes": 1000,
    "failed_writes": 0,
    "validation_errors": 0,
    "success_rate": "100.0%"
  },
  "next_steps": {
    "verify_data": "GET /init/status",
    "check_influxdb": "GET /influxdb/verify",
    "proceed_mlflow": "Data ready for ML models"
  }
}
```

## Resolución de Problemas

### Error: "Not Found" en ETL
```bash
# Verificar que el contenedor tiene el servicio
docker exec chocolate_factory_brain ls -la /app/services/datosclima_etl.py

# Si no existe, copiarlo
docker cp src/fastapi-app/services/datosclima_etl.py chocolate_factory_brain:/app/services/
```

### Error: "Permission Denied"
```bash
# El ETL usa /tmp/ que tiene permisos públicos
# No requiere acción adicional
```

### Error: "Type Conflict" en InfluxDB
```bash
# El ETL maneja tipos automáticamente
# Verificar que todos los campos son float()
```

## Datos Resultantes

### Antes del ETL
- **Weather Records**: ~80
- **Data Size**: 30MB
- **Status**: ❌ Insufficient for MLflow

### Después del ETL
- **Weather Records**: 1000+
- **Data Size**: 31MB+
- **Status**: ✅ Ready for MLflow

### Estructura de Datos Ingresados
```
Measurement: weather_data
Station: 5279X (Linares, Jaén)
Fields: temperature, humidity, pressure, wind, radiation
Period: 3-5 años históricos
Source: DatosClima_ETL
```

## Integración con Flujo Normal

Una vez completado el ETL:

1. ✅ **Continuar con MLflow**: Los datos son suficientes para modelos
2. ✅ **Usar predicciones**: El sistema tiene historical weather + REE
3. ✅ **Monitoreo normal**: El sistema operará con datos híbridos

## Ventajas de Esta Solución

- 🚀 **Rápido**: 2-5 minutos vs 48h de API fallida
- 💰 **Económico**: 3.50€ vs días de desarrollo
- 🔒 **Confiable**: CSV estático vs API inestable
- 📊 **Completo**: Hasta 100 años de datos disponibles
- 🔧 **Reutilizable**: ETL modular para otros proyectos

Esta solución garantiza que tu TFM tenga datos meteorológicos históricos suficientes para demostrar las capacidades de ML y análisis de correlaciones energía-clima.