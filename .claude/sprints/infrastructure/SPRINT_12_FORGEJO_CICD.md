# 🎯 SPRINT 12: Forgejo Self-Hosted + CI/CD con Tres Nodos Tailscale

> **Estado**: 🔴 NO INICIADO
> **Prioridad**: 🟡 MEDIA
> **Prerequisito**: Sprint 11 completado (Chatbot BI con RAG), Tailscale sidecar operacional
> **Duración estimada**: 1.5-2 semanas (30-40 horas)
> **Fecha inicio planeada**: 2025-10-13

---

## 📋 Objetivo Principal

Desplegar Forgejo self-hosted con CI/CD local (Gitea Actions) + Docker Registry privado, integrado con **TRES nodos Tailscale** separados:
- **Git/CI/CD**: `git.chocolate-factory.ts.net` (servidor Forgejo + runners + registry)
- **Desarrollo**: `chocolate-factory-dev.ts.net` (rama `develop`)
- **Producción**: `chocolate-factory.ts.net` (rama `main`)

### ¿Por qué Tres Nodos?

- ✅ **Aislamiento completo**: Servidor Git separado de las aplicaciones
- ✅ **Control de Acceso**: ACLs por nodo para diferentes niveles de acceso
- ✅ **Seguridad aumentada**: Compromiso en un nodo no afecta a otros
- ✅ **Gestión independiente**: Puedes actualizar Forgejo sin afectar apps
- ✅ **Escalabilidad**: Cada nodo puede tener recursos ajustados a su función

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

### 1. Forgejo Instance (Nodo Git/CI/CD)

**Archivo**: `docker/forgejo-compose.yml`

```yaml
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:1.21
    container_name: chocolate_factory_git
    ports:
      - "3000:3000"
      - "2222:22"
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEJO__database__DB_TYPE=sqlite3
      - FORGEJO__server__DOMAIN=${FORGEJO_DOMAIN:-git.chocolate-factory.ts.net}
      - FORGEJO__server__ROOT_URL=https://${FORGEJO_DOMAIN:-git.chocolate-factory.ts.net}/
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

### 2. Gitea Actions Runners Diferenciados

**Archivo**: `docker/gitea-runners-compose.yml`

```yaml
services:
  gitea-runner-dev:
    image: gitea/act_runner:latest
    container_name: chocolate_factory_runner_dev
    environment:
      - GITEA_INSTANCE_URL=http://forgejo:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN_DEV}
      - GITEA_RUNNER_NAME=chocolate-dev-runner
      - GITEA_RUNNER_LABELS=dev,ubuntu-latest,docker
    volumes:
      - ./services/gitea-runner/dev-data:/data
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - backend
    depends_on:
      - forgejo
    restart: unless-stopped

  gitea-runner-prod:
    image: gitea/act_runner:latest
    container_name: chocolate_factory_runner_prod
    environment:
      - GITEA_INSTANCE_URL=http://forgejo:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN_PROD}
      - GITEA_RUNNER_NAME=chocolate-prod-runner
      - GITEA_RUNNER_LABELS=prod,ubuntu-latest,docker
    volumes:
      - ./services/gitea-runner/prod-data:/data
      - /var/run/docker.sock:/var/run/docker.sock
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

### 4. Entornos Separados (Desarrollo vs Producción)

**Desarrollo** (`docker-compose.dev.yml`):
```yaml
services:
  fastapi-app-dev:
    image: localhost:5000/chocolate-factory:develop
    container_name: chocolate_factory_dev
    ports:
      - "8001:8000"
    environment:
      - ENVIRONMENT=development
      - APP_NAME=chocolate-factory-dev
    volumes:
      - ./src/fastapi-app:/app
      - ./models:/app/models
    networks:
      - frontend
      - backend
    restart: unless-stopped

  influxdb-dev:
    image: influxdb:2.7
    container_name: influxdb_dev
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
    volumes:
      - ./docker/services/influxdb/dev-data:/var/lib/influxdb2
    networks:
      - backend
    restart: unless-stopped
```

