# 🍫 Chocolate Factory - Commands

Comandos de Claude Code para gestión del sistema Chocolate Factory.

## 📂 Comandos Disponibles

Los siguientes comandos están disponibles directamente desde Claude Code usando la sintaxis `/comando`:

### 🔄 `/backfill` - Recuperación Principal de Datos
Análisis detallado y recuperación de gaps con confirmaciones interactivas.

```bash
/backfill [auto|full|ree|weather|check] [days]
```

**[Ver documentación completa →](./backfill.md)**

### ⚡ `/quick-backfill` - Recuperación Rápida
Ejecución inmediata sin confirmaciones para automatización.

```bash
/quick-backfill [auto|ree|weather|check]
```

**[Ver documentación completa →](./quick-backfill.md)**

### 🔒 `/security-check` - Verificación de Seguridad
Detecta información comprometida antes de commits.

```bash
/security-check [--trufflehog|--patterns|--staged|--fix]
```

**[Ver documentación completa →](./security-check.md)**

## 🔧 Configuración de Hooks

Los scripts también pueden ejecutarse automáticamente mediante hooks configurados en `../settings.json`:

### Hooks Disponibles (Deshabilitados por defecto)

- **PreToolUse**: Verificación de seguridad antes de editar archivos
- **UserPromptSubmit**: Security check antes de commits
- **SessionStart**: Verificación de datos al iniciar
- **PostToolUse**: Backfill automático después de cambios de config

### Habilitar Hooks

Editar `.claude/settings.json` y cambiar `"enabled": true` para los hooks deseados.

## 🚀 Uso Rápido

```bash
# Verificar estado de datos
/quick-backfill check

# Backfill automático
/backfill auto

# Verificación de seguridad pre-commit
/security-check --staged --fix
```

## 📁 Estructura

```
.claude/
├── commands/           # Documentación de comandos (este directorio)
│   ├── backfill.md
│   ├── quick-backfill.md
│   ├── security-check.md
│   └── README.md
├── hooks/              # Scripts ejecutables
│   ├── backfill.sh
│   ├── quick-backfill.sh
│   └── security-check.sh
└── settings.json       # Configuración de hooks y comandos
```

## 🛠️ Prerrequisitos

- Docker containers ejecutándose (`chocolate_factory_brain`)
- API disponible en `http://localhost:8000`
- Herramientas: `curl`, `jq`, `docker`
- Para TruffleHog: instalación opcional externa

## 📊 Endpoints API

| Endpoint | Uso | Comandos |
|----------|-----|----------|
| `GET /health` | Estado API | backfill |
| `GET /gaps/summary` | Resumen gaps | todos |
| `POST /gaps/backfill/auto` | Backfill automático | todos |
| `POST /gaps/backfill/ree` | Solo REE | backfill, quick-backfill |
| `POST /gaps/backfill/weather` | Solo weather | backfill, quick-backfill |

---

💡 **Tip**: Los comandos markdown proporcionan documentación y ejemplos, mientras que los hooks en `../hooks/` contienen la lógica ejecutable.