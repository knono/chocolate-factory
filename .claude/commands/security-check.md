# 🔒 Security Check - Verificación de Seguridad

Script defensivo para detectar información comprometida antes de commits y operaciones sensibles.

## Descripción

El comando `security-check` analiza el repositorio en busca de credenciales, tokens, URLs reales y otra información sensible que no debería ser commitada.

## Uso

```bash
# Desde Claude Code
/security-check [options]

# Opciones disponibles
/security-check               # Verificación completa
/security-check --trufflehog  # Solo TruffleHog
/security-check --patterns    # Solo búsqueda por patrones
/security-check --staged      # Solo archivos en staging
/security-check --fix         # Con sugerencias de corrección

# Ejemplos de uso
/security-check --staged --fix    # Pre-commit check con fixes
/security-check --trufflehog      # Detector avanzado de secretos
/security-check --patterns --fix  # Solo patrones con sugerencias
```

## Características Principales

- 🔍 **TruffleHog integration**: Detector avanzado de secretos
- 📝 **Pattern detection**: Búsqueda por patrones personalizados
- 🛡️ **Pre-commit checks**: Verificación antes de commits
- 📋 **Staged files**: Verificar solo archivos en staging
- 💡 **Fix suggestions**: Sugerencias automáticas de corrección
- 🚫 **Gitignore respect**: Respeta archivos excluidos en .gitignore
- 🏷️ **Placeholder aware**: Detecta y respeta placeholders (formato `<valor>`)
- 📊 **Smart filtering**: Evita falsos positivos en archivos .example

## Verificaciones de Seguridad

### ✅ **API Keys/Tokens**
- Detecta credenciales reales vs placeholders
- Filtra tokens con formato `<your_token_here>`
- Ignora archivos `.example`

### ✅ **URLs Tailscale**
- Identifica dominios `.ts.net` reales
- Excluye placeholders como `<your-domain>.ts.net`
- Verifica configuraciones de red

### ✅ **Direcciones IP**
- Filtra IPs localhost vs reales
- Excluye 127.0.0.1, 0.0.0.0, 255.255.255.*
- Detecta configuraciones de red privadas

### ✅ **Archivos .env**
- Verifica que no estén trackeados por git
- Sugiere correcciones automáticas
- Valida patrones en .gitignore

### ✅ **Secretos Hardcodeados**
- Passwords, keys, tokens en código
- Configuraciones de base de datos
- Credenciales de servicios

### ✅ **Archivos de Ejemplo**
- Verifica uso correcto de placeholders
- Valida archivos `.env.example`
- Asegura que no contengan valores reales

## Modos de Ejecución

### Verificación Completa
```bash
/security-check --all --fix
```
- Ejecuta todas las verificaciones
- Incluye sugerencias de corrección
- Recomendado para auditorías completas

### Pre-commit Check
```bash
/security-check --staged --fix
```
- Solo archivos en staging
- Con sugerencias de fix
- Ideal para hooks de pre-commit

### Solo TruffleHog
```bash
/security-check --trufflehog
```
- Requiere TruffleHog instalado
- Detector avanzado de secretos
- Para análisis profundo

### Solo Patrones
```bash
/security-check --patterns
```
- Búsqueda por patrones personalizados
- Sin dependencias externas
- Rápido y eficiente

## Instalación de TruffleHog (Opcional)

```bash
# Con Go
go install github.com/trufflesecurity/trufflehog/v3@latest

# Con Homebrew
brew install trufflehog

# Con Docker
docker pull trufflesecurity/trufflehog:latest
```

## Configuración de Pre-commit Hook

Para uso automático en commits:

```bash
# En .git/hooks/pre-commit
#!/bin/bash
./.claude/hooks/security-check.sh --staged
if [ $? -ne 0 ]; then
    echo "❌ Security check failed. Commit aborted."
    exit 1
fi
```

## Ejemplo de Salida

```bash
🔒 =============================================
   Chocolate Factory - Security Check Tool
=============================================

🔍 Modo: all
📋 Alcance: Todo el repositorio

🔍 TruffleHog - Detector de Secretos
----------------------------------------
✅ TruffleHog scan completado - No se encontraron secretos

📝 Búsqueda por Patrones - Información Sensible
----------------------------------------
🔑 Buscando posibles API keys...
🔐 Buscando secretos hardcodeados...
🌐 Verificando URLs reales...
🖥️ Buscando direcciones IP...
📄 Verificando archivos .env...
✅ Búsqueda por patrones completada - No se encontraron problemas

📋 Verificación de .gitignore
----------------------------------------
✅ Archivo .gitignore contiene los patrones de seguridad necesarios

📄 Verificación de Archivos de Ejemplo
----------------------------------------
✅ .env.example usa placeholders correctos
✅ .env.tailscale.example usa placeholders correctos

✅ Verificación de seguridad completada - No se encontraron problemas

🚀 El proyecto está listo para commit/push
```

## Troubleshooting

**TruffleHog no instalado:**
- El script continúa sin TruffleHog
- Solo usa verificación por patrones
- Instalar TruffleHog para análisis completo

**Falsos positivos:**
- Verificar que se usen placeholders: `<valor>`
- Añadir archivos a .gitignore si es necesario
- El script respeta automáticamente .gitignore

**Archivos .env trackeados:**
```bash
git rm --cached .env
echo ".env" >> .gitignore
```