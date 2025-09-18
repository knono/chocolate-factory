#!/bin/bash

# =============================================================================
# Chocolate Factory - Backfill Data Script
# =============================================================================
# Script para ejecutar backfill automático de datos faltantes
# Uso: ./backfill.sh [mode] [options]
#
# Modos disponibles:
#   auto      - Backfill automático inteligente (recomendado)
#   full      - Backfill completo de todos los gaps
#   ree       - Solo backfill de datos REE
#   weather   - Solo backfill de datos meteorológicos
#   check     - Solo verificar gaps sin ejecutar backfill
#
# Ejemplos:
#   ./backfill.sh auto                    # Backfill automático
#   ./backfill.sh full                    # Backfill completo
#   ./backfill.sh check                   # Solo revisar gaps
#   ./backfill.sh ree                     # Solo REE data
#   ./backfill.sh weather 7               # Weather de últimos 7 días
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000"
MODE=${1:-auto}
DAYS_BACK=${2:-7}

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "🍫 ============================================="
    echo "   Chocolate Factory - Data Backfill Tool"
    echo "=============================================${NC}"
    echo
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_system() {
    echo "🔍 Verificando estado del sistema..."

    # Check if containers are running
    if ! docker ps | grep -q "chocolate_factory_brain"; then
        print_error "El contenedor chocolate_factory_brain no está ejecutándose"
        echo "Ejecuta: docker compose up -d"
        exit 1
    fi

    # Check API health
    if ! curl -s "$API_BASE/health" > /dev/null; then
        print_error "La API no está disponible en $API_BASE"
        exit 1
    fi

    print_status "Sistema operativo"
}

show_gaps() {
    echo "📊 Análisis de gaps en datos..."
    echo

    # Get gap summary
    SUMMARY=$(curl -s "$API_BASE/gaps/summary")
    echo "$SUMMARY" | jq -r '
        "🏭 " + .["🏭"] + "\n" +
        "📊 " + .["📊"] + "\n" +
        "⏰ Timestamp: " + .timestamp + "\n" +
        "\n📋 Estado por tipo de datos:" +
        "\n• REE Prices: " + .ree_prices.status +
        "\n  └─ Último dato: " + .ree_prices.latest_data +
        "\n  └─ Gap: " + (.ree_prices.gap_hours | tostring) + " horas" +
        "\n• Weather Data: " + .weather_data.status +
        "\n  └─ Último dato: " + .weather_data.latest_data +
        "\n  └─ Gap: " + (.weather_data.gap_hours | tostring) + " horas"
    '

    echo

    # Get detailed gap analysis
    echo "🔍 Análisis detallado de gaps..."
    GAPS=$(curl -s "$API_BASE/gaps/detect")
    echo "$GAPS" | jq -r '
        "🏭 " + .["🏭"] + "\n" +
        "🔍 " + .["🔍"] + "\n" +
        "📊 Resumen: " + (.summary.total_gaps | tostring) + " gaps total" +
        "\n  └─ REE gaps: " + (.summary.ree_gaps | tostring) +
        "\n  └─ Weather gaps: " + (.summary.weather_gaps | tostring) +
        "\n  └─ Tiempo estimado: " + .summary.estimated_backfill_time
    '

    echo
}

execute_backfill() {
    local mode=$1
    local endpoint=""
    local description=""

    case $mode in
        "auto")
            endpoint="/gaps/backfill/auto"
            description="Backfill automático inteligente"
            ;;
        "full")
            endpoint="/gaps/backfill"
            description="Backfill completo"
            ;;
        "ree")
            endpoint="/gaps/backfill/ree"
            description="Backfill solo REE"
            ;;
        "weather")
            endpoint="/gaps/backfill/weather"
            description="Backfill solo meteorológicos"
            ;;
        *)
            print_error "Modo desconocido: $mode"
            show_usage
            exit 1
            ;;
    esac

    echo "🚀 Ejecutando: $description"
    echo "📡 Endpoint: POST $API_BASE$endpoint"

    if [ "$mode" = "weather" ] && [ "$DAYS_BACK" != "7" ]; then
        echo "📅 Días hacia atrás: $DAYS_BACK"
        endpoint="$endpoint?days_back=$DAYS_BACK"
    fi

    echo
    echo "⏳ Iniciando backfill..."

    # Execute backfill
    RESULT=$(curl -s -X POST "$API_BASE$endpoint")

    # Check if result contains error
    if echo "$RESULT" | grep -q "error\|Error\|ERROR"; then
        print_error "Error en backfill:"
        echo "$RESULT" | jq -r '.' 2>/dev/null || echo "$RESULT"
        exit 1
    fi

    # Parse successful result
    echo "$RESULT" | jq -r '
        if .status then
            "✅ Estado: " + .status
        else
            .
        end
    ' 2>/dev/null || {
        print_status "Backfill completado"
        echo "$RESULT"
    }
}

show_usage() {
    echo "Uso: $0 [mode] [days_back]"
    echo
    echo "Modos disponibles:"
    echo "  auto     - Backfill automático inteligente (recomendado)"
    echo "  full     - Backfill completo de todos los gaps"
    echo "  ree      - Solo backfill de datos REE"
    echo "  weather  - Solo backfill de datos meteorológicos"
    echo "  check    - Solo verificar gaps sin ejecutar backfill"
    echo
    echo "Parámetros opcionales:"
    echo "  days_back - Días hacia atrás para weather backfill (default: 7)"
    echo
    echo "Ejemplos:"
    echo "  $0 auto                # Backfill automático"
    echo "  $0 full                # Backfill completo"
    echo "  $0 check               # Solo revisar gaps"
    echo "  $0 weather 14          # Weather de últimos 14 días"
}

# Main execution
main() {
    print_header

    case $MODE in
        "help"|"-h"|"--help")
            show_usage
            exit 0
            ;;
        "check")
            check_system
            show_gaps
            exit 0
            ;;
        "auto"|"full"|"ree"|"weather")
            check_system
            show_gaps
            echo
            read -p "¿Continuar con $MODE backfill? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                execute_backfill "$MODE"
                echo
                print_status "Backfill completado. Ejecuta './backfill.sh check' para verificar"
            else
                print_warning "Backfill cancelado"
            fi
            ;;
        *)
            print_error "Modo inválido: $MODE"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"