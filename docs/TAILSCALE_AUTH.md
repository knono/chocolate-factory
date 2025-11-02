# Tailscale Authentication

**Sprint**: 18
**Date**: 2025-11-02
**Type**: Security

## Overview

Authentication middleware using Tailscale network access. Detects Tailscale CGNAT IPs (100.64.0.0/10) and enforces role-based access.

## Access Levels

1. **Admin**: Header + email in `TAILSCALE_ADMINS` → full access including `/vpn`
2. **Viewer with account**: Header but not admin → all except `/vpn`
3. **Viewer via node share**: No header but Tailscale IP → all except `/vpn`

## Implementation

### Middleware Logic

```
if IP not Tailscale (100.64.x.x):
    → 401 Unauthorized

if header + email in TAILSCALE_ADMINS:
    → role=admin (full access)

if header + email not in TAILSCALE_ADMINS:
    → role=viewer (all except /vpn)

if no header but Tailscale IP:
    → role=viewer, user=shared-node-{IP} (all except /vpn)
```

### Protected Routes

- `/vpn` - Admin only

### Public Routes

- `/health`, `/ready`, `/version` - No auth
- `/docs`, `/redoc`, `/openapi.json` - No auth (dev only)
- `/static/*` - No auth

## Configuration

### Environment Variables

```bash
# .env
TAILSCALE_AUTH_ENABLED=true
TAILSCALE_ADMINS=your-email@gmail.com
```

Multiple admins (comma-separated):
```bash
TAILSCALE_ADMINS=admin1@gmail.com,admin2@example.com
```

### Tailscale Sidecar

Requires Tailscale 1.92.0+ for header support:

```dockerfile
# docker/tailscale-sidecar.Dockerfile
RUN wget -O /tmp/tailscale.tgz https://pkgs.tailscale.com/stable/tailscale_1.92.0_amd64.tgz
```

### Nginx Configuration

Ensure nginx forwards Tailscale headers:

```nginx
location / {
    proxy_pass http://chocolate_factory_brain:8000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Tailscale-User-Login $http_tailscale_user_login;
}
```

## Node Share Behavior

When you share a node with another Tailnet:
- User accesses from their own Tailnet
- Tailscale does NOT send `Tailscale-User-Login` header
- Middleware detects Tailscale IP (100.64.x.x)
- Grants viewer role automatically
- Logs as `shared-node-{IP}`

## Audit Logging

All requests logged with user identity:

```
Admin user: admin@example.com → /vpn
Viewer user: viewer@example.com → /dashboard
Node share access: shared-node-100.64.2.100 → /dashboard
Forbidden: viewer@example.com (role=viewer) attempted admin route /vpn
```

Response headers:
- `X-Authenticated-User`: Email or `shared-node-{IP}`
- `X-User-Role`: `admin` or `viewer`

## Development Mode

Localhost bypass enabled when `ENVIRONMENT=development`:

```python
# main.py
app.add_middleware(
    TailscaleAuthMiddleware,
    enabled=settings.TAILSCALE_AUTH_ENABLED,
    admin_users=settings.TAILSCALE_ADMINS,
    bypass_local=(settings.ENVIRONMENT == "development")
)
```

Local access without Tailscale:
```bash
curl http://localhost:8000/vpn
# → 200 OK (bypassed in dev)
```

Disable bypass:
```bash
ENVIRONMENT=production
```

## Testing

Run tests:
```bash
cd src/fastapi-app
pytest tests/unit/test_tailscale_auth.py -v
```

**Coverage**: 16 tests
- Tailscale IP detection (7 parametrized cases)
- Admin access to /vpn
- Viewer cannot access /vpn
- Node share cannot access /vpn
- Node share can access other routes
- Non-Tailscale IP rejected
- Localhost bypass
- Auth disable toggle

## Troubleshooting

### Headers not arriving

**Symptom**: All requests via Tailscale return 401

**Check**:
```bash
# Verify nginx forwards headers
docker logs chocolate-factory-sidecar 2>&1 | grep Tailscale-User-Login

# Check Tailscale version
docker exec chocolate-factory-sidecar tailscale version
# Must be 1.92.0+
```

**Fix**: Rebuild sidecar
```bash
docker compose build chocolate-factory
docker compose up -d chocolate-factory
```

### Admin user gets 403 on /vpn

**Symptom**: Admin user cannot access /vpn

**Check**:
```bash
# Verify admin list
docker exec chocolate_factory_brain env | grep TAILSCALE_ADMINS
```

**Fix**: Update `.env`
```bash
TAILSCALE_ADMINS=your-actual-email@gmail.com
docker compose restart chocolate_factory_brain
```

### Node share gets 401

**Symptom**: Shared node cannot access any route

**Cause**: IP not in Tailscale CGNAT range

**Debug**:
```bash
# Check client IP in logs
docker logs chocolate_factory_brain 2>&1 | grep "Unauthorized"
```

**Valid Tailscale IPs**: 100.64.0.0 - 100.127.255.255

### Localhost bypass not working

**Symptom**: Localhost returns 401 in development

**Fix**:
```bash
# .env
ENVIRONMENT=development
docker compose restart chocolate_factory_brain
```

## Files

- `src/fastapi-app/api/middleware/tailscale_auth.py` - Middleware (228 lines)
- `src/fastapi-app/core/config.py` - Settings
- `src/fastapi-app/main.py` - Integration
- `src/fastapi-app/tests/unit/test_tailscale_auth.py` - Tests (16)
- `docker/tailscale-sidecar.Dockerfile` - Tailscale 1.92.0

## References

- Tailscale CGNAT: https://tailscale.com/kb/1015/100.x-addresses
- Node Sharing: https://tailscale.com/kb/1084/sharing
- Sprint 18: `.claude/sprints/infrastructure/SPRINT_18_TAILSCALE_AUTH_ALERTING.md`
