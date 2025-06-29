# Guía de Monitoreo y Verificación - TFM Chocolate Factory

## Tabla de Contenidos
1. [Comandos de Monitoreo Diario](#comandos-de-monitoreo-diario)
2. [Verificación de Estado del Sistema](#verificación-de-estado-del-sistema)
3. [Queries InfluxDB para Análisis](#queries-influxdb-para-análisis)
4. [Indicadores Clave de Rendimiento](#indicadores-clave-de-rendimiento)
5. [Alertas y Problemas Comunes](#alertas-y-problemas-comunes)

---

## Comandos de Monitoreo Diario

### Verificación Rápida del Sistema
```bash
# Estado general del sistema
curl -s http://localhost:8000/init/status | jq '{
  initialized: .status.is_initialized,
  historical_records: .status.historical_records,
  recent_records: .status.recent_records_24h
}'

# Conteo actual de registros
curl -s http://localhost:8000/influxdb/verify | jq '.total_records'

# Estado del scheduler
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.status'
```

### Verificación de Contenedores
```bash
# Ver estado de todos los contenedores
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verificar salud de contenedores
docker ps --filter "health=healthy" | wc -l
# Debe devolver 5 (todos los contenedores saludables)
```

---

## Verificación de Estado del Sistema

### 1. APIs Principales
```bash
# API FastAPI
curl -w "%{http_code}\n" -s -o /dev/null http://localhost:8000/health
# Esperado: 200

# InfluxDB
curl -w "%{http_code}\n" -s -o /dev/null http://localhost:8086/health
# Esperado: 200

# MLflow
curl -w "%{http_code}\n" -s -o /dev/null http://localhost:5000/health
# Esperado: 200
```

### 2. Scheduler y Trabajos Automáticos
```bash
# Detalles completos del scheduler
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | {
  id: .id,
  name: .name,
  next_run: .next_run,
  run_count: .stats.run_count // 0,
  success_count: .stats.success_count // 0,
  error_count: .stats.error_count // 0
}'
```

### 3. Estadísticas de Ingesta
```bash
# Trabajos con estadísticas
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | select(.stats != null) | {
  job: .id,
  runs: .stats.run_count,
  success_rate: ((.stats.success_count // 0) * 100 / (.stats.run_count // 1))
}'
```

---

## Queries InfluxDB para Análisis

### Acceso a la Interfaz Web
- **URL**: http://localhost:8086
- **Organización**: `chocolate_factory`
- **Bucket**: `energy_data`

### Query 1: Resumen de Datos por Fuente
```flux
from(bucket: "energy_data")
  |> range(start: -24h)
  |> group(columns: ["_measurement", "source"])
  |> count()
  |> sort(columns: ["_value"], desc: true)
```

### Query 2: Actividad de Ingesta Reciente
```flux
from(bucket: "energy_data")
  |> range(start: -2h)
  |> filter(fn: (r) => r._field == "price_eur_kwh" or r._field == "temperature")
  |> group(columns: ["_measurement"])
  |> last()
  |> keep(columns: ["_time", "_measurement", "_value", "source"])
  |> sort(columns: ["_time"], desc: true)
```

### Query 3: Verificar Continuidad de Datos
```flux
from(bucket: "energy_data")
  |> range(start: -6h)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> filter(fn: (r) => r._field == "price_eur_kwh")
  |> aggregateWindow(every: 15m, fn: count)
  |> map(fn: (r) => ({r with gap: if r._value == 0 then "❌ GAP" else "✅ OK"}))
```

### Query 4: Estadísticas de Precios Diarias
```flux
from(bucket: "energy_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> filter(fn: (r) => r._field == "price_eur_kwh")
  |> aggregateWindow(every: 1d, fn: mean)
  |> map(fn: (r) => ({r with price_cents: r._value * 100.0}))
```

### Query 5: Conteo Total de Registros Históricos
```flux
from(bucket: "energy_data")
  |> range(start: 2022-01-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "energy_prices")
  |> count()
  |> group()
  |> sum()
```

---

## Indicadores Clave de Rendimiento (KPIs)

### 1. Disponibilidad del Sistema
```bash
# Uptime de contenedores
docker ps --format "{{.Names}}: {{.Status}}" | grep -c "Up"
```
**Meta**: 5/5 contenedores activos

### 2. Tasa de Éxito de Ingesta
```bash
# Calcular tasa de éxito
curl -s http://localhost:8000/scheduler/status | jq -r '
.scheduler.jobs[] | 
select(.stats != null) | 
select(.id | contains("ingestion")) | 
"\(.id): \((.stats.success_count * 100 / .stats.run_count) | floor)% success rate"'
```
**Meta**: >95% tasa de éxito

### 3. Latencia de Datos
```bash
# Tiempo desde la última ingesta
curl -s http://localhost:8000/influxdb/verify | jq -r '
.data.energy_prices.latest_data[0].timestamp as $last |
(now - ($last | fromdateiso8601)) / 60 | floor |
"Último precio REE: \(.) minutos atrás"'
```
**Meta**: <30 minutos para datos REE

### 4. Volumen de Datos
```bash
# Crecimiento de datos en las últimas 24h
curl -s http://localhost:8000/init/status | jq '{
  total_historical: .status.historical_records,
  recent_24h: .status.recent_records_24h,
  growth_rate: (.status.recent_records_24h / 96 * 100 | floor)
}'
```
**Meta**: ~96 registros/día (cada 15 min)

---

## Alertas y Problemas Comunes

### 🔴 Alerta Crítica: Scheduler Detenido
```bash
# Verificar si el scheduler está corriendo
SCHEDULER_STATUS=$(curl -s http://localhost:8000/scheduler/status | jq -r '.scheduler.status')
if [ "$SCHEDULER_STATUS" != "running" ]; then
    echo "🔴 CRÍTICO: Scheduler no está funcionando"
    docker restart chocolate_factory_brain
fi
```

### 🟡 Alerta Media: Datos Desactualizados
```bash
# Verificar edad del último registro
LAST_RECORD_AGE=$(curl -s http://localhost:8000/influxdb/verify | jq -r '
(.data.energy_prices.latest_data[0].timestamp // "1970-01-01T00:00:00+00:00") as $last |
(now - ($last | fromdateiso8601)) / 3600 | floor'
)

if [ "$LAST_RECORD_AGE" -gt 2 ]; then
    echo "🟡 ADVERTENCIA: Datos REE con $LAST_RECORD_AGE horas de antigüedad"
fi
```

### 🟢 Verificación Rutinaria: Ingesta Funcionando
```bash
# Contar registros nuevos en última hora
NEW_RECORDS=$(curl -s http://localhost:8000/influxdb/verify | jq '.total_records')
echo "🟢 INFO: $NEW_RECORDS registros totales en sistema"
```

---

## Comandos de Troubleshooting

### 1. Reiniciar Servicios
```bash
# Reinicio completo del sistema
docker-compose restart

# Reinicio solo del cerebro (FastAPI)
docker restart chocolate_factory_brain

# Verificar logs después del reinicio
docker logs chocolate_factory_brain --tail 20
```

### 2. Verificar Conectividad de APIs Externas
```bash
# REE API
curl -w "%{http_code}\n" -s -o /dev/null "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

# OpenWeatherMap API
curl -w "%{http_code}\n" -s -o /dev/null "http://api.openweathermap.org/data/2.5/weather?q=Linares,ES&appid=YOUR_API_KEY"
```

### 3. Limpiar y Reinicializar
```bash
# Solo en caso de problemas graves
docker-compose down
docker system prune -f
docker-compose up -d

# Luego reinicializar datos
curl -X POST http://localhost:8000/init/all
```

---

## Monitoreo Automatizado

### Script de Monitoreo Diario
Crear `monitor.sh`:
```bash
#!/bin/bash
echo "=== Monitoreo TFM Chocolate Factory $(date) ==="

# 1. Estado de contenedores
echo "Contenedores activos: $(docker ps | grep -c chocolate_factory)"

# 2. Estado del sistema
STATUS=$(curl -s http://localhost:8000/init/status | jq -r '.status.is_initialized')
echo "Sistema inicializado: $STATUS"

# 3. Registros totales
RECORDS=$(curl -s http://localhost:8000/influxdb/verify | jq -r '.total_records')
echo "Registros totales: $RECORDS"

# 4. Scheduler
SCHEDULER=$(curl -s http://localhost:8000/scheduler/status | jq -r '.scheduler.status')
echo "Scheduler: $SCHEDULER"

echo "=== Fin del monitoreo ==="
```

### Programar con Cron (Opcional)
```bash
# Ejecutar cada hora
0 * * * * /path/to/monitor.sh >> /var/log/chocolate_factory_monitor.log 2>&1
```

---

## Dashboard de Monitoreo Web

### Acceso a Interfaces
- **InfluxDB**: http://localhost:8086 (Datos y queries)
- **MLflow**: http://localhost:5000 (Modelos ML)
- **Node-RED**: http://localhost:1880 (Dashboard visualización)
- **FastAPI Docs**: http://localhost:8000/docs (API endpoints)

### Métricas Recomendadas para Dashboard
1. **Tiempo real**: Precio actual de electricidad
2. **Histórico**: Gráfico de precios últimas 24h
3. **Sistema**: Estado de contenedores y scheduler
4. **Calidad**: Tasa de éxito de ingesta
5. **Volumen**: Registros totales y crecimiento diario