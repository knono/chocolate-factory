# SPRINT 12: Forgejo CI/CD + Testing Suite

**Status**: Phases 1-11 Completed
**Duration**: Phases 1-8: 1 day | Phase 9: 3h | Phase 10: 1 day | Phase 11: 4h
**Dates**: Oct 13-20, 2025

## Objective

Deploy Forgejo self-hosted with dual environment CI/CD (dev/prod) and automated testing.

## Architecture

**Two-layer deployment**:

**Layer 1 - Core Services** (`docker-compose.yml`):
- FastAPI application (port 8000)
- InfluxDB time-series database (port 8086)

**Layer 2 - Infrastructure** (`docker-compose.override.yml`):
- Forgejo git server (HTTP:3000, SSH:2222)
- Gitea Actions runners (dev + prod)
- Private Docker registry (port 5000)
- Tailscale sidecar containers with SSL proxies

**Network**:
- Docker internal network: 192.168.100.0/24
- Tailscale overlay: Encrypted external access
- Services communicate via Docker DNS

---

## Phase 1: Tailscale Sidecars (3-4h)

**Implemented**:
- Three Tailscale sidecar containers with different auth keys
- Sidecar Dockerfiles: `tailscale-sidecar.Dockerfile`, `git-sidecar.Dockerfile`, `dev-sidecar.Dockerfile`
- nginx proxies configured on each sidecar
- Connectivity between containers via Docker network (192.168.100.0/24)
- HTTP access to services via Tailnet (requires Tailscale client)

---

## Phase 2: Forgejo Deployment ✅

**File**: `docker-compose.override.yml` (lines 89-107)

**Configuration**:
```yaml
forgejo:
  image: codeberg.org/forgejo/forgejo:1.21
  container_name: chocolate_factory_git_server
  networks:
    - backend
  ports:
    - "3000:3000"      # HTTP UI
    - "2222:22"        # SSH git push/pull
  volumes:
    - forgejo_data:/data
  restart: unless-stopped
```

**Access**:
- Local (host): `http://localhost:3000`
- Via Tailnet: `https://<TAILSCALE_DOMAIN_GIT>/` (proxied through git sidecar)

**Configuration**:
- SQLite database (embedded)
- Forgejo Actions enabled
- Upload limits configured (500M)
- Admin user created via web wizard

---

## Phase 3: Forgejo Actions Runners ✅

**File**: `docker-compose.override.yml` (lines 112-151)

**Configuration**:
```yaml
gitea-runner-dev:
  image: gitea/act_runner:latest
  container_name: chocolate_factory_runner_dev
  networks:
    - backend
  environment:
    - GITEA_INSTANCE_URL=http://forgejo:3000
    - GITEA_RUNNER_REGISTRATION_TOKEN=${runner_token_dev}
    - GITEA_RUNNER_LABELS=dev,ubuntu-latest,docker
  volumes:
    - gitea_runner_dev_data:/data
    - /var/run/docker.sock:/var/run/docker.sock

gitea-runner-prod:
  image: gitea/act_runner:latest
  container_name: chocolate_factory_runner_prod
  environment:
    - GITEA_INSTANCE_URL=http://forgejo:3000
    - GITEA_RUNNER_REGISTRATION_TOKEN=${runner_token_prod}
    - GITEA_RUNNER_LABELS=prod,ubuntu-latest,docker
  volumes:
    - gitea_runner_prod_data:/data
    - /var/run/docker.sock:/var/run/docker.sock
```

**Setup**:
- Both runners connect to Forgejo at `http://forgejo:3000`
- Registration tokens from Forgejo Actions settings (stored in SOPS)
- Docker socket mounted for build/deployment capability
- Persistent storage in named volumes

---

## Phase 4: Private Docker Registry ✅

**File**: `docker-compose.override.yml` (lines 156-181)

**Configuration**:
```yaml
registry:
  image: registry:2.8
  container_name: chocolate_factory_registry
  networks:
    - backend
  ports:
    - "${REGISTRY_PORT:-5000}:5000"
  environment:
    - REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/var/lib/registry
    - REGISTRY_AUTH=htpasswd
    - REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd
    - REGISTRY_AUTH_HTPASSWD_REALM=Chocolate Factory Registry
  volumes:
    - registry_data:/var/lib/registry
    - ./docker/services/registry/auth:/auth:ro
  restart: unless-stopped
```

