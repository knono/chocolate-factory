# 🎯 SPRINT 12: Forgejo Self-Hosted + CI/CD Local

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 MEDIA
> **Prerequisito**: Sprint 11 completado (MCP server), Tailscale sidecar operacional
> **Duración estimada**: 1 semana (20-24 horas)
> **Fecha inicio planeada**: 2025-10-11

---

## 📋 Objetivo

**Desplegar Forgejo self-hosted** con CI/CD local (Gitea Actions) + Docker Registry privado, integrado con Tailscale para acceso seguro.

### ¿Por qué Forgejo?

Forgejo es un **fork community-driven de Gitea**, enfocado en:
- ✅ **Control total**: Datos en tu infraestructura
- ✅ **CI/CD nativo**: Gitea Actions (compatible GitHub Actions)
- ✅ **Lightweight**: ~100MB RAM, perfecto para self-hosting
- ✅ **Docker registry**: Incluido sin coste adicional
- ✅ **Open source**: Sin vendor lock-in

### Comparativa con Alternativas

| Feature | Forgejo | GitLab CE | Gitea | GitHub |
|---------|---------|-----------|-------|--------|
| RAM mínima | 100MB | 4GB | 100MB | N/A |
| CI/CD nativo | ✅ Actions | ✅ Pipelines | ✅ Actions | ✅ |
| Docker registry | ✅ Incluido | ✅ Incluido | ✅ Incluido | ✅ Paid |
| Self-hosted | ✅ Fácil | ⚠️ Complejo | ✅ Fácil | ❌ |
| Community-driven | ✅ | ❌ | ⚠️ | ❌ |

**Decisión**: Forgejo (mejor balance ligereza + features + filosofía open source)

---

## 📦 Entregables

### 1. Forgejo Instance (Docker)

**Archivo**: `docker/forgejo-compose.yml`

```yaml
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:1.21
    container_name: chocolate_factory_git
    ports:
      - "3000:3000"  # HTTP UI
      - "2222:22"    # SSH git push/pull
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEJO__database__DB_TYPE=sqlite3
      - FORGEJO__server__DOMAIN=${FORGEJO_DOMAIN:-localhost}
      - FORGEJO__server__ROOT_URL=https://${FORGEJO_DOMAIN:-localhost}/
      - FORGEJO__security__INSTALL_LOCK=true
    volumes:
      - ./services/forgejo/data:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### 2. Gitea Actions Runner (CI/CD)

**Archivo**: `docker/gitea-runner-compose.yml`

```yaml
services:
  gitea-runner:
    image: gitea/act_runner:latest
    container_name: chocolate_factory_runner
    environment:
      - GITEA_INSTANCE_URL=http://forgejo:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN}
      - GITEA_RUNNER_NAME=chocolate-runner-01
      - GITEA_RUNNER_LABELS=ubuntu-latest,docker
    volumes:
      - ./services/gitea-runner/data:/data
      - /var/run/docker.sock:/var/run/docker.sock  # Docker-in-Docker
    networks:
      - backend
    depends_on:
      - forgejo
    restart: unless-stopped
```

---

### 3. Docker Registry Privado

**Archivo**: `docker/registry-compose.yml`

```yaml
services:
  registry:
    image: registry:2.8
    container_name: chocolate_factory_registry
    ports:
      - "5000:5000"
    environment:
      - REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/var/lib/registry
      - REGISTRY_AUTH=htpasswd
      - REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd
      - REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm
    volumes:
      - ./services/registry/data:/var/lib/registry
      - ./services/registry/auth:/auth
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/v2/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### 4. Tailscale Integration

**Actualizar**: `docker/tailscale-sidecar.Dockerfile`

