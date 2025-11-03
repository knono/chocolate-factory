# Sprint 18 - Tailscale Auth + Telegram Alerting

**Status**: ✅ COMPLETADO
**Start Date**: 2025-11-02
**Completion Date**: 2025-11-03
**Duration**: 2 días
**Type**: Security + Observability
**Last Update**: 2025-11-03 15:30

---

## ESTADO ACTUAL (2025-11-03 15:30)

**Fase 1: ✅ COMPLETADA - Admin access /vpn funcional**
- Problema resuelto: Uvicorn no confiaba en proxy headers de nginx
- Solución: `--proxy-headers --forwarded-allow-ips 192.168.100.0/24`
- Verificado: Admin accede /vpn, viewer bloqueado correctamente
- Variables: `TAILSCALE_ADMINS`, `TAILSCALE_AUTH_ENABLED`

**Fase 2: ✅ COMPLETADA - 5/5 alertas Telegram implementadas**
- REE ingestion failures ✅
- Backfill completion/failure ✅
- Gap detection (>12h) ✅
- Health monitoring (nodos críticos offline >5min) ✅
- ML training failures (sklearn/Prophet) ✅
- Endpoint test: `/test-telegram` (dev + prod) ✅
- Sistema verificado funcionando correctamente ✅

**Fase 3: ✅ COMPLETADA - Documentación & Testing**
- [x] Actualizar CLAUDE.md (Sprint 18, endpoints, alertas)
- [x] Actualizar docs/INFRASTRUCTURE.md (secciones Auth + Alerts)
- [x] Integration tests (4 tests E2E añadidos a test_smoke_post_deploy.py)
- [x] Tests passing (4/4 tests Sprint 18)

## Objetivo

Implementar autenticación a nivel de aplicación usando headers Tailscale + sistema de alertas vía Telegram para fallos críticos.

**Motivación**:
- Actualmente cualquier usuario en Tailnet = admin (riesgo alto)
- Fallos silenciosos (AEMET down, backfill stuck, Prophet training fail)
- Necesidad de roles: viewer (dashboard) vs admin (API completa + VPN)

---

## Fase 1: Tailscale Authentication (2 días)

### Objetivo

Usar headers Tailscale (`Tailscale-User-Login`, `Tailscale-User-Name`) para control de acceso a nivel de middleware FastAPI.

### Tareas

1. **Upgrade Tailscale a 1.92+ en sidecar**
   - Modificar `docker/tailscale-sidecar.Dockerfile`
   - Actualizar versión de Tailscale (1.86.2 → 1.92.0+)
   - Rebuild sidecar: `docker compose build chocolate-factory`

2. **Configurar lista de admins**
   - Variable de entorno `TAILSCALE_ADMINS` con emails autorizados
   - Separados por comas: `admin1@example.com,admin2@example.com`
   - Control de acceso gestionado en middleware FastAPI

3. **Implementar middleware FastAPI**
   - Crear `src/fastapi-app/api/middleware/tailscale_auth.py`
   - Leer headers: `Tailscale-User-Login`, `Tailscale-User-Name`
   - Validar usuario existe en header
   - Verificar si ruta requiere admin
   - Rutas admin protegidas:
     - `/vpn` (VPN dashboard)
   - Retornar 403 Forbidden si viewer intenta acceder ruta admin
   - Adjuntar `request.state.user_login` para audit logging

4. **Configuración en settings**
   - Añadir en `core/config.py`:
     ```python
     TAILSCALE_AUTH_ENABLED: bool = Field(default=True)
     TAILSCALE_ADMINS: List[str] = Field(default=[])
     ```
   - Variables de entorno:
     ```bash
     TAILSCALE_AUTH_ENABLED=true
     TAILSCALE_ADMINS=admin@example.com,owner@example.com
     ```

5. **Integración en main.py**
   - Añadir middleware:
     ```python
     from api.middleware.tailscale_auth import tailscale_auth_middleware
     app.add_middleware(tailscale_auth_middleware)
     ```

6. **Audit logging**
   - Log cada request con user identity:
     ```python
     logger.info(f"User {user_login} accessed {request.url.path}")
     ```

7. **Tests**
   - Crear `tests/unit/test_tailscale_auth.py`
   - Test casos:
     - Header ausente → 401 Unauthorized
     - Viewer accede `/dashboard` → 200 OK
     - Viewer accede `/vpn` → 403 Forbidden
     - Admin accede `/vpn` → 200 OK
     - Admin accede `/predict/train` → 200 OK
     - Request state contiene user_login

