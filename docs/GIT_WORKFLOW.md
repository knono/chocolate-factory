# Git Workflow - Chocolate Factory

## Architecture

### Branch Strategy

```
main (production)
  - Always deployable
  - Receives merges from release/* and hotfix/*
  - Each commit = new production version
  - Tagged vX.Y.Z on each release

develop (pre-production)
  - Continuous integration of features
  - Receives merges from feature/*
  - Testing in development environment
  - Base for releases

feature/*  - New functionality (from develop)
release/*  - Release preparation (from develop)
hotfix/*   - Urgent production fix (from main)
bugfix/*   - Non-urgent fix (from develop)
```

### Dual Remotes

Project configured for simultaneous push to two repositories:

```
origin (multiple push)
├─ GitHub: git@github.com:knono/chocolate-factory.git
└─ Forgejo: https://git.azules-elver.ts.net/nono/chocolate-factory.git
```

**Verify configuration:**
```bash
git remote -v
git config --get-regexp "remote.origin.*"
```

**Expected output:**
```
remote.origin.url git@github.com:knono/chocolate-factory.git
remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
remote.origin.pushurl git@github.com:knono/chocolate-factory.git
remote.origin.pushurl https://git.azules-elver.ts.net/nono/chocolate-factory.git
```

---

## Git Flow Setup

```bash
git flow init -d

# Configuration:
gitflow.branch.master = main
gitflow.branch.develop = develop
gitflow.prefix.feature = feature/
gitflow.prefix.release = release/
gitflow.prefix.hotfix = hotfix/
gitflow.prefix.versiontag = v
```

---

## Workflow

### 1. Develop Feature

```bash
# Update develop
git checkout develop
git pull origin develop

# Start feature
git flow feature start descriptive-name
# Creates: feature/descriptive-name from develop

# Develop (hot-reload at http://localhost:8001)
# ... edit code ...

# Incremental commits
git add .
git commit -m "feat: description of change"

# Optional: Backup to GitHub
git push origin feature/descriptive-name
# ⚠️ Does NOT trigger CI/CD, just backup
```

**Status:**
- Feature branch isolated
- Changes visible in local development
- No impact on develop/main
- No pipeline execution

### 2. Integrate Feature → Deploy DEV

```bash
# Ensure code works
curl http://localhost:8001/health

# Finish feature
git flow feature finish descriptive-name
# Git Flow:
#   a) Merges feature/descriptive-name → develop
#   b) Deletes feature/descriptive-name
#   c) Leaves you on develop

# Push to develop (TRIGGERS CI/CD DEV)
git push origin develop
```

**Pipeline executed:**
```yaml
# .gitea/workflows/ci-cd-dual.yml
on:
  push:
    branches: [develop]

jobs:
  dev-deployment:
    - Run tests (134 tests)
    - Build Docker image
    - Deploy to development (port 8001)
    - Smoke tests
```

**Result:**
- ✅ Code in GitHub
- ✅ Code in Forgejo
- ✅ **DEV pipeline running**
- ✅ New version at http://localhost:8001

### 3. Release to Production

```bash
# Start release
git checkout develop
git pull origin develop
git flow release start 0.72.0

# Prepare release (version bumps, CHANGELOG)
# ... edit version files ...
git commit -m "chore: bump version to 0.72.0"

# Finish release
git flow release finish 0.72.0
# Git Flow:
#   a) Merges release/0.72.0 → main
#   b) Merges release/0.72.0 → develop (back-merge)
#   c) Tags v0.72.0
#   d) Deletes release/0.72.0
#   e) Leaves you on develop

# Push main (TRIGGERS CI/CD PROD)
git checkout main
git push origin main --follow-tags

# Push develop (sync back-merge)
git checkout develop
git push origin develop
```

**Pipeline executed:**
```yaml
on:
  push:
    branches: [main]

jobs:
  prod-deployment:
    - Run tests (134 tests)
    - Build Docker image
    - Deploy to production (port 8000)
    - Smoke tests
    - Rollback on failure
```

**Result:**
- ✅ Production deployed at port 8000
- ✅ Tagged v0.72.0
- ✅ develop synced with main

### 4. Hotfix (Urgent Production Fix)

```bash
# Start hotfix from main
git checkout main
git pull origin main
git flow hotfix start 0.72.1

# Fix the issue
# ... edit code ...
git commit -m "fix: critical bug in production"

# Finish hotfix
git flow hotfix finish 0.72.1
# Git Flow:
#   a) Merges hotfix/0.72.1 → main
#   b) Merges hotfix/0.72.1 → develop
#   c) Tags v0.72.1
#   d) Deletes hotfix/0.72.1
#   e) Leaves you on develop

# Push main (TRIGGERS CI/CD PROD)
git checkout main
git push origin main --follow-tags

# Push develop
git checkout develop
git push origin develop
```

---

## Important Behavior