**Producción** (`docker-compose.prod.yml`):
```yaml
services:
  fastapi-app-prod:
    image: localhost:5000/chocolate-factory:production
    container_name: chocolate_factory_prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - APP_NAME=chocolate-factory-prod
    volumes:
      - ./models:/app/models
    networks:
      - frontend
      - backend
    restart: unless-stopped

  influxdb-prod:
    image: influxdb:2.7
    container_name: influxdb_prod
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
    volumes:
      - ./docker/services/influxdb/prod-data:/var/lib/influxdb2
    networks:
      - backend
    restart: unless-stopped
```

---

### 5. CI/CD Dual Environment

**Archivo**: `.gitea/workflows/ci-cd-dual.yml`

```yaml
name: Chocolate Factory CI/CD Dual Environment

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test-all:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r src/fastapi-app/requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest src/fastapi-app/ -v --cov

  build-image:
    needs: test-all
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - branch: main
            tag: production
          - branch: develop
            tag: develop
    steps:
      - uses: actions/checkout@v3
      - name: Build and push image
        run: |
          docker build -t localhost:5000/chocolate-factory:${{ matrix.tag }} -f docker/fastapi.Dockerfile .
          docker push localhost:5000/chocolate-factory:${{ matrix.tag }}

  deploy-dev:
    needs: build-image
    runs-on: dev  # Usará runners con etiqueta "dev"
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to development
        run: |
          # Asumiendo que este pipeline se ejecuta en el nodo desarrollo
          docker pull localhost:5000/chocolate-factory:develop
          docker-compose -f docker-compose.dev.yml down
          docker-compose -f docker-compose.dev.yml up -d
      - name: Notification to dev channel
        run: |
          # Notificar a canal de desarrollo
          echo "Desarrollo actualizado con commit ${{ github.sha }}"

  deploy-prod:
    needs: build-image
    runs-on: prod  # Usará runners con etiqueta "prod"
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Asumiendo que este pipeline se ejecuta en el nodo producción
          docker pull localhost:5000/chocolate-factory:production
          docker-compose -f docker-compose.prod.yml down
          docker-compose -f docker-compose.prod.yml up -d
      - name: Notification to prod channel
        run: |
          # Notificar a canal de producción
          echo "Producción actualizado con commit ${{ github.sha }}"
```

---

### 6. Configuración de Tailscale con ACLs

**Archivo**: `tailscale-acls.json`

```json
{
  "acls": [
    {"action": "accept", "users": ["*"], "ports": ["*:*"]}
  ],
  "tagOwners": {
    "tag:git-server": ["group:admins"],
    "tag:dev-app": ["group:admins", "group:developers"],
    "tag:prod-app": ["group:admins"]
  },
  "hosts": {
    "git-server": "100.100.100.10",
    "dev-app": "100.100.100.11",
    "prod-app": "100.100.100.12"
  },
  "groups": {
    "group:admins": ["admin@yourdomain.com"],
    "group:developers": ["dev1@yourdomain.com", "dev2@yourdomain.com"]
  },
  "autoApprovers": {
    "routes": {
      "10.0.0.0/8": ["tag:git-server"]
    }
  }
}
```

**Nginx para Git/CI/CD** (`docker/sidecar-nginx-git.conf`):
```nginx
upstream forgejo_backend {
    server forgejo:3000;
}

server {
    listen 443 ssl http2;
    server_name git.chocolate-factory.ts.net;

    location / {
        proxy_pass http://forgejo_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Nginx para Desarrollo** (`docker/sidecar-nginx-dev.conf`):
```nginx
upstream fastapi_dev_backend {
    server fastapi-app-dev:8000;
}