8. **Documentación**
   - Crear `docs/TAILSCALE_AUTH.md`
   - Setup guide (ACLs, env vars)
   - Lista rutas protegidas
   - Troubleshooting (headers no llegan)

### Entregables

- [x] `docker/tailscale-sidecar.Dockerfile` (Tailscale 1.92+)
- [x] `api/middleware/tailscale_auth.py` (403 líneas)
- [x] `core/config.py` (TAILSCALE_ADMINS, TAILSCALE_AUTH_ENABLED)
- [x] `main.py` (middleware integrado)
- [x] `tests/unit/test_tailscale_auth.py` (12 tests)
- [x] `docs/TAILSCALE_AUTH.md` (setup guide)

### Criterios de Aceptación

- [x] Viewer accede `/dashboard` → 200 OK
- [x] Viewer accede `/vpn` → 403 Forbidden
- [x] Admin accede `/vpn` → 200 OK
- [x] Logs muestran user identity en cada request
- [x] Tests passing (12/12)

---

## Fase 2: Telegram Alerting (1.5 días)

### Objetivo

Sistema de alertas proactivo vía Telegram bot para detectar fallos críticos (AEMET down, backfill stuck, nodos offline, Prophet training fail).

### Tareas

1. **Crear Telegram bot**
   - Botfather → `/newbot`
   - Obtener `BOT_TOKEN`
   - Crear chat/canal privado
   - Obtener `CHAT_ID` (usar bot `@userinfobot`)

2. **Implementar servicio de alertas**
   - Crear `src/fastapi-app/services/telegram_alert_service.py`
   - Clase `TelegramAlertService`:
     ```python
     class TelegramAlertService:
         def __init__(self, bot_token: str, chat_id: str):
             self.bot_token = bot_token
             self.chat_id = chat_id
             self.api_url = f"https://api.telegram.org/bot{bot_token}"
             self._last_alerts = {}  # Rate limiting

         async def send_alert(self, message: str, severity: str = "INFO", topic: str = None):
             # Rate limiting: max 1 alert per topic per 15min
             if self._should_rate_limit(topic):
                 return

             emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}
             formatted = f"{emoji[severity]} {message}"

             async with httpx.AsyncClient() as client:
                 await client.post(
                     f"{self.api_url}/sendMessage",
                     json={"chat_id": self.chat_id, "text": formatted}
                 )

             self._last_alerts[topic] = datetime.utcnow()
     ```

3. **Configuración**
   - Añadir en `core/config.py`:
     ```python
     TELEGRAM_BOT_TOKEN: str = Field(default="")
     TELEGRAM_CHAT_ID: str = Field(default="")
     TELEGRAM_ALERTS_ENABLED: bool = Field(default=False)
     ```
   - `.env`:
     ```bash
     TELEGRAM_BOT_TOKEN=your_token_here
     TELEGRAM_CHAT_ID=your_chat_id
     TELEGRAM_ALERTS_ENABLED=true
     ```

4. **Integrar en servicios críticos**

   **a) REE ingestion failures**
   - `services/ree_service.py`
   - Detectar: >3 fallos consecutivos en 1h
   - Alert: `⚠️ WARNING: REE ingestion failed 3 times in last hour`

   **b) Backfill completion/failure**
   - `services/backfill_service.py`
   - Alert on completion: `ℹ️ INFO: Backfill completed - 48h gap filled (120 records)`
   - Alert on failure: `🚨 CRITICAL: Backfill failed after 3 retries`

   **c) Gap detection**
   - `services/gap_detector.py`
   - Detectar: gap >12h
   - Alert: `⚠️ WARNING: Data gap detected - 14.5h missing (REE prices)`

   **d) Critical nodes offline**
   - `tasks/health_monitoring_jobs.py`
   - Detectar: production/dev/git offline >5min
   - Alert: `🚨 CRITICAL: Production node offline for 5 minutes`

   **e) ML training failures**
   - `tasks/sklearn_jobs.py`
   - Detectar: sklearn training exception
   - Alert: `🚨 CRITICAL: sklearn training failed - {error_msg}`
   - `tasks/ml_jobs.py` (Prophet)
   - Detectar: Prophet training exception
   - Alert: `🚨 CRITICAL: Prophet training failed - forecast unavailable`

