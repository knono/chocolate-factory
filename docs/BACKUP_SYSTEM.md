# Sistema de Backup y Recuperación - Chocolate Factory

**Fecha**: 22 de Octubre, 2025
**Versión**: 1.0
**Estado**: ✅ Operacional

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Datos Respaldados](#datos-respaldados)
4. [Scripts Disponibles](#scripts-disponibles)
5. [Uso Básico](#uso-básico)
6. [Backups Automáticos (Cron)](#backups-automáticos-cron)
7. [Restauración](#restauración)
8. [Verificación de Backups](#verificación-de-backups)
9. [Políticas de Retención](#políticas-de-retención)
10. [Troubleshooting](#troubleshooting)

---

## Resumen Ejecutivo

El sistema de backup de Chocolate Factory proporciona **backup completo y restauración** de todos los componentes críticos del sistema:

- ✅ **InfluxDB** (124M+ datos de series temporales)
- ✅ **Modelos ML** (Prophet + sklearn pickles)
- ✅ **Configuración** (Docker Compose + Nginx)
- ✅ **Secrets encriptados** (SOPS + AGE keys)
- ✅ **Código fuente** (src/, scripts/, .claude/, docs/)
- ✅ **Logs recientes** (últimos 7 días)

**Características principales**:
- Almacenamiento **externo** al proyecto (`../chocolate-factory-backups/`)
- **3 tipos de backup**: daily, weekly, monthly
- **Retención automática**: 7 días / 4 semanas / 3 meses
- **Verificación de integridad** incluida
- **Backups automáticos** vía cron
- **Restauración con un comando**

---

## Arquitectura del Sistema

### Estructura de Directorios

```
/home/user/
├── chocolate-factory/                    # Proyecto
│   ├── backup.sh                         # Script de backup
│   ├── restore.sh                        # Script de restauración
│   ├── backup-verify.sh                  # Verificación de integridad
│   ├── setup-cron-backups.sh             # Configuración cron
│   └── ...
│
└── chocolate-factory-backups/            # Backups (EXTERNO)
    ├── daily/                            # Backups diarios (retención: 7 días)
    │   ├── chocolate-factory_daily_20251022_020000/
    │   ├── chocolate-factory_daily_20251021_020000/
    │   └── ...
    ├── weekly/                           # Backups semanales (retención: 4 semanas)
    │   ├── chocolate-factory_weekly_20251020_030000/
    │   └── ...
    └── monthly/                          # Backups mensuales (retención: 3 meses)
        ├── chocolate-factory_monthly_20251001_040000/
        └── ...
```

### Estructura de un Backup Individual

```
chocolate-factory_daily_20251022_020000/
├── MANIFEST.txt                          # Metadata del backup
├── influxdb/
│   ├── influxdb_data.tar.gz             # Datos completos (124M+)
│   └── influxdb_config.tar.gz           # Configuración InfluxDB
├── models/
│   ├── latest/                          # Modelos activos actuales
│   ├── *.pkl                            # Modelos últimos 7 días
│   └── model_registry.json              # Registry de modelos
├── config/
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   ├── *nginx*.conf
│   └── .env.example
├── secrets/
│   ├── secrets.enc.yaml                 # Secrets encriptados (SOPS)
│   └── age-key.txt                      # AGE key (CRÍTICO)
├── code/
│   ├── src.tar.gz                       # Código fuente completo
│   ├── scripts.tar.gz                   # Scripts de utilidad
│   ├── claude.tar.gz                    # Reglas y sprints
│   └── docs.tar.gz                      # Documentación
└── logs/
    └── *.log                            # Logs últimos 7 días
```

---

## Datos Respaldados

### 1. InfluxDB (Crítico)
- **Qué**: Base de datos completa de series temporales
- **Tamaño**: ~124M comprimido
- **Contenido**:
  - `energy_data` bucket (REE prices, weather)
  - `siar_historical` bucket (25 años datos históricos)
  - `analytics` bucket (métricas Tailscale)
- **Formato**: tar.gz de `docker/services/influxdb/data/`

### 2. Modelos ML (Crítico)
- **Qué**: Modelos entrenados de Prophet y sklearn
- **Contenido**:
  - Directorio `latest/` (symlinks a modelos activos)
  - Modelos `.pkl` últimos 7 días
  - `model_registry.json` con métricas
- **Formato**: Copia directa de archivos `.pkl`

### 3. Configuración (Crítico)
- **Qué**: Archivos de orquestación y configuración
- **Contenido**:
  - `docker-compose.yml` (+ override, dev, prod)
  - Nginx configs (sidecar, git, dev)
  - `.env.example` (NO el .env real)
- **Formato**: Copia directa de archivos

### 4. Secrets Encriptados (Crítico)
- **Qué**: Secrets gestionados con SOPS
- **Contenido**:
  - `secrets.enc.yaml` (secrets encriptados)
  - `age-key.txt` (clave de descifrado AGE)
- **Formato**: Copia directa de archivos
- **⚠️ IMPORTANTE**: El `age-key.txt` es CRÍTICO para descifrar secrets

### 5. Código Fuente (Importante)
- **Qué**: Todo el código del proyecto
- **Contenido**:
  - `src/` completo (excluye __pycache__, .pyc)
  - `scripts/` completo
  - `.claude/` (reglas, sprints, arquitectura)
  - `docs/` (documentación técnica)
- **Formato**: tar.gz por directorio

### 6. Logs (Opcional)
- **Qué**: Logs de aplicación recientes
- **Contenido**: Logs últimos 7 días
- **Formato**: Copia directa de archivos `.log`

---

## Scripts Disponibles

### 1. `backup.sh` - Script de Backup

**Ubicación**: `./backup.sh`

**Uso**:
```bash
./backup.sh [daily|weekly|monthly]
```

**Ejemplos**:
```bash
# Backup diario
./backup.sh daily

# Backup semanal
./backup.sh weekly

# Backup mensual
./backup.sh monthly
```

**Funcionalidades**:
- Crea estructura de directorios automáticamente
- Respalda todos los componentes críticos
- Genera MANIFEST.txt con metadata
- Aplica políticas de retención automáticamente
- Muestra resumen al finalizar

---

### 2. `restore.sh` - Script de Restauración

**Ubicación**: `./restore.sh`

**Uso**:
```bash
./restore.sh <backup_name> [--force]
```

**Ejemplos**:
```bash
# Restaurar con confirmación
./restore.sh chocolate-factory_daily_20251022_020000

# Restaurar sin confirmación (automatizado)
./restore.sh chocolate-factory_daily_20251022_020000 --force
```

**Funcionalidades**:
- Busca backup automáticamente en daily/weekly/monthly
- Muestra información del backup antes de restaurar
- Solicita confirmación (omitible con --force)
- Detiene contenedores antes de restaurar
- Verifica integridad de archivos
- Inicia contenedores después de restaurar
- Ejecuta health checks post-restauración

---

### 3. `backup-verify.sh` - Verificación de Integridad

**Ubicación**: `./backup-verify.sh`

**Uso**:
```bash
# Verificar todos los backups
./backup-verify.sh

# Verificar un backup específico
./backup-verify.sh chocolate-factory_daily_20251022_020000
```

**Verificaciones**:
- ✅ MANIFEST.txt existe
- ✅ Integridad de archivos tar.gz
- ✅ docker-compose.yml presente
- ✅ Modelos ML (.pkl files)
- ✅ model_registry.json
- ✅ Secrets encriptados
- ✅ Código fuente comprimido
- ✅ Tamaño total del backup

---

### 4. `setup-cron-backups.sh` - Automatización con Cron

**Ubicación**: `./setup-cron-backups.sh`

**Uso**:
```bash
# Instalar backups automáticos
./setup-cron-backups.sh install

# Ver estado actual
./setup-cron-backups.sh status

# Desinstalar backups automáticos
./setup-cron-backups.sh uninstall

# Probar script de backup
./setup-cron-backups.sh test
```

**Schedule predeterminado**:
- **Daily**: Todos los días a las 2:00 AM
- **Weekly**: Domingos a las 3:00 AM
- **Monthly**: Día 1 de cada mes a las 4:00 AM

---

## Uso Básico

### Primera Vez: Configuración Inicial

1. **Hacer scripts ejecutables**:
```bash
chmod +x backup.sh restore.sh backup-verify.sh setup-cron-backups.sh
```

2. **Probar backup manual**:
```bash
./backup.sh daily
```

3. **Verificar que funcionó**:
```bash
ls -lh ../chocolate-factory-backups/daily/
./backup-verify.sh
```

---

### Backup Manual

**Paso 1**: Ejecutar backup
```bash
./backup.sh daily
```

**Salida esperada**:
```
[INFO] Starting Chocolate Factory Backup System
[INFO] ===========================================

[INFO] Tipo de backup: daily
[INFO] Creando estructura de directorios...
[SUCCESS] Directorios creados: ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_143022
[INFO] Backing up InfluxDB...
[SUCCESS] InfluxDB data backed up (124M)
[INFO] Backing up ML models...
[SUCCESS] ML models backed up (47 files)
[INFO] Backing up configuration files...
[SUCCESS] Configuration files backed up
[INFO] Backing up encrypted secrets...
[SUCCESS] Encrypted secrets backed up
[INFO] Backing up critical source code...
[SUCCESS] Source code backed up
[INFO] Creating backup manifest...
[SUCCESS] Manifest created
[INFO] Applying retention policy...
[SUCCESS] Retention policy applied (7 days)

=============================================================================
                    BACKUP COMPLETED SUCCESSFULLY
=============================================================================
Backup Name:      chocolate-factory_daily_20251022_143022
Backup Location:  ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_143022
Backup Size:      156M
Backup Type:      daily
Timestamp:        2025-10-22 14:30:22
=============================================================================
```

---

### Restauración Manual

**Paso 1**: Listar backups disponibles
```bash
./restore.sh
```

**Paso 2**: Restaurar backup específico
```bash
./restore.sh chocolate-factory_daily_20251022_020000
```

**Paso 3**: Confirmar restauración
```
⚠️  ATENCIÓN: Esta operación sobreescribirá datos existentes ⚠️

Se restaurarán los siguientes componentes:
  - InfluxDB data (124M+)
  - ML models
  - Configuration files
  - Source code

¿Continuar con la restauración? (yes/no): yes
```

**Paso 4**: Verificar servicios
```bash
docker compose ps
curl http://localhost:8000/health
```

---

## Backups Automáticos (Cron)

### Instalación de Cron Jobs

**Paso 1**: Instalar cron jobs
```bash
./setup-cron-backups.sh install
```

**Salida esperada**:
```
[INFO] Installing automated backup cron jobs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SUCCESS] Backup script: OK
[SUCCESS] Docker: Running

[SUCCESS] Cron jobs installed successfully

Backup Schedule:
  • Daily:   Every day at 2:00 AM
  • Weekly:  Sundays at 3:00 AM
  • Monthly: 1st day of month at 4:00 AM

Logs location: ./logs/
```

**Paso 2**: Verificar instalación
```bash
./setup-cron-backups.sh status
```

**Paso 3**: Ver logs de backups
```bash
tail -f logs/backup-daily.log
tail -f logs/backup-weekly.log
tail -f logs/backup-monthly.log
```

---

### Horario de Backups Automáticos

| Tipo | Frecuencia | Hora | Retención | Log |
|------|------------|------|-----------|-----|
| Daily | Diario | 2:00 AM | 7 días | `logs/backup-daily.log` |
| Weekly | Domingos | 3:00 AM | 4 semanas | `logs/backup-weekly.log` |
| Monthly | Día 1 del mes | 4:00 AM | 3 meses | `logs/backup-monthly.log` |

---

### Modificar Horarios

**Opción 1**: Editar cron manualmente
```bash
crontab -e
```

**Opción 2**: Desinstalar y reinstalar con nuevos horarios
```bash
./setup-cron-backups.sh uninstall
# Editar setup-cron-backups.sh líneas 124-135
./setup-cron-backups.sh install
```

---

### Desinstalar Backups Automáticos

```bash
./setup-cron-backups.sh uninstall
```

---

## Restauración

### Escenario 1: Restauración Completa (Desastre)

**Situación**: Pérdida total del sistema

**Pasos**:
1. Clonar repositorio:
```bash
git clone <repo-url> chocolate-factory
cd chocolate-factory
```

2. Hacer scripts ejecutables:
```bash
chmod +x restore.sh
```

3. Listar backups disponibles:
```bash
./restore.sh
```

4. Restaurar último backup:
```bash
./restore.sh chocolate-factory_daily_20251022_020000
```

5. Descifrar secrets:
```bash
./decrypt-secrets.sh
```

6. Verificar servicios:
```bash
docker compose ps
curl http://localhost:8000/health
```

---

### Escenario 2: Restauración Parcial (Solo InfluxDB)

**Situación**: Corrupción de datos de InfluxDB

**Pasos**:
1. Detener servicios:
```bash
docker compose down
```

2. Extraer backup de InfluxDB:
```bash
cd ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_020000
tar -xzf influxdb/influxdb_data.tar.gz -C ~/chocolate-factory/docker/services/influxdb/
```

3. Iniciar servicios:
```bash
cd ~/chocolate-factory
docker compose up -d
```

---

### Escenario 3: Recuperación de Modelos ML

**Situación**: Modelos ML corrompidos

**Pasos**:
1. Copiar modelos desde backup:
```bash
cp -r ../chocolate-factory-backups/daily/chocolate-factory_daily_20251022_020000/models/* ./models/
```

2. Reiniciar FastAPI:
```bash
docker compose restart fastapi-app
```

---

## Verificación de Backups

### Verificación Completa (Todos los Backups)

```bash
./backup-verify.sh
```

**Salida esperada**:
```
[INFO] Chocolate Factory Backup Verification
[INFO] ======================================

[INFO] Available Backups
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INFO] DAILY Backups (7)
  • chocolate-factory_daily_20251022_020000 (156M, 2025-10-22)
  • chocolate-factory_daily_20251021_020000 (155M, 2025-10-21)
  ...

[INFO] Verifying: chocolate-factory_daily_20251022_020000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[OK] MANIFEST.txt exists
[OK] InfluxDB data (124M)
[OK]   └─ Archive integrity: OK
[OK] ML models (47 files)
[OK]   └─ model_registry.json exists
[OK] Configuration (7 files)
[OK]   └─ docker-compose.yml exists
[OK] Secrets (2 files)
[OK]   └─ secrets.enc.yaml exists
[OK]   └─ age-key.txt exists
[OK] Code archives (4 files)
[OK]   └─ src.tar.gz: OK
[OK]   └─ scripts.tar.gz: OK
[OK]   └─ claude.tar.gz: OK
[OK]   └─ docs.tar.gz: OK
[INFO] Total backup size: 156M

[SUCCESS] ✓ Backup verification: PASSED
```

---

### Verificación Individual

```bash
./backup-verify.sh chocolate-factory_daily_20251022_020000
```

---

### Verificación Periódica (Recomendado)

**Agregar a cron** para verificar backups semanalmente:

```bash
crontab -e
```

Agregar línea:
```cron
# Verificar backups todos los lunes a las 10:00 AM
0 10 * * 1 cd /path/to/chocolate-factory && ./backup-verify.sh >> logs/backup-verify.log 2>&1
```

---

## Políticas de Retención

### Retención Automática

El sistema aplica **retención automática** al ejecutar backups:

| Tipo | Retención | Cleanup |
|------|-----------|---------|
| Daily | 7 días | Elimina backups >7 días automáticamente |
| Weekly | 4 semanas (28 días) | Elimina backups >28 días automáticamente |
| Monthly | 3 meses (90 días) | Elimina backups >90 días automáticamente |

---

### Espacio en Disco Estimado

**Con schedule completo** (daily + weekly + monthly):
- 7 backups diarios × 156M = ~1.1 GB
- 4 backups semanales × 156M = ~624 MB
- 3 backups mensuales × 156M = ~468 MB
- **Total**: ~2.2 GB

**Crecimiento**:
- InfluxDB: +5-10 MB/día (datos nuevos)
- ML models: +500 KB/día (reentrenamientos)
- Logs: +10 MB/día (descartados después de 7 días)

---

### Limpieza Manual

**Eliminar backups antiguos manualmente**:
```bash
# Eliminar backups daily >14 días
find ../chocolate-factory-backups/daily/ -type d -mtime +14 -name "chocolate-factory_*" -exec rm -rf {} \;

# Eliminar backups weekly >60 días
find ../chocolate-factory-backups/weekly/ -type d -mtime +60 -name "chocolate-factory_*" -exec rm -rf {} \;
```

---

## Troubleshooting

### Problema 1: "Permission denied" al crear backup

**Síntomas**:
```
[ERROR] Permission denied: ../chocolate-factory-backups/
```

**Solución**:
```bash
# Crear directorio manualmente con permisos correctos
mkdir -p ../chocolate-factory-backups
chmod 755 ../chocolate-factory-backups
```

---

### Problema 2: Backup de InfluxDB falla

**Síntomas**:
```
[WARNING] InfluxDB data directory not found
```

**Solución**:
```bash
# Verificar que InfluxDB está corriendo y tiene datos
docker compose ps influxdb
ls -lh docker/services/influxdb/data/

# Si no existen datos, inicializar InfluxDB
docker compose up -d influxdb
sleep 30
docker compose logs influxdb
```

---

### Problema 3: "tar: Removing leading `/` from member names"

**Síntomas**:
```
tar: Removing leading `/' from member names
```

**Solución**:
Esto es solo un **warning**, no un error. El backup funciona correctamente.

---

### Problema 4: Restauración falla porque contenedores siguen corriendo

**Síntomas**:
```
[ERROR] Cannot remove directory: Device or resource busy
```

**Solución**:
```bash
# Detener contenedores manualmente
docker compose down

# Verificar que no hay contenedores corriendo
docker ps

# Reintentar restauración
./restore.sh chocolate-factory_daily_20251022_020000 --force
```

---

### Problema 5: Cron no ejecuta backups

**Síntomas**:
Logs vacíos o no se crean backups automáticamente

**Solución 1**: Verificar cron
```bash
# Ver cron jobs instalados
crontab -l | grep CHOCOLATE_FACTORY

# Ver logs de cron del sistema
grep CRON /var/log/syslog | tail -20
```

**Solución 2**: Verificar permisos
```bash
# Scripts deben ser ejecutables
chmod +x backup.sh

# Logs directory debe existir
mkdir -p logs
chmod 755 logs
```

**Solución 3**: Verificar paths absolutos
```bash
# Editar crontab manualmente
crontab -e

# Verificar que paths son ABSOLUTOS, no relativos:
# ✅ CORRECTO: /home/user/chocolate-factory/backup.sh
# ❌ INCORRECTO: ./backup.sh
```

---

### Problema 6: Backup tarda demasiado

**Síntomas**:
Backup tarda >10 minutos

**Causa**: InfluxDB data muy grande (>500 MB)

**Soluciones**:

**Opción 1**: Excluir logs antiguos de InfluxDB
```bash
# Limpiar datos antiguos de InfluxDB (>90 días)
docker exec chocolate_factory_storage influx delete \
  --org chocolate_factory \
  --bucket energy_data \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -d '90 days ago' -Iseconds)
```

**Opción 2**: Usar compresión máxima
Editar `backup.sh` línea ~137:
```bash
tar -czf ... --use-compress-program="gzip -9"
```

---

### Problema 7: "age-key.txt not found" al restaurar

**Síntomas**:
```
[WARNING] AGE key not found, cannot decrypt secrets
```

**Solución**:
```bash
# Si tienes el age-key.txt en otro lugar, copiarlo manualmente:
cp /path/to/age-key.txt .

# Luego descifrar secrets:
./decrypt-secrets.sh

# Si perdiste el age-key.txt, regenerar secrets desde cero:
# 1. Generar nueva AGE key
age-keygen -o age-key.txt

# 2. Reconfigurar todas las API keys manualmente en .env
nano .env
```

---

## Mejores Prácticas

### ✅ Recomendado

1. **Backups automáticos**: Instalar cron jobs con `setup-cron-backups.sh install`
2. **Verificación semanal**: Agregar `backup-verify.sh` a cron
3. **Backup offsite**: Copiar backups mensuales a almacenamiento externo (USB, NAS)
4. **Probar restauración**: Hacer restore test cada 3 meses
5. **Monitorear logs**: Revisar `logs/backup-*.log` periódicamente
6. **Espacio en disco**: Alertar si `../chocolate-factory-backups/` >5 GB

---

### ❌ Evitar

1. **NO** respaldar `.env` sin encriptar (usar `secrets.enc.yaml` en su lugar)
2. **NO** almacenar backups en el mismo servidor (backup offsite)
3. **NO** modificar directamente archivos dentro de backups
4. **NO** ejecutar backups mientras se está ejecutando entrenamiento ML pesado
5. **NO** ignorar warnings de verificación de integridad

---

## Referencias

- **SOPS Secrets Management**: `docs/SOPS_SECRETS_MANAGEMENT.md`
- **Docker Compose**: `docker-compose.yml`
- **InfluxDB Backup**: https://docs.influxdata.com/influxdb/v2.7/backup-restore/
- **Cron syntax**: https://crontab.guru/

---

**Última actualización**: 2025-10-22
**Versión**: 1.0
**Autor**: Backup System Documentation