```dockerfile
# Añadir configuración nginx para Forgejo
upstream forgejo_backend {
    server forgejo:3000;
}

server {
    listen 443 ssl http2;
    server_name git.${TAILSCALE_DOMAIN};

    location / {
        proxy_pass http://forgejo_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 5. CI/CD Pipeline Templates

**Archivo**: `.forgejo/workflows/test.yml`

```yaml
name: Chocolate Factory - Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-api:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r src/fastapi-app/requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          cd src/fastapi-app
          pytest test_architecture.py test_foundation.py -v --cov

      - name: Test MCP server
        run: |
          cd mcp-server
          pytest test_mcp_tools.py -v

  build-docker:
    runs-on: ubuntu-latest
    needs: test-api
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -t localhost:5000/chocolate-factory:${{ github.sha }} -f docker/fastapi.Dockerfile .

      - name: Push to registry
        if: github.ref == 'refs/heads/main'
        run: |
          docker push localhost:5000/chocolate-factory:${{ github.sha }}
```

**Archivo**: `.forgejo/workflows/ml-validation.yml`

```yaml
name: ML Models Validation

on:
  push:
    paths:
      - 'src/fastapi-app/services/direct_ml.py'
      - 'src/fastapi-app/services/price_forecasting_service.py'
      - 'models/**'

jobs:
  validate-models:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ML dependencies
        run: |
          pip install scikit-learn prophet pandas numpy

      - name: Validate model files
        run: |
          python scripts/validate_ml_models.py

      - name: Test Prophet forecasting
        run: |
          pytest tests/test_price_forecasting.py -v

      - name: Check model metrics
        run: |
          python scripts/check_model_metrics.py --mae-threshold 0.05
```

---

### 6. Documentación Setup

**Archivo**: `docs/FORGEJO_SETUP.md`

**Contenido**:
- Instalación Forgejo + Runner
- Configuración SSH keys
- Setup Docker registry
- Configuración webhooks
- Ejemplos pipelines
- Troubleshooting

---

## 📝 Plan de Implementación

### Fase 1: Despliegue Forgejo (3-4 horas)

- [ ] Crear `docker/forgejo-compose.yml`
- [ ] Configurar volúmenes persistentes
- [ ] Iniciar servicio: `docker compose -f docker/forgejo-compose.yml up -d`
- [ ] Completar wizard instalación inicial (http://localhost:3000)
- [ ] Crear usuario admin
- [ ] Migrar repositorio desde GitHub (opcional)

### Fase 2: Configurar Gitea Actions Runner (2-3 horas)

- [ ] Generar registration token en Forgejo UI
- [ ] Crear `docker/gitea-runner-compose.yml`
- [ ] Iniciar runner: `docker compose -f docker/gitea-runner-compose.yml up -d`
- [ ] Verificar runner registrado en UI
- [ ] Test básico: crear pipeline "Hello World"

### Fase 3: Docker Registry Privado (2-3 horas)

- [ ] Generar htpasswd: `htpasswd -Bbn admin YOUR_PASSWORD_HERE > auth/htpasswd`
- [ ] Crear `docker/registry-compose.yml`
- [ ] Iniciar registry: `docker compose -f docker/registry-compose.yml up -d`
- [ ] Configurar Docker para usar registry insecure (localhost)
- [ ] Test push/pull imagen

### Fase 4: Integración Tailscale (3-4 horas)

- [ ] Actualizar `docker/sidecar-nginx.conf` con upstream Forgejo
- [ ] Añadir DNS `git.your-hostname.your-tailnet.ts.net`
- [ ] Configurar SSL con Tailscale ACME
- [ ] Verificar acceso remoto: `https://git.${TAILSCALE_DOMAIN}`
- [ ] Configurar SSH forwarding para git push/pull

### Fase 5: CI/CD Pipelines (4-6 horas)

- [ ] Crear directorio `.forgejo/workflows/`
- [ ] Implementar `test.yml` (tests Python + Docker build)
- [ ] Implementar `ml-validation.yml` (validación modelos ML)
- [ ] Configurar secrets en Forgejo (tokens, passwords)
- [ ] Test pipeline completo: push → tests → build → registry

### Fase 6: Scripts Validación ML (3-4 horas)

**Archivo**: `scripts/validate_ml_models.py`