5. **Rate limiting**
   - Max 1 alert por topic cada 15min
   - Evitar spam si fallo persistente
   - Log alerts suprimidas: `logger.debug(f"Alert rate limited: {topic}")`

6. **Dependency injection**
   - Añadir en `dependencies.py`:
     ```python
     _telegram_alert_instance = None

     def get_telegram_alert_service():
         global _telegram_alert_instance
         if _telegram_alert_instance is None:
             if settings.TELEGRAM_ALERTS_ENABLED:
                 _telegram_alert_instance = TelegramAlertService(
                     bot_token=settings.TELEGRAM_BOT_TOKEN,
                     chat_id=settings.TELEGRAM_CHAT_ID
                 )
         return _telegram_alert_instance
     ```

7. **Tests**
   - Crear `tests/unit/test_telegram_alerts.py`
   - Mock httpx.AsyncClient
   - Test casos:
     - send_alert success (200 OK)
     - send_alert API failure (retry)
     - Rate limiting (2 alerts mismo topic <15min)
     - Emoji formatting correcto
     - Disabled cuando TELEGRAM_ALERTS_ENABLED=false

8. **Documentación**
   - Crear `docs/TELEGRAM_ALERTS.md`
   - Setup guide (Botfather, obtener token/chat_id)
   - Lista alertas implementadas
   - Rate limiting behavior
   - Troubleshooting (alerts no llegan)

### Entregables

- [ ] Bot Telegram creado (BOT_TOKEN, CHAT_ID)
- [ ] `services/telegram_alert_service.py` (~150 líneas)
- [ ] `core/config.py` (TELEGRAM_* variables)
- [ ] `dependencies.py` (get_telegram_alert_service)
- [ ] 5 servicios integrados (ree, backfill, gap, health, ml)
- [ ] `tests/unit/test_telegram_alerts.py` (6 tests)
- [ ] `docs/TELEGRAM_ALERTS.md` (setup guide)

### Criterios de Aceptación

- [ ] Alert enviada cuando REE falla 3 veces
- [ ] Alert enviada cuando backfill completa
- [ ] Alert enviada cuando gap >12h detectado
- [ ] Alert enviada cuando nodo crítico offline >5min
- [ ] Alert enviada cuando Prophet training falla
- [ ] Rate limiting funciona (max 1/15min por topic)
- [ ] Tests passing (6/6)

---

## Fase 3: Documentación & Testing (1.5 días)

### Tareas

1. **Actualizar CLAUDE.md**
   - Añadir Sprint 18 a historia
   - Actualizar endpoints protegidos
   - Actualizar sistema de alertas

2. **Actualizar docs/INFRASTRUCTURE.md**
   - Sección Tailscale Auth
   - Sección Telegram Alerts

3. **Integration tests**
   - Test end-to-end:
     - User viewer → `/dashboard` → 200
     - User viewer → `/vpn` → 403
     - Simular fallo REE → alert enviada
     - Simular gap >12h → alert enviada

### Entregables

- [ ] `CLAUDE.md` actualizado
- [ ] `docs/INFRASTRUCTURE.md` actualizado
- [ ] Integration tests (4 tests)

---

## Métricas de Éxito

- [ ] Auth middleware funcional (8 tests passing)
- [ ] 5 tipos de alertas implementadas
- [ ] Telegram bot recibe alertas correctamente
- [ ] Viewer NO puede acceder `/vpn` (403)
- [ ] Admin puede acceder todas las rutas
- [ ] Audit logs muestran user identity
- [ ] Rate limiting funciona (no spam)
- [ ] Documentación completa (2 docs nuevos)

---

## Notas Técnicas

### Tailscale Headers

Cuando Tailscale proxy hace forward a FastAPI, inyecta headers:
```
Tailscale-User-Login: user@example.com
Tailscale-User-Name: John Doe
Tailscale-User-Profile-Pic: https://...
```

FastAPI middleware lee estos headers:
```python
user_login = request.headers.get("Tailscale-User-Login")
```

**Importante**: Headers solo presentes si request viene via Tailscale sidecar. Acceso directo `localhost:8000` NO tiene headers (desarrollo local).

### Telegram API - sendMessage

Endpoint:
```
POST https://api.telegram.org/bot{BOT_TOKEN}/sendMessage
Body: {"chat_id": "123456", "text": "🚨 Alert message"}
```

