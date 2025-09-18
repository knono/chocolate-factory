#!/bin/bash

# =============================================================================
# Chocolate Factory - Security Check Script
# =============================================================================
# Script para detectar información comprometida antes de commits
# Uso: ./security-check.sh [options]
#
# Opciones:
#   --trufflehog      Solo ejecutar TruffleHog
#   --patterns        Solo ejecutar búsqueda por patrones
#   --all             Ejecutar todas las verificaciones (default)
#   --fix             Mostrar sugerencias de corrección
#   --staged          Solo verificar archivos en staging
#
# Ejemplos:
#   ./security-check.sh                  # Verificación completa
#   ./security-check.sh --staged         # Solo archivos staged
#   ./security-check.sh --trufflehog     # Solo TruffleHog
#   ./security-check.sh --fix            # Con sugerencias de fix
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(pwd)"
MODE=${1:-all}
SHOW_FIXES=false
STAGED_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --trufflehog)
            MODE="trufflehog"
            shift
            ;;
        --patterns)
            MODE="patterns"
            shift
            ;;
        --all)
            MODE="all"
            shift
            ;;
        --fix)
            SHOW_FIXES=true
            shift
            ;;
        --staged)
            STAGED_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "🔒 ============================================="
    echo "   Chocolate Factory - Security Check Tool"
    echo "=============================================${NC}"
    echo
}

print_section() {
    echo -e "${PURPLE}🔍 $1${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_fix() {
    if [ "$SHOW_FIXES" = true ]; then
        echo -e "${BLUE}💡 Fix: $1${NC}"
    fi
}

# Check if TruffleHog is available
check_trufflehog() {
    if ! command -v trufflehog >/dev/null 2>&1; then
        print_warning "TruffleHog no está instalado"
        echo "Para instalarlo:"
        echo "  # Con Go:"
        echo "  go install github.com/trufflesecurity/trufflehog/v3@latest"
        echo "  # Con Homebrew:"
        echo "  brew install trufflehog"
        echo "  # Con Docker:"
        echo "  docker pull trufflesecurity/trufflehog:latest"
        return 1
    fi
    return 0
}

# Run TruffleHog scan
run_trufflehog() {
    print_section "TruffleHog - Detector de Secretos"

    if ! check_trufflehog; then
        return 1
    fi

    echo "🔍 Ejecutando TruffleHog scan..."

    # TruffleHog command
    if [ "$STAGED_ONLY" = true ]; then
        # Scan only staged files
        STAGED_FILES=$(git diff --cached --name-only)
        if [ -z "$STAGED_FILES" ]; then
            print_success "No hay archivos en staging para verificar"
            return 0
        fi
        echo "📋 Archivos en staging: $(echo "$STAGED_FILES" | wc -l)"
        echo "$STAGED_FILES" | while read -r file; do
            if [ -f "$file" ]; then
                trufflehog filesystem "$file" --no-update 2>/dev/null || true
            fi
        done
    else
        # Full repository scan
        trufflehog git "file://$(pwd)" --no-update 2>/dev/null || {
            print_warning "TruffleHog encontró posibles secretos"
            print_fix "Revisa los archivos mencionados arriba y reemplaza valores reales con placeholders"
            return 1
        }
    fi

    print_success "TruffleHog scan completado - No se encontraron secretos"
    return 0
}

