# CI/CD Pipeline - Dual Environment

Este documento explica el funcionamiento del pipeline CI/CD automatizado para desarrollo y producción.

## 🎯 Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                          GITEA ACTIONS                          │
│                     git.azules-elver.ts.net                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │    GIT PUSH (develop o main)            │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         JOB 1: TESTS                    │
        │  - Setup Python 3.11                    │
        │  - Install dependencies                 │
        │  - Run pytest                           │
        │  - Validate imports                     │
        └─────────────────────────────────────────┘
                              │
                    ✅ Tests passed
                              ▼
        ┌─────────────────────────────────────────┐
        │    JOB 2: BUILD & PUSH                  │
        │  - Determine tag (develop/production)   │
        │  - Build Docker image                   │
        │  - Push to registry                     │
        └─────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │   develop branch      │   │   main branch         │
    │   JOB 3: DEPLOY DEV   │   │   JOB 4: DEPLOY PROD  │
    │   - Pull image        │   │   - Pull image        │
    │   - docker compose    │   │   - docker compose    │
    │     -f dev.yml up     │   │     -f prod.yml up    │
    │   - Health check      │   │   - Health check      │
    └───────────────────────┘   └───────────────────────┘
            │                           │
            ▼                           ▼
    🟢 Development            🟢 Production
    localhost:8001           localhost:8000
