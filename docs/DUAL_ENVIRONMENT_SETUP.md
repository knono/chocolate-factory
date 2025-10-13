# Dual Environment Setup - Development & Production

Esta guía explica cómo desplegar y gestionar los entornos de desarrollo y producción separados en nodos Tailscale independientes.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    TAILSCALE NETWORK                        │
│                   azules-elver.ts.net                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐ │
│  │  NODO GIT/CI/CD  │  │  NODO DESARROLLO │  │  NODO    │ │
│  │  git.azules...   │  │  chocolate-fa... │  │  PRODUCCIÓN│
│  │                  │  │  -dev.azules...  │  │  chocolate│
│  │                  │  │                  │  │  -factory │
│  │  - Forgejo       │  │  - FastAPI Dev   │  │  - FastAPI│
│  │  - Runners       │  │  - InfluxDB Dev  │  │    Prod   │
│  │  - Registry      │  │  - Hot Reload    │  │  - InfluxDB│
│  │                  │  │                  │  │    Prod   │
│  └──────────────────┘  └──────────────────┘  └──────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisitos

1. **Docker Secrets creados**:
   ```bash
   cd docker/secrets
   ./create_secrets.sh
   ```

2. **Imágenes en el registry**:
   ```bash
   # Tagear y pushear imágenes
   docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:develop
   docker push localhost:5000/chocolate-factory:develop

   docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:production
   docker push localhost:5000/chocolate-factory:production
   ```

3. **Nodos Tailscale activos**:
   - `chocolate-factory-dev.azules-elver.ts.net`
   - `chocolate-factory.azules-elver.ts.net`

## 🛠️ Despliegue

### Entorno de Desarrollo

**En el host o nodo de desarrollo:**

```bash
# 1. Descargar imagen
docker login localhost:5000 -u admin -p chocolateregistry123
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
- ✅ Hot reload activado
- ✅ Código fuente montado como bind mount
- ✅ Logs nivel DEBUG
- ✅ Puerto 8001 (para evitar conflicto con producción local)
- ✅ Base de datos InfluxDB independiente

### Entorno de Producción

**En el host o nodo de producción:**

```bash
# 1. Descargar imagen
docker login localhost:5000 -u admin -p chocolateregistry123
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

### Docker Secrets

Ambos entornos usan Docker Secrets para credenciales sensibles:

```yaml
secrets:
  - ree_api_token
  - aemet_api_key
  - openweathermap_api_key
  - anthropic_api_key
  - influxdb_token
  - influxdb_admin_password
```

Los secrets se leen desde archivos en `/run/secrets/` dentro de los contenedores.

### Variables de Entorno

**Desarrollo:**
- `ENVIRONMENT=development`
- `LOG_LEVEL=DEBUG`
- `INFLUXDB_ORG=chocolate-factory-dev`
- `INFLUXDB_BUCKET=energy_data_dev`

**Producción:**
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- `INFLUXDB_ORG=chocolate-factory`
- `INFLUXDB_BUCKET=energy_data`

## 🌐 Acceso via Tailscale

### Desarrollo
- **Local**: http://localhost:8001
- **Tailscale** (requiere sidecar nginx): http://chocolate-factory-dev.azules-elver.ts.net

### Producción
- **Local**: http://localhost:8000
- **Tailscale**: http://chocolate-factory.azules-elver.ts.net (con sidecar existente)

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
curl -u admin:chocolateregistry123 http://localhost:5000/v2/chocolate-factory/tags/list

# Si no existe, buildear y pushear
docker build -t localhost:5000/chocolate-factory:develop -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:develop
```

### Error: "secret not found"

```bash
# Verificar que los secrets existen
ls -la docker/secrets/*.txt

# Si no existen, generarlos
cd docker/secrets && ./create_secrets.sh
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

**Última actualización**: 2025-10-13
**Versión**: 1.0