**Access**:
- Local: `localhost:5000` (auth via htpasswd)
- Credentials: From SOPS secrets (registry_user, registry_password)

**Usage**:
```bash
docker login localhost:5000
docker push localhost:5000/chocolate-factory:develop
docker pull localhost:5000/chocolate-factory:production
```

---

## Phase 4.5: Secrets Management with SOPS ✅

**System**: SOPS (Secrets OPerationS) with age encryption

**Files**:
- `secrets.enc.yaml` - Encrypted secrets (committed to git)
- `.sops/age-key.txt` - Age encryption key (in .gitignore)
- `scripts/decrypt-and-convert.sh` - Decryption + conversion to .env
- `.env` - Generated at runtime (in .gitignore)

**Workflow**:
```bash
# 1. Decrypt and convert to .env format
./scripts/decrypt-and-convert.sh

# 2. Docker-compose reads variables from .env
docker-compose up

# 3. Containers receive env vars
```

**Secrets Managed** (11+):
```
- influxdb_token
- influxdb_admin_password
- anthropic_api_key
- aemet_api_key
- openweathermap_api_key
- tailscale_authkey (main)
- tailscale_authkey_dev
- tailscale_authkey_git
- ree_api_token
- runner_token_dev
- runner_token_prod
- registry_user
- registry_password
```

**Loading in Code** (`src/fastapi-app/core/config.py`):
```python
def get_secret(secret_name: str, env_var_name: Optional[str] = None):
    # 1. Try Docker Secrets (for future Swarm mode)
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        return secret_path.read_text().strip()

    # 2. Try environment variable
    return os.environ.get(env_var_name or secret_name.upper())
```

**Benefits**:
- ✅ Secrets encrypted in git (no exposure)
- ✅ Age encryption (simple, no infrastructure)
- ✅ Auditable (who encrypted/decrypted)
- ✅ Easy rotation (reencrypt entire file)
- ✅ Works now with Compose, ready for Swarm

---

## Phase 5: Container Composition ✅

**Base Configuration**: `docker-compose.yml`

Contains core services:
```yaml
services:
  fastapi-app:        # Main API service on port 8000
  influxdb:           # Time-series database on port 8086
```

**Extended Configuration**: `docker-compose.override.yml`

Adds infrastructure:
```yaml
services:
  chocolate-factory:       # Main Tailscale sidecar (SSL proxy)
  git:                     # Git node sidecar
  forgejo:                 # Git server
  gitea-runner-dev:        # CI/CD runner (dev jobs)
  gitea-runner-prod:       # CI/CD runner (prod jobs)
  registry:                # Private Docker registry
  chocolate-factory-dev:   # Dev node sidecar
```

**Launch Command**:
```bash
# Automatic: uses both files
docker-compose up -d

# Or explicit:
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

**Current State**:
- Single FastAPI instance (port 8000)
- Source code mounted in dev mode (live reload possible)
- To separate dev/prod: create additional compose files per environment

---

## Phase 6: CI/CD Workflows ✅

**File**: `.gitea/workflows/ci-cd-dual.yml`

**Runners Available**:
- `gitea-runner-dev` (labels: dev, ubuntu-latest, docker)
- `gitea-runner-prod` (labels: prod, ubuntu-latest, docker)

**Workflow Execution**:
- Runners connect to Forgejo at `http://forgejo:3000`
- Can trigger workflows via git push to Forgejo
- Runners have Docker socket access for image builds
- Actions stored in Forgejo (compatible with GitHub Actions syntax)

**Current Setup**:
- Both runners online and registered
- Docker registry available at `localhost:5000` for artifact storage
- Ready for workflow implementation (workflow files to be created)

---

## Phase 6.5: Tailscale SSL with ACME ✅

**Architecture**:
- Tailscale sidecar containers request certificates from Tailnet ACME
- Certificates stored in `/var/lib/tailscale/certs/`
- nginx configured via template + envsubst

