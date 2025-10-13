# Gitea Actions Workflows

Este directorio contiene los workflows de CI/CD para Gitea Actions (compatible con GitHub Actions).

## 📁 Estructura

```
.gitea/workflows/
├── README.md            # Este archivo
├── ci-cd-dual.yml      # Pipeline principal (develop/main → deploy)
└── quick-test.yml      # Tests rápidos (PRs y feature branches)
```

## 🎯 Workflows

### `ci-cd-dual.yml` - Pipeline Principal

**Propósito**: Build, test y deploy automático para develop y main

**Ejecuta en:**
- Push a `main` → Deploy a producción
- Push a `develop` → Deploy a desarrollo
- Pull Request a `main` o `develop` → Solo tests

**Jobs:**
1. `test-all`: Tests con pytest
2. `build-image`: Build y push a registry
3. `deploy-dev`: Deploy a desarrollo (solo rama develop)
4. `deploy-prod`: Deploy a producción (solo rama main)

**Runners requeridos:**
- `ubuntu-latest`: Para tests y build
- `dev`: Para deploy desarrollo
- `prod`: Para deploy producción

### `quick-test.yml` - Tests Rápidos

**Propósito**: Feedback rápido en PRs y feature branches

**Ejecuta en:**
- Pull Requests
- Push a `feature/**`, `hotfix/**`, `bugfix/**`

**Jobs:**
1. `quick-test`: Tests básicos con pytest y lint

## 🚀 Cómo Activar

Los workflows se activan automáticamente al hacer push/PR. No requieren activación manual.

## 🔍 Ver Ejecuciones

1. Ve a Forgejo: http://git.azules-elver.ts.net/
2. Navega a tu repositorio
3. Click en "Actions" (menú superior)
4. Ver workflows, runs y logs

## ⚙️ Configuración

### Variables de Entorno

Definidas en cada workflow:
```yaml
env:
  REGISTRY: localhost:5000
  IMAGE_NAME: chocolate-factory
```

### Secrets (Futuro)

Configurar en Forgejo UI → Settings → Secrets:
- `REGISTRY_USER`: Usuario del registry
- `REGISTRY_PASSWORD`: Password del registry

## 📝 Sintaxis

Los workflows usan sintaxis de GitHub Actions (compatible con Gitea):
- **`on`**: Triggers del workflow
- **`jobs`**: Jobs a ejecutar
- **`runs-on`**: Runner donde ejecutar
- **`steps`**: Pasos del job
- **`uses`**: Acciones pre-hechas
- **`run`**: Comandos shell

## 🧪 Testing Local

Para testear workflows localmente, usa `act`:

```bash
# Instalar act
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash

# Ejecutar workflow localmente
act -W .gitea/workflows/quick-test.yml

# Ejecutar job específico
act -j quick-test -W .gitea/workflows/quick-test.yml
```

## 🔗 Referencias

- **Gitea Actions**: https://docs.gitea.com/usage/actions/overview
- **GitHub Actions Syntax**: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- **Act (local testing)**: https://github.com/nektos/act
