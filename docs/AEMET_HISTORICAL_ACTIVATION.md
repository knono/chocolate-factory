# Activación Manual de Datos Históricos AEMET

## Resumen Ejecutivo

Los datos históricos de AEMET proporcionan información meteorológica oficial española que complementa perfectamente los datos de REE para crear un dataset completo para MLflow. 

**Beneficios clave:**
- 📊 **Dataset completo**: REE + AEMET = 18,615 registros históricos
- 🇪🇸 **Datos oficiales**: Agencia Estatal de Meteorología (gobierno español)
- 🌤️ **Cobertura temporal**: 3 años de datos diarios (2022-2025)
- 🎯 **MLflow ready**: Features meteorológicos para modelos de ML

---

## Secuencias de Activación Manual

### Opción A: Dataset Completo para MLflow (Recomendada)

```bash
# 1. Verificar estado actual
curl http://localhost:8000/init/status

# 2. Cargar REE + AEMET histórico (completo)
curl -X POST http://localhost:8000/init/complete-historical-data

# 3. Monitorear progreso (ejecutar cada 10 minutos)
curl -s http://localhost:8000/init/status | jq '.historical_ree_records, .historical_weather_records'

# 4. Verificar finalización exitosa
curl http://localhost:8000/init/aemet/status
```

**Resultado esperado:**
- ✅ `ree_initialized`: `true` (~17,520 registros)
- ✅ `weather_initialized`: `true` (~1,095 registros) 
- ⏱️ **Duración**: 45-90 minutos

---

### Opción B: Solo AEMET Histórico

Si ya tienes datos REE y solo necesitas AEMET:

```bash
# 1. Verificar estado AEMET específico
curl http://localhost:8000/init/aemet/status

# 2. Cargar solo datos meteorológicos históricos
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=3"

# 3. Verificar progreso AEMET
curl http://localhost:8000/init/aemet/status

# 4. Confirmar finalización
curl -s http://localhost:8000/init/status | jq '.weather_initialized'
```

**Resultado esperado:**
- ✅ `weather_initialized`: `true`
- 📊 ~1,095 registros meteorológicos diarios
- ⏱️ **Duración**: 15-30 minutos

---

### Opción C: Configuración Personalizada

Para diferentes períodos de tiempo:

```bash
# Solo 1 año de datos AEMET
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=1"

# 2 años de datos AEMET  
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=2"

# 5 años de datos AEMET (máximo por limitación API)
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=5"
```

---

## Monitoreo Durante la Activación

### Scripts de Monitoreo

**Monitor básico (cada 5 minutos):**
```bash
while true; do
  echo "$(date): AEMET Status Check"
  curl -s http://localhost:8000/init/aemet/status | jq '.weather_data.total_weather_records, .weather_data.weather_completion_percentage'
  sleep 300
done
```

**Monitor completo (cada 10 minutos):**
```bash
while true; do
  echo "=== $(date) ==="
  echo "REE Records:" $(curl -s http://localhost:8000/init/status | jq '.historical_ree_records')
  echo "Weather Records:" $(curl -s http://localhost:8000/init/status | jq '.historical_weather_records')
  echo "Fully Initialized:" $(curl -s http://localhost:8000/init/status | jq '.is_fully_initialized')
  echo ""
  sleep 600
done
```

### Logs en Tiempo Real

```bash
# Ver logs del contenedor durante la carga
docker logs chocolate_factory_brain --tail 50 -f

# Filtrar solo logs de AEMET
docker logs chocolate_factory_brain 2>&1 | grep -i "aemet\|weather\|historical"
```

---

## Verificación Post-Activación

### Lista de Verificación AEMET

```bash
# ✅ Token AEMET válido
curl http://localhost:8000/aemet/token/status

# ✅ Datos históricos cargados
curl http://localhost:8000/init/aemet/status

# ✅ Datos en InfluxDB
curl http://localhost:8000/influxdb/verify

# ✅ Weather híbrido funcionando
curl http://localhost:8000/weather/hybrid

# ✅ Comparación de fuentes
curl http://localhost:8000/weather/comparison
```

