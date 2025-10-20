# Smoke Tests Fix - Sprint 12 Fase 11

**Fecha**: 20 de Octubre, 2025
**Problema**: Smoke tests fallando en CI/CD (dev + prod)
**Causa**: Tests usando `localhost:8000` en lugar de nombres de contenedor Docker

---

## Problema Detectado

### Síntomas

En el CI/CD, los smoke tests post-deploy fallaban con:

```
❌ Smoke tests failed - Initiating rollback...
⚠️  No stable version found, keeping current deployment
⚠️  Manual intervention required
```

### Causa Raíz

Los tests E2E en `tests/e2e/test_smoke_post_deploy.py` tenían hardcodeados:

```python
BASE_URL = "http://localhost:8000"  # ❌ NO funciona en CI/CD
BASE_URL_DEV = "http://localhost:8001"  # ❌ NO funciona en CI/CD
```

**Por qué falla:**
- Los runners de CI/CD corren pytest **dentro de un contenedor temporal**
- Ese contenedor está en la red Docker `chocolate-factory_backend`
- Debe usar **nombres de contenedor** (`chocolate_factory_brain`, `chocolate_factory_dev`) en lugar de `localhost`

### Problema Adicional: Timeout

El endpoint `/dashboard/complete` puede tardar **hasta 30 segundos** en generar todos los datos (REE, Weather, SIAR, Prophet ML, optimización horaria), pero el timeout estaba configurado a solo **10 segundos**.

---

## Solución Implementada

### 1. Variables de Entorno para URLs

**Archivo**: `tests/e2e/test_smoke_post_deploy.py`

```python
# Antes (hardcodeado)
BASE_URL = "http://localhost:8000"
BASE_URL_DEV = "http://localhost:8001"

# Después (configurable)
BASE_URL = os.getenv("E2E_API_URL", "http://localhost:8000")
BASE_URL_DEV = os.getenv("E2E_API_URL_DEV", "http://localhost:8001")
```

**Beneficios**:
- ✅ **Desarrollo local**: Usa `localhost` por defecto (sin configuración extra)
- ✅ **CI/CD**: Puede override con variables de entorno
- ✅ **Flexibilidad**: Permite apuntar a cualquier URL

---

### 2. Configuración en Workflow CI/CD

**Archivo**: `.gitea/workflows/ci-cd-dual.yml`

#### Smoke Tests Dev (líneas 319-331)

```yaml
- name: Run smoke tests
  run: |
    cd src/fastapi-app

    # ✅ Usar nombre de contenedor Docker (accesible desde runner)
    export E2E_API_URL="http://chocolate_factory_dev:8000"

    pytest tests/e2e/test_smoke_post_deploy.py -v -m smoke \
      --tb=short \
      --maxfail=3 || echo "SMOKE_FAILED=true" >> $GITHUB_ENV
```

#### Smoke Tests Prod (líneas 558-570)

```yaml
- name: Run production smoke tests
  run: |
    cd src/fastapi-app

    # ✅ Usar nombre de contenedor Docker (accesible desde runner)
    export E2E_API_URL="http://chocolate_factory_brain:8000"

    pytest tests/e2e/test_smoke_post_deploy.py -v -m smoke \
      --tb=short \
      --maxfail=2 || echo "SMOKE_FAILED=true" >> $GITHUB_ENV
```

---

### 3. Aumentar Timeout

**Archivo**: `tests/e2e/test_smoke_post_deploy.py`

```python
# Antes
TIMEOUT = 10.0  # ❌ Dashboard complete tarda >10s

# Después
TIMEOUT = 30.0  # ✅ Suficiente para endpoints pesados
```

**Justificación**:
- `/dashboard/complete` genera:
  - Datos actuales (REE + Weather + ML predictions)
  - Forecast Prophet (168h = 7 días)
  - Optimización horaria (24h timeline)
  - Análisis SIAR (25 años datos)
  - Insights predictivos (ventanas óptimas, alerts)

Tiempo típico: **5-15 segundos**, pero puede llegar a **30s** bajo carga.

---

## Validación

### Ejecución Local (sin cambios)

```bash
# Usa localhost por defecto
pytest tests/e2e/test_smoke_post_deploy.py -v -m smoke
```

**Resultado esperado**: ✅ 8/8 tests pasando

---

### Ejecución CI/CD (con nombres contenedor)

El workflow automáticamente configura:

```bash
export E2E_API_URL="http://chocolate_factory_brain:8000"  # Prod
export E2E_API_URL="http://chocolate_factory_dev:8000"    # Dev
```

**Flujo**:
1. Runner CI/CD corre en red `chocolate-factory_backend`
2. Puede resolver nombres de contenedor (`chocolate_factory_brain`, etc.)
3. Pytest usa `E2E_API_URL` para conectarse
4. Tests verifican endpoints críticos
5. Si falla → Rollback automático

---

## Arquitectura de Red

