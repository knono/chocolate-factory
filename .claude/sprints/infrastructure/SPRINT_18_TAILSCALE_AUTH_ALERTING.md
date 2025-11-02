# Sprint 18 - Tailscale Auth + Telegram Alerting

**Status**: EN PROGRESO
**Start Date**: 2025-11-02
**Completion Date**: TBD
**Duration**: 5 días
**Type**: Security + Observability
**Last Update**: 2025-11-02 19:30

---

## ESTADO ACTUAL (2025-11-02 20:00)

**Fase 1: ✅ COMPLETADA - Admin access /vpn funcional**
- Problema resuelto: Uvicorn no confiaba en proxy headers de nginx
- Solución: `--proxy-headers --forwarded-allow-ips 192.168.100.0/24`
- Verificado: Admin accede /vpn, viewer bloqueado correctamente

**Fase 2: 40% - 2/5 alertas implementadas**
- sklearn/Prophet alertas ✅
- Falta: REE, backfill, gap_detector, health_monitoring

## Objetivo

Implementar autenticación a nivel de aplicación usando Tailscale App Capabilities + sistema de alertas vía Telegram para fallos críticos.

**Motivación**:
- Actualmente cualquier usuario en Tailnet = admin (riesgo alto)
- Fallos silenciosos (AEMET down, backfill stuck, Prophet training fail)
- Necesidad de roles: viewer (dashboard) vs admin (API completa + VPN)

---

## Fase 1: Tailscale App Capabilities (2 días)

### Objetivo

Usar headers Tailscale (`Tailscale-User-Login`, `Tailscale-User-Name`) para control de acceso sin OAuth ni gestión de credenciales.

### Tareas

1. **Upgrade Tailscale a 1.92+ en sidecar**
   - Modificar `docker/tailscale-sidecar.Dockerfile`
   - Actualizar versión de Tailscale (1.86.2 → 1.92.0+)
   - Rebuild sidecar: `docker compose build chocolate-factory`

2. **Configurar Tailscale ACLs con app connectors**
   - Editar ACLs en Tailscale Admin Console
   - Definir grupos: `group:viewers`, `group:admins`
   - Configurar app connectors para routes específicas
   - Ejemplo:
     ```json
     {
       "src": ["group:viewers"],
       "app": {
         "tailscale.com/app-connectors": [{
           "name": "chocolate-factory",
           "connectors": ["/dashboard", "/static/*", "/health"]
         }]
       }
     }
     ```

3. **Implementar middleware FastAPI**
   - Crear `src/fastapi-app/api/middleware/tailscale_auth.py`
   - Leer headers: `Tailscale-User-Login`, `Tailscale-User-Name`
   - Validar usuario existe en header
   - Verificar si ruta requiere admin
   - Rutas admin protegidas:
     - `/vpn` (VPN dashboard)
     - `/predict/train*` (entrenamiento ML)
     - `/gaps/backfill*` (backfill manual)
     - `/chat/ask` (chatbot - costoso API)
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

- [ ] `docker/tailscale-sidecar.Dockerfile` (Tailscale 1.92+)
- [ ] Tailscale ACLs configuradas (Admin Console)
- [ ] `api/middleware/tailscale_auth.py` (~100 líneas)
- [ ] `core/config.py` (TAILSCALE_ADMINS, TAILSCALE_AUTH_ENABLED)
- [ ] `main.py` (middleware integrado)
- [ ] `tests/unit/test_tailscale_auth.py` (8 tests)
- [ ] `docs/TAILSCALE_AUTH.md` (setup guide)

### Criterios de Aceptación

- [ ] Viewer accede `/dashboard` → 200 OK
- [ ] Viewer accede `/vpn` → 403 Forbidden
- [ ] Admin accede `/vpn` → 200 OK
- [ ] Admin accede `/predict/train` → 200 OK
- [ ] Logs muestran user identity en cada request
- [ ] Tests passing (8/8)

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

4. **Sprint retrospective**
   - Crear `.claude/sprints/infrastructure/SPRINT_18_RETROSPECTIVE.md`
   - Issues encontrados
   - Lecciones aprendidas

### Entregables

- [ ] `CLAUDE.md` actualizado
- [ ] `docs/INFRASTRUCTURE.md` actualizado
- [ ] Integration tests (4 tests)
- [ ] Sprint retrospective document

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

### Tailscale App Capabilities - Headers

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

- Tailscale 1.92+ (App Capabilities feature)
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
- [ ] Fase 2 completada (Telegram Alerts)
- [ ] Fase 3 completada (Docs + Tests)
- [ ] Tests passing: 14 nuevos (8 auth + 6 alerts)
- [ ] Documentación: 2 docs nuevos
- [ ] CLAUDE.md actualizado
- [ ] Sistema funciona end-to-end
- [ ] Sprint retrospective escrito
