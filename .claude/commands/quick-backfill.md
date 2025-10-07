# ⚡ Quick Backfill - Recuperación Rápida

Script simplificado para ejecución inmediata de backfill sin confirmaciones interactivas.

## Descripción

El comando `quick-backfill` ejecuta operaciones de backfill de forma inmediata, ideal para automatización y uso frecuente.

## Uso

```bash
# Desde Claude Code
/quick-backfill [mode]

# Modos disponibles
/quick-backfill auto     # Backfill automático inmediato
/quick-backfill ree      # Solo datos REE
/quick-backfill weather  # Solo datos meteorológicos
/quick-backfill check    # Check rápido de gaps
```

## Características

- 🚀 **Ejecución inmediata** sin confirmaciones
- 📊 **Output compacto** y directo al grano
- ⚡ **Ideal para automatización** y scripts
- 🔄 **Mismos endpoints** que backfill principal
- 📋 **Feedback mínimo** pero informativo

## Casos de Uso

### Automatización
```bash
# En cron jobs o scripts automatizados
/quick-backfill auto
```

### Desarrollo
```bash
# Check rápido durante desarrollo
/quick-backfill check

# Backfill específico inmediato
/quick-backfill ree
```

### Monitoreo
```bash
# Verificación periódica sin ruido
/quick-backfill check
```

## Diferencias con Backfill Principal

| Característica | `backfill` | `quick-backfill` |
|---------------|------------|------------------|
| Confirmaciones | ✅ Interactivo | ❌ Inmediato |
| Output | 🎨 Detallado | 📊 Compacto |
| Análisis | 📈 Completo | ⚡ Básico |
| Uso | 🛡️ Manual seguro | 🚀 Automatización |

## Prerrequisitos

- Docker containers ejecutándose (`chocolate_factory_brain`)
- API disponible en `http://localhost:8000`
- Herramientas: `curl`, `jq`

## Endpoints API Utilizados

- `GET /gaps/summary` - Resumen de gaps
- `POST /gaps/backfill/auto?max_gap_hours=6.0` - Backfill automático inteligente
- `POST /gaps/backfill?days_back=N` - Backfill completo (REE + Weather)

## Ejemplo de Uso Típico

```bash
# Rutina de mantenimiento diario
/quick-backfill check    # Ver estado
/quick-backfill auto     # Aplicar fixes si necesario

# En scripts de CI/CD
/quick-backfill auto     # Mantener datos actualizados
```

## Configuración

El script utiliza las mismas variables que `backfill`:

```bash
API_BASE="http://localhost:8000"
DAYS_BACK=7  # Para weather backfill
```

## Monitoreo del Resultado

```bash
# Verificar éxito
/quick-backfill check

# Ver logs detallados si es necesario
docker logs chocolate_factory_brain --tail=20
```