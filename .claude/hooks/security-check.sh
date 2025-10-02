#!/bin/bash

# =============================================================================
# Chocolate Factory - Security Check Hook (Claude Code Integration)
# =============================================================================
# Hook inteligente para Claude Code que recibe contexto JSON por stdin
#
# Input JSON esperado:
# {
#   "tool": "Edit|Write|Bash",
#   "parameters": {
#     "file_path": "/path/to/file",
#     "old_string": "...",
#     "new_string": "...",
#     "content": "..."
#   }
# }
#
# Output:
#   - Exit 0: Permitir operación
#   - Exit 1: Bloquear operación (con mensaje explicativo)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}" >&2; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}" >&2; }
print_error() { echo -e "${RED}❌ $1${NC}" >&2; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}" >&2; }

# Check if jq is available
if ! command -v jq >/dev/null 2>&1; then
    print_warning "jq no está instalado - ejecutando verificación completa del repo"
    exec "$(dirname "$0")/security-check-legacy.sh" --all
fi

# Read JSON input from stdin (with timeout for safety)
INPUT=$(timeout 2s cat || echo "{}")

# Parse JSON input
TOOL=$(echo "$INPUT" | jq -r '.tool // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.parameters.file_path // empty')
NEW_CONTENT=$(echo "$INPUT" | jq -r '.parameters.new_string // .parameters.content // empty')

# Determine verification strategy
if [ "$TOOL" == "unknown" ] || [ -z "$FILE_PATH" ]; then
    # No context available - skip hook (allow operation)
    print_info "Sin contexto JSON - hook pasivo"
    exit 0
fi

print_info "Hook activado - Tool: $TOOL | File: $FILE_PATH"

# =============================================================================
# SECURITY CHECKS
# =============================================================================

check_file_extension() {
    local file="$1"
    case "$file" in
        *.env|*.key|*.pem|*.token)
            print_error "Intentando editar archivo sensible: $file"
            print_error "Estos archivos deben estar en .gitignore y no ser editados directamente"
            return 1
            ;;
        *.example)
            # Verificar placeholders en archivos de ejemplo
            if [ -n "$NEW_CONTENT" ]; then
                if ! echo "$NEW_CONTENT" | grep -q "<.*>"; then
                    print_warning "Archivo .example sin placeholders detectado"
                    print_error "Los archivos .example deben usar formato: <your_value_here>"
                    return 1
                fi
            fi
            ;;
    esac
    return 0
}

check_secrets_in_content() {
    local content="$1"

    # Skip if content is empty
    [ -z "$content" ] && return 0

    # Pattern-based detection (respecting placeholders)
    local secret_patterns=(
        "password.*=.*['\"][^<][^>]{3,}['\"]"
        "secret.*=.*['\"][^<][^>]{3,}['\"]"
        "token.*=.*['\"][A-Za-z0-9]{20,}['\"]"
        "api[_-]?key.*=.*['\"][A-Za-z0-9]{15,}['\"]"
    )

    for pattern in "${secret_patterns[@]}"; do
        if echo "$content" | grep -qE "$pattern" && ! echo "$content" | grep -q "placeholder"; then
            print_error "Patrón sospechoso de secreto detectado: $pattern"
            print_error "Contenido sospechoso encontrado (usa placeholders con <...>)"
            return 1
        fi
    done

    # Check for Tailscale URLs (excluding placeholders)
    if echo "$content" | grep -qE "https://[a-zA-Z0-9.-]+\.ts\.net" && \
       ! echo "$content" | grep -q "<.*>" && \
       ! echo "$content" | grep -q "your-domain"; then
        print_error "URL real de Tailscale detectada"
        print_error "Usar: https://<your-domain>.ts.net"
        return 1
    fi

    # Check for IP addresses (excluding common safe ones)
    if echo "$content" | grep -qE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" && \
       ! echo "$content" | grep -qE "127\.0\.0\.1|localhost|0\.0\.0\.0|<.*>"; then
        print_warning "Dirección IP detectada - verificar si es privada"
        # Warning only, not blocking
    fi

    return 0
}

check_gitignore_coverage() {
    local file="$1"

    # Check if file should be in .gitignore
    case "$file" in
        */.env|*/.env.local|*/.env.production)
            if git check-ignore -q "$file" 2>/dev/null; then
                print_success "Archivo protegido por .gitignore"
                return 0
            else
                print_error "Archivo sensible NO está en .gitignore: $file"
                print_error "Añadir patrón a .gitignore antes de continuar"
                return 1
            fi
            ;;
    esac
    return 0
}

# =============================================================================
# MAIN VERIFICATION LOGIC
# =============================================================================

main() {
    local issues_found=false

    # 1. Check file extension and type
    if ! check_file_extension "$FILE_PATH"; then
        issues_found=true
    fi

    # 2. Check content for secrets (if available)
    if [ -n "$NEW_CONTENT" ]; then
        if ! check_secrets_in_content "$NEW_CONTENT"; then
            issues_found=true
        fi
    fi

    # 3. Verify gitignore coverage
    if ! check_gitignore_coverage "$FILE_PATH"; then
        issues_found=true
    fi

    # 4. TruffleHog check on specific file (if available and file exists)
    if command -v trufflehog >/dev/null 2>&1 && [ -f "$FILE_PATH" ]; then
        print_info "Ejecutando TruffleHog en: $FILE_PATH"
        if ! trufflehog filesystem "$FILE_PATH" --no-update 2>/dev/null; then
            print_error "TruffleHog detectó posibles secretos en: $FILE_PATH"
            issues_found=true
        else
            print_success "TruffleHog: sin secretos detectados"
        fi
    fi

    # Decision
    if [ "$issues_found" = true ]; then
        echo  # Blank line for readability
        print_error "🔒 OPERACIÓN BLOQUEADA - Problemas de seguridad detectados"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
        echo -e "${YELLOW}Correcciones necesarias:${NC}" >&2
        echo "  1. Reemplazar valores reales con placeholders: <your_value_here>" >&2
        echo "  2. Verificar que archivos sensibles estén en .gitignore" >&2
        echo "  3. Ejecutar manualmente: .claude/hooks/security-check-legacy.sh --fix" >&2
        exit 1
    else
        print_success "Verificación de seguridad OK - operación permitida"
        exit 0
    fi
}

# Execute main verification
main