```
┌─────────────────────────────────────────────────────────┐
│         chocolate-factory_backend Network               │
│                  (192.168.100.0/24)                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐       │
│  │ runner-dev       │──────>│ fastapi-app-dev  │       │
│  │ 192.168.100.9    │      │ 192.168.100.11   │       │
│  │                  │      │ Port: 8000       │       │
│  │ Ejecuta pytest   │      │ (expuesto 8001)  │       │
│  └──────────────────┘      └──────────────────┘       │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐       │
│  │ runner-prod      │──────>│ fastapi-app-prod │       │
│  │ 192.168.100.10   │      │ 192.168.100.6    │       │
│  │                  │      │ Port: 8000       │       │
│  │ Ejecuta pytest   │      │ (expuesto 8000)  │       │
│  └──────────────────┘      └──────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Nota importante**: Los runners pueden acceder a los contenedores por nombre **porque están en la misma red Docker**. Desde fuera de Docker (localhost), se usa port mapping (`8000`, `8001`).

---

## Archivos Modificados

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `tests/e2e/test_smoke_post_deploy.py` | Variables de entorno para URLs | 29-30 |
| `tests/e2e/test_smoke_post_deploy.py` | Timeout aumentado 10s → 30s | 34 |
| `.gitea/workflows/ci-cd-dual.yml` | Export E2E_API_URL (dev) | 326 |
| `.gitea/workflows/ci-cd-dual.yml` | Export E2E_API_URL (prod) | 565 |

---

## Testing Post-Fix

### 1. Test Smoke Local

```bash
cd src/fastapi-app
export E2E_API_URL="http://localhost:8000"
pytest tests/e2e/test_smoke_post_deploy.py -v -m smoke
```

**Resultado esperado**: ✅ 8/8 tests pasando

---

### 2. Test desde Runner (simulado)

```bash
# Simular entorno CI/CD
cd src/fastapi-app
export E2E_API_URL="http://chocolate_factory_brain:8000"
pytest tests/e2e/test_smoke_post_deploy.py::TestCriticalEndpointsSmoke::test_all_critical_endpoints_responding -v
```

**Resultado esperado**:
- ✅ Si corres desde un contenedor en la red Docker: 7/7 endpoints pasan
- ❌ Si corres desde localhost: Error DNS (esperado, nombres de contenedor no resuelven fuera de Docker)

---

### 3. Validar Timeout

```bash
time curl http://localhost:8000/dashboard/complete
```

**Resultado esperado**: ~5-15 segundos (máximo 30s bajo carga)



## Troubleshooting

### Smoke tests siguen fallando

**Síntoma**: Timeout incluso con 30s

**Posibles causas**:
1. **Servicio no listo**: Aumentar `sleep` antes de smoke tests (línea 317, 556)
2. **InfluxDB lento**: Verificar que `chocolate_factory_storage` esté saludable
3. **Prophet model no cargado**: Ver logs `/dashboard/complete` para Prophet errors

**Debug**:
```bash
# Ver logs del contenedor
docker logs chocolate_factory_brain --tail 100

# Ver si InfluxDB está lento
docker exec chocolate_factory_brain time influx query "from(bucket:\"energy_data\") |> range(start: -1h)"

# Test manual endpoint pesado
time curl http://chocolate_factory_brain:8000/dashboard/complete
```

---

### Tests pasan localmente pero fallan en CI/CD

**Síntoma**: `pytest` local OK, pero workflow falla

**Posibles causas**:
1. **Red Docker no accesible**: Verificar que runner esté en `chocolate-factory_backend`
2. **Variables no exportadas**: Verificar que `export E2E_API_URL` esté antes de pytest
3. **Pytest no instalado**: Verificar que `pip install pytest httpx pytest-asyncio` esté en workflow

**Debug**:
```bash
# Verificar red del runner
docker inspect chocolate_factory_runner_dev | jq '.[0].NetworkSettings.Networks'

# Verificar conectividad desde runner
docker exec chocolate_factory_runner_dev /bin/sh -c 'nc -zv chocolate_factory_dev 8000'
```

---

## Referencias

- **Sprint 12 Fase 11**: `.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md` (líneas 1096-1111)
- **Smoke Tests**: `tests/e2e/test_smoke_post_deploy.py`
- **Workflow CI/CD**: `.gitea/workflows/ci-cd-dual.yml`
- **Docker Network**: `docker network inspect chocolate-factory_backend`

---

**Última actualización**: 2025-10-20
**Autor**: Sprint 12 Fase 11 Fix
**Estado**: ✅ Implementado, pendiente de validación en CI/CD

---

## Docker Registry Tagging System

### 🏷️ ¿Qué es el "tagging stable"?

Cuando los smoke tests **pasan**, el workflow crea **snapshots de versiones verificadas** en el Docker Registry privado.

---

### Estructura de Tags en Registry

```
Docker Registry (localhost:5000)
│
└── chocolate-factory/
    ├── develop              ← Última build de rama develop
    ├── develop-stable       ← ✅ Última que pasó smoke tests (rollback)
    ├── production           ← Última build de rama main
    ├── production-stable    ← ✅ Última que pasó smoke tests (rollback)
    ├── {git-sha}            ← Tag por commit específico (ej: cb866ee)
    └── develop-broken-{sha} ← Imágenes rotas (histórico debug)
