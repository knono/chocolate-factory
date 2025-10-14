# Dual Environment Setup - Development & Production

Esta guía explica cómo desplegar y gestionar los entornos de desarrollo y producción separados en nodos Tailscale independientes.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                       TAILSCALE NETWORK                             │
│                      <your-tailnet>.ts.net                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  NODO GIT/CI/CD  │  │  NODO DESARROLLO │  │  NODO PRODUCCIÓN │ │
│  │  git.<tailnet>   │  │  chocolate-fa... │  │  chocolate-...   │ │
│  │                  │  │  -dev.<tailnet>  │  │  factory         │ │
│  │  - Forgejo       │  │                  │  │                  │ │
│  │  - Runners       │  │  - FastAPI Dev   │  │  - FastAPI Prod  │ │
│  │  - Registry      │  │    (Hot Reload)  │  │  - InfluxDB Prod │ │
│  │                  │  │  - Dashboard Dev │  │    (INGESTION)   │ │
│  │                  │  │    ───────┐      │  │                  │ │
│  │                  │  │           │      │  │                  │ │
│  │                  │  │           └──────┼──┼─> Lee datos ──┐  │ │
│  │                  │  │                  │  │                │  │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┼──┘ │
│                                                                 │    │
│  DEV: Solo desarrollo dashboard/APIs (NO ingesta)             │    │
│  PROD: Ingesta datos + servicio dashboard producción    <─────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisitos

1. **Archivo `.env` configurado**:
   ```bash
   cp .env.example .env
   # Editar .env con tus valores reales
   ```

2. **Docker Secrets creados**:
   ```bash
   cd docker/secrets
   ./create_secrets.sh
   # Verifica que se crearon con permisos 600
   ls -la *.txt
   ```

3. **Imágenes en el registry**:
   ```bash
   # Tagear y pushear imágenes
   docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:develop
   docker push localhost:5000/chocolate-factory:develop

   docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:production
   docker push localhost:5000/chocolate-factory:production
   ```

3. **Nodos Tailscale activos**:
   - `chocolate-factory-dev.<your-tailnet>.ts.net`
   - `chocolate-factory.<your-tailnet>.ts.net`

## 🛠️ Despliegue

### Entorno de Desarrollo

**En el host o nodo de desarrollo:**

```bash
# 1. Descargar imagen
docker login localhost:5000 -u admin -p <registry-password>
docker pull localhost:5000/chocolate-factory:develop

# 2. Desplegar servicios
docker compose -f docker-compose.dev.yml up -d

# 3. Verificar estado
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f fastapi-app-dev

# 4. Acceso local
curl http://localhost:8001/health
```

**Características del entorno de desarrollo:**
- ✅ Hot reload activado (cambios instantáneos en Python/HTML/CSS/JS)
- ✅ Código fuente montado como bind mount
- ✅ Logs nivel DEBUG para debugging detallado
- ✅ Puerto 8001 (para evitar conflicto con producción local)
- ⚠️ **Base de datos: USA LA MISMA InfluxDB de PRODUCCIÓN**
  - NO ingesta datos (evita duplicados y conflictos)
  - Solo CONSUME y TRANSFORMA datos existentes
  - Propósito: Desarrollo de dashboard, APIs y modelos ML con datos reales

### Entorno de Producción

**En el host o nodo de producción:**

```bash
# 1. Descargar imagen
docker login localhost:5000 -u admin -p <registry-password>
docker pull localhost:5000/chocolate-factory:production

# 2. Desplegar servicios
docker compose -f docker-compose.prod.yml up -d

# 3. Verificar estado
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f fastapi-app-prod

# 4. Acceso local
curl http://localhost:8000/health
```

**Características del entorno de producción:**
- ✅ Sin hot reload
- ✅ Código fuente inmutable (dentro de la imagen)
- ✅ Logs nivel INFO
- ✅ Puerto 8000 (estándar)
- ✅ Base de datos InfluxDB independiente
- ✅ Volúmenes read-only donde aplica

## 🔄 Workflow de Actualización

### Actualizar Desarrollo

```bash
# En CI/CD o local
docker build -t localhost:5000/chocolate-factory:develop -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:develop

# En nodo desarrollo
docker pull localhost:5000/chocolate-factory:develop
docker compose -f docker-compose.dev.yml up -d --no-deps fastapi-app-dev
```