Response 200 OK:
```json
{"ok": true, "result": {"message_id": 789, ...}}
```

Rate limits Telegram:
- 30 mensajes/segundo a mismo chat
- No problema para este use case

### Rate Limiting - Implementación

```python
from datetime import datetime, timedelta

class TelegramAlertService:
    def __init__(self):
        self._last_alerts = {}  # {topic: datetime}

    def _should_rate_limit(self, topic: str) -> bool:
        if topic not in self._last_alerts:
            return False

        last_alert = self._last_alerts[topic]
        elapsed = datetime.utcnow() - last_alert
        return elapsed < timedelta(minutes=15)
```

---

## Dependencias

- Tailscale 1.92+ (header injection support)
- httpx (ya instalado)
- pytest-asyncio (ya instalado)
- Telegram bot token (obtener via Botfather)

---

## Riesgos

1. **Tailscale headers no llegan a FastAPI**
   - Causa: nginx no hace proxy de headers
   - Solución: Verificar nginx config en sidecar (`proxy_set_header`)

2. **Telegram API down**
   - Causa: api.telegram.org unreachable
   - Solución: Log error, no crashear aplicación

3. **Alert spam**
   - Causa: Rate limiting no funciona
   - Solución: Test exhaustivo rate limiting logic

---

## Problemas Técnicos y Soluciones (Fase 1)

### Problema 1: Admin no puede acceder /vpn (2025-11-02)

**Síntoma**:
```
Forbidden: shared-node-192.168.100.8 (role=viewer) attempted admin route /static/vpn.html
```

**Diagnóstico**:
1. Nginx (sidecar `192.168.100.8`) veía IP real Tailscale (`100.106.17.48`)
2. Nginx configuraba headers: `X-Real-IP`, `X-Forwarded-For`
3. FastAPI middleware recibía: `X-Real-IP=None`, `client.host=192.168.100.8`
4. Uvicorn por defecto NO confía en proxy headers

**Causa raíz**: Uvicorn ignora headers de proxy sin configuración explícita.

**Solución**:

1. **Modificar `docker/fastapi.Dockerfile`** (línea 72):
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000",
     "--proxy-headers", "--forwarded-allow-ips", "192.168.100.0/24"]
