# Manual de Inicialización del Sistema TFM Chocolate Factory

## Tabla de Contenidos
1. [Instalación Inicial](#instalación-inicial)
2. [Verificación del Sistema](#verificación-del-sistema)
3. [Inicialización de Datos](#inicialización-de-datos)
4. [Monitoreo y Verificación](#monitoreo-y-verificación)
5. [Troubleshooting](#troubleshooting)

---

## Instalación Inicial

### 1. Levantar Contenedores
```bash
docker-compose up -d
```

### 2. Verificar Estado de Contenedores
```bash
docker ps
```
**Esperado**: 5 contenedores en estado `Up` y `healthy`
- `chocolate_factory_brain` (FastAPI - Puerto 8000)
- `chocolate_factory_storage` (InfluxDB - Puerto 8086)
- `chocolate_factory_mlops` (MLflow - Puerto 5000)
- `chocolate_factory_monitor` (Node-RED - Puerto 1880)
- `chocolate_factory_postgres` (PostgreSQL - Puerto 5432)

---

## Verificación del Sistema

### Verificar Servicios
```bash
# API Principal
curl http://localhost:8000/health

# InfluxDB
curl http://localhost:8086/health

# MLflow
curl http://localhost:5000/health
```

### Estado del Sistema
```bash
curl http://localhost:8000/init/status
```

**Respuesta esperada:**
```json
{
  "status": {
    "is_fully_initialized": true/false,
    "ree_initialized": true/false,
    "weather_initialized": true/false,
    "historical_ree_records": número_registros_ree,
    "historical_weather_records": número_registros_aemet,
    "recent_records_24h": registros_recientes,
    "estimated_missing_ree_records": registros_ree_faltantes,
    "estimated_missing_weather_records": registros_aemet_faltantes,
    "initialization_recommended": {
      "ree_data": true/false,
      "weather_data": true/false,
      "complete_historical": true/false
    }
  }
}
```

### Estado Específico de AEMET 🌤️ **NUEVO**
```bash
curl http://localhost:8000/init/aemet/status
```

**Respuesta esperada:**
```json
{
  "data_source": "AEMET (Agencia Estatal de Meteorología)",
  "station": "5279X - Linares, Jaén",
  "weather_data": {
    "total_weather_records": número_registros,
    "earliest_weather_date": "fecha_más_antigua",
    "latest_weather_date": "fecha_más_reciente",
    "expected_weather_records": 1095,
    "weather_completion_percentage": porcentaje,
    "needs_weather_historical_load": true/false
  },
  "recommendations": {
    "load_historical": true/false,
    "endpoint": "POST /init/aemet/historical-data?years_back=3"
  }
}
```

---

## Inicialización de Datos

### Opción 1: Inicialización Histórica Completa (Recomendada para MLflow)
```bash
curl -X POST http://localhost:8000/init/complete-historical-data
```
- ✅ **Incluye**: REE (precios eléctricos) + AEMET (datos meteorológicos)
- ⏱️ **Duración**: 45-90 minutos
- 📊 **Resultado**: ~18,615 registros (17,520 REE + 1,095 AEMET)
- 🎯 **MLflow Ready**: Dataset completo para modelos de ML

### Opción 2: Solo Datos Históricos REE
```bash
curl -X POST http://localhost:8000/init/historical-data
```
- ✅ **Incluye**: Solo precios eléctricos REE (2022-2024)
- ⏱️ **Duración**: 30-60 minutos
- 📊 **Resultado**: ~17,520 registros históricos

### Opción 3: Solo Datos Históricos AEMET 🌤️ **NUEVO**
```bash
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=3"
```
- ✅ **Incluye**: Datos meteorológicos oficiales AEMET (Linares, Jaén)
- ⏱️ **Duración**: 15-30 minutos
- 📊 **Resultado**: ~1,095 registros diarios (3 años)
- 📍 **Estación**: 5279X - Linares (VOR - AUTOMÁTICA)

### Opción 4: Inicialización Completa del Sistema
```bash
curl -X POST http://localhost:8000/init/all
```
- ✅ **Incluye**: Datos históricos + weather sintético + configuración completa
- ⏱️ **Duración**: 45-90 minutos
- 📊 **Resultado**: ~31,000 registros históricos (2022-2024)

### Opción 5: Solo Tiempo Real
- ✅ **Automática**: Sin intervención requerida
- ⏱️ **Frecuencia**: Cada 15 minutos (modo acelerado)
- 📊 **Para MLflow**: 24-48h para 200+ registros

---

## Monitoreo y Verificación

### 1. Verificar Datos en InfluxDB
```bash
curl http://localhost:8000/influxdb/verify
```

**Interpretar respuesta:**
- `total_records`: Número total de registros visibles
- `energy_prices.records_found`: Registros de precios REE
- `weather_data.records_found`: Registros meteorológicos

### 2. Monitorear Progreso de Inicialización
```bash
# Verificar cada 5-10 minutos durante la carga histórica
curl -s http://localhost:8000/init/status | jq '.status.historical_records'
```

### 3. Estado del Scheduler
```bash
curl http://localhost:8000/scheduler/status
```

**Información clave:**
- `scheduler.status`: debe ser "running"
- `jobs[].next_run`: próxima ejecución
- `jobs[].stats.run_count`: número de ejecuciones
- `jobs[].stats.success_count`: ejecuciones exitosas

### 4. Verificar Logs del Sistema
```bash
docker logs chocolate_factory_brain --tail 50
```

---

## Queries InfluxDB para Verificación

### Acceder a la Interfaz Web
- **URL**: http://localhost:8086
- **Organización**: `chocolate_factory`
- **Bucket**: `energy_data`

### Query Básica - Verificar Datos
```flux
from(bucket: "energy_data")
  |> range(start: -24h)
  |> limit(n: 10)
```

### Query - Contar Registros Históricos
```flux
from(bucket: "energy_data")
  |> range(start: 2022-01-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> count()
```

### Query - Monitorear Tiempo Real
```flux
from(bucket: "energy_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "energy_prices" or r._measurement == "weather_data")
  |> keep(columns: ["_time", "_measurement", "_field", "_value"])
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 20)
```

---

## Estados del Sistema

### ✅ Sistema Completamente Inicializado
- `is_fully_initialized`: `true`
- `ree_initialized`: `true` 
- `weather_initialized`: `true`
- `historical_ree_records`: ~17,520
- `historical_weather_records`: ~1,095
- `estimated_missing_*_records`: 0
- Scheduler ejecutando trabajos cada 15 minutos

### 🔄 Inicialización en Progreso
- `is_fully_initialized`: `false`
- `ree_initialized`: `true/false` (según progreso)
- `weather_initialized`: `true/false` (según progreso)
- Registros históricos < esperados (aumentando)
- Ingesta en tiempo real funcionando paralelamente

### ❌ Sistema No Inicializado  
- `is_fully_initialized`: `false`
- `ree_initialized`: `false`
- `weather_initialized`: `false`
- `initialization_recommended.complete_historical`: `true`
- Ejecutar inicialización completa

### 🌤️ Solo AEMET Pendiente
- `ree_initialized`: `true`
- `weather_initialized`: `false`
- `initialization_recommended.weather_data`: `true`
- Ejecutar: `curl -X POST http://localhost:8000/init/aemet/historical-data`

---

## Programación Automática

Una vez inicializado, el sistema opera automáticamente:

### Trabajos Programados
- **REE Price Ingestion**: Cada 15 minutos (modo acelerado)
- **Weather Data Ingestion**: Cada 15 minutos
- **Health Checks**: Cada 15 minutos
- **Production Optimization**: Cada 30 minutos
- **Daily Backfill**: 01:00 AM diariamente
- **Weekly Cleanup**: Sábados 02:00 AM
- **Token Renewal**: Diariamente 03:00 AM

### Sin Intervención Manual
- El sistema funciona 24/7 autónomamente
- Los datos persisten entre reinicios de contenedores
- No requiere mantenimiento diario

---

## Verificación Post-Inicialización

### Lista de Verificación
- [ ] Todos los contenedores están corriendo (`docker ps`)
- [ ] APIs responden correctamente (`curl` health checks)
- [ ] Scheduler está activo y ejecutando trabajos
- [ ] InfluxDB contiene datos históricos (31K+ registros)
- [ ] Ingesta en tiempo real funciona (nuevos registros cada 15 min)
- [ ] Interfaces web accesibles (InfluxDB, MLflow, Node-RED)

### Comandos de Verificación Final
```bash
# Verificación completa del sistema
curl http://localhost:8000/init/status
curl http://localhost:8000/init/aemet/status
curl http://localhost:8000/influxdb/verify
curl http://localhost:8000/scheduler/status

# Verificar persistencia de datos
ls -la docker/services/influxdb/data/
ls -la docker/services/postgres/data/
ls -la docker/services/mlflow/artifacts/
```

### Comandos Específicos para AEMET 🌤️ **NUEVO**
```bash
# Estado del token AEMET
curl http://localhost:8000/aemet/token/status

# Renovar token AEMET (si es necesario)
curl -X POST http://localhost:8000/aemet/token/renew

# Verificar estaciones meteorológicas disponibles
curl http://localhost:8000/aemet/stations

# Probar conexión con estación de Linares
curl http://localhost:8000/aemet/test-linares

# Datos meteorológicos actuales (tiempo real)
curl http://localhost:8000/aemet/weather

# Weather híbrido (AEMET + OpenWeatherMap)
curl http://localhost:8000/weather/hybrid

# Comparación de fuentes meteorológicas
curl http://localhost:8000/weather/comparison
```

---

## Notas Importantes

1. **Primera vez**: La inicialización histórica puede tardar 30-90 minutos
2. **Datos seguros**: Todos los datos persisten en volúmenes Docker
3. **Operación continua**: El sistema funciona mientras los contenedores estén activos
4. **Modo acelerado**: Actual frecuencia de 15 minutos se revertirá a 1 hora tras recolección MLflow
5. **APIs externas**: REE (público), AEMET (con token), OpenWeatherMap (con API key)

---

## Próximos Pasos

Una vez completada la inicialización:
1. **Implementar modelos MLflow** con los datos históricos
2. **Configurar dashboard Node-RED** para visualización
3. **Optimizar frecuencia de ingesta** según necesidades de producción
4. **Implementar alertas y monitoreo** avanzado