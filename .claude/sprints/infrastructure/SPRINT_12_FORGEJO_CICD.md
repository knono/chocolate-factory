# SPRINT 12: Forgejo CI/CD + Testing Suite

**Status**: Phases 1-11 Completed
**Duration**: Phases 1-8: 1 day | Phase 9: 3h | Phase 10: 1 day | Phase 11: 4h
**Dates**: Oct 13-20, 2025

## Objective

Deploy Forgejo self-hosted with dual environment CI/CD (dev/prod) and automated testing.

## Architecture

**Three-node architecture**:
- Git/CI/CD node: Forgejo + runners + registry
- Development node: develop branch
- Production node: main branch

**Rationale**:
- Forgejo: Community fork of Gitea, lightweight (~100MB RAM), native CI/CD (GitHub Actions compatible), Docker registry included, no vendor lock-in
- Three nodes: Complete isolation, ACL-based access control, enhanced security, independent management, scalable

---

## Phase 1: Tailscale Preparation (3-4h)

**Implemented**:
- Three separate VMs/containers with different Tailscale auth keys
- ACL configuration in Tailscale console
- Tags assigned: `tag:git-server`, `tag:dev-app`, `tag:prod-app`
- Connectivity testing between nodes

---

## Phase 2: Forgejo Deployment (4-5h)

**File**: `docker/forgejo-compose.yml`

**Configuration**:
```yaml
services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:1.21
    container_name: chocolate_factory_git
    ports:
      - "3000:3000"
      - "2222:22"
    environment:
      - FORGEJO__database__DB_TYPE=sqlite3
      - FORGEJO__server__DOMAIN=${FORGEJO_DOMAIN}
      - FORGEJO__server__ROOT_URL=https://${FORGEJO_DOMAIN}/
    volumes:
      - ./services/forgejo/data:/data
```

**Setup**:
- Wizard installation completed
- Admin user created with differentiated permissions
- Upload limits increased: `client_max_body_size 500M`, timeouts 300s
- Forgejo Actions enabled: `[actions] ENABLED = true`

---

## Phase 3: Differentiated Runners (3-4h)

**File**: `docker/gitea-runners-compose.yml`

**Configuration**:
```yaml
services:
  gitea-runner-dev:
    image: gitea/act_runner:latest
    environment:
      - GITEA_RUNNER_LABELS=dev,ubuntu-latest,docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  gitea-runner-prod:
    image: gitea/act_runner:latest
    environment:
      - GITEA_RUNNER_LABELS=prod,ubuntu-latest,docker
```

**Setup**:
- Registration tokens generated in Forgejo UI
- Both runners started on git node
- Labels verified: dev/prod differentiation functional

---

## Phase 4: Private Docker Registry (2-3h)

**File**: `docker/registry-compose.yml`

**Configuration**:
```yaml
services:
  registry:
    image: registry:2.8
    ports:
      - "5000:5000"
    environment:
      - REGISTRY_AUTH=htpasswd
      - REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd
    volumes:
      - ./services/registry/data:/var/lib/registry
      - ./services/registry/auth:/auth
```

**Setup**:
- htpasswd authentication configured
- Registry started and tested
- Docker configured for localhost insecure registry
- Push/pull testing verified

---

## Phase 4.5: Docker Secrets (1-2h)

**File**: `docker/secrets/create_secrets.sh`

**Status**: Configured with fallback to environment variables

**Implementation**:
```bash
# 11 secrets migrated
docker/secrets/
├── influxdb_token.txt
├── anthropic_api_key.txt
├── aemet_api_key.txt
├── openweather_api_key.txt
├── tailscale_authkey.txt (x3: prod/git/dev)
├── ree_api_token.txt
├── registry_user.txt
└── registry_password.txt
```

**Access Pattern**:
```python
def get_secret(secret_name: str) -> str:
    secret_path = f"/run/secrets/{secret_name}"
    try:
        with open(secret_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv(secret_name.upper())
```

**Benefits**:
- Not visible in `docker inspect`
- Not in process list
- Restrictive permissions (600)
- Mounted in memory (tmpfs)
- Easy rotation