```

## 📋 Workflows Disponibles

### 1. `ci-cd-dual.yml` - Pipeline Principal

**Triggers:**
- Push a `main` o `develop`
- Pull Request a `main` o `develop`

**Jobs:**

1. **test-all**
   - Ejecuta en: `ubuntu-latest` (cualquier runner)
   - Instala Python 3.11
   - Ejecuta tests con pytest
   - Valida imports de FastAPI

2. **build-image**
   - Ejecuta en: `ubuntu-latest`
   - Determina tag según rama:
     - `main` → tag `production`
     - `develop` → tag `develop`
   - Construye imagen Docker
   - Pushea a registry privado

3. **deploy-dev**
   - Ejecuta en: runner con etiqueta `dev`
   - Condición: `github.ref == 'refs/heads/develop'`
   - Pull de imagen `:develop`
   - Deploy con `docker-compose.dev.yml`
   - Health check en `:8001`

4. **deploy-prod**
   - Ejecuta en: runner con etiqueta `prod`
   - Condición: `github.ref == 'refs/heads/main'`
   - Pull de imagen `:production`
   - Deploy con `docker-compose.prod.yml`
   - Health check en `:8000`

### 2. `quick-test.yml` - Tests Rápidos

**Triggers:**
- Pull Requests
- Push a ramas `feature/**`, `hotfix/**`, `bugfix/**`

**Propósito:**
- Feedback rápido en PRs
- Validación antes de merge
- No despliega, solo testea

## 🚀 Flujo de Trabajo

### Desarrollo Normal

```bash
# 1. Crear rama feature
git checkout -b feature/nueva-funcionalidad

# 2. Hacer cambios
# ... editar código ...

# 3. Commit y push
git add .
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad

# 4. Crear PR hacia develop
# → Se ejecuta quick-test.yml
# → Revisar y aprobar PR

# 5. Merge a develop
# → Se ejecuta ci-cd-dual.yml
# → Despliega automáticamente en desarrollo
```

### Release a Producción

```bash
# 1. Verificar que develop está estable
curl http://localhost:8001/health

# 2. Crear PR de develop a main
git checkout main
git pull origin main
# En Forgejo UI: Create PR from develop to main

# 3. Revisar cambios en el PR
# → Se ejecuta quick-test.yml

# 4. Aprobar y merge
# → Se ejecuta ci-cd-dual.yml
# → Despliega automáticamente en producción
```

## 🔐 Configuración Requerida

### 1. Runners Configurados

Los runners deben tener las etiquetas correctas:

```yaml
# Runner desarrollo
GITEA_RUNNER_LABELS: dev,ubuntu-latest,ubuntu-22.04

# Runner producción
GITEA_RUNNER_LABELS: prod,ubuntu-latest,ubuntu-22.04
```

**Verificar en Forgejo UI:**
- http://localhost:3000/admin/actions/runners

### 2. Registry Credentials

El pipeline usa credenciales hardcoded (por ahora):
- Usuario: `admin`
- Password: `chocolateregistry123`

**TODO**: Migrar a secrets de Forgejo:
```yaml
- name: Login to registry
  run: |
    echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login ${{ env.REGISTRY }} -u ${{ secrets.REGISTRY_USER }} --password-stdin
```

### 3. Docker Compose Files

Los archivos deben estar en el repositorio:
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`

### 4. Docker Secrets

Los secrets deben existir en el host donde corre el runner:
```bash
ls -la docker/secrets/*.txt
```

## 📊 Monitoreo del Pipeline

### Ver Ejecuciones

En Forgejo UI:
1. Ir al repositorio
2. Click en "Actions" (menú superior)
3. Ver workflows ejecutados

### Logs en Tiempo Real

```bash
# Ver logs del runner desarrollo
docker logs chocolate_factory_runner_dev -f

# Ver logs del runner producción
docker logs chocolate_factory_runner_prod -f
```

### Verificar Despliegues

```bash
# Development
curl http://localhost:8001/health
docker compose -f docker-compose.dev.yml ps

# Production
curl http://localhost:8000/health
docker compose -f docker-compose.prod.yml ps
```

## ⚡ Troubleshooting

### Pipeline falla en "test-all"

**Causa**: Tests no pasan o dependencias faltantes

**Solución**:
```bash
# Ejecutar tests localmente
cd src/fastapi-app
pytest tests/ -v

# Verificar requirements.txt está actualizado
pip freeze > requirements.txt
```

### Pipeline falla en "build-image"

**Causa**: Dockerfile tiene errores o dependencias faltantes

**Solución**:
```bash
# Buildear localmente para debuggear
docker build -f docker/fastapi.Dockerfile -t test .

# Ver logs detallados
docker build --progress=plain -f docker/fastapi.Dockerfile .
```

### Pipeline falla en "deploy-dev" o "deploy-prod"

**Causa**:
- Compose file no existe
- Secrets no disponibles
- Puerto ya en uso

**Solución**:
```bash
# Verificar compose files
ls -la docker-compose.*.yml

# Verificar secrets
ls -la docker/secrets/*.txt

# Liberar puertos
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.prod.yml down
```

### Runner no aparece online

**Causa**: Runner no registrado o token inválido

**Solución**:
```bash
# Ver logs del runner
docker logs chocolate_factory_runner_dev

# Recrear con nuevo token
docker compose down gitea-runner-dev
# Generar nuevo token en Forgejo UI
# Actualizar RUNNER_TOKEN_DEV en .env
docker compose up -d gitea-runner-dev
```

## 🎯 Mejoras Futuras

### 1. Notifications

Añadir notificaciones a Slack/Discord:
```yaml
- name: Notify deployment
  uses: actions/notify@v1
  with:
    webhook: ${{ secrets.WEBHOOK_URL }}
    message: "✅ Deployed to production"
```

### 2. Rollback Automático

Si health check falla, volver a versión anterior:
```yaml
- name: Rollback on failure
  if: failure()
  run: |
    docker tag localhost:5000/chocolate-factory:production-previous localhost:5000/chocolate-factory:production
    docker compose -f docker-compose.prod.yml up -d
```

### 3. Smoke Tests

Añadir tests post-deployment:
```yaml
- name: Smoke tests
  run: |
    curl http://localhost:8000/health
    curl http://localhost:8000/dashboard/summary
    # ... más endpoints críticos
```

### 4. Staging Environment

Añadir tercer entorno:
- `develop` → Development
- `staging` → Staging (pre-producción)
- `main` → Production

### 5. Manual Approval para Producción

```yaml
deploy-prod:
  needs: build-image
  runs-on: prod
  environment:
    name: production
    # Requiere aprobación manual en Forgejo UI
```

## 📚 Referencias

- **Gitea Actions Docs**: https://docs.gitea.com/usage/actions/overview
- **GitHub Actions Syntax**: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- **Docker Compose**: https://docs.docker.com/compose/
- **Sprint 12 Docs**: `.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md`

---

**Última actualización**: 2025-10-13
**Versión**: 1.0