server {
    listen 443 ssl http2;
    server_name chocolate-factory-dev.ts.net;

    location / {
        proxy_pass http://fastapi_dev_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Nginx para Producción** (`docker/sidecar-nginx-prod.conf`):
```nginx
upstream fastapi_prod_backend {
    server fastapi-app-prod:8000;
}

server {
    listen 443 ssl http2;
    server_name chocolate-factory.ts.net;

    location / {
        proxy_pass http://fastapi_prod_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 7. Configuración de Git Remotes Doble Destino

**Archivo**: `scripts/setup-dual-remotes.sh`

```bash
#!/bin/bash
# Configurar git para hacer push a ambos servidores

# Asegurar que ambos remotes están configurados
if ! git remote get-url forgejo &>/dev/null; then
    echo "Agregando remote forgejo..."
    git remote add forgejo https://git.chocolate-factory.ts.net/usuario/chocolate-factory.git
fi

# Configurar push a múltiples destinos para el remote 'origin'
git remote set-url --add --push origin https://github.com/usuario/chocolate-factory.git
git remote set-url --add --push origin https://git.chocolate-factory.ts.net/usuario/chocolate-factory.git

echo "Configuración completada. Ahora 'git push origin' enviará a ambos servidores."
```

---

### 8. Documentación Setup

**Archivo**: `docs/FORGEJO_SETUP.md`

**Contenido**:
- Instalación Forgejo + Runners diferenciados
- Configuración de tres nodos Tailscale con ACLs
- Configuración SSH keys
- Setup Docker registry
- Configuración doble entorno (desarrollo/producción)
- Configuración de ACLs por nodo
- Configuración git remotes dobles
- Ejemplos pipelines CI/CD dual
- Troubleshooting
- Guía de migración Git Flow

---

## 📝 Plan de Implementación

### Fase 1: Preparación Tailscale (3-4 horas)

- [ ] Crear 3 máquinas virtuales/contenedores separados
- [ ] Asignar diferentes auth keys de Tailscale
- [ ] Configurar ACLs en Tailscale console
- [ ] Asignar tags: `tag:git-server`, `tag:dev-app`, `tag:prod-app`
- [ ] Test conectividad entre nodos

### Fase 2: Despliegue Forgejo (4-5 horas)

- [ ] En nodo `tag:git-server` crear `docker/forgejo-compose.yml`
- [ ] Configurar volúmenes persistentes
- [ ] Iniciar servicio: `docker compose -f docker/forgejo-compose.yml up -d`
- [ ] Completar wizard instalación inicial
- [ ] Crear usuario admin con permisos diferenciados
- [ ] Configurar permisos de acceso (desarrollo vs producción)

### Fase 3: Runners Diferenciados (3-4 horas)

- [ ] Generar tokens de registro (dev y prod) en Forgejo UI
- [ ] Crear `docker/gitea-runners-compose.yml`
- [ ] Configurar runners con etiquetas diferenciadas (dev/prod)
- [ ] Iniciar ambos runners en nodo git
- [ ] Verificar que están registrados en UI con sus etiquetas
- [ ] Test runners desde nodos correspondientes

### Fase 4: Docker Registry Privado (2-3 horas)

- [ ] En nodo `tag:git-server` configurar htpasswd para autenticación
- [ ] Crear `docker/registry-compose.yml`
- [ ] Iniciar registry
- [ ] Configurar Docker para registry inseguro (localhost)
- [ ] Test push/pull imagen

### Fase 5: Entornos Separados (5-7 horas)

- [ ] En nodos correspondientes crear archivos `docker-compose.dev.yml` y `docker-compose.prod.yml`
- [ ] Configurar servicios con diferentes nombres, puertos y datos
- [ ] Implementar variables de entorno diferenciadas
- [ ] Test despliegue independiente de cada entorno
- [ ] Configurar sidecar nginx para cada nodo

### Fase 6: CI/CD Dual (5-7 horas)

- [ ] Crear workflow `.gitea/workflows/ci-cd-dual.yml`
- [ ] Configurar jobs con condiciones para cada rama
- [ ] Configurar runners específicos para cada entorno
- [ ] Implementar notificaciones diferenciadas
- [ ] Test completo: push develop → deploy dev, push main → deploy prod

### Fase 7: Configuración Git (1-2 horas)

- [ ] Crear script para configurar remotes dobles
- [ ] Documentar flujo de trabajo Git
- [ ] Configurar hooks si es necesario
- [ ] Validar push a ambos servidores

### Fase 8: Documentación y Pruebas (3-4 horas)

- [ ] Escribir `docs/FORGEJO_SETUP.md`
- [ ] Documentar flujo CI/CD dual
- [ ] Guía de migración de Git flow
- [ ] Actualizar CLAUDE.md con nueva arquitectura
- [ ] Test completo de extremo a extremo

---

## 🧪 Criterios de Éxito

### Tests Funcionales

1. **Forgejo operativo** en `git.chocolate-factory.ts.net`:
   ```bash
   curl https://git.chocolate-factory.ts.net/api/healthz
   # Expected: HTTP 200
   ```

2. **Runners registrados**:
   - Verificar que ambos runners están online con etiquetas `dev` y `prod`
   - Test pipelines usando diferentes etiquetas

3. **CI/CD funcional dual**:
   ```bash
   # Push a develop → despliega en entorno desarrollo
   git push origin develop
   # Verificar en UI y en chocolate-factory-dev.ts.net
   ```

   ```bash
   # Push a main → despliega en entorno producción
   git push origin main
   # Verificar en UI y en chocolate-factory.ts.net
   ```

4. **Registry funcional**:
   ```bash
   docker pull localhost:5000/chocolate-factory:develop
   docker pull localhost:5000/chocolate-factory:production
   # Expected: imágenes con ambos tags descargadas correctamente
   ```

5. **Acceso Tailscale triple**:
   ```bash
   curl https://git.chocolate-factory.ts.net/api/healthz
   curl https://chocolate-factory-dev.ts.net/api/healthz
   curl https://chocolate-factory.ts.net/api/healthz
   # Expected: HTTP 200 en los tres nodos
   ```

### Métricas de Éxito

- ✅ Tres nodos completamente aislados
- ✅ Control de acceso diferenciado por ACLs
- ✅ CI/CD automatizado para ambas ramas
- ✅ Push único a ambos servidores (GitHub + Forgejo)
- ✅ Acceso remoto separado para git, desarrollo y producción
- ✅ Documentación completa

---

## 🚧 Problemas Potenciales

### Problema 1: Comunicación entre nodos

**Síntomas**: Pipeline no puede desplegar en nodos remotos

**Solución**:
```bash
# Configurar runners para acceder a nodos remotos via Tailscale
# Usar IPs Tailscale o nombres de host internos
# Asegurar que ACLs permiten comunicación entre nodos
```

### Problema 2: Acceso al registry desde nodos remotos

**Síntomas**: Nodos de desarrollo/producción no pueden pull de registry

**Solución**:
```bash
# Configurar credenciales en nodos de destino
# O usar registry público dentro de Tailscale
# Asegurar que ACLs permiten acceso al registry
```

### Problema 3: DNS interno no resuelve

**Síntomas**: Nodos no pueden comunicarse por nombres

**Solución**:
```bash
# Usar IPs Tailscale directas
# O configurar DNS interno
# O usar /etc/hosts en cada nodo
```

---

## 📊 Valor del Sprint 12

### Beneficios Inmediatos

1. **Aislamiento completo**: Cada capa en su propio nodo
2. **Control de Acceso**: ACLs específicas por función
3. **Seguridad mejorada**: Aislamiento de compromisos
4. **CI/CD automatizado**: Tests y despliegues automáticos
5. **Backup dual**: Código en GitHub y Forgejo
6. **Escalabilidad**: Cada nodo puede dimensionarse independientemente

### Casos de Uso Reales

#### Caso 1: Gestión de accesos diferenciados

```bash
# Desarrolladores:
# - Acceso a git.chocolate-factory.ts.net (git, CI/CD)
# - Acceso a chocolate-factory-dev.ts.net (desarrollo)
# - Sin acceso a chocolate-factory.ts.net (producción)

# Administradores:
# - Acceso a todos los nodos
# - Pueden hacer deploy a producción
```

#### Caso 2: CI/CD seguro

```yaml
# Pipelines se ejecutan en nodos dedicados
# Despliegue solo a entornos autorizados
# Aislamiento de credenciales
```

#### Caso 3: Git Flow dual con ACLs

```bash
# Flujo de trabajo:
git checkout develop        # Trabajo en desarrollo
git push origin develop     # → CI/CD → despliegue en dev
git checkout main           # Fusión a producción
git merge develop           # → revisión de admins
git push origin main        # → CI/CD → despliegue en prod
```

---

## 🔄 Integración con Sprint 11 (Chatbot BI con RAG)

### Tests del Chatbot en CI/CD dual

```yaml
# .gitea/workflows/test-chatbot.yml
name: Test Chatbot BI (Claude Haiku)

on:
  push:
    paths:
      - 'src/fastapi-app/services/chatbot*.py'
      - 'src/fastapi-app/api/routers/chatbot.py'

jobs:
  test-chatbot-dev:
    runs-on: dev
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Install Chatbot dependencies
        run: pip install anthropic slowapi httpx pytest
      - name: Test Chatbot services in dev
        run: |
          cd src/fastapi-app
          pytest tests/test_chatbot_*.py -v --cov
      - name: Validate RAG context building
        run: python scripts/test_chatbot_integration.py

  test-chatbot-prod:
    runs-on: prod
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Install Chatbot dependencies
        run: pip install anthropic slowapi httpx pytest
      - name: Test Chatbot services in prod
        run: |
          cd src/fastapi-app
          pytest tests/test_chatbot_*.py -v --cov
      - name: Validate API Key and rate limiting
        run: curl -X POST http://localhost:8000/chat/health
```

**Nota importante**: Sprint 11 implementó un **chatbot con RAG local usando Claude Haiku API**, no un MCP server. El chatbot usa keyword matching para construcción de contexto inteligente.

---

## 🔐 Seguridad

### Seguridad de Acceso por Nodos

```bash
# Tailscale ACLs:
# tag:git-server → solo admins (gestión de código)
# tag:dev-app → admins + developers (acceso desarrollo)
# tag:prod-app → solo admins (acceso producción)
```

### Seguridad de Despliegue

```yaml
# Pipelines con acceso restringido:
deploy-dev:
  # Solo desarrolladores pueden desplegar en desarrollo
  # Validaciones mínimas

deploy-prod:
  # Solo admins pueden desplegar en producción
  # Validaciones exhaustivas
  # Confirmación manual opcional
```

---

## 📚 Referencias

- **Forgejo Docs**: https://forgejo.org/docs/
- **Gitea Actions**: https://docs.gitea.com/usage/actions/overview
- **Docker Registry**: https://docs.docker.com/registry/
- **Tailscale ACLs**: https://tailscale.com/kb/0008/acls/
- **Three-node architecture**: https://tailscale.com/kb/1154/secure-admin-access/

---

## 🚀 Próximos Pasos después Sprint 12

### Sprint 13 (Monitoring) - Opcional
- Prometheus + Grafana para todos los nodos
- Métricas custom por servicio
- Alerting diferenciado por nodos
- Dashboard central para monitorear salud del sistema completo

### Extensiones
- Webhooks para notificaciones diferenciadas por nodo
- Integración con herramientas de alerta (PagerDuty, etc.)
- Backup automatizado de volúmenes persistentes
- Alta disponibilidad para nodos críticos

---

**Fecha creación**: 2025-10-08
**Fecha actualización**: 2025-10-13
**Autor**: Infrastructure Sprint Planning
**Versión**: 2.0 (actualizado con tres nodos Tailscale + dual environment)
**Sprint anterior**: Sprint 11 - Chatbot BI con RAG (✅ COMPLETADO)
**Sprint siguiente**: Sprint 13 - Monitoring (opcional)

---

## 🔄 Changelog v2.0

**Cambios vs v1.0**:
- ✅ **Añadido**: Arquitectura de 3 nodos Tailscale separados
- ✅ **Añadido**: Runners diferenciados por etiqueta (`dev`/`prod`)
- ✅ **Añadido**: Entornos separados con `docker-compose.dev.yml` y `docker-compose.prod.yml`
- ✅ **Añadido**: CI/CD dual con matrix strategy para build y deploy
- ✅ **Añadido**: Configuración ACLs Tailscale por nodo
- ✅ **Añadido**: Nginx configs separados por nodo
- ✅ **Añadido**: Script setup dual remotes (GitHub + Forgejo)
- ✅ **Corregido**: Referencias a "MCP server" → "Chatbot BI con RAG"
- ⚡ **Aumentado**: Duración estimada 20-24h → 30-40h (arquitectura más compleja)

**Justificación cambios**:
- Arquitectura de 3 nodos proporciona **mejor aislamiento, seguridad y escalabilidad**
- Dual environment permite **testing real antes de producción**
- Git remotes dobles aseguran **backup y portabilidad**