### Actualizar Producción

```bash
# En CI/CD o local
docker build -t localhost:5000/chocolate-factory:production -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:production

# En nodo producción
docker pull localhost:5000/chocolate-factory:production
docker compose -f docker-compose.prod.yml up -d --no-deps fastapi-app-prod
```

## 🔐 Seguridad

### Docker Secrets ⚠️ IMPLEMENTADO CON FALLBACK

**Realidad actual**: Sistema híbrido que intenta Docker Secrets pero usa variables de entorno como fallback.

**Secrets configurados en compose**:
```yaml
secrets:
  - ree_api_token
  - aemet_api_key
  - openweathermap_api_key
  - anthropic_api_key
  - influxdb_token
  - influxdb_admin_password
```

**Cómo funciona REALMENTE**:
1. Los archivos de secrets están en `docker/secrets/*.txt` con permisos `600`
2. Docker Compose monta estos archivos en `/run/secrets/` dentro de los contenedores
3. ⚠️ **Problema**: Usuario `appuser` no puede leerlos (Permission denied)
4. ✅ **Solución automática**: El código Python hace fallback a variables del `.env`

**Orden de búsqueda** (`core/config.py`):
```python
# 1. Intenta /run/secrets/{secret_name} (Docker Swarm)
#    └─> ❌ Falla: Permission denied en Compose

# 2. Intenta ${SECRET}_FILE (variable apuntando a archivo)
#    └─> ⏭️  No definida, skip

# 3. Fallback a ${SECRET} (variable de entorno del .env)
#    └─> ✅ ÉXITO: Lee desde .env
```

**Ventajas del sistema actual**:
- ✅ Funciona en desarrollo (Docker Compose)
- ✅ Funcionará en producción (Docker Swarm sin cambios)
- ✅ Código robusto con fallback inteligente
- ⚠️ Seguridad media (mejor que antes, no óptima)

**Limitaciones actuales**:
- ⚠️ Secrets visibles en `docker inspect` (variables de entorno)
- ⚠️ No usa Docker Secrets nativos (problema de permisos)
- ✅ Preparado para Swarm futuro (sin cambios de código)

### Variables de Entorno vs Secrets (Realidad)

**Variables de entorno (no sensibles)**:

Desarrollo:
- `ENVIRONMENT=development`
- `LOG_LEVEL=DEBUG`
- `INFLUXDB_URL=http://chocolate_factory_storage:8086` ⚠️ **USA DB PRODUCCIÓN**
- `INFLUXDB_ORG=chocolate_factory` ⚠️ **Misma org que producción**
- `INFLUXDB_BUCKET=energy_data` ⚠️ **Mismo bucket que producción**

Producción:
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- `INFLUXDB_URL=http://influxdb:8086`
- `INFLUXDB_ORG=chocolate_factory`
- `INFLUXDB_BUCKET=energy_data`

**Secrets (sensibles - INTENTA archivos, USA variables)**:

Configuración compose:
```yaml
environment:
  - REE_API_TOKEN_FILE=/run/secrets/ree_api_token  # Intenta leer
  - AEMET_API_KEY_FILE=/run/secrets/aemet_api_key
  # ... etc
```

**Pero realmente usa**:
```bash
# Del archivo .env (fallback automático)
REE_API_TOKEN=valor_real
AEMET_API_KEY=valor_real
OPENWEATHERMAP_API_KEY=valor_real
ANTHROPIC_API_KEY=valor_real
INFLUXDB_TOKEN=valor_real
```

El código Python:
1. Intenta leer `/run/secrets/*` → Falla (Permission denied)
2. Hace fallback a variables de entorno del `.env` → ✅ Funciona

## 🌐 Acceso via Tailscale

### Desarrollo
- **Local**: http://localhost:8001
- **Tailscale** (requiere sidecar nginx): http://chocolate-factory-dev.<your-tailnet>.ts.net

### Producción
- **Local**: http://localhost:8000
- **Tailscale**: http://chocolate-factory.<your-tailnet>.ts.net (con sidecar existente)

## 📊 Monitoreo

### Verificar Salud de Desarrollo

```bash
# Healthcheck
curl http://localhost:8001/health

# Logs en tiempo real
docker compose -f docker-compose.dev.yml logs -f

# Estado de contenedores
docker compose -f docker-compose.dev.yml ps
```

