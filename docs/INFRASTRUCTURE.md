# Infrastructure Documentation

**Version**: 1.0
**Last Updated**: 2025-10-23

---

## Table of Contents

1. [Dual Environment Setup](#dual-environment-setup)
2. [Secrets Management (SOPS)](#secrets-management-sops)
3. [Backup System](#backup-system)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Docker Compose Reference](#docker-compose-reference)

---

## Dual Environment Setup

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   TAILSCALE NETWORK                         │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  GIT/CI/CD │  │   DEVELOPMENT   │  │   PRODUCTION    │  │
│  │  Forgejo   │  │   Port: 8001    │  │   Port: 8000    │  │
│  │  Runners   │  │   Hot Reload    │  │   Ingestion     │  │
│  │  Registry  │  │   Read-only DB  │  │   InfluxDB      │  │
│  └────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Configuration

**Development** (`docker-compose.dev.yml`):
- Port: 8001
- Hot reload enabled
- Debug logging
- Uses production InfluxDB (read-only, no ingestion)
- Bind mount: `./src/fastapi-app:/app` (live code changes)

**Production** (`docker-compose.prod.yml`):
- Port: 8000
- No hot reload
- Info logging
- Independent InfluxDB instance
- Immutable code (within image)

### Prerequisites

1. Create `.env`:
```bash
cp .env.example .env
# Edit with actual values
```

2. Create Docker secrets:
```bash
cd docker/secrets
./create_secrets.sh
ls -la *.txt  # Verify permissions: 600
```

3. Push images to registry:
```bash
docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:develop
docker push localhost:5000/chocolate-factory:develop

docker tag chocolate-factory-fastapi-app:latest localhost:5000/chocolate-factory:production
docker push localhost:5000/chocolate-factory:production
```

### Deployment

**Development**:
```bash
docker login localhost:5000 -u admin -p <registry-password>
docker pull localhost:5000/chocolate-factory:develop
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
curl http://localhost:8001/health
```

**Production**:
```bash
docker login localhost:5000 -u admin -p <registry-password>
docker pull localhost:5000/chocolate-factory:production
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### Update Workflow

**Development**:
```bash
docker build -t localhost:5000/chocolate-factory:develop -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:develop
docker pull localhost:5000/chocolate-factory:develop
docker compose -f docker-compose.dev.yml up -d --no-deps fastapi-app-dev
```

**Production**:
```bash
docker build -t localhost:5000/chocolate-factory:production -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:production
docker pull localhost:5000/chocolate-factory:production
docker compose -f docker-compose.prod.yml up -d --no-deps fastapi-app-prod
```

### Troubleshooting

**Image not found**:
```bash
curl -u admin:<registry-password> http://localhost:5000/v2/chocolate-factory/tags/list
docker build -t localhost:5000/chocolate-factory:develop -f docker/fastapi.Dockerfile .
docker push localhost:5000/chocolate-factory:develop
```

**Permission denied warnings (expected)**:
```bash
# WARNING: Failed to read secret from /run/secrets/* (NORMAL)
# System uses .env fallback automatically
# Verify application started:
docker logs chocolate_factory_dev 2>&1 | grep -i "startup complete"
curl http://localhost:8001/health
```

**Network not found**:
```bash
docker network create chocolate-factory_dev-backend
```

---

## Secrets Management (SOPS)

### Overview

SOPS (Secrets OPerationS) manages 14 secrets encrypted with age encryption.

**Secrets managed**:
- `aemet_api_key` - AEMET OpenData API
- `anthropic_api_key` - Claude Haiku API
- `influxdb_admin_password` - InfluxDB admin
- `influxdb_token_dev` - InfluxDB dev token
- `influxdb_token` - InfluxDB prod token
- `openweathermap_api_key` - OpenWeatherMap API
- `ree_api_token` - REE electricity API
- `registry_password` - Docker Registry
- `registry_user` - Docker Registry user
- `runner_token_dev` - Gitea Actions runner (dev)
- `runner_token_prod` - Gitea Actions runner (prod)
- `tailscale_authkey_dev` - Tailscale auth (dev)
- `tailscale_authkey_git` - Tailscale auth (git)
- `tailscale_authkey` - Tailscale auth (prod)

### Installation

```bash
# Install SOPS and age
sudo apt-get update
sudo apt-get install -y sops age

# Verify
sops --version  # 3.11.0+
age --version   # 1.1.1+

# Generate age key
mkdir -p .sops
age-keygen -o .sops/age-key.txt
cat .sops/age-key.txt
```

**Output**:
```
# public key: age1<your_public_key_here>
AGE-SECRET-KEY-<your_private_key_here>
```

### Create and Encrypt Secrets

```bash
# Create plain YAML
cat > .sops/secrets.yaml << EOF
aemet_api_key: "your_key_here"
anthropic_api_key: "your_key_here"
# ... more secrets
EOF

# Encrypt
export SOPS_AGE_RECIPIENTS=age1<your_public_key_here>
sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml

# Commit encrypted file
git add secrets.enc.yaml
git commit -m "chore: add encrypted secrets"
```

### Local Workflow

**Decrypt secrets**:
```bash
# Using helper script
./decrypt-secrets.sh

# Manual
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops --decrypt secrets.enc.yaml > .env
```

**Update secrets**:
```bash
# Edit encrypted file (opens editor)
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops secrets.enc.yaml

# Re-encrypt from plain YAML
sops --encrypt --age $SOPS_AGE_RECIPIENTS .sops/secrets.yaml > secrets.enc.yaml

# Commit
git add secrets.enc.yaml
git commit -m "chore: update API keys"
```

**Rotate keys**:
```bash
age-keygen -o .sops/age-key-new.txt
export NEW_PUBLIC_KEY=$(grep "public key:" .sops/age-key-new.txt | awk '{print $4}')
sops --rotate --age $NEW_PUBLIC_KEY secrets.enc.yaml
git add secrets.enc.yaml
git commit -m "chore: rotate encryption keys"
```

### CI/CD Integration

**Forgejo Secret Configuration**:
1. Navigate to `http://localhost:3000/<user>/<repo>`
2. Settings > Secrets > Add Secret
3. Name: `SOPS_AGE_KEY`
4. Value: `AGE-SECRET-KEY-<your_private_key>` (from `.sops/age-key.txt`)
5. Save

**Pipeline usage** (`.gitea/workflows/ci-cd-dual.yml`):
```yaml
- name: Decrypt secrets with SOPS
  run: |
    if ! command -v sops &> /dev/null; then
      sudo apt-get update && sudo apt-get install -y sops age
    fi
    echo "${{ secrets.SOPS_AGE_KEY }}" > /tmp/age-key.txt
    export SOPS_AGE_KEY_FILE=/tmp/age-key.txt
    sops --decrypt secrets.enc.yaml > .env
    rm /tmp/age-key.txt
```

### Troubleshooting

**"no age key found"**:
```bash
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops --decrypt secrets.enc.yaml > .env
```

**"failed to decrypt sops data key"**:
```bash
# Verify key matches
cat .sops/age-key.txt | grep "public key"
grep "recipient:" secrets.enc.yaml
```

**Variables not loaded in Docker**:
```bash
cat .env | head -5
./decrypt-secrets.sh
docker compose -f docker-compose.dev.yml config | grep "aemet_api_key"
```

---

## Backup System

### Overview

Complete backup and restore system for all critical components:
- InfluxDB (124M+ time series data)
- ML models (Prophet + sklearn)
- Configuration (Docker Compose + Nginx)
- Encrypted secrets (SOPS + AGE keys)
- Source code (src/, scripts/, .claude/, docs/)
- Recent logs (last 7 days)

### Directory Structure

```
/home/user/
├── chocolate-factory/              # Project
│   ├── backup.sh
│   ├── restore.sh
│   ├── backup-verify.sh
│   └── setup-cron-backups.sh
│
└── chocolate-factory-backups/      # Backups (external)
    ├── daily/                      # 7 days retention
    ├── weekly/                     # 4 weeks retention
    └── monthly/                    # 3 months retention
```

### Backup Contents

```
chocolate-factory_daily_20251022_020000/
├── MANIFEST.txt
├── influxdb/
│   ├── influxdb_data.tar.gz       # 124M+
│   └── influxdb_config.tar.gz
├── models/
│   ├── latest/
│   ├── *.pkl
│   └── model_registry.json
├── config/
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   └── *.conf
├── secrets/
│   ├── secrets.enc.yaml
│   └── age-key.txt                 # CRITICAL
├── code/
│   ├── src.tar.gz
│   ├── scripts.tar.gz
│   ├── claude.tar.gz
│   └── docs.tar.gz
└── logs/
    └── *.log
```

### Usage

**Initial setup**:
```bash
chmod +x backup.sh restore.sh backup-verify.sh setup-cron-backups.sh
./backup.sh daily
ls -lh ../chocolate-factory-backups/daily/
```

**Manual backup**:
```bash
./backup.sh [daily|weekly|monthly]
```

**List backups**:
```bash
./restore.sh
```

**Restore backup**:
```bash
./restore.sh chocolate-factory_daily_20251022_020000
# Or without confirmation:
./restore.sh chocolate-factory_daily_20251022_020000 --force
```

**Verify backups**:
```bash
# All backups
./backup-verify.sh

# Specific backup
./backup-verify.sh chocolate-factory_daily_20251022_020000
```

### Automated Backups (Cron)

**Install**:
```bash
./setup-cron-backups.sh install
```

**Schedule**:
- Daily: 2:00 AM (retention: 7 days)
- Weekly: Sundays 3:00 AM (retention: 4 weeks)
- Monthly: 1st day 4:00 AM (retention: 3 months)

**Status**:
```bash
./setup-cron-backups.sh status
crontab -l | grep CHOCOLATE_FACTORY
```

**View logs**:
```bash
tail -f logs/backup-daily.log
tail -f logs/backup-weekly.log
tail -f logs/backup-monthly.log
```

**Uninstall**:
```bash
./setup-cron-backups.sh uninstall
```

### Restoration Scenarios

**Complete disaster recovery**:
```bash
git clone <repo-url> chocolate-factory
cd chocolate-factory
chmod +x restore.sh
./restore.sh
./restore.sh chocolate-factory_daily_20251022_020000
./decrypt-secrets.sh
docker compose ps
curl http://localhost:8000/health
```

**InfluxDB only**:
```bash
docker compose down
cd ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_020000
tar -xzf influxdb/influxdb_data.tar.gz -C ~/chocolate-factory/docker/services/influxdb/
cd ~/chocolate-factory
docker compose up -d
```

**ML models only**:
```bash
cp -r ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_020000/models/* ./models/
docker compose restart fastapi-app
```

### Retention Policy

Automatic cleanup applied during backup execution:

| Type | Retention | Cleanup |
|------|-----------|---------|
| Daily | 7 days | Deletes backups >7 days |
| Weekly | 28 days | Deletes backups >28 days |
| Monthly | 90 days | Deletes backups >90 days |

**Disk space estimate**:
- 7 daily × 156M = ~1.1 GB
- 4 weekly × 156M = ~624 MB
- 3 monthly × 156M = ~468 MB
- **Total**: ~2.2 GB

### Troubleshooting

**Permission denied**:
```bash
mkdir -p ../chocolate-factory-backups
chmod 755 ../chocolate-factory-backups
```

**InfluxDB backup fails**:
```bash
docker compose ps influxdb
ls -lh docker/services/influxdb/data/
docker compose up -d influxdb
```

**Cron not executing**:
```bash
crontab -l | grep CHOCOLATE_FACTORY
grep CRON /var/log/syslog | tail -20
chmod +x backup.sh
mkdir -p logs && chmod 755 logs
```

**Backup takes too long**:
```bash
# Clean old InfluxDB data (>90 days)
docker exec chocolate_factory_storage influx delete \
  --org chocolate_factory \
  --bucket energy_data \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -d '90 days ago' -Iseconds)
```

---

## CI/CD Pipeline

### Architecture

```
GITEA ACTIONS (git.<tailnet>.ts.net)
    │
    ▼
GIT PUSH (develop/main)
    │
    ▼
JOB 1: TESTS
  - Setup Python 3.11
  - Install dependencies
  - Run pytest
  - Validate imports
    │
    ▼
JOB 2: BUILD & PUSH
  - Determine tag (develop/production)
  - Build Docker image
  - Push to registry
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
JOB 3: DEPLOY DEV   JOB 4: DEPLOY PROD
  - Pull image       - Pull image
  - docker-compose   - docker-compose
  - Health check     - Health check
    │                 │
    ▼                 ▼
Development         Production
localhost:8001      localhost:8000
```

### Workflows

**1. `ci-cd-dual.yml` (Main Pipeline)**

Triggers:
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

Jobs:
- `test-all`: Python 3.11, pytest, import validation
- `build-image`: Build Docker image, push to registry
- `deploy-dev`: Deploy to development (condition: `develop` branch)
- `deploy-prod`: Deploy to production (condition: `main` branch)

**2. `quick-test.yml` (Fast Feedback)**

Triggers:
- Pull requests
- Push to `feature/**`, `hotfix/**`, `bugfix/**`

Purpose: Fast validation, no deployment

### Workflow Examples

**Development**:
```bash
git checkout -b feature/new-feature
# Make changes
git add .
git commit -m "feat: new feature"
git push origin feature/new-feature
# Create PR to develop → quick-test.yml runs
# Merge to develop → ci-cd-dual.yml runs → auto-deploy to dev
```

**Production release**:
```bash
curl http://localhost:8001/health  # Verify dev stable
# Create PR from develop to main in Forgejo UI
# Approve and merge → ci-cd-dual.yml runs → auto-deploy to prod
```

### Configuration

**Runner labels**:
```yaml
# Development runner
GITEA_RUNNER_LABELS: dev,ubuntu-latest,ubuntu-22.04

# Production runner
GITEA_RUNNER_LABELS: prod,ubuntu-latest,ubuntu-22.04
```

Verify: `http://localhost:3000/admin/actions/runners`

**Registry credentials** (configured in pipeline):
- User: `admin`
- Password: `chocolateregistry123`

**Required files**:
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`
- `secrets.enc.yaml` (SOPS encrypted)

### SOPS Integration

Pipeline decrypts secrets automatically:
```yaml
- name: Decrypt secrets with SOPS
  run: |
    if ! command -v sops &> /dev/null; then
      sudo apt-get update && sudo apt-get install -y sops age
    fi
    echo "${{ secrets.SOPS_AGE_KEY }}" > /tmp/age-key.txt
    export SOPS_AGE_KEY_FILE=/tmp/age-key.txt
    sops --decrypt secrets.enc.yaml > .env
    rm /tmp/age-key.txt
```

### Monitoring

**View executions**:
- Forgejo UI > Repository > Actions

**Runner logs**:
```bash
docker logs chocolate_factory_runner_dev -f
docker logs chocolate_factory_runner_prod -f
```

**Verify deployments**:
```bash
# Development
curl http://localhost:8001/health
docker compose -f docker-compose.dev.yml ps

# Production
curl http://localhost:8000/health
docker compose -f docker-compose.prod.yml ps
```

### Troubleshooting

**Tests fail**:
```bash
cd src/fastapi-app
pytest tests/ -v
pip freeze > requirements.txt
```

**Build fails**:
```bash
docker build -f docker/fastapi.Dockerfile -t test .
docker build --progress=plain -f docker/fastapi.Dockerfile .
```

**Deploy fails**:
```bash
ls -la docker-compose.*.yml
ls -la docker/secrets/*.txt
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.prod.yml down
```

**Runner offline**:
```bash
docker logs chocolate_factory_runner_dev
docker compose down gitea-runner-dev
# Generate new token in Forgejo UI
# Update RUNNER_TOKEN_DEV in .env
docker compose up -d gitea-runner-dev
```

---

## Docker Compose Reference

### Development (`docker-compose.dev.yml`)

**Services**:
- `fastapi-app-dev`: FastAPI application (port 8001)
  - Hot reload enabled
  - Bind mount: `./src/fastapi-app:/app`
  - Environment: `ENVIRONMENT=development`, `LOG_LEVEL=DEBUG`
  - Uses production InfluxDB (read-only)

**Networks**:
- `dev-backend`: Internal network

**Volumes**:
- Source code: Bind mount for live changes
- Models: `chocolate-factory_models_dev` (persistent)

### Production (`docker-compose.prod.yml`)

**Services**:
- `fastapi-app-prod`: FastAPI application (port 8000)
  - No hot reload
  - Immutable code (within image)
  - Environment: `ENVIRONMENT=production`, `LOG_LEVEL=INFO`
- `influxdb`: InfluxDB time series database (port 8086)
  - Data ingestion enabled
  - Volume: `chocolate-factory_influxdb_prod_data` (persistent)

**Networks**:
- `prod-backend`: Internal network

**Volumes**:
- InfluxDB data: Named volume (persistent)
- Models: `chocolate-factory_models_prod` (persistent)

### Environment Variables

**Common**:
- `INFLUXDB_URL`: InfluxDB connection URL
- `INFLUXDB_ORG`: Organization name (`chocolate_factory`)
- `INFLUXDB_BUCKET`: Bucket name (`energy_data`)

**From SOPS (`.env` decrypted)**:
- `AEMET_API_KEY`: AEMET API key
- `ANTHROPIC_API_KEY`: Claude API key
- `INFLUXDB_TOKEN`: InfluxDB access token
- `OPENWEATHERMAP_API_KEY`: OpenWeatherMap key
- `REE_API_TOKEN`: REE API token

### Health Checks

**FastAPI**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**InfluxDB**:
```yaml
healthcheck:
  test: ["CMD", "influx", "ping"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Commands

**Start services**:
```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.prod.yml up -d
```

**Stop services**:
```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.prod.yml down
```

**View logs**:
```bash
docker compose -f docker-compose.dev.yml logs -f
docker compose -f docker-compose.prod.yml logs --tail=100
```

**Update service**:
```bash
docker compose -f docker-compose.dev.yml up -d --no-deps fastapi-app-dev
docker compose -f docker-compose.prod.yml up -d --no-deps fastapi-app-prod
```

**Clean volumes** (deletes data):
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.prod.yml down -v
```

---

## References

- SOPS: https://github.com/getsops/sops
- age encryption: https://github.com/FiloSottile/age
- Gitea Actions: https://docs.gitea.com/usage/actions/overview
- Docker Compose: https://docs.docker.com/compose/
- InfluxDB Backup: https://docs.influxdata.com/influxdb/v2.7/backup-restore/

---

**End of Infrastructure Documentation**