### Queries InfluxDB para Verificar Datos AEMET

**Acceso directo a InfluxDB:**
- URL: http://localhost:8086
- Organización: `chocolate_factory`
- Bucket: `energy_data`

**Query: Contar registros AEMET históricos**
```flux
from(bucket: "energy_data")
  |> range(start: 2022-01-01T00:00:00Z, stop: now())
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r.source == "aemet_historical")
  |> count()
```

**Query: Verificar datos recientes**
```flux
from(bucket: "energy_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r.source == "aemet_historical")
  |> keep(columns: ["_time", "_field", "_value", "station_id"])
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 20)
```

**Query: Resumen por fuente de datos**
```flux
from(bucket: "energy_data")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> group(columns: ["source"])
  |> count()
  |> yield(name: "weather_sources_count")
```

---

## Troubleshooting

### Problemas Comunes

**❌ Token AEMET expirado:**
```bash
# Síntoma: HTTP 401 en llamadas AEMET
curl -X POST http://localhost:8000/aemet/token/renew
```

**❌ Carga lenta o interrumpida:**
```bash
# Verificar logs para errores específicos
docker logs chocolate_factory_brain --tail 100 | grep -i "error\|fail"

# Reintentar solo la parte de AEMET
curl -X POST "http://localhost:8000/init/aemet/historical-data?years_back=3"
```

**❌ Datos no aparecen en InfluxDB:**
```bash
# Verificar conexión InfluxDB
curl http://localhost:8086/health

# Verificar bucket y organización
curl http://localhost:8000/influxdb/verify
```

### Códigos de Estado

| Estado | Descripción | Acción |
|--------|-------------|---------|
| `needs_weather_historical_load: true` | AEMET histórico pendiente | Ejecutar `POST /init/aemet/historical-data` |
| `weather_initialized: false` | Datos AEMET incompletos | Verificar carga en progreso o errores |
| `weather_completion_percentage < 100` | Carga parcial | Esperar finalización o reintentar |
| `total_weather_records: 0` | No hay datos AEMET | Verificar token y conectividad API |

---

## Beneficios del Dataset Completo

### Para Modelos de Machine Learning

**Features meteorológicos disponibles:**
- `temperature` - Temperatura diaria (°C)
- `humidity` - Humedad relativa (%)
- `pressure` - Presión atmosférica (hPa)
- `wind_speed` - Velocidad del viento (km/h)
- `precipitation` - Precipitación (mm)

**Features energéticos (REE):**
- `price_eur_kwh` - Precio eléctrico horario
- `demand_mw` - Demanda energética nacional
- `tariff_period` - Período tarifario (P1-P6)

**Modelos recomendados:**
1. **Optimización de producción de chocolate** basada en temperatura/humedad
2. **Predicción de costos energéticos** con correlación meteorológica
3. **Control de calidad automatizado** según condiciones ambientales
4. **Planificación de producción** con predicción meteorológica

### Correlaciones Esperadas

- 🌡️ **Temperatura alta** → Mayor consumo de refrigeración → Costos energéticos
- 💧 **Humedad alta** → Problemas en chocolate → Ajustes de producción
- 🌪️ **Viento fuerte** → Cambios en generación renovable → Precios REE
- ☔ **Precipitación** → Aumento hidroeléctrica → Precios más bajos

---

## Próximos Pasos

Una vez completada la activación de datos históricos AEMET:

1. **✅ Datos listos para MLflow**: Dataset completo con 18,615 registros
2. **🔄 Automatización activa**: Ingesta continua cada 15 minutos
3. **📊 Dashboard preparation**: Node-RED con datos meteorológicos
4. **🤖 ML Models**: Implementación de modelos predictivos
5. **🎯 Production optimization**: Algoritmos de optimización de fábrica

**El sistema está ahora completamente preparado para desarrollo de modelos de ML avanzados con features energéticos y meteorológicos oficiales españoles.**