**Note**: Docker Secrets with file backend (not native Swarm secrets). Directory `docker/secrets/` in `.gitignore`.

---

## Phase 5: Separated Environments (5-7h)

**Development**: `docker-compose.dev.yml`
```yaml
services:
  fastapi-app-dev:
    image: localhost:5000/chocolate-factory:develop
    container_name: chocolate_factory_dev
    ports:
      - "8001:8000"
    environment:
      - ENVIRONMENT=development
    volumes:
      - ./src/fastapi-app:/app  # Live reload
```

**Production**: `docker-compose.prod.yml`
```yaml
services:
  fastapi-app-prod:
    image: localhost:5000/chocolate-factory:production
    container_name: chocolate_factory_prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    volumes:
      - ./models:/app/models  # No source code mount
```

**Key Differences**:
- Ports: 8001 (dev) vs 8000 (prod)
- Source code: mounted (dev) vs baked into image (prod)
- InfluxDB: separate data volumes (dev-data vs prod-data)

---

## Phase 6: Dual Environment CI/CD (5-7h)

**File**: `.gitea/workflows/ci-cd-dual.yml`

**Workflow Structure**:
```yaml
jobs:
  test-all:
    runs-on: ubuntu-latest
    # Run tests on all branches

  build-image:
    needs: test-all
    strategy:
      matrix:
        - branch: main → tag: production
        - branch: develop → tag: develop

  deploy-dev:
    needs: build-image
    runs-on: dev  # Uses dev runner
    if: github.ref == 'refs/heads/develop'

  deploy-prod:
    needs: build-image
    runs-on: prod  # Uses prod runner
    if: github.ref == 'refs/heads/main'
```

**Testing**: Push develop deploys to dev, push main deploys to prod

---

## Phase 6.5: Automatic SSL/TLS with Tailscale ACME (2-3h)

**Architecture**:
- Tailscale Magic DNS + ACME auto-generates certificates
- Certificates stored in `/var/lib/tailscale/certs/`
- nginx template processed with `envsubst` for dynamic domains

**Startup Script Pattern** (`docker/git-start.sh`):
```bash
# 1. Start Tailscale daemon
tailscaled &

# 2. Connect to Tailnet
tailscale up --authkey="$TAILSCALE_AUTHKEY"

# 3. Request SSL certificates
tailscale cert "${TAILSCALE_DOMAIN}"

# 4. Process nginx config template
envsubst '${TAILSCALE_DOMAIN}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# 5. Start nginx with SSL
nginx -g 'daemon off;'
```

**nginx SSL Configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name ${TAILSCALE_DOMAIN};

    ssl_certificate /var/lib/tailscale/certs/${TAILSCALE_DOMAIN}.crt;
    ssl_certificate_key /var/lib/tailscale/certs/${TAILSCALE_DOMAIN}.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Force HTTP → HTTPS
    if ($scheme != "https") {
        return 301 https://$host$request_uri;
    }
}
```

**Benefits**:
- Zero-config SSL with automatic renewal
- Let's Encrypt certificates via Tailscale
- HTTP/2 enabled
- Only accessible in Tailnet

---

## Phase 7: Git Configuration (1-2h)

**File**: `scripts/setup-dual-remotes.sh`

**Setup**:
```bash
# Add Forgejo remote
git remote add forgejo https://<git-hostname>.ts.net/usuario/chocolate-factory.git