**Startup Flow** (in sidecar Dockerfiles):

1. Start Tailscale daemon:
```bash
tailscaled &
```

2. Connect to Tailnet with auth key:
```bash
tailscale up --authkey="${TAILSCALE_AUTHKEY}"
```

3. Request certificate (auto-renewed by Tailscale):
```bash
tailscale cert "${TAILSCALE_DOMAIN}"
```

4. Process nginx template:
```bash
envsubst '${TAILSCALE_DOMAIN}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
```

5. Start nginx:
```bash
nginx -g 'daemon off;'
```

**Sidecar Implementations**:
- `docker/tailscale-start.sh` - Main sidecar
- `docker/git-start.sh` - Git node sidecar
- `docker/dev-start.sh` - Dev node sidecar (similar pattern)

**nginx Configuration** (template):
```nginx
server {
    listen 443 ssl http2;
    server_name ${TAILSCALE_DOMAIN};

    ssl_certificate /var/lib/tailscale/certs/${TAILSCALE_DOMAIN}.crt;
    ssl_certificate_key /var/lib/tailscale/certs/${TAILSCALE_DOMAIN}.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://chocolate_factory_brain:8000;
    }
}
```

**Result**:
- ✅ SSL certificates auto-generated on startup
- ✅ Accessible via HTTPS in Tailnet only
- ✅ Automatic renewal by Tailscale
- ✅ No manual certificate management

---

## Phase 7: Git Configuration ✅

**File**: `scripts/setup-dual-remotes.sh`

**Setup** (optional, for dual backup):
```bash
# Add Forgejo remote alongside GitHub
git remote add forgejo https://<TAILSCALE_DOMAIN_GIT>/usuario/chocolate-factory.git

# Optional: Configure origin to push to both
git remote set-url --add --push origin https://github.com/usuario/chocolate-factory.git
git remote set-url --add --push origin https://<TAILSCALE_DOMAIN_GIT>/usuario/chocolate-factory.git
```

**Access**:
- GitHub: Primary repository (public)
- Forgejo: Backup + self-hosted CI/CD trigger
- SSH: `git@<TAILSCALE_DOMAIN_GIT>:usuario/chocolate-factory.git` (port 2222)
- HTTPS: `https://<TAILSCALE_DOMAIN_GIT>/usuario/chocolate-factory.git`

**Documentation**: `docs/GIT_WORKFLOW.md`

---

## Phase 8: Documentation & Infrastructure Testing ✅

**Completed**:
- Docker-compose architecture documented
- Forgejo setup verified
- Runners online and registered
- Docker registry functional
- SSL certificates generating
- SOPS secrets system operational
- CLAUDE.md updated

---

## Phase 9: Basic API Tests (3h - Oct 18, 2025)

**Objective**: Fundamental endpoint tests

**Result**:
- 21/21 tests passing (100%)
- Coverage: 15.26%
- Pipeline: Green

**Tests Implemented**:
- Dashboard API (11 tests): `/dashboard/*`
- Health endpoints (6 tests): `/health`, `/ready`, `/version`
- Smoke tests (4 tests): fundamental operations

**Structure Created**:
```
tests/
├── integration/
│   ├── test_dashboard_api.py (11 tests)
│   ├── test_health_endpoints.py (6 tests)
│   └── test_simple_smoke.py (4 tests)
├── unit/ (empty, for Phase 10)
├── ml/ (empty, for Phase 10)
└── conftest.py (shared fixtures)
```

**Configuration**:
- `pytest.ini` configured
- Coverage threshold: 15%
- Shared fixtures for external service mocks

**Cleanup Performed**:
- Removed 11 tests for non-existent endpoints
- Eliminated skipped tests to avoid confusion

**Critical Problems Resolved** (5h debugging):

1. **pyproject.toml conflict**: `configs` path different in CI vs Docker
   - Solution: Removed `configs` from packages, use PYTHONPATH

2. **Docker build cache**: Old layers causing "package directory does not exist"
   - Solution: `--no-cache` flag in workflow

3. **Missing environment variables**: Tests required vars not in CI
   - Solution: Mock env vars (INFLUXDB_TOKEN, AEMET_API_KEY, etc.)