```python
#!/usr/bin/env python3
"""Validate ML model files integrity."""

import pickle
from pathlib import Path

def validate_models():
    models_dir = Path("models")
    required_models = [
        "energy_optimization.pkl",
        "production_classifier.pkl",
        "prophet_price_model.pkl"
    ]

    for model_file in required_models:
        model_path = models_dir / model_file
        assert model_path.exists(), f"Missing model: {model_file}"

        # Try loading
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        print(f"✓ {model_file} is valid")

if __name__ == "__main__":
    validate_models()
```

**Archivo**: `scripts/check_model_metrics.py`

```python
#!/usr/bin/env python3
"""Check ML model metrics meet thresholds."""

import argparse
from services.direct_ml import DirectMLService

def check_metrics(mae_threshold: float = 0.05):
    ml_service = DirectMLService()
    status = ml_service.get_model_status()

    # Check energy model
    energy_mae = status["energy_model"]["metrics"]["mae"]
    assert energy_mae < mae_threshold, f"Energy MAE {energy_mae} > {mae_threshold}"

    # Check production model
    prod_accuracy = status["production_model"]["metrics"]["accuracy"]
    assert prod_accuracy > 0.85, f"Production accuracy {prod_accuracy} < 0.85"

    print(f"✓ All metrics pass thresholds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mae-threshold", type=float, default=0.05)
    args = parser.parse_args()
    check_metrics(args.mae_threshold)
```

### Fase 7: Documentación (2-3 horas)

- [ ] Escribir `docs/FORGEJO_SETUP.md`
- [ ] Documentar flujo CI/CD completo
- [ ] Guía migración desde GitHub
- [ ] Troubleshooting común
- [ ] Actualizar CLAUDE.md

---

## 🧪 Criterios de Éxito

### Tests Funcionales

1. **Test Forgejo accesible**:
   ```bash
   curl http://localhost:3000/api/healthz
   # Expected: HTTP 200
   ```

2. **Test pipeline CI/CD**:
   ```bash
   # Push código → trigger pipeline
   git push forgejo main
   # Verificar en UI: pipeline ejecuta, tests pasan, imagen buildeada
   ```

3. **Test Docker registry**:
   ```bash
   docker pull localhost:5000/chocolate-factory:latest
   # Expected: imagen descargada correctamente
   ```

4. **Test acceso Tailnet**:
   ```bash
   curl https://git.your-hostname.your-tailnet.ts.net/api/healthz
   # Expected: HTTP 200 via Tailscale
   ```

### Métricas de Éxito

- ✅ Forgejo operacional con UI accesible
- ✅ Runner CI/CD registrado y funcional
- ✅ Al menos 2 pipelines creados y testeados
- ✅ Docker registry acepta push/pull
- ✅ Acceso Tailnet con SSL funcionando
- ✅ Documentación completa

---

## 🚧 Problemas Potenciales

### Problema 1: Runner no se registra

**Síntomas**: Runner offline en Forgejo UI

**Solución**:
```bash
# Regenerar token
# Forgejo UI: Site Administration → Actions → Runners → Create token

# Verificar logs runner
docker logs chocolate_factory_runner

# Reiniciar runner
docker restart chocolate_factory_runner
```

### Problema 2: Docker registry rechaza push

**Síntomas**: "unauthorized" al hacer docker push

**Solución**:
```bash
# Login al registry
docker login localhost:5000 -u admin -p YOUR_PASSWORD_HERE

# Verificar /etc/docker/daemon.json
{
  "insecure-registries": ["localhost:5000"]
}

# Restart Docker daemon
sudo systemctl restart docker
```

### Problema 3: Pipeline falla con "permission denied"

**Síntomas**: Pipeline no puede ejecutar Docker commands

**Solución**:
```bash
# Verificar runner tiene acceso a Docker socket
ls -la /var/run/docker.sock

# Ajustar permisos si necesario
sudo chmod 666 /var/run/docker.sock  # Temporal
# O añadir usuario runner al grupo docker
```

### Problema 4: Tailscale no expone Forgejo

**Síntomas**: `https://git.${TAILSCALE_DOMAIN}` retorna 502