```

2. **Modificar `docker/sidecar-nginx.conf`** (líneas 201-203):
```nginx
location ~ ^/(static|css|js|images|fonts)/ {
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Flags críticos**:
- `--proxy-headers`: Habilita lectura de X-Forwarded-For, X-Real-IP
- `--forwarded-allow-ips 192.168.100.0/24`: Confía en headers desde nginx sidecar

**Resultado**:
```
Admin access granted: maldonadohervas@gmail.com → /vpn
INFO: 100.106.17.48:0 - "GET /vpn HTTP/1.0" 307 Temporary Redirect
```

**Verificación**:
```bash
# Nginx ve IP correcta
docker exec chocolate-factory tail /var/log/nginx/access.log
# 100.106.17.48 (via -) - ...

# FastAPI recibe IP correcta
docker logs chocolate_factory_brain | grep "Admin access granted"
# Admin access granted: maldonadohervas@gmail.com → /vpn
```

---

## Checklist Final Sprint 18

- [x] Fase 1 completada (Tailscale Auth)
- [x] Fase 2 completada (Telegram Alerts)
- [x] Sistema funciona end-to-end
- [x] Fase 3 completada (Docs + Tests)
- [x] Integration tests E2E (4 tests)
- [x] CLAUDE.md actualizado
- [x] docs/INFRASTRUCTURE.md actualizado

---

## Configuración Práctica

### Gestión de Secretos con SOPS

**Flujo completo para añadir/modificar secretos:**

1. **Editar archivo desencriptado** (`.sops/secrets.yaml`):
```yaml
# Añadir nuevos secretos
tailscale_admins: "user@example.com"
tailscale_auth_enabled: "true"
telegram_bot_token: "<your_bot_token>"
telegram_chat_id: "<your_chat_id>"
telegram_alerts_enabled: "true"
```

2. **Encriptar con SOPS**:
```bash
export SOPS_AGE_KEY_FILE=.sops/age-key.txt
sops --encrypt --age age1gwyvmk9vecx83l9c0zrjsfx4ts4nw6xqcakvduerzcxk9056dcsspd7k8u \
  .sops/secrets.yaml >| secrets.enc.yaml
```

3. **Regenerar `.env`** desde archivo encriptado:
```bash
bash scripts/decrypt-and-convert.sh
```

4. **Verificar variables generadas**:
```bash
grep TAILSCALE .env
grep TELEGRAM .env
```

**Resultado esperado** (snake_case + UPPERCASE):
```bash
tailscale_admins=user@example.com
tailscale_auth_enabled=true
TAILSCALE_ADMINS=user@example.com
TAILSCALE_AUTH_ENABLED=true

telegram_bot_token=<token>
telegram_chat_id=<chat_id>
telegram_alerts_enabled=true
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>
TELEGRAM_ALERTS_ENABLED=true
```

### Script decrypt-and-convert.sh

**Conversión automática snake_case → UPPERCASE:**

El script `scripts/decrypt-and-convert.sh` realiza:
1. Desencripta `secrets.enc.yaml` → `/tmp/secrets-plain.yaml`
2. Convierte YAML a formato `.env` (snake_case)
3. **Genera versiones UPPERCASE** de variables críticas:

```bash
# Líneas 96-100: Tailscale Auth
TAILSCALE_ADMINS_VALUE=$(grep "^tailscale_admins=" .env | cut -d= -f2)
TAILSCALE_AUTH_ENABLED_VALUE=$(grep "^tailscale_auth_enabled=" .env | cut -d= -f2)
echo "TAILSCALE_ADMINS=${TAILSCALE_ADMINS_VALUE}" >> .env
echo "TAILSCALE_AUTH_ENABLED=${TAILSCALE_AUTH_ENABLED_VALUE}" >> .env

# Líneas 103-108: Telegram Alerts
TELEGRAM_BOT_TOKEN_VALUE=$(grep "^telegram_bot_token=" .env | cut -d= -f2)
TELEGRAM_CHAT_ID_VALUE=$(grep "^telegram_chat_id=" .env | cut -d= -f2)
TELEGRAM_ALERTS_ENABLED_VALUE=$(grep "^telegram_alerts_enabled=" .env | cut -d= -f2)
echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN_VALUE}" >> .env
echo "TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID_VALUE}" >> .env
echo "TELEGRAM_ALERTS_ENABLED=${TELEGRAM_ALERTS_ENABLED_VALUE}" >> .env
```

**Razón**: Docker Compose lee variables como `${TELEGRAM_BOT_TOKEN}` (UPPERCASE).

### Configuración Telegram Bot

**1. Crear bot con BotFather:**
```
1. Abrir Telegram → buscar @BotFather
2. /newbot
3. Nombre: Chocolate Factory Alerts
4. Username: chocolate_factory_alerts_bot
5. Copiar TOKEN: 1234567890:ABCdef...
```

**2. Obtener CHAT_ID:**
```bash
# Enviar /start al bot primero
curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

Extraer `chat.id` del JSON response.

**3. Añadir credenciales a `.sops/secrets.yaml`:**
```yaml
telegram_bot_token: "1234567890:ABCdef..."
telegram_chat_id: "123456789"
telegram_alerts_enabled: "true"
```

**4. Encriptar, regenerar .env, y reiniciar contenedores:**
```bash
# Encriptar
sops --encrypt --age age1gwyvmk9vecx83l9c0zrjsfx4ts4nw6xqcakvduerzcxk9056dcsspd7k8u \
  .sops/secrets.yaml >| secrets.enc.yaml

# Regenerar .env
bash scripts/decrypt-and-convert.sh

# Reiniciar contenedores
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d fastapi-app
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml up -d fastapi-app-dev
```

**5. Verificar funcionamiento:**
```bash
# Test endpoint
curl -X POST http://localhost:8000/test-telegram
curl -X POST http://localhost:8001/test-telegram

# Verificar logs
docker logs chocolate_factory_brain 2>&1 | grep -i telegram
docker logs chocolate_factory_dev 2>&1 | grep -i telegram
```

### Variables de Entorno en docker-compose

**docker-compose.yml (producción):**
```yaml
environment:
  # Sprint 18: Tailscale Authentication
  - TAILSCALE_AUTH_ENABLED=${TAILSCALE_AUTH_ENABLED:-true}
  - TAILSCALE_ADMINS=${TAILSCALE_ADMINS}
  # Sprint 18: Telegram Alerts
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
  - TELEGRAM_ALERTS_ENABLED=${TELEGRAM_ALERTS_ENABLED:-true}
```

**docker-compose.dev.yml (desarrollo):**
```yaml
environment:
  # Sprint 18: Tailscale Authentication
  - TAILSCALE_AUTH_ENABLED=${TAILSCALE_AUTH_ENABLED:-true}
  - TAILSCALE_ADMINS=${TAILSCALE_ADMINS}
  # Sprint 18: Telegram Alerts
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
  - TELEGRAM_ALERTS_ENABLED=${TELEGRAM_ALERTS_ENABLED:-true}
```

### Alertas Implementadas

**1. REE Ingestion Failures** (`services/ree_service.py`):
- Trigger: >3 fallos consecutivos en 1 hora
- Severity: WARNING
- Topic: `ree_ingestion`
- Rate limit: 15 min

**2. Backfill Completion/Failure** (`services/backfill_service.py`):
- Trigger: Backfill completo o error
- Severity: INFO (success) / CRITICAL (failure)
- Topics: `backfill_completion`, `backfill_failure`
- Rate limit: 15 min

**3. Gap Detection** (`services/gap_detector.py`):
- Trigger: Gap >12 horas detectado
- Severity: WARNING
- Topic: `gap_detection`
- Rate limit: 15 min

**4. Health Monitoring** (`tasks/health_monitoring_jobs.py`):
- Trigger: Nodo crítico offline >5 minutos
- Severity: CRITICAL
- Topic: `health_monitoring_{node_id}`
- Rate limit: 15 min

**5. ML Training Failures** (`tasks/sklearn_jobs.py`, `tasks/ml_jobs.py`):
- Trigger: Excepción durante training
- Severity: CRITICAL
- Topics: `ml_training_sklearn`, `ml_training_prophet`
- Rate limit: 15 min

### Dependency Injection

**Servicios actualizados para recibir `telegram_service`:**

```python
# dependencies.py
def get_telegram_alert_service():
    if settings.TELEGRAM_ALERTS_ENABLED:
        return TelegramAlertService(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
            enabled=True
        )
    return None

def get_backfill_service():
    telegram = get_telegram_alert_service()
    return BackfillService(telegram_service=telegram)
```

**Routers actualizados:**
- `api/routers/ree.py`: Inyecta telegram en REEService
- `tasks/ree_jobs.py`: Inyecta telegram en job programado
- `api/routers/gaps.py`: Usa `get_backfill_service()`
- `services/scheduler.py`: Usa `get_backfill_service()`

### Testing

**Endpoint de prueba** (`/test-telegram`):
```bash
# Dev (puerto 8001)
curl -X POST http://localhost:8001/test-telegram

# Prod (puerto 8000)
curl -X POST http://localhost:8000/test-telegram
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "message": "Test alert sent successfully",
  "telegram_enabled": true,
  "timestamp": "2025-11-03T09:18:16.976113"
}
```

**Mensaje en Telegram:**
```
ℹ️ INFO

