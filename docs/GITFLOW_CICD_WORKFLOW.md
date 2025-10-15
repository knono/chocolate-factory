# Git Flow + CI/CD Workflow - Chocolate Factory

**Fecha**: 15 de Octubre, 2025
**Versión**: 1.0
**Status**: ✅ DOCUMENTACIÓN OFICIAL

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura de Ramas](#arquitectura-de-ramas)
3. [Workflow Completo](#workflow-completo)
4. [Casos de Uso Detallados](#casos-de-uso-detallados)
5. [Troubleshooting](#troubleshooting)
6. [Scripts de Automatización](#scripts-de-automatización)
7. [Mejores Prácticas](#mejores-prácticas)
8. [Checklist de Calidad](#checklist-de-calidad)

---

## Resumen Ejecutivo

Este documento describe el workflow oficial de **Git Flow + CI/CD Dual Environment** para el proyecto Chocolate Factory.

### Flujo de Trabajo

```
Feature → Develop (CI/CD DEV) → Release → Main (CI/CD PROD)
```

### Puntos Clave

- ✅ **Feature branches**: Desarrollo aislado sin CI/CD
- ✅ **Push a develop**: Dispara pipeline de **desarrollo** (puerto 8001)
- ✅ **Release finish**: Integra a main + develop, **te devuelve a develop**
- ✅ **Push a main**: Dispara pipeline de **producción** (puerto 8000)
- ✅ **Push a develop después de release**: Sincroniza back-merge
- ✅ **Hotfix**: Fix urgente que va a main + develop

### ⚠️ Comportamiento Importante de Git Flow

**Después de `git flow release finish` o `git flow hotfix finish`:**
- Git Flow **te devuelve automáticamente a `develop`** (no a `main`)
- Debes hacer `git checkout main` manualmente para pushear a producción
- Luego vuelves a `develop` para pushear el back-merge

Este es el **comportamiento por diseño** de Git Flow, ya que asume que tu flujo de trabajo continúa en `develop`.

---

## Arquitectura de Ramas

### Ramas Permanentes

```
main (producción)
  - Siempre deployable
  - Solo recibe merges de release/* y hotfix/*
  - Cada commit en main = nueva versión en producción
  - Tag vX.Y.Z en cada release

develop (pre-producción)
  - Integración continua de features
  - Recibe merges de feature/*
  - Testing en entorno de desarrollo
  - Base para releases
```

### Ramas Temporales

```
feature/*     - Nueva funcionalidad (desde develop)
release/*     - Preparación release (desde develop)
hotfix/*      - Fix urgente producción (desde main)
bugfix/*      - Fix no urgente (desde develop)
```

### Configuración Git Flow

```bash
git flow init -d

# Configuración resultante:
gitflow.branch.master = main
gitflow.branch.develop = develop
gitflow.prefix.feature = feature/
gitflow.prefix.release = release/
gitflow.prefix.hotfix = hotfix/
gitflow.prefix.bugfix = bugfix/
gitflow.prefix.versiontag = v
```

---

## Workflow Completo

### 1. Desarrollar Feature

```bash
# Paso 1: Actualizar develop
git checkout develop
git pull origin develop

# Paso 2: Iniciar feature
git flow feature start nombre-descriptivo
# Crea: feature/nombre-descriptivo desde develop

# Paso 3: Desarrollar (con hot-reload en http://localhost:8001)
# ... editar código ...

# Paso 4: Commits incrementales
git add .
git commit -m "feat: descripción del cambio"

# Paso 5 (Opcional): Backup remoto
git push origin feature/nombre-descriptivo
# ⚠️ NO dispara CI/CD, solo backup
```

**Estado en este punto**:
- Rama feature aislada
- Cambios visibles en desarrollo local
- Sin impacto en develop/main
- Sin ejecución de pipelines

### 2. Integrar Feature → Deploy DEV

```bash
# Paso 1: Asegurar que el código funciona
curl http://localhost:8001/health
# Navegar a http://localhost:8001/dashboard

# Paso 2: Finalizar feature
git flow feature finish nombre-descriptivo
# Git Flow hace:
#   a) Merge feature/nombre-descriptivo → develop
#   b) Borra rama feature/nombre-descriptivo
#   c) Te deja en develop

# Paso 3: Push a develop (DISPARA CI/CD DEV)
git push origin develop
```

**Pipeline Ejecutado**:

```yaml
# .gitea/workflows/ci-cd-dual.yml

on:
  push:
    branches: [develop]

jobs:
  test-all:
    runs-on: ubuntu-latest
    # Tests automáticos

  build-image:
    runs-on: ubuntu-latest
    # Build imagen con tag "develop"

  deploy-dev:
    runs-on: dev
    # Deploy a http://localhost:8001
```

**Verificación**:
```bash
# Ver pipeline
firefox http://localhost:3000/nono/chocolate-factory/actions

# Verificar despliegue
curl http://localhost:8001/health
docker logs chocolate_factory_dev --tail 50
```

### 3. Preparar Release

```bash
# Paso 1: Desde develop (después de feature finish)
git status
# On branch develop

# Paso 2: Iniciar release (ejemplo: 0.63.0)
git flow release start 0.63.0
# Crea: release/0.63.0 desde develop

# Paso 3 (Opcional): Ajustes finales
echo "0.63.0" > VERSION
git add VERSION
git commit -m "chore: bump version to 0.63.0"

# Actualizar CHANGELOG.md
cat >> CHANGELOG.md << 'EOF'
## [0.63.0] - 2025-10-15

### Added
- feat: descripción de features añadidas

### Fixed
- fix: correcciones incluidas

### Changed
- refactor: mejoras de código
EOF

git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for 0.63.0"
```

### 4. Finalizar Release → Deploy PROD

```bash
# Paso 1: Finalizar release
git flow release finish 0.63.0

# Git Flow te pregunta mensaje para el tag, escribe:
"""
Release 0.63.0 - Título del Release

### Features
- feat: descripción feature 1
- feat: descripción feature 2

### Fixes
- fix: corrección importante
- fix: otra corrección

### Performance
- perf: optimización X
"""

# Git Flow hace AUTOMÁTICAMENTE:
#   a) Merge release/0.63.0 → main
#   b) Crea tag v0.63.0 en main
#   c) Merge release/0.63.0 → develop (back-merge)
#   d) Borra rama release/0.63.0
#   e) Te deja en develop ✅ (COMPORTAMIENTO REAL)

# Paso 2: Verificar estado
git status
# On branch develop ← Git Flow te devuelve a develop

git log --oneline -5
# Debe mostrar el back-merge del release

# Paso 3: Cambiar a main para push de producción
git checkout main

# Paso 4: Push a main (DISPARA CI/CD PROD)
git push origin main --follow-tags
# --follow-tags envía también el tag v0.63.0

# Paso 5: Volver a develop
git checkout develop

# Paso 6: Push a develop (sincronizar back-merge)
git push origin develop
```

**Pipeline Ejecutado en PROD**:

```yaml
# .gitea/workflows/ci-cd-dual.yml

on:
  push:
    branches: [main]

jobs:
  test-all:
    runs-on: ubuntu-latest
    # Tests automáticos

  build-image:
    runs-on: ubuntu-latest
    # Build imagen con tag "production"

  deploy-prod:
    runs-on: prod
    # Deploy a http://localhost:8000
```

**Verificación**:
```bash
# Ver pipeline
firefox http://localhost:3000/nono/chocolate-factory/actions

# Verificar producción local
curl http://localhost:8000/health

# Verificar producción Tailscale
curl https://chocolate-factory.azules-elver.ts.net/health

# Ver tag creado
git tag -l -n1 v0.63.0
```

### 5. Hotfix Urgente

```bash
# Escenario: Bug crítico en producción que requiere fix inmediato

# Paso 1: Desde main
git checkout main
git pull origin main

# Paso 2: Iniciar hotfix
git flow hotfix start 0.63.1
# Crea: hotfix/0.63.1 desde main

# Paso 3: Aplicar fix
vim src/fastapi-app/api/routers/dashboard.py
git add .
git commit -m "fix: corregir error crítico en dashboard"

# Paso 4: Finalizar hotfix
git flow hotfix finish 0.63.1

# Mensaje del tag:
"""
Hotfix 0.63.1 - Fix Crítico Dashboard

### Fixed
- fix: corregir error que impedía carga del dashboard
"""

# Git Flow hace:
#   a) Merge hotfix/0.63.1 → main
#   b) Tag v0.63.1 en main
#   c) Merge hotfix/0.63.1 → develop (para no perder el fix)
#   d) Borra rama hotfix/0.63.1
#   e) Te deja en develop ✅ (COMPORTAMIENTO REAL)

# Paso 5: Verificar estado
git status
# On branch develop ← Git Flow te devuelve a develop

# Paso 6: Cambiar a main para push de producción
git checkout main

# Paso 7: Push a main (DISPARA CI/CD PROD INMEDIATO)
git push origin main --follow-tags

# Paso 8: Volver a develop y sincronizar
git checkout develop
git push origin develop
```

---

## Casos de Uso Detallados

### Caso 1: Feature con Múltiples Commits

```bash
# Iniciar feature
git flow feature start mejorar-predicciones

# Commit 1: Estructura base
git add src/fastapi-app/services/predictor_service.py
git commit -m "feat: añadir estructura base predictor"

# Commit 2: Lógica ML
git add src/fastapi-app/domain/ml/predictor.py
git commit -m "feat: implementar lógica predicción Prophet"

# Commit 3: Tests
git add src/fastapi-app/tests/test_predictor.py
git commit -m "test: añadir tests para predictor"

# Commit 4: Documentación
git add docs/API_REFERENCE.md
git commit -m "docs: documentar API predictor"

# Finalizar feature (todos los commits se fusionan)
git flow feature finish mejorar-predicciones

# Push a develop (dispara CI/CD)
git push origin develop
```

### Caso 2: Feature con Conflictos en Develop

```bash
# Estás en feature/mi-feature
git flow feature finish mi-feature

# ❌ CONFLICTO: Otros cambios en develop
# Auto-merging src/fastapi-app/main.py
# CONFLICT (content): Merge conflict in src/fastapi-app/main.py
# Automatic merge failed; fix conflicts and then commit the result.

# Resolver conflictos
vim src/fastapi-app/main.py
# ... resolver manualmente ...

# Marcar como resuelto
git add src/fastapi-app/main.py

# Completar merge
git commit -m "Merge feature/mi-feature into develop (resolved conflicts)"

# Ahora sí, push
git push origin develop
```

### Caso 3: Release con Rollback Necesario

```bash
# Has hecho release 0.64.0 y detectas bug crítico en producción
# Opción A: Hotfix inmediato (recomendado)

git checkout main
git flow hotfix start 0.64.1
# ... aplicar fix ...
git flow hotfix finish 0.64.1
git push origin main --follow-tags
git checkout develop && git push origin develop

# Opción B: Rollback a versión anterior

# 1. Ver tags disponibles
git tag -l

# 2. Checkout a versión anterior
git checkout v0.63.0

# 3. Crear tag temporal
git tag -a v0.64.1 -m "Rollback to 0.63.0"

# 4. Push (dispara CI/CD con código anterior)
git push origin v0.64.1

# 5. Volver a develop para fix definitivo
git checkout develop
```

### Caso 4: Cancelar Release en Progreso

```bash
# Has iniciado release pero necesitas cancelar
git flow release start 0.65.0

# ... decides que NO es el momento de release ...

# Opción A: Abortar release (Git Flow no tiene comando oficial)
git checkout develop
git branch -D release/0.65.0

# Opción B: Convertir en feature para seguir trabajando
git checkout develop
git branch feature/preparacion-0.65.0 release/0.65.0
git branch -D release/0.65.0
git checkout feature/preparacion-0.65.0
```

### Caso 5: Múltiples Features en Paralelo

```bash
# Desarrollador A: Feature dashboard
git flow feature start mejorar-dashboard
# ... trabajar ...
git flow feature finish mejorar-dashboard
git push origin develop  # CI/CD DEV ejecutado

# Desarrollador B: Feature API (en paralelo)
git checkout develop
git pull origin develop  # Obtener cambios de A
git flow feature start nueva-api
# ... trabajar ...
git flow feature finish nueva-api
git push origin develop  # CI/CD DEV ejecutado de nuevo

# Ambas features integradas en develop
# Luego release incluirá ambas:
git flow release start 0.66.0
git flow release finish 0.66.0
git push origin main --follow-tags
```

---

## Troubleshooting

### Problema 1: Pipeline Falla en Tests

**Síntoma**:
```bash
git push origin develop
# Pipeline falla en job "test-all"
```

**Diagnóstico**:
```bash
# Ver logs del pipeline
# http://localhost:3000/nono/chocolate-factory/actions

# Ejecutar tests localmente
cd src/fastapi-app
pytest tests/ -v --tb=short

# Ver errores específicos
pytest tests/test_api.py::test_health -vv
```

**Solución**:
```bash
# Fix del código
vim src/fastapi-app/api/routers/health.py

# Commit fix
git add .
git commit -m "fix: corregir test de health endpoint"

# Push de nuevo (dispara pipeline otra vez)
git push origin develop
```

### Problema 2: Olvidaste Pushear Develop Después de Release

**Síntoma**:
```bash
git flow release finish 0.67.0
git push origin main --follow-tags

# ❌ OLVIDASTE: git checkout develop && git push origin develop

# Otro desarrollador hace:
git checkout develop
git pull origin develop
# No ve el back-merge del release
```

**Solución**:
```bash
# Volver a develop
git checkout develop

# Verificar que tienes el back-merge localmente
git log --oneline -5
# Debe aparecer el merge de release/0.67.0

# Push ahora
git push origin develop

# Verificar sincronización
git log origin/develop --oneline -3
```

### Problema 3: Registry Unhealthy - Build Falla

**Síntoma**:
```bash
# Pipeline falla en "push image to registry"
# Error: connection refused localhost:5000
```

**Diagnóstico**:
```bash
# Verificar registry
docker ps | grep registry
# chocolate_factory_registry ... (unhealthy)

# Ver logs
docker logs chocolate_factory_registry --tail 50
```

**Solución**:
```bash
# Reiniciar registry
docker restart chocolate_factory_registry

# Esperar healthcheck
sleep 10

# Verificar
curl http://localhost:5000/v2/

# Re-ejecutar pipeline (push de nuevo)
git commit --allow-empty -m "chore: trigger pipeline"
git push origin develop
```

### Problema 4: SOPS Key No Configurada

**Síntoma**:
```bash
# Pipeline falla en "Decrypt secrets with SOPS"
# Error: no such key
```

**Solución**:
```bash
# 1. Generar clave age (si no existe)
mkdir -p .sops
age-keygen -o .sops/age-key.txt

# Ver clave privada
grep "AGE-SECRET-KEY" .sops/age-key.txt
# AGE-SECRET-KEY-1ABCD...

# 2. Añadir a Forgejo
# http://localhost:3000/nono/chocolate-factory/settings/secrets
# Name: SOPS_AGE_KEY
# Value: AGE-SECRET-KEY-1ABCD...

# 3. Ver clave pública
grep "public key" .sops/age-key.txt
# public key: age1xyz...

# 4. Encriptar secrets
export SOPS_AGE_RECIPIENTS=age1xyz...
sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml

# 5. Commitear archivo encriptado
git add secrets.enc.yaml
git commit -m "chore: add encrypted secrets"
git push origin develop
```

Ver documentación completa: [SOPS_SECRETS_MANAGEMENT.md](./SOPS_SECRETS_MANAGEMENT.md)

### Problema 5: Conflicto en Merge de Release

**Síntoma**:
```bash
git flow release finish 0.68.0

# CONFLICTO en el merge a main
# CONFLICT (content): Merge conflict in src/fastapi-app/main.py
```

**Solución**:
```bash
# 1. Resolver conflicto en main
vim src/fastapi-app/main.py
# ... resolver conflictos ...

# 2. Marcar como resuelto
git add src/fastapi-app/main.py

# 3. Continuar merge
git commit

# 4. Git Flow continuará automáticamente con:
#    - Tag del release
#    - Merge a develop

# Si también hay conflicto en develop:
# ... resolver de la misma manera ...

# 5. Verificar estado final
git status
# On branch main

# 6. Push
git push origin main --follow-tags
git checkout develop
git push origin develop
```

### Problema 6: Hot-Reload No Funciona en DEV

**Síntoma**:
```bash
# Editas código en src/fastapi-app/main.py
# Pero http://localhost:8001 NO refleja cambios
```

**Diagnóstico**:
```bash
# Verificar bind mounts
docker inspect chocolate_factory_dev | grep -A 5 Mounts

# Verificar que uvicorn tiene --reload
docker logs chocolate_factory_dev | grep reload
```

**Solución**:
```bash
# Verificar docker-compose.dev.yml tiene bind mounts
grep -A 10 "volumes:" docker-compose.dev.yml

# Debe incluir:
#   - ./src/fastapi-app/main.py:/app/main.py
#   - ./src/fastapi-app/api:/app/api
#   ... etc

# Si falta algún directorio, añadir y recrear
docker compose -f docker-compose.dev.yml up -d --force-recreate fastapi-app-dev

# Verificar logs de recarga
docker logs chocolate_factory_dev -f
# Debe mostrar: "Reloading..."
```

---

## Scripts de Automatización

### Script 1: Release Automatizado

Crea `scripts/release.sh`:

```bash
#!/bin/bash
# Automatizar proceso completo de release

set -e  # Exit on error

VERSION=$1
CHANGELOG_ENTRY=$2

if [ -z "$VERSION" ]; then
    echo "❌ Error: Debes especificar versión"
    echo "Uso: ./scripts/release.sh 0.63.0 'Descripción del release'"
    exit 1
fi

echo "🚀 Iniciando release $VERSION"

# 1. Asegurar que develop está actualizado
echo "📥 Actualizando develop..."
git checkout develop
git pull origin develop

# 2. Verificar que no hay cambios sin commitear
if [[ -n $(git status -s) ]]; then
    echo "❌ Error: Hay cambios sin commitear"
    git status -s
    exit 1
fi

# 3. Iniciar release
echo "🌿 Creando rama release/$VERSION..."
git flow release start $VERSION

# 4. Actualizar VERSION
echo "📝 Actualizando VERSION..."
echo "$VERSION" > VERSION
git add VERSION
git commit -m "chore: bump version to $VERSION"

# 5. Actualizar CHANGELOG si se proporcionó
if [ -n "$CHANGELOG_ENTRY" ]; then
    echo "📝 Actualizando CHANGELOG..."
    DATE=$(date +%Y-%m-%d)
    echo -e "\n## [$VERSION] - $DATE\n\n$CHANGELOG_ENTRY\n" | cat - CHANGELOG.md > temp && mv temp CHANGELOG.md
    git add CHANGELOG.md
    git commit -m "docs: update CHANGELOG for $VERSION"
fi

# 6. Finalizar release
echo "✅ Finalizando release..."
GIT_MERGE_AUTOEDIT=no git flow release finish -m "Release $VERSION" $VERSION

# 7. Push a ambas ramas
echo "📤 Pushing to main..."
git checkout main
git push origin main --follow-tags

echo "📤 Pushing to develop..."
git checkout develop
git push origin develop

echo ""
echo "✅ Release $VERSION completado exitosamente!"
echo ""
echo "🔗 Ver pipeline: http://localhost:3000/nono/chocolate-factory/actions"
echo "🏷️  Tag creado: v$VERSION"
echo ""
echo "Próximos pasos:"
echo "  - Verificar pipeline de producción"
echo "  - Probar en https://chocolate-factory.azules-elver.ts.net"
echo "  - Anunciar release al equipo"
```

**Uso**:
```bash
chmod +x scripts/release.sh

# Ejemplo 1: Release básico
./scripts/release.sh 0.63.0

# Ejemplo 2: Release con entrada de CHANGELOG
./scripts/release.sh 0.63.0 "### Added
- feat: nuevo predictor Prophet
- feat: dashboard mejorado

### Fixed
- fix: corrección bug crítico"
```

### Script 2: Hotfix Rápido

Crea `scripts/hotfix.sh`:

```bash
#!/bin/bash
# Automatizar hotfix urgente

set -e

VERSION=$1
DESCRIPTION=$2

if [ -z "$VERSION" ] || [ -z "$DESCRIPTION" ]; then
    echo "❌ Error: Faltan argumentos"
    echo "Uso: ./scripts/hotfix.sh 0.63.1 'Descripción del fix'"
    exit 1
fi

echo "🔥 Iniciando hotfix $VERSION"

# 1. Desde main
git checkout main
git pull origin main

# 2. Iniciar hotfix
git flow hotfix start $VERSION

# 3. Esperar a que usuario aplique fix
echo ""
echo "⏸️  Aplica el fix ahora. Cuando termines, presiona Enter para continuar..."
read -p ""

# 4. Verificar que hay cambios
if [[ -z $(git status -s) ]]; then
    echo "❌ Error: No hay cambios para commitear"
    exit 1
fi

# 5. Commit automático
git add -A
git commit -m "fix: $DESCRIPTION"

# 6. Finalizar hotfix
GIT_MERGE_AUTOEDIT=no git flow hotfix finish -m "Hotfix $VERSION - $DESCRIPTION" $VERSION

# 7. Push
git checkout main
git push origin main --follow-tags
git checkout develop
git push origin develop

echo ""
echo "✅ Hotfix $VERSION aplicado!"
echo "🔗 Ver pipeline: http://localhost:3000/nono/chocolate-factory/actions"
```

**Uso**:
```bash
chmod +x scripts/hotfix.sh

./scripts/hotfix.sh 0.63.1 "corregir error crítico dashboard"
# Script espera a que hagas el fix
# Luego presionas Enter y automatiza el resto
```

### Script 3: Verificar Estado Pre-Release

Crea `scripts/pre-release-check.sh`:

```bash
#!/bin/bash
# Checklist antes de release

echo "🔍 Ejecutando pre-release checks..."
echo ""

ERRORS=0

# 1. Tests
echo "🧪 Ejecutando tests..."
cd src/fastapi-app
if pytest tests/ -q; then
    echo "✅ Tests: PASSED"
else
    echo "❌ Tests: FAILED"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# 2. Desarrollo funcional
echo "🏥 Verificando salud de desarrollo..."
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo "✅ Development health: OK"
else
    echo "❌ Development health: FAILED"
    ERRORS=$((ERRORS + 1))
fi

# 3. Producción funcional
echo "🏥 Verificando salud de producción..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ Production health: OK"
else
    echo "❌ Production health: FAILED"
    ERRORS=$((ERRORS + 1))
fi

# 4. Registry operativo
echo "📦 Verificando registry..."
if curl -s http://localhost:5000/v2/ | grep -q "{}"; then
    echo "✅ Registry: OK"
else
    echo "⚠️  Registry: WARNING (might be unhealthy)"
fi

# 5. Runners conectados
echo "🏃 Verificando runners..."
if docker logs chocolate_factory_runner_dev 2>&1 | tail -5 | grep -q "declare successfully"; then
    echo "✅ Runner DEV: Connected"
else
    echo "❌ Runner DEV: NOT connected"
    ERRORS=$((ERRORS + 1))
fi

if docker logs chocolate_factory_runner_prod 2>&1 | tail -5 | grep -q "declare successfully"; then
    echo "✅ Runner PROD: Connected"
else
    echo "❌ Runner PROD: NOT connected"
    ERRORS=$((ERRORS + 1))
fi

# 6. Git status clean
echo "🌿 Verificando git status..."
if [[ -z $(git status -s) ]]; then
    echo "✅ Git status: Clean"
else
    echo "⚠️  Git status: Uncommitted changes"
    git status -s
fi

# 7. Branch correcto
echo "🌿 Verificando rama actual..."
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "develop" ]]; then
    echo "✅ Branch: develop (OK para release)"
else
    echo "⚠️  Branch: $CURRENT_BRANCH (debería ser develop)"
fi

echo ""
echo "=================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ TODOS LOS CHECKS PASARON"
    echo "✅ Listo para hacer release!"
    echo ""
    echo "Siguiente comando:"
    echo "  git flow release start X.Y.Z"
    exit 0
else
    echo "❌ $ERRORS CHECKS FALLARON"
    echo "❌ NO hacer release hasta resolver problemas"
    exit 1
fi
```

**Uso**:
```bash
chmod +x scripts/pre-release-check.sh

# Antes de cada release:
./scripts/pre-release-check.sh

# Si todo OK → proceder con release
# Si hay errores → resolver antes de release
```

### Script 4: Sync Fork (Para Repositorios Forked)

Crea `scripts/sync-fork.sh`:

```bash
#!/bin/bash
# Sincronizar fork con upstream (si aplica)

set -e

echo "🔄 Sincronizando fork con upstream..."

# 1. Añadir upstream si no existe
if ! git remote get-url upstream &>/dev/null; then
    echo "📥 Añadiendo remote upstream..."
    read -p "URL del repositorio upstream: " UPSTREAM_URL
    git remote add upstream "$UPSTREAM_URL"
fi

# 2. Fetch upstream
echo "📥 Fetching upstream..."
git fetch upstream

# 3. Merge a develop
echo "🔀 Merging upstream/develop..."
git checkout develop
git merge upstream/develop

# 4. Push a origin
echo "📤 Pushing to origin..."
git push origin develop

echo "✅ Fork sincronizado!"
```

---

## Mejores Prácticas

### 1. Convenciones de Nombres

**Features**:
```bash
# ✅ Bien
git flow feature start mejorar-dashboard
git flow feature start agregar-api-predictor
git flow feature start fix-bug-critico

# ❌ Mal
git flow feature start feature1
git flow feature start cambios
git flow feature start test
```

**Releases**:
```bash
# ✅ Bien (versionado semántico)
git flow release start 0.63.0   # Minor release
git flow release start 1.0.0    # Major release

# ❌ Mal
git flow release start release-octubre
git flow release start v1
```

**Hotfixes**:
```bash
# ✅ Bien
git flow hotfix start 0.63.1    # Patch version

# ❌ Mal
git flow hotfix start fix
git flow hotfix start hotfix-urgente
```

### 2. Mensajes de Commit (Conventional Commits)

```bash
# Formato: <tipo>(<scope>): <descripción>

# Features
git commit -m "feat: añadir predicción Prophet 7 días"
git commit -m "feat(dashboard): mejorar visualización gráficos"
git commit -m "feat(api): nuevo endpoint /predict/hourly"

# Fixes
git commit -m "fix: corregir cálculo eficiencia chocolate"
git commit -m "fix(ml): resolver error en entrenamiento modelo"
git commit -m "fix(dashboard): corregir tooltips no visibles"

# Docs
git commit -m "docs: actualizar README con nuevas APIs"
git commit -m "docs(api): añadir ejemplos de uso"

# Tests
git commit -m "test: añadir tests para backfill service"
git commit -m "test(ml): tests unitarios para predictor"

# Chores
git commit -m "chore: bump version to 0.63.0"
git commit -m "chore(deps): update dependencies"

# Refactor
git commit -m "refactor: reorganizar servicios ML"
git commit -m "refactor(api): simplificar routers"

# Performance
git commit -m "perf: optimizar consultas InfluxDB"
git commit -m "perf(ml): mejorar velocidad predicciones"

# Breaking changes
git commit -m "feat!: cambiar estructura API response

BREAKING CHANGE: El formato de respuesta de /predict
cambió de {prediction: float} a {value: float, confidence: float}"
```

### 3. Tamaño de Features

```bash
# ✅ Bien: Features pequeñas y enfocadas
git flow feature start mejorar-tooltips-dashboard
# ... solo cambios en tooltips ...
git flow feature finish mejorar-tooltips-dashboard

# ❌ Mal: Feature gigante con muchos cambios
git flow feature start mejoras-generales
# ... cambios en dashboard, API, ML, docs, tests ...
# Difícil de revisar, riesgoso
```

**Regla de oro**: Si la feature tarda >3 días, probablemente es muy grande. Dividirla.

### 4. Frecuencia de Releases

```bash
# ✅ Recomendado: Releases frecuentes y pequeños
Week 1: develop → 0.63.0 (2 features)
Week 2: develop → 0.64.0 (3 features)
Week 3: develop → 0.65.0 (1 feature + fixes)

# ⚠️  Evitar: Releases gigantes infrecuentes
Month 1-3: acumular 50 features
End of Q1: develop → 1.0.0 (release gigante)
# Riesgoso, difícil de rollback
```

### 5. Testing en Develop Antes de Release

```bash
# SIEMPRE probar en desarrollo ANTES de release

# 1. Feature integrada en develop
git flow feature finish mi-feature
git push origin develop
# ⬆️ CI/CD despliega a localhost:8001

# 2. Testing manual en desarrollo
curl http://localhost:8001/health
firefox http://localhost:8001/dashboard
# ... probar funcionalidad nueva ...

# 3. Si todo OK → release a producción
git flow release start 0.63.0
# ...

# 4. Si hay bugs → fix en develop primero
git checkout develop
# ... fix bugs ...
git add .
git commit -m "fix: corregir bug encontrado en testing"
git push origin develop
# ⬆️ CI/CD redespliega desarrollo
# Volver a probar
```

### 6. Documentar en el Código

```python
# ✅ Bien: Docstrings completos
def predict_energy_optimization(
    price: float,
    temperature: float,
    humidity: float
) -> float:
    """
    Predice el score de optimización energética.

    Args:
        price: Precio electricidad en €/kWh
        temperature: Temperatura en °C
        humidity: Humedad relativa en %

    Returns:
        Score de optimización (0-100)

    Example:
        >>> predict_energy_optimization(0.15, 22.0, 55.0)
        87.5

    Raises:
        ValueError: Si los parámetros están fuera de rango

    Since:
        v0.63.0
    """
    pass

# ❌ Mal: Sin documentación
def predict(p, t, h):
    pass
```

---

## Checklist de Calidad

### Pre-Feature Checklist

Antes de iniciar feature:

```bash
□ Estoy en develop actualizado
   → git checkout develop && git pull origin develop

□ Nombre de feature es descriptivo
   → git flow feature start nombre-descriptivo

□ Tengo claro el alcance de la feature
   → Escribir en issue/ticket qué incluye y qué NO

□ Desarrollo local funciona
   → http://localhost:8001 accesible
```

### Pre-Merge Feature Checklist

Antes de `git flow feature finish`:

```bash
□ Tests locales pasan
   → cd src/fastapi-app && pytest tests/ -v

□ Código formateado correctamente
   → ruff check src/fastapi-app/

□ No hay credenciales en el código
   → grep -r "password\|secret\|key" src/ (revisar resultados)

□ Funcionalidad probada en localhost:8001
   → Manual testing completo

□ Commits tienen mensajes descriptivos
   → git log --oneline feature/mi-feature

□ Documentación actualizada si aplica
   → README.md, API_REFERENCE.md, etc.
```

### Pre-Release Checklist

Antes de `git flow release start`:

```bash
□ Todas las features en develop funcionan
   → http://localhost:8001/health OK

□ Tests automáticos pasan
   → pytest src/fastapi-app/tests/ -v --cov

□ Pipeline de develop está verde
   → http://localhost:3000/actions (último run OK)

□ CHANGELOG actualizado con features nuevas
   → vim CHANGELOG.md

□ README actualizado si hay cambios en uso
   → vim README.md

□ No hay issues críticos abiertos
   → Revisar issues de GitHub/Forgejo

□ Runners están conectados
   → docker logs chocolate_factory_runner_* | grep "declare successfully"

□ Registry está healthy
   → curl http://localhost:5000/v2/
```

### Post-Release Checklist

Después de `git push origin main`:

```bash
□ Pipeline de producción ejecutado exitosamente
   → http://localhost:3000/actions (último run main OK)

□ Producción responde correctamente
   → curl http://localhost:8000/health
   → curl https://chocolate-factory.azules-elver.ts.net/health

□ Tag creado correctamente
   → git tag -l v* | tail -1

□ Develop sincronizado con back-merge
   → git checkout develop && git pull origin develop

□ Release anunciado al equipo
   → Slack/Email/Discord con release notes

□ Monitoreo post-deploy (primeras 24h)
   → docker logs chocolate_factory_brain
   → Verificar métricas de uso
```

---

## Referencias

- **Git Flow Original**: [nvie.com/posts/a-successful-git-branching-model](https://nvie.com/posts/a-successful-git-branching-model/)
- **Conventional Commits**: [conventionalcommits.org](https://www.conventionalcommits.org/)
- **Semantic Versioning**: [semver.org](https://semver.org/)
- **CI/CD Pipeline**: [CI_CD_PIPELINE.md](./CI_CD_PIPELINE.md)
- **Dual Environment**: [DUAL_ENVIRONMENT_SETUP.md](./DUAL_ENVIRONMENT_SETUP.md)
- **SOPS Secrets**: [SOPS_SECRETS_MANAGEMENT.md](./SOPS_SECRETS_MANAGEMENT.md)
- **Sprint 12 Docs**: [../.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md](../.claude/sprints/infrastructure/SPRINT_12_FORGEJO_CICD.md)

---

**Última actualización**: 2025-10-15
**Autor**: Sprint 12 - Forgejo CI/CD Implementation
**Versión**: 1.1

---

## 📝 Changelog

### v1.1 (2025-10-15)
- **🐛 Corrección importante**: Documentado el comportamiento real de `git flow release finish` y `git flow hotfix finish`
  - Git Flow te devuelve a `develop` (no a `main`) después de finalizar release/hotfix
  - Añadida sección explicativa sobre este comportamiento por diseño
  - Actualizado workflow con los pasos correctos: `git checkout main` manual necesario
  - Corregido en §4 (Finalizar Release) y §5 (Hotfix Urgente)

### v1.0 (2025-10-15)
- Versión inicial de la documentación oficial Git Flow + CI/CD