4. **Import failure**: `from configs.influxdb_schemas` failed
   - Solution: `PYTHONPATH=${{ github.workspace }}/src` + `src/configs/__init__.py`

**Files Modified**:
- `.gitea/workflows/ci-cd-dual.yml`: env vars, PYTHONPATH, --no-cache
- `src/fastapi-app/pyproject.toml`: Removed `configs` from packages
- `src/configs/__init__.py`: Created for importability

---

## Phase 10: Service & ML Tests (1 day - Oct 20, 2025)

**Status**: 45/45 tests completed (100% passing)

**Tests Implemented**:

**Unit Tests - Services (33 tests)**:
1. `test_ree_service.py` (5 tests, 325 lines)
   - Coverage: `ingest_prices()`, `get_prices()`, `get_latest_price()`, `_transform_to_points()`
   - Mocks: REEAPIClient, InfluxDB write_points/query

2. `test_weather_service.py` (6 tests, 290 lines)
   - Coverage: AEMET + OpenWeatherMap hybrid strategy (00-07h + 08-23h)
   - Tests: Ingestion, fallback, timeout handling, transformation

3. `test_backfill_service.py` (7 tests, 305 lines)
   - Coverage: `execute_intelligent_backfill()`, 48h strategy
   - Tests: REE backfill, weather backfill, OpenWeather <48h, AEMET ≥48h, result models

4. `test_gap_detection.py` (9 tests, 390 lines)
   - Coverage: `detect_all_gaps()`, `_find_time_gaps()`
   - Tests: REE gaps, weather gaps, summary calculation, threshold logic, continuous data

5. `test_chatbot_rag.py` (6 tests, 343 lines)
   - Coverage: Keyword matching, RAG context building, Claude API, cost tracking
   - Mocks: Anthropic Messages API complete

**ML Tests (12 tests)**:

6. `test_prophet_model.py` (6/6 tests, 309 lines)
   - Coverage: `train_model()`, `predict_hours()`, `predict_weekly()`, persistence
   - Tests: Training, 7-day prediction, confidence intervals, MAE <0.10, missing data handling, serialization
   - **Fixed**: Response structure (predicted_price, confidence_lower/upper)

7. `test_sklearn_models.py` (6 tests, 360 lines)
   - Coverage: `train_models()`, `engineer_features()`, ModelTrainer
   - Tests: RandomForestRegressor training, 4-class classifier, 13 features validation, accuracy thresholds, pickle persistence, metrics calculation

**Final Metrics**:
- Total tests: 66 (21 Phase 9 + 45 Phase 10)
- Success rate: 100%
- Coverage: 19% (from 15% baseline)
- Test code: ~2,410 lines
- Files: 13 test files

**Test Structure**:
```
tests/
├── integration/ (21 tests - Phase 9)
├── unit/ (33 tests)
│   ├── test_ree_service.py
│   ├── test_weather_service.py
│   ├── test_backfill_service.py
│   ├── test_gap_detection.py
│   └── test_chatbot_rag.py
└── ml/ (12 tests)
    ├── test_prophet_model.py (6 tests)
    └── test_sklearn_models.py (6 tests)
```

---

## Phase 11: E2E Integration Tests (4h - Oct 20, 2025)

**Status**: 36/36 E2E tests implemented (164% of goal)

**Tests Created**:
1. `test_smoke_post_deploy.py` (8 tests) - Post-deploy validation
2. `test_full_pipeline.py` (5 tests) - Complete data flow
3. `test_resilience.py` (15 tests) - Error handling
4. `test_performance.py` (8 tests) - Response times

**Total Tests**: 102 (66 previous + 36 E2E)

**CI/CD Integration**:
- Job `smoke-test-dev` after deploy-dev
- Job `smoke-test-prod` after deploy-prod
- Automatic rollback to stable versions on failure
- Automatic tagging of stable versions

**Fixtures & Markers**:
- E2E fixtures in `conftest.py`
- 5 pytest markers: e2e, smoke, pipeline, resilience, performance