### Verificar Salud de Producción

```bash
# Healthcheck
curl http://localhost:8000/health

# Logs (últimas 100 líneas)
docker compose -f docker-compose.prod.yml logs --tail=100

# Estado de contenedores
docker compose -f docker-compose.prod.yml ps
```

## 🧹 Limpieza y Mantenimiento

### Detener Entornos

```bash
# Desarrollo
docker compose -f docker-compose.dev.yml down

# Producción
docker compose -f docker-compose.prod.yml down
```

### Limpiar Volúmenes (⚠️ CUIDADO - Borra datos)

```bash
# Desarrollo
docker compose -f docker-compose.dev.yml down -v

# Producción
docker compose -f docker-compose.prod.yml down -v
```

### Backup de Datos

```bash
# Backup InfluxDB Desarrollo
docker run --rm -v chocolate-factory_influxdb_dev_data:/data -v $(pwd):/backup alpine tar czf /backup/influxdb-dev-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup InfluxDB Producción
docker run --rm -v chocolate-factory_influxdb_prod_data:/data -v $(pwd):/backup alpine tar czf /backup/influxdb-prod-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## ⚡ Troubleshooting

### Error: "no such image"

```bash
# Verificar que la imagen existe en el registry
curl -u admin:<registry-password> http://localhost:5000/v2/chocolate-factory/tags/list

# Si no existe, buildear y pushear
docker build -t localhost:5000/chocolate-factory:develop -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:develop
```

### Warning: "Failed to read secret from /run/secrets/X" (NORMAL)

**Este warning es ESPERADO y no es un error**:

```bash
⚠️  Failed to read secret from /run/secrets/influxdb_token: [Errno 13] Permission denied
```

**¿Por qué aparece?**
- Docker Compose monta secrets con permisos del host
- Usuario `appuser` del contenedor no puede leerlos
- **Sistema hace fallback automático a .env**

**¿Es un problema?**
- ❌ NO - La aplicación funciona correctamente
- ✅ Sistema carga credenciales desde `.env` (fallback)
- ✅ Aplicación arranca sin errores

**¿Cómo verificar que funciona?**
```bash
# 1. Ver logs de inicio
docker logs chocolate_factory_dev 2>&1 | grep -i "startup complete"
# Debe mostrar: INFO: Application startup complete.

# 2. Test health endpoint
curl http://localhost:8001/health
# Debe responder: {"status":"healthy", ...}

# 3. Verificar que usa .env (esperado)
docker logs chocolate_factory_dev 2>&1 | grep "WARNING.*not found"
# Verás warnings pero app funciona igual
```

### Error: "secret not found" o falla real

**Solo si la aplicación NO arranca**:

```bash
# 1. Verificar que .env existe y tiene valores
cat .env | grep -E "INFLUXDB_TOKEN|AEMET_API_KEY"

# 2. Si .env está vacío, configurarlo
cp .env.example .env
vim .env  # Editar con valores reales

# 3. Reiniciar contenedor
docker compose -f docker-compose.dev.yml restart fastapi-app-dev
```

### Error: "network dev-backend not found"

```bash
# Docker Compose crea la red automáticamente
# Si persiste, crear manualmente:
docker network create chocolate-factory_dev-backend
```

### Contenedor reiniciándose constantemente

```bash
# Ver logs detallados
docker compose -f docker-compose.dev.yml logs --tail=50 fastapi-app-dev

# Verificar healthcheck
docker inspect chocolate_factory_dev | grep -A 10 Health
```

## 📚 Referencias

- **Docker Compose Docs**: https://docs.docker.com/compose/
- **Docker Secrets**: https://docs.docker.com/engine/swarm/secrets/
- **Tailscale**: https://tailscale.com/kb/
- **Sprint 12 Documentation**: `.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`

---

**Última actualización**: 2025-10-14
**Versión**: 1.1

## 📝 Notas de Versión

### v1.1 (2025-10-14)
- ⚠️ **CAMBIO IMPORTANTE**: Entorno desarrollo ahora usa la misma InfluxDB de producción
- Propósito: Desarrollo de dashboard/APIs/ML con datos reales (NO ingesta)
- InfluxDB-dev deprecado (ya no se usa)
- Documentación actualizada con arquitectura revisada

### v1.0 (2025-10-13)
- Versión inicial con entornos separados