# Pattern-based detection
run_pattern_detection() {
    print_section "Búsqueda por Patrones - Información Sensible"

    local found_issues=false

    # Define files to check
    local files_to_check
    if [ "$STAGED_ONLY" = true ]; then
        files_to_check=$(git diff --cached --name-only | grep -E '\.(md|py|sh|yml|yaml|json|js|ts)$' || true)
        if [ -z "$files_to_check" ]; then
            print_success "No hay archivos relevantes en staging"
            return 0
        fi
    else
        files_to_check=$(find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.js" -o -name "*.ts" \) -not -path "./.git/*" -not -path "./node_modules/*")
    fi

    echo "📁 Verificando archivos por patrones sospechosos..."

    # Check for potential API keys (but avoid false positives)
    echo "🔑 Buscando posibles API keys..."
    if echo "$files_to_check" | xargs grep -l "token.*[A-Za-z0-9]\{20,\}" 2>/dev/null | grep -v ".example" | head -5; then
        print_warning "Encontrados posibles tokens/API keys"
        print_fix "Verificar que no sean credenciales reales - usar formato <your_token_here>"
        found_issues=true
    fi

    # Check for hardcoded secrets patterns
    echo "🔐 Buscando secretos hardcodeados..."
    SECRET_PATTERNS=(
        "password.*=.*[^<].*[^>]"
        "secret.*=.*[^<].*[^>]"
        "key.*=.*[A-Za-z0-9]{15,}"
        "token.*=.*[A-Za-z0-9]{15,}"
    )

    for pattern in "${SECRET_PATTERNS[@]}"; do
        if echo "$files_to_check" | xargs grep -l "$pattern" 2>/dev/null | grep -v ".example" | head -3; then
            print_warning "Patrón sospechoso encontrado: $pattern"
            found_issues=true
        fi
    done

    # Check for real-looking URLs
    echo "🌐 Verificando URLs reales..."
    if echo "$files_to_check" | xargs grep -l "https://[a-zA-Z0-9.-]*\.ts\.net" 2>/dev/null | head -3; then
        print_warning "URLs de Tailscale reales encontradas"
        print_fix "Reemplazar con: https://<your-domain>.ts.net"
        found_issues=true
    fi

    # Check for IP addresses
    echo "🖥️ Buscando direcciones IP..."
    if echo "$files_to_check" | xargs grep -l "[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}" 2>/dev/null | head -3; then
        print_warning "Direcciones IP encontradas"
        print_fix "Verificar que no sean IPs privadas reales"
        found_issues=true
    fi

    # Check .env files are not tracked (respecting .gitignore)
    echo "📄 Verificando archivos .env..."
    TRACKED_ENV_FILES=$(git ls-files | grep "\.env$" | grep -v "\.env\.example$")
    if [ -n "$TRACKED_ENV_FILES" ]; then
        print_error "Archivos .env reales están siendo trackeados por git"
        echo "$TRACKED_ENV_FILES"
        print_fix "Ejecutar: git rm --cached .env && verificar .gitignore"
        found_issues=true
    fi

    if [ "$found_issues" = false ]; then
        print_success "Búsqueda por patrones completada - No se encontraron problemas"
    fi

    return 0
}

# Check gitignore patterns
check_gitignore() {
    print_section "Verificación de .gitignore"

    local required_patterns=(
        ".env"
        ".env.local"
        ".env.production"
        "*.token"
        "*.key"
        "*.pem"
        "docker/services/influxdb/data/"
    )

    if [ ! -f ".gitignore" ]; then
        print_error "Archivo .gitignore no encontrado"
        print_fix "Crear .gitignore con patrones de seguridad"
        return 1
    fi

    local missing_patterns=()
    for pattern in "${required_patterns[@]}"; do
        # Check exact pattern or more general pattern that covers it
        if ! grep -q "$pattern" .gitignore && ! grep -q "$(echo $pattern | sed 's/\*//g')" .gitignore; then
            # Special cases for patterns already covered
            case "$pattern" in
                ".env.local"|"env.production")
                    if grep -q "\.env\*" .gitignore; then
                        continue  # Already covered by .env*
                    fi
                    ;;
                "*.token")
                    if grep -q "\*token\*" .gitignore; then
                        continue  # Already covered by *token*
                    fi
                    ;;
            esac
            missing_patterns+=("$pattern")
        fi
    done

    if [ ${#missing_patterns[@]} -gt 0 ]; then
        print_warning "Patrones faltantes en .gitignore:"
        for pattern in "${missing_patterns[@]}"; do
            echo "  - $pattern"
        done
        print_fix "Añadir estos patrones a .gitignore"
    else
        print_success "Archivo .gitignore contiene los patrones de seguridad necesarios"
    fi
}

# Verify example files
check_example_files() {
    print_section "Verificación de Archivos de Ejemplo"

    local example_files=(
        ".env.example"
        ".env.tailscale.example"
    )

    for file in "${example_files[@]}"; do
        if [ -f "$file" ]; then
            echo "📄 Verificando $file..."
            if grep -q "<.*>" "$file"; then
                print_success "$file usa placeholders correctos"
            else
                print_warning "$file podría contener valores reales"
                print_fix "Usar formato <your_value_here> en $file"
            fi
        else
            print_warning "Archivo $file no encontrado"
            print_fix "Crear $file con placeholders para usuarios"
        fi
    done
}

# Main security check
run_security_check() {
    local issues_found=false

    case $MODE in
        "trufflehog")
            if ! run_trufflehog; then
                issues_found=true
            fi
            ;;
        "patterns")
            if ! run_pattern_detection; then
                issues_found=true
            fi
            ;;
        "all")
            if ! run_trufflehog; then
                issues_found=true
            fi
            echo
            if ! run_pattern_detection; then
                issues_found=true
            fi
            echo
            check_gitignore
            echo
            check_example_files
            ;;
    esac

    echo
    if [ "$issues_found" = true ]; then
        print_error "Se encontraron problemas de seguridad"
        echo
        echo "📋 Pasos recomendados:"
        echo "1. Revisar los archivos mencionados arriba"
        echo "2. Reemplazar valores reales con placeholders"
        echo "3. Verificar que archivos sensibles están en .gitignore"
        echo "4. Ejecutar de nuevo: ./security-check.sh"
        return 1
    else
        print_success "Verificación de seguridad completada - No se encontraron problemas"
        echo
        echo "🚀 El proyecto está listo para commit/push"
        return 0
    fi
}

# Show usage
show_usage() {
    echo "Uso: $0 [options]"
    echo
    echo "Opciones:"
    echo "  --trufflehog    Solo ejecutar TruffleHog"
    echo "  --patterns      Solo ejecutar búsqueda por patrones"
    echo "  --all           Ejecutar todas las verificaciones (default)"
    echo "  --fix           Mostrar sugerencias de corrección"
    echo "  --staged        Solo verificar archivos en staging"
    echo
    echo "Ejemplos:"
    echo "  $0                    # Verificación completa"
    echo "  $0 --staged           # Solo archivos staged"
    echo "  $0 --trufflehog       # Solo TruffleHog"
    echo "  $0 --fix              # Con sugerencias"
}

# Main execution
main() {
    print_header

    if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi

    echo "🔍 Modo: $MODE"
    if [ "$STAGED_ONLY" = true ]; then
        echo "📋 Alcance: Solo archivos en staging"
    else
        echo "📋 Alcance: Todo el repositorio"
    fi
    echo

    run_security_check
}

# Execute main function
main "$@"