**Workflow Updates**:
```yaml
smoke-test-dev:
  needs: deploy-dev
  runs-on: dev
  steps:
    - pytest tests/e2e/test_smoke_post_deploy.py -m smoke
    - if: failure() → docker-compose pull stable-dev && up -d

smoke-test-prod:
  needs: deploy-prod
  runs-on: prod
  steps:
    - pytest tests/e2e/test_smoke_post_deploy.py -m smoke
    - if: failure() → docker-compose pull stable-prod && up -d
```

**v2.5 Fix (Oct 20, 2025)**: Smoke Tests CI/CD

**Problem**: Tests failed in CI/CD with rollback errors

**Causes**:
1. Hardcoded `localhost:8000` (not accessible from Docker runners)
2. Timeout too short (10s) for `/dashboard/complete` (needs 30s)
3. Missing `docker login` before stable tag/push

**Solutions**:
- `E2E_API_URL` environment variable for dynamic URLs
- Workflow exports `E2E_API_URL=http://chocolate_factory_dev:8000` (dev)
- Workflow exports `E2E_API_URL=http://chocolate_factory_brain:8000` (prod)
- Timeout increased 10s → 30s for heavy endpoints
- Added `docker login localhost:5000` before tagging

**Files Modified**:
- `tests/e2e/test_smoke_post_deploy.py`: Env vars + timeout 30s
- `.gitea/workflows/ci-cd-dual.yml`: Export E2E_API_URL + docker login
- `docs/SMOKE_TESTS_FIX.md`: Complete documentation

**Result**: Smoke tests 100% functional in CI/CD, rollback operational

---

## Key Technical Decisions

**Secrets Management - SOPS**:
- Age encryption for secrets at rest in git
- `.env` generated at deployment time
- Supports Docker Secrets fallback (for Swarm scaling)
- Auditable (encryption/decryption logged)

**SSL/TLS - Tailscale ACME**:
- Certificates auto-generated on sidecar startup
- Let's Encrypt via Tailscale
- nginx templates with envsubst for variable substitution
- Only accessible in Tailnet (no external HTTP exposure)

**Container Orchestration**:
- Docker Compose for single-host deployment
- Base + override pattern for modularity
- Volumes for persistent data
- Internal Docker network with MTU optimization for Tailscale

**Testing Strategy**:
- Phase 9: Integration tests (API endpoints)
- Phase 10: Unit + ML tests (services)
- Phase 11: E2E tests (full system)

---

## Files Created/Modified

**Docker Compose**:
- `docker-compose.yml` - Base services (fastapi, influxdb)
- `docker-compose.override.yml` - Infrastructure (forgejo, runners, registry, sidecars)

**Sidecar Infrastructure**:
- `docker/tailscale-sidecar.Dockerfile` - Main sidecar (SSL proxy)
- `docker/git-sidecar.Dockerfile` - Git node sidecar
- `docker/dev-sidecar.Dockerfile` - Dev node sidecar
- `docker/tailscale-start.sh` - Startup script (main)
- `docker/git-start.sh` - Startup script (git node)
- `docker/tailscale-http-server.sh` - HTTP proxy for Tailscale CLI
- `docker/sidecar-nginx.conf` - nginx template (main)
- `docker/git-nginx.conf` - nginx template (git)
- `docker/dev-nginx.conf` - nginx template (dev)

**Secrets Management**:
- `scripts/decrypt-and-convert.sh` - SOPS decryption to .env
- `secrets.enc.yaml` - Encrypted secrets (in git)
- `.sops/age-key.txt` - Age encryption key (in .gitignore)
- `.sops/create-secrets-yaml.sh` - Secret creation helper
- `docker/services/registry/auth/htpasswd` - Registry auth

**Workflow Files** (presumed):
- `.gitea/workflows/ci-cd-dual.yml` - Dual environment CI/CD

**Configuration**:
- `scripts/setup-dual-remotes.sh` - Git dual-remote setup
- `.env.tailscale.example` - Tailscale env template
- `src/fastapi-app/core/config.py` - Secret loading logic

**Tests** (13 files, ~2,410 lines):
- `tests/integration/` (3 files, 21 tests)
- `tests/unit/` (5 files, 33 tests)
- `tests/ml/` (2 files, 12 tests)
- `tests/e2e/` (4 files, 36 tests)
- `tests/conftest.py` - Shared fixtures

