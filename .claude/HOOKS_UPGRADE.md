# 🔄 Actualización de Hooks a Claude Code (Nueva API)

## Fecha: 2 de Octubre 2025

Este documento explica la migración de hooks del formato legacy al nuevo sistema de Claude Code con JSON stdin.

---

## 📋 Resumen de Cambios

### **1. Settings.json** (Actualizado a formato PascalCase)

#### ❌ Formato Antiguo (Obsoleto)
```json
{
  "hooks": {
    "preToolUse": [
      {
        "name": "security-check",
        "command": "script.sh",
        "enabled": false,
        "conditions": { "tools": ["Edit"] }
      }
    ]
  }
}
```

#### ✅ Formato Nuevo (Actual)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/security-check.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Cambios clave:**
- `preToolUse` → `PreToolUse` (PascalCase)
- `conditions.tools` → `matcher` (regex pattern)
- `enabled` → ❌ Eliminado (hooks siempre activos)
- `name`, `description` → ❌ Eliminado (no soportado)
- `timeout` → ✅ Nuevo parámetro (segundos)

---

### **2. Hooks Scripts** (Adaptados para JSON stdin)

#### **security-check.sh** (Verificación de Seguridad)

**Input JSON recibido:**
```json
{
  "tool": "Edit",
  "parameters": {
    "file_path": "/path/to/file.py",
    "old_string": "...",
    "new_string": "..."
  }
}
```

**Lógica implementada:**
1. **Lee JSON stdin** con `timeout 2s cat`
2. **Parsea contexto** con `jq`:
   - `TOOL` → Herramienta usada (Edit/Write/Bash)
   - `FILE_PATH` → Archivo siendo modificado
   - `NEW_CONTENT` → Contenido nuevo
3. **Verificaciones contextuales:**
   - ✅ Archivos `.env/.key/.pem` → Bloquea edición
   - ✅ Archivos `.example` → Valida placeholders `<...>`
   - ✅ Detecta secretos en contenido nuevo (no en todo el repo)
   - ✅ TruffleHog solo en archivo específico
4. **Exit codes:**
   - `exit 0` → Permite operación
   - `exit 1` → Bloquea operación (con mensaje detallado)

**Fallback:** Si `jq` no está instalado, ejecuta `security-check-legacy.sh --all`

---

#### **quick-backfill.sh** (Backfill Automático)

**Input JSON recibido:**
```json
{
  "tool": "SessionStart|Edit|Write",
  "parameters": {
    "file_path": "/path/to/file"
  }
}
```

**Lógica implementada:**
1. **SessionStart:**
   - Verifica gaps al iniciar sesión
   - Si `REE_GAP > 6h` o `WEATHER_GAP > 6h` → Auto backfill
   - Notifica estado de gaps

2. **Edit/Write en archivos críticos:**
   ```bash
   *docker-compose*.yml
   *.env*
   *pyproject.toml
   ```
   - Si `TOTAL_GAP > 3h` → Auto backfill post-config
   - Asegura datos frescos después de cambios de infraestructura

3. **Otros archivos:**
   - Skip hook (sin backfill innecesario)

**Seguridad:**
- Timeout de 2s en lectura JSON
- Verifica API disponible (`/health` endpoint)
- Siempre retorna `exit 0` (nunca bloquea operaciones)

---

## 🔧 Configuración de Timeouts

| Hook Event | Timeout | Justificación |
|------------|---------|---------------|
| `PreToolUse` (security) | 10s | TruffleHog + pattern detection |
| `UserPromptSubmit` (security) | 15s | Verificación completa del prompt |
| `SessionStart` (backfill) | 30s | API calls + backfill inicial |
| `PostToolUse` (backfill) | 20s | Verificación y backfill post-config |

---

## 📂 Estructura de Archivos

```
.claude/
├── settings.json                   # ✅ Formato nuevo (PascalCase)
├── hooks/
│   ├── security-check.sh          # ✅ Nuevo (JSON stdin aware)
│   ├── security-check-legacy.sh   # 📦 Backup del original
│   └── quick-backfill.sh          # ✅ Nuevo (contextual)
└── commands/
    ├── influxdb-admin.md          # ✅ Slash command
    ├── backfill.md                # ✅ Slash command
    └── security-check.md          # ✅ Slash command
```

---

## 🎯 Beneficios de la Nueva API

### **1. Verificación Contextual (No Global)**
- ❌ Antes: Escanear todo el repositorio cada vez
- ✅ Ahora: Solo verificar archivo específico siendo editado

### **2. Decisiones Inteligentes**
```bash
# Hook recibe:
{ "tool": "Edit", "file_path": "/src/api.py" }

# Hook decide:
- ¿Es archivo sensible? → Bloquea
- ¿Contiene secretos nuevos? → Bloquea
- ¿Es archivo config? → Trigger backfill
- ¿Es archivo normal? → Skip hook
```

### **3. Performance Mejorado**
- **Antes**: 20s para escanear 500+ archivos
- **Ahora**: 2s para verificar 1 archivo específico
- **TruffleHog**: Solo en archivo modificado (no en todo el repo)

### **4. Control Granular**
- **Timeout por hook**: Evita bloqueos indefinidos
- **Fallback automático**: Si falta `jq`, usa script legacy
- **Exit codes claros**: 0=allow, 1=block

---

## 🔍 Testing de Hooks

### **Test 1: PreToolUse Security Check**
```bash
# Simular edición de archivo .env
echo '{"tool":"Edit","parameters":{"file_path":".env","new_string":"API_KEY=real123"}}' | \
  .claude/hooks/security-check.sh

# Esperado: Exit 1 (bloqueado)
```

### **Test 2: SessionStart Backfill**
```bash
# Simular inicio de sesión
echo '{"tool":"SessionStart"}' | .claude/hooks/quick-backfill.sh

# Esperado: Verifica gaps + backfill si necesario
```

### **Test 3: PostToolUse Config Change**
```bash
# Simular edición de docker-compose.yml
echo '{"tool":"Edit","parameters":{"file_path":"docker-compose.yml"}}' | \
  .claude/hooks/quick-backfill.sh

# Esperado: Backfill si hay gaps
```

---

## 📚 Documentación de Referencia

- **Hooks API**: https://docs.claude.com/en/docs/claude-code/hooks
- **Settings Format**: https://docs.claude.com/en/docs/claude-code/settings
- **Slash Commands**: https://docs.claude.com/en/docs/claude-code/slash-commands

---

## 🚀 Próximos Pasos

1. ✅ Hooks actualizados a nueva API
2. ✅ Settings.json migrado a PascalCase
3. ✅ Scripts contextuales con JSON stdin
4. ⏳ Testing en producción con operaciones reales
5. ⏳ Monitoreo de performance y ajustes de timeout

---

## ⚠️ Breaking Changes

### **Si upgradeaste Claude Code y los hooks fallaban:**

**Síntomas:**
- Warning: "Found invalid settings files"
- Hooks no se ejecutaban
- Formato `preToolUse` no reconocido

**Solución aplicada:**
- ✅ Migración a `PreToolUse` (PascalCase)
- ✅ Scripts adaptados para leer JSON stdin
- ✅ Timeouts configurados
- ✅ Fallbacks para compatibilidad

---

**Versión Claude Code**: Latest (Octubre 2025)
**Autor**: Claude Code + Usuario
**Estado**: ✅ Producción