🧪 TEST ALERT

This is a test message from Chocolate Factory.
If you received this, Telegram alerts are working correctly!

Timestamp: 2025-11-03T09:18:16.976113
```

---

## Lecciones Aprendidas

### Fase 1: Tailscale Auth

**Problema**: Uvicorn no confiaba en headers de proxy por defecto.

**Solución**: Flags `--proxy-headers --forwarded-allow-ips 192.168.100.0/24` en Dockerfile.

**Aprendizaje**: Configuración de proxy requiere trust explícito de red interna.

### Fase 2: Telegram Alerts

**Problema 1**: Variables no llegaban a contenedores.

**Solución**: Añadir a ambos `docker-compose.yml` y `docker-compose.dev.yml`.

**Problema 2**: Script no generaba versiones UPPERCASE.

**Solución**: Actualizar `decrypt-and-convert.sh` con conversión explícita.

**Aprendizaje**: Docker Compose interpola `${VAR}` (UPPERCASE), pero código Python lee de `config.py` (puede usar cualquier formato). Mantener ambas versiones en `.env` asegura compatibilidad.

### SOPS Workflow

**Secuencia crítica**:
1. Editar `.sops/secrets.yaml` (desencriptado)
2. Encriptar → `secrets.enc.yaml`
3. Regenerar `.env` desde encriptado
4. Reiniciar contenedores

**Error común**: Editar `.env` directamente (se pierde al regenerar).

**Solución**: Siempre editar `.sops/secrets.yaml` como fuente de verdad.