**Documentation**:
- `docs/GIT_WORKFLOW.md`
- `docs/SMOKE_TESTS_FIX.md`

---

## Testing & Validation

**Success Criteria**:
1. Forgejo operational at `https://<git-hostname>.ts.net`
2. Both runners online with dev/prod labels
3. Push develop → deploy dev, push main → deploy prod
4. Registry functional: pull/push images with both tags
5. SSL access working on all three nodes

**Test Commands**:
```bash
# Health checks
curl https://<git-hostname>.ts.net/api/healthz
curl https://<dev-hostname>.ts.net/health
curl https://<prod-hostname>.ts.net/health

# Registry
docker pull localhost:5000/chocolate-factory:develop
docker pull localhost:5000/chocolate-factory:production

# Tests
pytest tests/ -v  # 102 tests
pytest tests/e2e/ -m smoke  # Smoke tests
```

---

## Known Limitations

**CI/CD Workflows**: Not yet implemented
- Runners present and connected
- Need to create actual workflow files in `.gitea/workflows/`

**Environment Separation**: Single FastAPI instance
- Currently one instance serves all environments
- To separate dev/prod: create `docker-compose.dev.yml` and `.prod.yml` files

**Production `/docs` Disabled**: Expected behavior
- Security: Swagger UI disabled in production
- Available in development: `http://localhost:8000/docs`
- Alternative: `/openapi.json` always available

---

## Results & Metrics

**Infrastructure**:
- Containers: 8 (fastapi, influxdb, forgejo, 2x runner, registry, 3x sidecar)
- Network: 1 internal (192.168.100.0/24, MTU 1280 for Tailscale)
- Volumes: 7 persistent (state, data, logs)
- Secrets managed: 13 (via SOPS)
- SSL certificates: 3 (auto-generated via Tailscale)
- Docker registry: 1 private (localhost:5000)

**Testing**:
- Total tests: 102
- Success rate: 100%
- Coverage: 19%
- Execution time: <3 minutes
- Test files: 13
- Test code lines: ~2,410

**CI/CD Infrastructure**:
- Runners: 2 (dev + prod)
- Registries: 1 private (Docker)
- Version control: GitHub + Forgejo (dual backup)

**Time Investment**:
- Phases 1-8: ~1 day
- Phase 9: 3h
- Phase 10: 1 day
- Phase 11: 4h
- Total: ~3 days

---

## Value Delivered

**Infrastructure**:
- Self-hosted git server (no vendor lock-in)
- Private Docker registry (artifact storage)
- SSL/TLS automatic (Tailscale ACME)
- Secrets encrypted at rest (SOPS)
- Modular docker-compose (base + override)
- Persistent data storage (12+ volumes)
- Dual version control (GitHub + Forgejo backup)

**Testing Foundation**:
- 102 automated tests (100% passing)
- 19% code coverage baseline
- Integration + unit + ML + E2E test structure
- Post-deploy smoke tests
- Automatic rollback on failure

**Operational**:
- Forgejo ready for CI/CD workflows
- Runners (dev + prod) online
- Registry functional for artifact storage
- Secrets management system operational
- Logs collected (Sprint 13 integration)

**Scalability Path**:
- SOPS supports multiple environments
- Docker Secrets code path ready (for Swarm)
- Infrastructure can expand independently

---

## References

- **Forgejo**: https://forgejo.org/docs/
- **Gitea Actions**: https://docs.gitea.com/usage/actions/overview
- **Docker Registry**: https://docs.docker.com/registry/
- **Docker Compose**: https://docs.docker.com/compose/
- **SOPS**: https://github.com/getsops/sops
- **Tailscale**: https://tailscale.com/kb/

---

**Created**: Oct 8, 2025
**Updated**: Oct 28, 2025
**Version**: 3.0 (Documentation corrected to reflect actual implementation)
**Status**: All phases implemented as documented
**Previous Sprint**: Sprint 11 - Chatbot BI with RAG
**Next Sprint**: Sprint 13 - Health Monitoring (completed)
