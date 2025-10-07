# 🔄 Backfill - Recuperación de Datos

Script principal para detectar y recuperar gaps de datos en el sistema Chocolate Factory.

## Descripción

El comando `backfill` ejecuta análisis detallado de gaps en datos REE y meteorológicos, con confirmaciones interactivas y múltiples modos de operación.

## Uso

```bash
# Desde Claude Code
/backfill [mode] [options]

# Modos disponibles
/backfill auto        # Backfill automático inteligente (recomendado)
/backfill full        # Backfill completo de todos los gaps
/backfill ree         # Solo backfill de datos REE
/backfill weather     # Solo backfill de datos meteorológicos
/backfill check       # Solo verificar gaps sin ejecutar backfill

# Ejemplos con parámetros
/backfill weather 14  # Weather de últimos 14 días
/backfill auto        # Backfill automático con confirmación
```

## Características

- ✅ **Verificación del estado del sistema** antes de ejecutar
- 📊 **Análisis detallado de gaps** con estadísticas completas
- 🛡️ **Confirmación interactiva** antes de operaciones críticas
- 🎨 **Output colorizado** y estructurado para fácil lectura
- ⚠️ **Manejo robusto de errores** con mensajes descriptivos
- 🔄 **Múltiples estrategias** de backfill según el tipo de datos

## Modos de Operación

### `auto` - Automático Inteligente (Recomendado)
- Detecta automáticamente el tipo de gaps
- Usa estrategia optimizada según el período
- Confirmación antes de ejecutar
- Ideal para uso diario

### `full` - Backfill Completo
- Procesa todos los gaps detectados
- Sin límites de tiempo
- Para recuperación masiva de datos

### `check` - Solo Verificación
- Analiza gaps sin ejecutar backfill
- Genera reporte detallado
- Útil para monitoreo

### `ree` / `weather` - Específicos
- Backfill solo del tipo seleccionado
- Parámetro opcional de días hacia atrás
- Control granular

## Prerrequisitos

- Docker containers ejecutándose (`chocolate_factory_brain`)
- API disponible en `http://localhost:8000`
- Herramientas: `curl`, `jq`, `docker`

## Endpoints API Utilizados

- `GET /health` - Verificar estado de la API
- `GET /gaps/summary` - Resumen rápido de gaps
- `GET /gaps/detect?days_back=N` - Análisis detallado de gaps
- `POST /gaps/backfill/auto?max_gap_hours=6.0` - Backfill automático inteligente
- `POST /gaps/backfill?days_back=10` - Backfill completo (REE + Weather)
- `POST /gaps/backfill/range` - Backfill específico por rango de fechas

**Nota**: Los modos `ree` y `weather` en el script ejecutan `/gaps/backfill` que procesa ambos tipos de datos. Para backfill selectivo usar `/gaps/backfill/range` con `data_source`.

## Ejemplo de Ejecución

```bash
# Verificar estado actual
/backfill check

# Backfill automático (recomendado)
/backfill auto

# Backfill específico de weather (últimos 7 días)
/backfill weather 7
```

## Troubleshooting

**Error: "API no disponible"**
```bash
# Verificar containers
docker ps | grep chocolate_factory

# Reiniciar si es necesario
docker compose up -d
```

**Gaps no se resuelven**
```bash
# Verificar logs del container
docker logs chocolate_factory_brain --tail=50

# Intentar con más días
/backfill weather 30
```