**After `git flow release finish` or `git flow hotfix finish`:**
- Git Flow **returns you to `develop`** (not `main`)
- You must `git checkout main` manually to push to production
- Then return to `develop` to push the back-merge
- This is **by design** in Git Flow

---

## CI/CD Integration

### Pipeline Triggers

**develop branch:**
- Triggers DEV pipeline
- Deploys to port 8001
- Uses `docker-compose.dev.yml`

**main branch:**
- Triggers PROD pipeline
- Deploys to port 8000
- Uses `docker-compose.prod.yml`

**feature/* branches:**
- NO pipeline execution
- Only backup to GitHub

### Pipeline Steps

```yaml
# Both dev and prod pipelines
1. Checkout code
2. Run tests (134 tests, pytest)
3. Build Docker image
4. Push to registry
5. Deploy to environment
6. Smoke tests (36 E2E tests)
7. Rollback on failure (prod only)
```

---

## Dual Remotes Workflow

### Push to Both Repositories

```bash
# Standard push (goes to both)
git push origin <branch-name>

# Examples:
git push origin develop   # Triggers DEV pipeline
git push origin main      # Triggers PROD pipeline
```

### Push to Single Repository

```bash
# Only to GitHub (SSH)
git push git@github.com:knono/chocolate-factory.git <branch>

# Only to Forgejo (HTTPS)
git push https://git.azules-elver.ts.net/nono/chocolate-factory.git <branch>
```

### Verify Pipelines

**GitHub:**
- URL: https://github.com/knono/chocolate-factory/actions
- Use: Backup, external collaboration

**Forgejo:**
- URL: https://git.azules-elver.ts.net/nono/chocolate-factory/actions
- Use: CI/CD automation, deployment

---

## Best Practices

### 1. Atomic Commits

```bash
# ✅ GOOD: One commit = one functionality
git commit -m "feat: add user authentication"

# ❌ BAD: Huge commits with multiple changes
git commit -m "various fixes and features"
```

### 2. Commit Message Format

```
<type>: <short description>

<detailed description (optional)>

<issue/task references>
```

**Types:**
- `feat`: New functionality
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code changes
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance tasks

### 3. Pull Before Push

```bash
# Always pull before push
git pull origin develop
git push origin develop
```

### 4. Verify Deployment

```bash
# After DEV deployment
curl http://localhost:8001/health
curl http://localhost:8001/dashboard

# After PROD deployment
curl http://localhost:8000/health
curl http://localhost:8000/dashboard
```

---

## Complete Sprint Workflow

```bash
# 1. Start sprint
git checkout develop
git pull origin develop
git flow feature start sprint_XX_description

# 2. Development
# ... code ...
git add .
git commit -m "feat: sprint XX implementation"

# 3. Backup to GitHub
git push origin feature/sprint_XX_description

# 4. Merge to develop (triggers DEV pipeline)
git flow feature finish sprint_XX_description
git push origin develop

# 5. Verify DEV deployment
curl http://localhost:8001/health

# 6. Release to production
git flow release start 0.XX.0
# ... version bumps, CHANGELOG ...
git flow release finish 0.XX.0

# 7. Push main (triggers PROD pipeline)
git checkout main
git push origin main --follow-tags

# 8. Sync develop
git checkout develop
git push origin develop

# 9. Verify PROD deployment
curl http://localhost:8000/health
```

---

## Troubleshooting

### Failed Push to Remotes

**Error:** "failed to push some refs"

**Solution:**
```bash
# Pull first
git pull origin <branch>

# Resolve conflicts if any
git mergetool

# Retry push
git push origin <branch>
```

### Authentication Failed (Forgejo)

**Solution:**
```bash
# Configure git credential helper
git config --global credential.helper cache

# Push (will ask for credentials once)
git push origin develop
```

### Slow Push or Timeout

**Solution (individual push):**
```bash
# Push to GitHub first
git push git@github.com:knono/chocolate-factory.git <branch>

# Then to Forgejo
git push https://git.azules-elver.ts.net/nono/chocolate-factory.git <branch>
```

### Pipeline Failure

**Check logs:**
```bash
# View pipeline logs in Forgejo UI
# https://git.azules-elver.ts.net/nono/chocolate-factory/actions

# Check container logs
docker logs chocolate_factory_brain
```

**Rollback (production only):**
- PROD pipeline automatically rolls back on test failure
- Check logs for failure reason
- Fix issue in hotfix branch

---

## References

- GitHub Repository: https://github.com/knono/chocolate-factory
- Forgejo Repository: https://git.azules-elver.ts.net/nono/chocolate-factory
- Forgejo Actions: https://git.azules-elver.ts.net/nono/chocolate-factory/actions
- Pipeline Configuration: `.gitea/workflows/ci-cd-dual.yml`
- CI/CD Documentation: `docs/CI_CD_PIPELINE.md`
