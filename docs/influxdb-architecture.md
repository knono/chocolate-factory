# InfluxDB Architecture - Chocolate Factory

**Documentación técnica completa de la arquitectura de datos de series temporales**

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura de Buckets](#arquitectura-de-buckets)
3. [Esquemas de Datos](#esquemas-de-datos)
4. [Flujos de Ingestion](#flujos-de-ingestion)
5. [Queries y ML Integration](#queries-y-ml-integration)
6. [Operaciones y Mantenimiento](#operaciones-y-mantenimiento)
7. [Troubleshooting](#troubleshooting)

---

## Visión General

### Configuración del Sistema

```yaml
Container: chocolate_factory_storage
Image: influxdb:2.7
Ports: 8086 (host) → 8086 (container)
Network: backend (192.168.100.0/24)
Storage: ./docker/services/influxdb/data → /var/lib/influxdb2

Conexión:
  URL: http://chocolate_factory_storage:8086  # Internal Docker
  Org: chocolate-factory
  Token: ${INFLUXDB_TOKEN}
  Default Bucket: energy_data
```

**Fuente:** [docker-compose.yml](../docker-compose.yml#L65-87)

### Estadísticas del Sistema (Octubre 2025)

| Bucket | Measurements | Records | Date Range | Size |
|--------|--------------|---------|------------|------|
| `energy_data` | 2 | ~50,000 | 2022-2025 | ~15 MB |
| `siar_historical` | 1 | 88,935 | 2000-2025 | ~25 MB |
| `_monitoring` | N/A | Sistema | 7 días | ~5 MB |
| `_tasks` | N/A | Sistema | 3 días | ~2 MB |

---

## Arquitectura de Buckets

### 1. `energy_data` - Bucket Principal de Producción

**Propósito:** Datos operacionales en tiempo real para ML y dashboard

#### Measurement: `energy_prices`

```
Fuente: REE API (PVPC precios)
Frecuencia: Cada 5 minutos (APScheduler)
Records: ~42,578 (2022-2025)
```

**Tags (Indexed):**
- `market_type`: "spot" (fijo)
- `tariff_period`: "P1" | "P2" | "P3" | "P4" | "P5" | "P6"
- `day_type`: "weekday" | "weekend" | "holiday"
- `season`: "winter" | "spring" | "summer" | "fall"
- `provider`: "ree" (fijo)
- `data_source`: "ree_historical" | "ree_realtime"

**Fields (Data):**
- `price_eur_mwh`: float (precio original API)
- `price_eur_kwh`: float (dividido por 1000)
- `energy_cost`: float (base cost)
- `grid_fees`: float (placeholder, default 0.0)
- `system_charges`: float (placeholder, default 0.0)

**Código:** [data_ingestion.py:129-170](../src/fastapi-app/services/data_ingestion.py#L129-170)

#### Measurement: `weather_data`

```
Fuentes: AEMET (00:00-07:00) + OpenWeatherMap (08:00-23:00)
Estrategia: Híbrida 24/7
Frecuencia: Cada 5 minutos (APScheduler)
Records: ~7,460/mes
```

**Tags (Indexed):**
- `station_id`: "5279X" (Linares, Jaén) | "5298X" (Andújar backup)
- `data_source`: "aemet" | "openweathermap"
- `data_type`: "current" | "current_realtime"
- `season`: "winter" | "spring" | "summer" | "fall"
- `station_name`: string (opcional)
- `province`: "Jaén" (opcional)

**Fields (Data):**
```python
# Temperatura
temperature: float          # °C
temperature_max: float      # °C (diaria)
temperature_min: float      # °C (diaria)

# Humedad
humidity: float            # %
humidity_max: float        # % (diaria)
humidity_min: float        # % (diaria)

# Presión
pressure: float            # hPa
pressure_max: float        # hPa (diaria)
pressure_min: float        # hPa (diaria)

# Viento
wind_speed: float          # km/h
wind_direction: float      # grados
wind_gust: float          # km/h

# Otros
precipitation: float       # mm
solar_radiation: float     # W/m²
altitude: float           # metros

# Derivados (calculados)
heat_index: float                    # Índice de calor
chocolate_production_index: float    # Índice de confort chocolate
```

**Código:** [data_ingestion.py:454-535](../src/fastapi-app/services/data_ingestion.py#L454-535)

---

### 2. `siar_historical` - Archivo Histórico

**Propósito:** Datos históricos para entrenamiento ML (25 años)

#### Measurement: `siar_weather`

```
Fuente: SIAR CSV files (manual ETL)
Cobertura: Agosto 2000 - Septiembre 2025
Records: 88,935 observaciones diarias
Stations: J09 (2000-2017), J17 (2018-2025)
```

**Tags (Indexed):**
- `station_id`: "SIAR_J09_Linares" | "SIAR_J17_Linares"
- `data_source`: "siar_historical"

**Fields (Data):**
```python
# Temperaturas (°C)
temperatura_media: float
temperatura_maxima: float
temperatura_minima: float

# Humedad y Presión
humedad_relativa_media: float      # %
presion_atmosferica: float         # hPa

# Viento
velocidad_viento_media: float      # m/s
direccion_viento: float            # grados

# Radiación y Precipitación
radiacion_solar_global: float      # MJ/m²
precipitacion: float               # mm

# Evapotranspiración
etc_referencia: float              # mm (ET0 - FAO)
evapotranspiracion: float          # mm
```

**ETL Script:** [test_siar_simple.py](../scripts/test_siar_simple.py)

**Características especiales:**
- Formato español: DD/MM/YYYY, decimales con coma
- Limpieza Unicode automática
- Batch processing (100 records/batch)
- Detección automática de estación (J09/J17 por filename)

---

### 3. Buckets del Sistema

#### `_monitoring` (Sistema)
- **Retention:** 7 días
- **Uso:** Logs de InfluxDB internos
- **Queries:** Performance monitoring

#### `_tasks` (Sistema)
- **Retention:** 3 días
- **Uso:** Task execution logs
- **Queries:** Task debugging

---

## Flujos de Ingestion

### 1. REE Electricity Prices

```mermaid
REE API → REEClient → DataIngestionService → InfluxDB
         (PVPC)     (transform)    (validate)    (energy_data/energy_prices)
```

**Pipeline:**
1. `REEClient.get_pvpc_prices()` - Fetch API data
2. `_validate_price_data()` - Range validation (0-500 €/MWh)
3. `_transform_ree_price_to_influx_point()` - Create Point with tags/fields
4. `write_api.write()` - Batch write to InfluxDB

**APScheduler Job:**
```python
# Cada 5 minutos
scheduler.add_job(
    ingest_ree_prices,
    trigger="interval",
    minutes=5,
    id="ree_ingestion"
)
```

**Fuente:** [scheduler.py](../src/fastapi-app/services/scheduler.py)

---

### 2. Weather Data (Hybrid Strategy)

```mermaid
00:00-07:00                    08:00-23:00
    ↓                              ↓
AEMET API                  OpenWeatherMap API
    ↓                              ↓
AEMETClient               OpenWeatherMapClient
    ↓                              ↓
    └────→ DataIngestionService ←──┘
                  ↓
         InfluxDB (energy_data/weather_data)
```

**Estrategia Híbrida:**
```python
def ingest_hybrid_weather():
    current_hour = datetime.now(timezone.utc).hour

    if 0 <= current_hour <= 7:
        # AEMET: Observaciones oficiales españolas
        stats = await ingest_aemet_weather(station_ids=["5279X"])
    else:
        # OpenWeatherMap: Datos en tiempo real
        stats = await ingest_openweathermap_weather()

    return stats
```

**Razón:** AEMET tiene mejor precisión pero actualiza cada 1h, OpenWeatherMap es real-time pero menos preciso.

**APScheduler Job:**
```python
# Cada 5 minutos
scheduler.add_job(
    ingest_hybrid_weather,
    trigger="interval",
    minutes=5,
    id="weather_ingestion"
)
```

---

### 3. SIAR Historical (Manual ETL)

```mermaid
CSV Files (J09/J17) → Clean Unicode → Parse Spanish Format → InfluxDB
   (25 years)          (line-by-line)   (DD/MM/YYYY, comma)  (siar_historical)
```

**Proceso:**
1. **Detección archivos:** `find /app/data -name '*.csv'`
2. **Limpieza Unicode:** Character-by-character filtering
3. **Parse formato español:**
   - Fechas: `DD/MM/YYYY` → `datetime`
   - Decimales: `18,5` → `18.5`
4. **Identificación estación:** Filename pattern (`J09` vs `J17`)
5. **Batch write:** 100 records/batch para performance

**Ejecución:**
```bash
docker exec chocolate_factory_brain python /app/scripts/test_siar_simple.py
```

**Output:**
```
Found 26 CSV files to process
🚀 Processing SIAR file: J09_2000.csv
✅ Batch 1: 100 records → InfluxDB
...
📊 Total: 88,935 records written to siar_historical
```

---

## Queries y ML Integration

### Feature Extraction para ML

**Datos Recientes (24h):**
```python
# enhanced_ml_service.py línea 79
flux_query = f'''
    from(bucket: "{service.config.bucket}")
    |> range(start: -24h)
    |> filter(fn: (r) => r._measurement == "energy_prices" or r._measurement == "weather_data")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
```

**Datos Históricos SIAR:**
```python
# enhanced_ml_service.py línea 88
flux_query = f'''
    from(bucket: "siar_historical")
    |> range(start: 2000-01-01T00:00:00Z, stop: now())
    |> filter(fn: (r) => r._measurement == "siar_weather")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
```

**Dashboard Analytics:**
```python
# dashboard.py - Precios REE últimos 30 días
flux_query = f'''
    from(bucket: "{service.config.bucket}")
    |> range(start: -30d)
    |> filter(fn: (r) => r._measurement == "energy_prices")
    |> filter(fn: (r) => r._field == "price_eur_kwh")
    |> aggregateWindow(every: 1h, fn: mean)
'''
```

### Gap Detection

```python
# gap_detector.py línea 93
flux_query = f'''
    from(bucket: "{service.config.bucket}")
    |> range(start: {start_time}, stop: {end_time})
    |> filter(fn: (r) => r._measurement == "energy_prices")
    |> aggregateWindow(every: 1h, fn: count)
    |> map(fn: (r) => ({{r with _value: if r._value == 0 then 1 else 0}}))
    |> sum()
'''
```

**Output:** Número de horas con 0 registros = gaps detectados

---

## Operaciones y Mantenimiento

### Backup Strategy

**Diario (Recomendado):**
```bash
#!/bin/bash
# backup-daily.sh

DATE=$(date +%Y%m%d)

# Backup energy_data (crítico)
docker exec chocolate_factory_storage influx backup \
  /var/lib/influxdb2/backups/energy_data_${DATE}.tar \
  -b energy_data

# Backup siar_historical (semanal)
if [ $(date +%u) -eq 7 ]; then
  docker exec chocolate_factory_storage influx backup \
    /var/lib/influxdb2/backups/siar_historical_${DATE}.tar \
    -b siar_historical
fi

# Copiar al host
docker cp chocolate_factory_storage:/var/lib/influxdb2/backups/energy_data_${DATE}.tar \
  ./docker/services/influxdb/backups/

# Cleanup (mantener últimos 7 días)
find ./docker/services/influxdb/backups/ -name "*.tar" -mtime +7 -delete
```

**Agregar a APScheduler:**
```python
# scheduler.py
scheduler.add_job(
    run_backup_daily,
    trigger="cron",
    hour=2,
    minute=0,
    id="backup_daily"
)
```

---

### Retention Policies

**Actual:**
```
energy_data:       ♾️ Indefinido (producción)
siar_historical:   ♾️ Indefinido (archivo)
_monitoring:       7 días
_tasks:            3 días
```

**Recomendado para Optimización:**
```bash
# Si crece demasiado energy_data/weather_data:
# Retener solo últimos 90 días de weather, archivar resto a CSV

influx bucket update \
  -i <bucket-id> \
  --retention 7776000s  # 90 días en segundos
```

---

### Performance Monitoring

**Métricas Clave:**
```bash
# Write throughput
docker exec chocolate_factory_storage influx query '
from(bucket: "_monitoring")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "boltdb_writes_total")
  |> derivative(unit: 1m)
  |> mean()
'

# Query latency
docker exec chocolate_factory_storage influx query '
from(bucket: "_monitoring")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "query_control_requests_total")
  |> derivative(unit: 1m)
'

# Disk usage
docker exec chocolate_factory_storage du -sh /var/lib/influxdb2/engine/data/*
```

**Alertas Recomendadas:**
- Write rate < 1/min → Ingestion falló
- Query latency > 5s → Performance issue
- Disk usage > 80% → Space cleanup

---

## Troubleshooting

### Problema 1: Gaps en REE Data

**Síntomas:** Dashboard muestra huecos en precios

**Diagnóstico:**
```bash
# 1. Detectar gaps
curl http://localhost:8000/gaps/summary

# 2. Ver último registro
docker exec chocolate_factory_storage influx query '
from(bucket: "energy_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> last()
'

# 3. Check logs ingestion
docker logs chocolate_factory_brain | grep "REE Ingestion"
```

**Solución:**
```bash
# Backfill automático
curl -X POST http://localhost:8000/gaps/backfill/auto?max_gap_hours=24

# O manual para rango específico
curl -X POST http://localhost:8000/gaps/backfill?days_back=7
```

---

### Problema 2: Weather Data Desbalanceado

**Síntomas:** Solo OpenWeatherMap, no AEMET

**Diagnóstico:**
```bash
docker exec chocolate_factory_storage influx query '
from(bucket: "energy_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> group(columns: ["data_source"])
  |> count()
'
```

**Esperado:**
- `aemet`: ~7 records (00:00-07:00, 1/hora)
- `openweathermap`: ~192 records (08:00-23:00, cada 5min)

**Solución:**
```bash
# 1. Verificar AEMET API key
docker exec chocolate_factory_brain env | grep AEMET_API_KEY

# 2. Renovar token AEMET (cada 6 días)
curl http://localhost:8000/aemet/renew-token

# 3. Test manual AEMET
docker exec chocolate_factory_brain python -c "
from services.aemet_client import AEMETClient
import asyncio
async def test():
    async with AEMETClient() as client:
        data = await client.get_current_weather('5279X')
        print(data)
asyncio.run(test())
"
```

---

### Problema 3: SIAR Historical No Aparece en ML

**Síntomas:** ML solo usa datos recientes

**Diagnóstico:**
```bash
# 1. Verificar bucket existe
docker exec chocolate_factory_storage influx bucket list | grep siar

# 2. Count registros
docker exec chocolate_factory_storage influx query '
from(bucket: "siar_historical")
  |> range(start: 2000-01-01T00:00:00Z, stop: now())
  |> count()
  |> group()
  |> sum()
'
```

**Esperado:** `_value: 88935` (o similar)

**Solución:**
```bash
# Re-importar SIAR data
docker exec chocolate_factory_brain python /app/scripts/test_siar_simple.py

# Verificar ML usa ambos buckets
grep -n "siar_historical" src/fastapi-app/services/enhanced_ml_service.py
# Debería aparecer línea 88
```

---

### Problema 4: Queries Lentas

**Síntomas:** Dashboard tarda >10s en cargar

**Diagnóstico:**
```bash
# 1. Check cardinality
docker exec chocolate_factory_storage influx query '
import "influxdata/influxdb/schema"
schema.measurementTagKeys(bucket: "energy_data", measurement: "weather_data")
  |> count()
'
```

**Tags con >1000 valores únicos = problema**

**Solución:**
```python
# Optimizar queries:
# ❌ Malo: Scan completo
from(bucket: "energy_data") |> range(start: 0)

# ✅ Bueno: Time-bounded
from(bucket: "energy_data") |> range(start: -7d)

# ✅ Mejor: Con filtros específicos
from(bucket: "energy_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> filter(fn: (r) => r.data_source == "ree_historical")
```

---

## Referencias Rápidas

### Comandos de Un Solo Paso

```bash
# Ver TODO el sistema de un vistazo
docker exec chocolate_factory_storage influx query '
import "influxdata/influxdb/schema"

buckets = from(bucket: "_monitoring")
  |> range(start: -1m)
  |> schema.buckets()
  |> yield(name: "buckets")
'

# Export completo para análisis offline
docker exec chocolate_factory_storage influx query '
from(bucket: "energy_data")
  |> range(start: -30d)
  |> pivot(rowKey:["_time"], columnKey:["_measurement","_field"], valueColumn:"_value")
' --raw > full_export_$(date +%Y%m%d).csv

# Health check completo
docker exec chocolate_factory_storage influx ping && \
docker logs chocolate_factory_brain --tail 50 | grep -E "InfluxDB|Ingestion" && \
curl -s http://localhost:8000/health | jq
```

---

### Archivos Clave del Proyecto

| Archivo | Propósito | Líneas Importantes |
|---------|-----------|-------------------|
| `services/data_ingestion.py` | Ingestion service principal | 74-100 (client), 191-308 (REE), 572-789 (weather) |
| `services/ree_client.py` | REE API client | 166-253 (PVPC prices) |
| `services/aemet_client.py` | AEMET API client | - |
| `services/openweathermap_client.py` | OpenWeatherMap client | - |
| `services/gap_detector.py` | Gap detection | 93-141 (REE gaps), 324-335 (weather gaps) |
| `services/backfill_service.py` | Auto-backfill | - |
| `scripts/test_siar_simple.py` | SIAR ETL | 24-50 (cleaning), 95-150 (write) |
| `configs/influxdb_schemas.py` | Schema definitions | - |
| `docker-compose.yml` | InfluxDB config | 65-87 |

---

## Siguiente Pasos Recomendados

1. **Automatizar backups** → Agregar job APScheduler
2. **Monitoring dashboard** → Grafana para métricas InfluxDB
3. **Alerting** → Notificaciones si gaps > 6h
4. **Optimización** → Retention policy para weather_data viejo
5. **Documentación** → Actualizar este doc cuando cambien schemas

---

**Última actualización:** Octubre 2025
**Mantenido por:** Chocolate Factory Team
**Para ayuda rápida:** Usa `/influxdb-admin` command
