# AEMET Historical Data - Quick Start Guide
# Guía de Inicio Rápido - Datos Históricos AEMET

**TFM Chocolate Factory - Ingesta Rápida de Datos Meteorológicos**

---

## 🚀 Inicio Rápido (5 minutos)

### 1. Verificar Estado Actual
```bash
# Verificar sistema
curl http://localhost:8000/init/status

# Estado AEMET específico
curl http://localhost:8000/aemet/historical/status

# Datos actuales en InfluxDB
curl http://localhost:8000/influxdb/verify
```

### 2. Ingesta Rápida (Últimos 2 años)
```bash
# Opción A: Síncrono (recomendado para testing)
curl -X POST "http://localhost:8000/aemet/load-progressive?start_year=2023&end_year=2025"

# Opción B: Background (recomendado para producción)
curl -X POST "http://localhost:8000/aemet/load-progressive?start_year=2020&end_year=2025" \
  -H "Content-Type: application/json"
```

### 3. Monitorear Progreso
```bash
# Logs en tiempo real
docker logs -f chocolate_factory_brain | grep -E "aemet|weather|Q[1-4]"

# Verificar registros almacenados
curl http://localhost:8000/influxdb/verify | jq '.data.weather_data.records_found'
```

---

## ⚡ Comandos Esenciales

### Ingesta por Períodos

```bash
# Último año (rápido - 5 min)
curl -X POST "http://localhost:8000/aemet/load-progressive?start_year=2024&end_year=2025"

# Últimos 3 años (medio - 15 min)
curl -X POST "http://localhost:8000/aemet/load-progressive?start_year=2022&end_year=2025"

# 5 años completos (completo - 30-45 min)
curl -X POST "http://localhost:8000/aemet/load-progressive?start_year=2020&end_year=2025"
```

### Verificación de Datos

```bash
# Conteo total de registros weather
curl -s http://localhost:8000/influxdb/verify | \
  jq '.data.weather_data.records_found'

# Estado de inicialización
curl -s http://localhost:8000/init/status | \
  jq '.status.historical_weather_records'

# Verificar últimos datos ingresados
curl -s http://localhost:8000/influxdb/verify | \
  jq '.data.weather_data.latest_data[0]'
```

### Troubleshooting Rápido

```bash
# Si hay errores HTTP 429
# Esperar 2-3 minutos y reintentar con chunk más pequeño
curl -X POST "http://localhost:8000/aemet/test-historical?months_back=3"

# Si InfluxDB no responde
docker-compose restart chocolate_factory_storage

# Si AEMET token inválido
curl http://localhost:8000/aemet/token/status
# Verificar AEMET_API_KEY en variables de entorno
```

---

## 📊 Resultados Esperados

### Después de Ingesta Completa (5 años)

```json
{
  "historical_weather_records": 1800,
  "period_covered": "2020-2025",
  "station": "5279X LINARES, JAÉN",
  "data_quality": {
    "temperature": "95% coverage",
    "humidity": "90% coverage", 
    "pressure": "85% coverage"
  },
  "ready_for_mlflow": true
}
```

### Verificación en InfluxDB UI

1. **Acceder**: http://localhost:8086
2. **Login**: Con credenciales configuradas
3. **Query**: 
```flux
from(bucket: "energy_data")
  |> range(start: -5y)
  |> filter(fn: (r) => r._measurement == "weather_data")
  |> filter(fn: (r) => r.station_id == "5279X")
  |> count()
```

---

## 🎯 Próximos Pasos

Una vez completada la ingesta histórica:

1. ✅ **Datos listos**: ~1800 registros AEMET + 31k registros REE
2. 🚀 **MLflow**: Implementar modelos de predicción energética
3. 📊 **Correlaciones**: Precio eléctrico vs condiciones meteorológicas
4. 🏭 **Optimización**: Programación de producción chocolate según datos

---

## 📞 Ayuda Rápida

### Documentación Completa
- `docs/AEMET_HISTORICAL_INGESTION.md` - Guía completa
- `docs/MONITORING_GUIDE.md` - Monitoreo del sistema
- `docs/TROUBLESHOOTING.md` - Resolución problemas

### Comandos de Emergencia

```bash
# Reiniciar sistema completo
docker-compose restart

# Solo reiniciar API (mantiene datos)
docker-compose restart chocolate_factory_brain

# Verificar todos los contenedores
docker-compose ps

# Limpiar logs si están muy llenos
docker system prune
```

---

**🎯 Objetivo**: Tener 1800+ registros AEMET históricos listos para Machine Learning en menos de 1 hora.

*Última actualización: 29 de junio de 2025*