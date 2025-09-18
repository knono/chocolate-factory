# REGLA: Manejo Seguro de Información Sensible

## OBJETIVO

Esta regla establece las pautas obligatorias para manejar información sensible (API keys, tokens, credenciales) en el proyecto Chocolate Factory, garantizando que no se expongan en el código fuente público.

## INFORMACIÓN SENSIBLE IDENTIFICADA

### API Keys y Tokens
- **REE API Token**: `REE_API_TOKEN`
- **AEMET API Key**: `AEMET_API_KEY`
- **OpenWeatherMap API Key**: `OPENWEATHERMAP_API_KEY`
- **InfluxDB Token**: `INFLUXDB_TOKEN`
- **Tailscale Auth Key**: `TAILSCALE_AUTHKEY`

### Credenciales de Base de Datos
- **InfluxDB Admin Token**: Token de administrador
- **Database URLs**: URLs con credenciales embebidas
- **Certificados SSL**: Archivos de certificados privados

### Información de Infraestructura
- **IPs privadas**: Direcciones IP internas
- **Puertos de servicios**: Configuraciones de red sensibles
- **Rutas de archivos**: Paths del sistema que revelan estructura

## PATRONES OBLIGATORIOS PARA PROTEGER INFORMACIÓN

### 1. Archivos .env (Variables de Entorno)

**✅ FORMATO CORRECTO para archivos .example**:
```bash
# .env.example (archivo de ejemplo público)
REE_API_TOKEN=<your_ree_api_token_here>
AEMET_API_KEY=<your_aemet_api_key_here>
INFLUXDB_TOKEN=<your_influxdb_token_here>
TAILSCALE_AUTHKEY=tskey-auth-<your-key-example>
```

### 2. Archivos de Configuración

**✅ USAR SIEMPRE placeholders**:
```python
# config.py
INFLUX_TOKEN = "<your_influxdb_token_here>"  # ✅ PLACEHOLDER
API_KEY = os.getenv('API_KEY', '<your_api_key_here>')  # ✅ SEGURO
```

### 3. Documentación y README

**✅ FORMATO SEGURO para documentación**:
```markdown
## Setup
```bash
export INFLUX_TOKEN="<your_influxdb_token>"
curl -H "Authorization: Bearer <your_api_token>"
```

### 4. Scripts y Comandos

**✅ FORMATO PARAMETRIZADO**:
```bash
# backup.sh
curl -H "Authorization: Token ${INFLUX_TOKEN}"  # ✅ VARIABLE
# O usar placeholder en documentación
curl -H "Authorization: Token <your_influx_token>"  # ✅ EJEMPLO
```

## FORMATOS DE PLACEHOLDER OBLIGATORIOS

### Para API Keys
```
<your_api_key_here>
<your_token_here>
<your_secret_here>
```

### Para Configuraciones Específicas
```
<your_ree_api_token>
<your_aemet_api_key>
<your_openweather_api_key>
<your_influxdb_token>
<your_tailscale_authkey>
```

### Para URLs y Endpoints
```
<your_server_url>
<your_database_host>
<your_domain_here>
```

### Para Valores Estructurados
```
# Tailscale
tskey-auth-<your-key-example>

# Tokens con prefijo
Bearer <your_bearer_token>

# URLs completas
https://<your-domain>.ts.net/dashboard
```

## ARCHIVOS QUE DEBEN USAR PLACEHOLDERS

### Archivos de Configuración
- `.env.example` ✅
- `.env.tailscale.example` ✅
- `config.py` (en ejemplos de código)
- `docker-compose.override.yml.example`

### Documentación
- `README.md` ✅
- `docs/*.md` ✅
- `CLAUDE.md` (en secciones de setup)
- Scripts en `.claude/commands/*.sh` (en comentarios de ejemplo)

### Scripts de Ejemplo
- Cualquier script en `/scripts/` destinado a ser copiado
- Templates de configuración
- Archivos de inicialización

## ARCHIVOS QUE NUNCA DEBEN SUBIRSE

### Archivo .gitignore Obligatorio
```gitignore
# Environment files with real credentials
.env
.env.local
.env.production

# Tailscale configuration
.env.tailscale

# InfluxDB data and tokens
docker/services/influxdb/data/
*.token

# SSL certificates
*.pem
*.key
*.crt

# Backup files
*.backup
*.dump
```

## VERIFICACIÓN ANTES DE COMMIT

### Checklist Obligatorio
- [ ] ¿Hay algún valor que parezca una API key real?
- [ ] ¿Todas las URLs contienen placeholders en lugar de dominios reales?
- [ ] ¿Los tokens usan formato `<your_token_here>`?
- [ ] ¿Los archivos .env están en .gitignore?
- [ ] ¿Los ejemplos usan valores genéricos?

### Comandos de Verificación
```bash
# Buscar posibles tokens reales (longitud sospechosa)
grep -r "token.*[0-9a-f]\{20,\}" . --exclude-dir=.git

# Buscar API keys con formato sospechoso
grep -r "api.*key.*[A-Za-z0-9]\{15,\}" . --exclude-dir=.git

# Verificar que .env no está en git
git ls-files | grep "\.env$"
```

## EJEMPLOS CORRECTOS DE USO

### En README.md
```markdown
# Configurar variables de entorno personales
cp .env.example .env
nano .env

# Ejemplo de configuración
REE_API_TOKEN=<your_ree_token_here>
AEMET_API_KEY=<your_aemet_jwt_token>
```

### En Scripts
```bash
# commands/backup.sh
curl -H "Authorization: Token ${INFLUXDB_TOKEN:-<your_influx_token>}"
```

### En Documentación Técnica
```python
# Configuración de ejemplo
INFLUX_URL = "http://chocolate_factory_storage:8086"
INFLUX_TOKEN = "<your_influxdb_token_here>"  # Obtener con: influx auth list
```

## RECOVERY EN CASO DE EXPOSICIÓN

### Si se expone información sensible:
1. **Regenerar credenciales** inmediatamente
2. **Forzar push** con historia limpia
3. **Actualizar todos los servicios** con nuevas credenciales
4. **Verificar logs** por accesos no autorizados

### Comando de limpieza de git:
```bash
# Remover archivos sensibles del historial
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' HEAD
```

## RESPONSABILIDADES

### Del Desarrollador
- Verificar placeholders antes de cada commit
- Usar variables de entorno en lugar de hardcodear
- Mantener .gitignore actualizado

### Del Sistema
- Archivos .env.example siempre actualizados
- Documentación con ejemplos seguros
- Scripts parametrizados correctamente

---

**REGLA CRÍTICA**: Toda información que permita acceso a servicios externos o internos DEBE usar placeholders en el código público.

**ÚLTIMA ACTUALIZACIÓN**: Septiembre 2025
**APLICACIÓN**: Obligatoria para todos los archivos del proyecto