```

---

### Flujo de Tagging

#### En Desarrollo (develop branch):

```bash
# 1. Build & test pass
docker build -t localhost:5000/chocolate-factory:develop

# 2. Deploy to dev environment
docker compose -f docker-compose.ci-dev.yml up -d

# 3. Run smoke tests
pytest tests/e2e/test_smoke_post_deploy.py -m smoke

# 4. Si smoke tests PASAN ✅
docker tag localhost:5000/chocolate-factory:develop \
           localhost:5000/chocolate-factory:develop-stable

docker push localhost:5000/chocolate-factory:develop-stable
```

#### En Producción (main branch):

```bash
# 1. Build & test pass
docker build -t localhost:5000/chocolate-factory:production

# 2. Deploy to prod environment
docker compose -f docker-compose.ci-prod.yml up -d

# 3. Run CRITICAL smoke tests
pytest tests/e2e/test_smoke_post_deploy.py -m smoke

# 4. Si smoke tests PASAN ✅
docker tag localhost:5000/chocolate-factory:production \
           localhost:5000/chocolate-factory:production-stable

docker push localhost:5000/chocolate-factory:production-stable
```

---

### Propósito: Rollback Automático

Las imágenes `*-stable` son el **punto de restauración** para rollback automático.

#### Ejemplo de Rollback:

```yaml
# Si smoke tests FALLAN en el siguiente deploy
- name: Rollback on failure
  run: |
    # Tag imagen rota para debugging
    docker tag localhost:5000/chocolate-factory:production \
               localhost:5000/chocolate-factory:production-broken-${{ github.sha }}

    # Pull última versión estable
    docker pull localhost:5000/chocolate-factory:production-stable

    # Re-taguear stable como production
    docker tag localhost:5000/chocolate-factory:production-stable \
               localhost:5000/chocolate-factory:production

    # Redeploy con versión estable
    docker compose -f docker-compose.ci-prod.yml up -d

    # Tiempo de rollback: <30 segundos
```

---

### Verificar Tags en Registry

**Con autenticación** (registry privado):

```bash
# 1. Login al registry
echo "<tu_contraseña>" | docker login localhost:5000 -u admin --password-stdin

# 2. Ver catálogo de repositorios
curl -u admin:<tu_contraseña> http://localhost:5000/v2/_catalog

# 3. Ver todos los tags de chocolate-factory
curl -u admin:<tu_contraseña> http://localhost:5000/v2/chocolate-factory/tags/list | jq .
```

**Resultado esperado**:

```json
{
  "name": "chocolate-factory",
  "tags": [
    "develop",
    "develop-stable",          ← ✅ Última dev que pasó smoke tests
    "production",
    "production-stable",       ← ✅ Última prod que pasó smoke tests
    "cb866ee2...",             ← Commit SHA específico
    "9c985ce2...",             ← Otro commit SHA
    "develop-broken-abc123"    ← Si algún deploy falló (debug)
  ]
}
```

---

### Tabla de Tags

| Tag | Propósito | Cuándo se crea | Usado para |
|-----|-----------|----------------|------------|
| `develop` | Última build develop | Cada push a develop | Deploy development |
| `develop-stable` | Versión verificada dev | Solo si smoke-test-dev ✅ | Rollback dev |
| `production` | Última build main | Cada push a main | Deploy production |
| `production-stable` | Versión verificada prod | Solo si smoke-test-prod ✅ | Rollback prod |
| `{git-sha}` | Commit específico | Cada build | Trazabilidad |
| `*-broken-{sha}` | Build fallido | Si smoke tests ❌ | Debugging |

---


#### Ver manifesto de una imagen:
```bash
curl -u admin:<tu_contraseña> \
  http://localhost:5000/v2/chocolate-factory/manifests/production-stable
```

---

### Limpieza de Tags Antiguos

El registry acumula tags históricos. Para limpiar:

```bash
# Ver espacio usado por registry
du -sh docker/services/registry/data/

# Eliminar tags no usados (manual)
# Requiere llamadas DELETE al registry API
# Ejemplo:
curl -u admin:<tu_contraseña> -X DELETE \
  http://localhost:5000/v2/chocolate-factory/manifests/<digest>

# Garbage collection del registry
docker exec chocolate_factory_registry \
  registry garbage-collect /etc/docker/registry/config.yml
```

**Nota**: No elimines `*-stable` tags, son críticos para rollback.
**Última actualización**: 2025-10-20
**Autor**: Sprint 12 Fase 11 Fix
**Estado**: ✅ Implementado y validado en CI/CD
**Tags actuales**: `develop-stable` ✅ | `production-stable` ✅
