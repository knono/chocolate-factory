# Guía de Troubleshooting - TFM Chocolate Factory

## Tabla de Contenidos
1. [Problemas de Inicialización](#problemas-de-inicialización)
2. [Problemas de Ingesta de Datos](#problemas-de-ingesta-de-datos)
3. [Problemas de Contenedores](#problemas-de-contenedores)
4. [Problemas de APIs Externas](#problemas-de-apis-externas)
5. [Problemas de InfluxDB](#problemas-de-influxdb)
6. [Problemas de Scheduler](#problemas-de-scheduler)
7. [Recuperación de Desastres](#recuperación-de-desastres)

---

## Problemas de Inicialización

### ❌ Problema: "Sistema no inicializado"
**Síntomas:**
```bash
curl http://localhost:8000/init/status
# Respuesta: "is_initialized": false
```

**Diagnóstico:**
```bash
# Verificar contenedores
docker ps | grep chocolate_factory

# Verificar logs
docker logs chocolate_factory_brain --tail 20
```

**Solución:**
```bash
# 1. Reiniciar contenedores
docker-compose restart

# 2. Esperar 2-3 minutos y ejecutar inicialización
curl -X POST http://localhost:8000/init/all

# 3. Verificar progreso
curl http://localhost:8000/init/status
```

### ❌ Problema: "Inicialización lenta o colgada"
**Síntomas:**
- `historical_records` no aumenta después de 30 minutos
- Proceso de inicialización parece detenido

**Diagnóstico:**
```bash
# Verificar conectividad API REE
curl -w "%{http_code}\n" -s -o /dev/null "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

# Verificar logs de ingesta
docker logs chocolate_factory_brain | grep -i "ree\|historical\|error"
```

**Solución:**
```bash
# 1. Cancelar inicialización actual (si está colgada)
docker restart chocolate_factory_brain

# 2. Intentar solo datos recientes
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'

# 3. Si funciona, reintentar inicialización histórica
curl -X POST http://localhost:8000/init/historical-data
```

---

## Problemas de Ingesta de Datos

### ❌ Problema: "Solo pocos registros después de horas"
**Síntomas:**
- `total_records` en InfluxDB muy bajo (< 50 después de 2+ horas)
- Scheduler corriendo pero no generando datos

**Diagnóstico:**
```bash
# Verificar ejecuciones del scheduler
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | {id: .id, run_count: .stats.run_count // 0, errors: .stats.error_count // 0}'

# Verificar última actividad
docker logs chocolate_factory_brain --since="1h" | grep -i "ingestion\|ree\|weather"
```

**Solución:**
```bash
# 1. Forzar ingesta manual
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'
curl -X POST http://localhost:8000/ingest-now -d '{"source": "hybrid"}'

# 2. Si manual funciona, reiniciar scheduler
docker restart chocolate_factory_brain

# 3. Verificar que jobs están programados correctamente
curl http://localhost:8000/scheduler/status
```

### ❌ Problema: "Error 'No data retrieved from API'"
**Síntomas:**
- Logs muestran "No price data retrieved from REE API"
- APIs externas devuelven datos vacíos

**Diagnóstico:**
```bash
# Verificar APIs manualmente
curl "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=$(date -d '1 hour ago' '+%Y-%m-%dT%H:%M')&end_date=$(date '+%Y-%m-%dT%H:%M')&time_trunc=hour"
```

**Solución:**
```bash
# 1. Problema temporal - esperar y reintentar
sleep 300  # 5 minutos
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'

# 2. Si persiste, usar datos históricos
curl -X POST http://localhost:8000/init/historical-data
```

---

## Problemas de Contenedores

### ❌ Problema: "Contenedor no saludable o no inicia"
**Síntomas:**
```bash
docker ps
# Estado: Restarting, Exited, o Unhealthy
```

**Diagnóstico:**
```bash
# Ver logs del contenedor problemático
docker logs chocolate_factory_brain
docker logs chocolate_factory_storage
docker logs chocolate_factory_mlops

# Verificar recursos del sistema
df -h  # Espacio en disco
free -h  # Memoria RAM
```

**Solución por Contenedor:**

**FastAPI (chocolate_factory_brain):**
```bash
# Verificar puertos
netstat -tulpn | grep :8000

# Reiniciar con logs
docker restart chocolate_factory_brain
docker logs -f chocolate_factory_brain
```

**InfluxDB (chocolate_factory_storage):**
```bash
# Verificar permisos de datos
ls -la docker/services/influxdb/data/

# Reiniciar InfluxDB
docker restart chocolate_factory_storage

# Verificar conectividad
curl http://localhost:8086/health
```

**MLflow (chocolate_factory_mlops):**
```bash
# Verificar PostgreSQL primero
docker logs chocolate_factory_postgres

# Reiniciar MLflow
docker restart chocolate_factory_mlops
curl http://localhost:5000/health
```

### ❌ Problema: "Conflictos de puertos"
**Síntomas:**
- "Port already in use" al iniciar contenedores
- Servicios no accesibles desde puertos esperados

**Diagnóstico:**
```bash
# Verificar puertos ocupados
netstat -tulpn | grep -E ':(8000|8086|5000|1880|5432)'

# Ver qué proceso usa el puerto
lsof -i :8000
```

**Solución:**
```bash
# 1. Matar procesos que usan los puertos
sudo kill -9 $(lsof -t -i:8000)
sudo kill -9 $(lsof -t -i:8086)

# 2. Reiniciar contenedores
docker-compose down
docker-compose up -d
```

---

## Problemas de APIs Externas

### ❌ Problema: "REE API devuelve errores 500/503"
**Síntomas:**
- Logs muestran errores HTTP de la API REE
- Datos REE desactualizados

**Diagnóstico:**
```bash
# Verificar estado de API REE
curl -I "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"

# Verificar conectividad
ping apidatos.ree.es
```

**Solución:**
```bash
# 1. Esperar recuperación de API (común en REE)
# 2. Usar datos en caché o históricos
curl -X POST http://localhost:8000/init/historical-data

# 3. Verificar recuperación cada 30 minutos
watch -n 1800 'curl -X POST http://localhost:8000/ingest-now -d "{\"source\": \"ree\"}"'
```

### ❌ Problema: "OpenWeatherMap API key inválida"
**Síntomas:**
- Weather ingestion falla
- Logs muestran "API key invalid"

**Diagnóstico:**
```bash
# Verificar variable de entorno
docker exec chocolate_factory_brain env | grep OPENWEATHER

# Verificar API key manualmente
curl "http://api.openweathermap.org/data/2.5/weather?q=Linares,ES&appid=YOUR_API_KEY"
```

**Solución:**
```bash
# 1. Actualizar API key en docker-compose.yml
# 2. Reiniciar contenedor
docker-compose down
docker-compose up -d

# 3. Verificar funcionamiento
curl -X POST http://localhost:8000/ingest-now -d '{"source": "hybrid"}'
```

---

## Problemas de InfluxDB

### ❌ Problema: "Connection refused" a InfluxDB
**Síntomas:**
- FastAPI no puede conectar a InfluxDB
- Queries fallan en interfaz web

**Diagnóstico:**
```bash
# Verificar contenedor InfluxDB
docker ps | grep influxdb

# Verificar logs
docker logs chocolate_factory_storage

# Verificar conectividad
curl http://localhost:8086/health
```

**Solución:**
```bash
# 1. Reiniciar InfluxDB
docker restart chocolate_factory_storage

# 2. Verificar configuración de red
docker network ls
docker network inspect tfm-chocolate-factory_default

# 3. Reiniciar todo si persiste
docker-compose restart
```

### ❌ Problema: "Queries no devuelven datos"
**Síntomas:**
- Interface web InfluxDB funciona pero queries están vacías
- Bucket/organización correctos pero sin resultados

**Diagnóstico:**
```bash
# Verificar datos via API FastAPI
curl http://localhost:8000/influxdb/verify

# Verificar configuración de bucket
curl http://localhost:8086/api/v2/buckets -H "Authorization: Token YOUR_TOKEN"
```

**Solución:**
```bash
# 1. Verificar organización y bucket en query
# Organization: chocolate_factory
# Bucket: energy_data

# 2. Query de prueba simple
from(bucket: "energy_data")
  |> range(start: -24h)
  |> limit(n: 1)

# 3. Si no hay datos, reinicializar
curl -X POST http://localhost:8000/init/all
```

---

## Problemas de Scheduler

### ❌ Problema: "Scheduler corriendo pero jobs no ejecutan"
**Síntomas:**
- `scheduler.status = "running"`
- `run_count = 0` o no aumenta
- `next_run` en el pasado

**Diagnóstico:**
```bash
# Verificar estado detallado de jobs
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | {id: .id, next_run: .next_run, stats: .stats}'

# Verificar logs de scheduler
docker logs chocolate_factory_brain | grep -i "scheduler\|job\|apscheduler"
```

**Solución:**
```bash
# 1. Reiniciar contenedor FastAPI
docker restart chocolate_factory_brain

# 2. Verificar que scheduler reinicia correctamente
sleep 30
curl http://localhost:8000/scheduler/status

# 3. Forzar ejecución manual si persiste
curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}'
```

### ❌ Problema: "Jobs con alta tasa de errores"
**Síntomas:**
- `error_count > 0` en estadísticas
- `success_count` menor que `run_count`

**Diagnóstico:**
```bash
# Ver errores específicos
curl -s http://localhost:8000/scheduler/status | jq '.scheduler.jobs[] | select(.stats.error_count > 0) | {id: .id, errors: .stats.error_count, last_error: .stats.last_error}'

# Verificar logs de errores
docker logs chocolate_factory_brain | grep -i "error\|failed\|exception"
```

**Solución:**
```bash
# 1. Identificar causa del error en logs
# 2. Reiniciar servicios relacionados
# 3. Verificar APIs externas
# 4. Reinicializar si es necesario
```

---

## Recuperación de Desastres

### 🚨 Escenario: "Sistema completamente no funcional"
**Síntomas:**
- Múltiples contenedores fallando
- APIs no responden
- Datos corruptos o perdidos

**Recuperación Completa:**
```bash
# 1. Parar todo
docker-compose down

# 2. Limpiar sistema Docker
docker system prune -a -f
docker volume prune -f

# 3. Verificar espacio en disco
df -h

# 4. Reconstruir desde cero
docker-compose build --no-cache
docker-compose up -d

# 5. Esperar que todos los contenedores estén healthy
watch docker ps

# 6. Reinicializar datos
curl -X POST http://localhost:8000/init/all

# 7. Verificar funcionamiento
curl http://localhost:8000/init/status
```

### 🚨 Escenario: "Pérdida de datos históricos"
**Síntomas:**
- InfluxDB vacío o con pocos registros
- `historical_records = 0`

**Recuperación de Datos:**
```bash
# 1. Verificar si los archivos de datos existen
ls -la docker/services/influxdb/data/

# 2. Si existen, reiniciar InfluxDB
docker restart chocolate_factory_storage

# 3. Si no existen, reinicializar datos históricos
curl -X POST http://localhost:8000/init/historical-data

# 4. Monitorear progreso
watch 'curl -s http://localhost:8000/init/status | jq .status.historical_records'
```

---

## Scripts de Autorecuperación

### Script de Verificación y Autorecuperación
Crear `auto_recovery.sh`:
```bash
#!/bin/bash

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verificar contenedores
CONTAINERS_UP=$(docker ps --filter "name=chocolate_factory" | wc -l)
if [ $CONTAINERS_UP -lt 5 ]; then
    log "❌ Contenedores faltantes. Reiniciando..."
    docker-compose restart
    sleep 60
fi

# Verificar APIs
if ! curl -s http://localhost:8000/health > /dev/null; then
    log "❌ FastAPI no responde. Reiniciando contenedor..."
    docker restart chocolate_factory_brain
    sleep 30
fi

# Verificar scheduler
SCHEDULER_STATUS=$(curl -s http://localhost:8000/scheduler/status 2>/dev/null | jq -r '.scheduler.status // "unknown"')
if [ "$SCHEDULER_STATUS" != "running" ]; then
    log "❌ Scheduler no funciona. Reiniciando..."
    docker restart chocolate_factory_brain
    sleep 30
fi

# Verificar datos recientes
RECORDS=$(curl -s http://localhost:8000/influxdb/verify 2>/dev/null | jq -r '.total_records // 0')
if [ "$RECORDS" -lt 10 ]; then
    log "❌ Pocos datos en sistema. Ejecutando ingesta manual..."
    curl -X POST http://localhost:8000/ingest-now -d '{"source": "ree"}' > /dev/null 2>&1
fi

log "✅ Verificación completada. Sistema funcionando."
```

### Programar Autorecuperación con Cron
```bash
# Ejecutar cada 15 minutos
*/15 * * * * /path/to/auto_recovery.sh >> /var/log/chocolate_factory_recovery.log 2>&1
```

---

## Contactos de Soporte y Recursos

### Logs Importantes
- **FastAPI**: `docker logs chocolate_factory_brain`
- **InfluxDB**: `docker logs chocolate_factory_storage`
- **PostgreSQL**: `docker logs chocolate_factory_postgres`
- **MLflow**: `docker logs chocolate_factory_mlops`

### Archivos de Configuración
- **Docker Compose**: `docker-compose.yml`
- **FastAPI Config**: `src/fastapi-app/.env`
- **Datos InfluxDB**: `docker/services/influxdb/data/`

### APIs de Referencia
- **REE API**: https://www.ree.es/es/apidatos
- **AEMET API**: https://opendata.aemet.es/centrodedescargas/inicio
- **OpenWeatherMap**: https://openweathermap.org/api

### Comandos de Emergencia
```bash
# Parada de emergencia
docker-compose down

# Reinicio completo
docker-compose restart

# Limpiar y reconstruir
docker-compose down && docker system prune -a -f && docker-compose up -d
```