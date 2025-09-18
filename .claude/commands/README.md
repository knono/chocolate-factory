# 🍫 Chocolate Factory - Command Scripts

Scripts de utilidad para gestión del sistema Chocolate Factory.

## 📂 Scripts Disponibles

### 🔄 `backfill.sh` - Script Principal de Backfill
Script completo con análisis detallado y confirmaciones interactivas.

```bash
# Uso básico
./backfill.sh [mode] [options]

# Modos disponibles
./backfill.sh auto        # Backfill automático inteligente (recomendado)
./backfill.sh full        # Backfill completo de todos los gaps
./backfill.sh ree         # Solo backfill de datos REE
./backfill.sh weather     # Solo backfill de datos meteorológicos
./backfill.sh check       # Solo verificar gaps sin ejecutar backfill

# Ejemplos con parámetros
./backfill.sh weather 14  # Weather de últimos 14 días
./backfill.sh auto        # Backfill automático con confirmación
```

**Características:**
- ✅ Verificación del estado del sistema
- 📊 Análisis detallado de gaps
- 🛡️ Confirmación interactiva antes de ejecutar
- 🎨 Output colorizado y estructurado
- ⚠️ Manejo robusto de errores

### 🔒 `security-check.sh` - Verificación de Seguridad
Script para detectar información comprometida antes de commits.

```bash
# Uso básico
./security-check.sh [options]

# Opciones disponibles
./security-check.sh               # Verificación completa
./security-check.sh --trufflehog  # Solo TruffleHog
./security-check.sh --patterns    # Solo búsqueda por patrones
./security-check.sh --staged      # Solo archivos en staging
./security-check.sh --fix         # Con sugerencias de corrección

# Ejemplos de uso
./security-check.sh --staged --fix    # Pre-commit check con fixes
./security-check.sh --trufflehog      # Detector avanzado de secretos
```

**Características:**
- 🔍 **TruffleHog integration**: Detector avanzado de secretos
- 📝 **Pattern detection**: Búsqueda por patrones personalizados
- 🛡️ **Pre-commit checks**: Verificación antes de commits
- 📋 **Staged files**: Verificar solo archivos en staging
- 💡 **Fix suggestions**: Sugerencias automáticas de corrección

### ⚡ `quick-backfill.sh` - Script Rápido
Script simplificado para ejecución rápida sin confirmaciones.

```bash
# Uso rápido
./quick-backfill.sh [auto|ree|weather|check]

# Ejemplos
./quick-backfill.sh auto     # Backfill automático inmediato
./quick-backfill.sh check    # Check rápido de gaps
./quick-backfill.sh ree      # Solo REE
./quick-backfill.sh weather  # Solo weather
```

**Características:**
- 🚀 Ejecución inmediata sin confirmaciones
- 📊 Output compacto
- ⚡ Ideal para scripts automatizados

## 🎯 Casos de Uso Recomendados

### 🔍 **Verificar Estado de Datos**
```bash
# Análisis completo
./backfill.sh check

# Check rápido
./quick-backfill.sh check
```

### 🔄 **Backfill Automático** (Recomendado)
```bash
# Con confirmación (seguro)
./backfill.sh auto

# Inmediato (para automatización)
./quick-backfill.sh auto
```

### ⚡ **Backfill Específico**
```bash
# Solo datos REE
./backfill.sh ree
./quick-backfill.sh ree

# Solo datos meteorológicos
./backfill.sh weather
./quick-backfill.sh weather
```

### 📅 **Backfill de Períodos Específicos**
```bash
# Weather de últimos 30 días
./backfill.sh weather 30

# Backfill completo sin límites
./backfill.sh full
```

## 🛠️ Configuración

### Prerrequisitos
- Docker containers ejecutándose (`chocolate_factory_brain`)
- API disponible en `http://localhost:8000`
- Herramientas: `curl`, `jq`, `docker`

### Variables de Configuración
Edita los scripts para personalizar:

```bash
# En backfill.sh o quick-backfill.sh
API_BASE="http://localhost:8000"  # URL base de la API
DAYS_BACK=7                       # Días por defecto para weather backfill
```

## 📊 Endpoints API Utilizados

| Endpoint | Propósito | Script |
|----------|-----------|---------|
| `GET /health` | Verificar API | backfill.sh |
| `GET /gaps/summary` | Resumen de gaps | Ambos |
| `GET /gaps/detect` | Análisis detallado | backfill.sh |
| `POST /gaps/backfill/auto` | Backfill automático | Ambos |
| `POST /gaps/backfill` | Backfill completo | backfill.sh |
| `POST /gaps/backfill/ree` | Solo REE | Ambos |
| `POST /gaps/backfill/weather` | Solo weather | Ambos |

## 🚨 Troubleshooting

### Error: "API no disponible"
```bash
# Verificar containers
docker ps | grep chocolate_factory

# Reiniciar si es necesario
docker compose up -d
```

### Error: "Comando no encontrado"
```bash
# Dar permisos de ejecución
chmod +x .claude/commands/*.sh

# Ejecutar desde directorio del proyecto
cd /ruta/al/chocolate-factory
./.claude/commands/backfill.sh check
```

### Gaps no se resuelven
```bash
# Verificar logs del container
docker logs chocolate_factory_brain --tail=50

# Ejecutar backfill manual con más días
./backfill.sh weather 30
```

## 📈 Monitoreo

### Verificar Éxito del Backfill
```bash
# Antes del backfill
./quick-backfill.sh check

# Ejecutar backfill
./quick-backfill.sh auto

# Verificar después
./quick-backfill.sh check
```

### Logs del Sistema
```bash
# Ver logs en tiempo real
docker logs chocolate_factory_brain -f

# Ver logs de scheduler
curl -s http://localhost:8000/scheduler/status | jq '.jobs[].stats'
```

---

**💡 Tip**: Para uso diario, recomendamos `./quick-backfill.sh auto` como comando rápido para mantener los datos actualizados.