**Solución**:
```bash
# Verificar nginx config
docker exec chocolate-factory cat /etc/nginx/nginx.conf

# Test upstream Forgejo accesible desde sidecar
docker exec chocolate-factory curl http://forgejo:3000/api/healthz

# Reiniciar sidecar
docker restart chocolate-factory
```

---

## 📊 Valor del Sprint 12

### Beneficios Inmediatos

1. **Control total datos**: Git repos en tu infraestructura
2. **CI/CD automatizado**: Tests corren en cada push
3. **Registry privado**: Imágenes Docker sin Docker Hub
4. **Integración Tailnet**: Acceso seguro remoto
5. **Detección temprana bugs**: Pipeline valida antes de deploy

### Casos de Uso Reales

#### Caso 1: Validación automática ML models

```yaml
# Push nuevo modelo → pipeline valida
# Si MAE > threshold → pipeline falla → no merge
# Si MAE OK → auto-merge → deploy

# Antes (manual):
# 1. Entrenar modelo
# 2. Copiar .pkl a servidor
# 3. Reiniciar FastAPI
# 4. Verificar métricas manualmente

# Después (automatizado):
# 1. git push
# (Pipeline hace pasos 2-4 automáticamente)
```

#### Caso 2: Docker images versionadas

```bash
# Cada commit main → imagen taggeada con SHA
localhost:5000/chocolate-factory:abc123d  # Commit SHA
localhost:5000/chocolate-factory:v0.42.0  # Tag release
localhost:5000/chocolate-factory:latest   # Main branch

# Rollback instantáneo si falla deploy:
docker-compose pull chocolate-factory:previous_sha
docker-compose up -d
```

#### Caso 3: Tests pre-merge obligatorios

```yaml
# Configurar branch protection en Forgejo
# → PR no mergeable hasta tests pasen
# → Evita romper main branch
```

---

## 🔄 Integración con Sprint 11 (MCP)

### MCP Server en CI/CD

```yaml
# .forgejo/workflows/test-mcp.yml
name: Test MCP Server

on:
  push:
    paths:
      - 'mcp-server/**'

jobs:
  test-mcp-tools:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install MCP dependencies
        run: pip install mcp anthropic-mcp httpx pytest

      - name: Test MCP tools
        run: |
          cd mcp-server
          pytest test_mcp_tools.py -v --cov

      - name: Validate tool schemas
        run: python mcp-server/validate_schemas.py
```

---

## 🔐 Seguridad

### Secrets Management

```bash
# Almacenar secrets en Forgejo (no en código)
# Site Administration → Actions → Secrets

# Ejemplos:
INFLUXDB_TOKEN=xxx
AEMET_API_KEY=xxx
DOCKER_REGISTRY_PASSWORD=xxx
TAILSCALE_AUTHKEY=xxx
```

### Network Isolation

```yaml
# docker-compose.yml
networks:
  backend:
    internal: true  # No acceso internet directo

  internet:
    # Solo servicios que necesitan internet (Forgejo, runner)
```

---

## 📚 Referencias

- **Forgejo Docs**: https://forgejo.org/docs/
- **Gitea Actions**: https://docs.gitea.com/usage/actions/overview
- **Docker Registry**: https://docs.docker.com/registry/
- **Tailscale ACME**: https://tailscale.com/kb/1153/enabling-https

---

## 🚀 Próximos Pasos después Sprint 12

### Sprint 13 (Monitoring) - Opcional
- Prometheus + Grafana
- Métricas custom FastAPI
- Alerting Telegram/Discord

### Extensiones Forgejo
- Webhooks para Telegram (notificaciones push)
- Integración Woodpecker CI (alternativa Gitea Actions)
- Forgejo CLI automation

---

**Fecha creación**: 2025-10-08
**Autor**: Infrastructure Sprint Planning
**Versión**: 1.0
**Sprint anterior**: Sprint 11 - MCP Server (planeado)
**Sprint siguiente**: Sprint 13 - Monitoring (opcional)