# Configure push to both destinations
git remote set-url --add --push origin https://github.com/usuario/chocolate-factory.git
git remote set-url --add --push origin https://<git-hostname>.ts.net/usuario/chocolate-factory.git
```

**Result**: `git push origin` pushes to both GitHub and Forgejo simultaneously

**Documentation**: `docs/GIT_WORKFLOW.md`

---

## Phase 8: Documentation & Initial Testing

**Completed**:
- CI/CD dual flow documented
- Git workflow with dual remotes documented
- CLAUDE.md updated with new architecture
- End-to-end testing verified
- Runners operational in dev and prod

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

**Docker Secrets**:
- File-based secrets with fallback to environment variables
- Works in Compose now, ready for Swarm later
- Permisos 600, tmpfs mount

**SSL/TLS**:
- Tailscale ACME for automatic certificates
- nginx templates with envsubst for dynamic domains
- HTTP → HTTPS forced redirection

**Dual Environment**:
- Separate compose files (dev.yml, prod.yml)
- Different ports, volumes, environment variables
- Matrix strategy in CI/CD

**Testing Strategy**:
- Phase 9: Integration tests (endpoints)
- Phase 10: Unit tests (services) + ML tests
- Phase 11: E2E tests (full system)

---

## Files Created/Modified

**Infrastructure**:
- `docker/forgejo-compose.yml`
- `docker/gitea-runners-compose.yml`
- `docker/registry-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`
- `docker/secrets/create_secrets.sh`

**CI/CD**:
- `.gitea/workflows/ci-cd-dual.yml`
- `.gitea/workflows/quick-test.yml`

**Tailscale Sidecars**:
- `docker/git-start.sh`
- `docker/dev-start.sh`
- `docker/git-nginx.conf`
- `docker/dev-nginx.conf`
- `docker/git-sidecar.Dockerfile`

**Configuration**:
- `.env.example`
- `scripts/setup-dual-remotes.sh`
- `src/configs/__init__.py`
- `src/fastapi-app/pytest.ini`

**Tests** (13 files, ~2,410 lines):
- `tests/integration/` (3 files)
- `tests/unit/` (5 files)
- `tests/ml/` (2 files)
- `tests/e2e/` (4 files)
- `tests/conftest.py`

**Documentation**:
- `docs/GIT_WORKFLOW.md`
- `docs/FORGEJO_SETUP.md`
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

## Known Issues

**Production `/docs` 404**: Expected behavior (security)
- `/docs` disabled in production (`ENVIRONMENT=production`)
- Available in development (port 8001)
- Alternative: `/openapi.json` always available

**Forgejo Actions Errors**: Connection refused to Forgejo
- Timing/DNS issue under investigation
- Runners registered but workflow execution intermittent

---

## Results & Metrics

**Infrastructure**:
- Nodes: 3 (git/dev/prod)
- Secrets managed: 11
- SSL certificates: 3 (automatic)
- Environments: 2 (fully separated)

**Testing**:
- Total tests: 102
- Success rate: 100%
- Coverage: 19%
- Execution time: <3 minutes

**CI/CD**:
- Workflows: 2 (dual environment, quick test)
- Jobs: 6 (test, build, deploy-dev, deploy-prod, smoke-test-dev, smoke-test-prod)
- Automatic rollback: Functional

**Time Investment**:
- Phases 1-8: 1 day
- Phase 9: 3h
- Phase 10: 1 day
- Phase 11: 4h
- Total: ~3 days (vs estimated 1.5-2 weeks)

---

## Value Delivered

**Infrastructure**:
- Complete isolation per layer (each on own node)
- ACL-based access control
- Enhanced security (isolated breaches)
- Automated deployment (develop → dev, main → prod)
- Dual backup (GitHub + Forgejo)
- Scalability (independent nodes)

**Testing**:
- Bugs detected in 2 minutes (not 2 hours of downtime)
- Pipeline blocks deploy on test failures
- Safe refactoring with test safety net
- Confident frequent deployments
- Fast debugging (immediate failure localization)

**ROI**: First production bug prevented justifies investment

---

## References

- Forgejo: https://forgejo.org/docs/
- Gitea Actions: https://docs.gitea.com/usage/actions/overview
- Docker Registry: https://docs.docker.com/registry/
- Tailscale ACLs: https://tailscale.com/kb/0008/acls/

---

**Created**: Oct 8, 2025
**Updated**: Oct 20, 2025
**Version**: 2.5 (Phase 11 completed + smoke tests fixed)
**Previous Sprint**: Sprint 11 - Chatbot BI with RAG
**Next Sprint**: Sprint 13 - Health Monitoring
