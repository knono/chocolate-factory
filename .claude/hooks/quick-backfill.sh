#!/bin/bash

# =============================================================================
# Quick Backfill Hook - Chocolate Factory (Claude Code Integration)
# =============================================================================
# Hook inteligente para backfill automático basado en contexto JSON
#
# Input JSON esperado:
# {
#   "tool": "Edit|Write|SessionStart",
#   "parameters": {
#     "file_path": "/path/to/file"
#   }
# }
#
# Estrategia:
# - SessionStart: Verificar gaps al iniciar sesión
# - Edit/Write en archivos de config: Auto backfill si hay gaps
# - Otros casos: Skip hook (sin backfill innecesario)
# =============================================================================

set -e

API_BASE="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}" >&2; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}" >&2; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}" >&2; }

# Check if jq is available
if ! command -v jq >/dev/null 2>&1; then
    print_warning "jq no instalado - hook deshabilitado"
    exit 0
fi

# Read JSON input from stdin (with timeout)
INPUT=$(timeout 2s cat 2>/dev/null || echo "{}")

# Parse JSON context
TOOL=$(echo "$INPUT" | jq -r '.tool // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.parameters.file_path // empty')

# =============================================================================
# DECISION LOGIC
# =============================================================================

# Check if API is reachable
if ! curl -s --max-time 2 "$API_BASE/health" >/dev/null 2>&1; then
    print_warning "API no disponible - skip backfill hook"
    exit 0
fi

case "$TOOL" in
    "SessionStart")
        # Al iniciar sesión, verificar gaps
        print_info "SessionStart detectado - verificando gaps..."

        GAPS=$(curl -s --max-time 5 "$API_BASE/gaps/summary" 2>/dev/null)
        REE_GAP=$(echo "$GAPS" | jq -r '.ree_prices.gap_hours // 0')
        WEATHER_GAP=$(echo "$GAPS" | jq -r '.weather_data.gap_hours // 0')

        if (( $(echo "$REE_GAP > 6" | bc -l 2>/dev/null || echo 0) )) || \
           (( $(echo "$WEATHER_GAP > 6" | bc -l 2>/dev/null || echo 0) )); then
            print_warning "Gaps detectados - REE: ${REE_GAP}h, Weather: ${WEATHER_GAP}h"
            print_info "Ejecutando auto backfill..."

            curl -s -X POST "$API_BASE/gaps/backfill/auto?max_gap_hours=6.0" >/dev/null 2>&1

            print_success "Backfill automático completado"
        else
            print_success "No hay gaps significativos"
        fi
        ;;

    "Edit"|"Write")
        # Si se edita config, verificar si hay gaps
        case "$FILE_PATH" in
            *docker-compose*.yml|*.env*|*pyproject.toml)
                print_info "Archivo de config modificado: $FILE_PATH"

                # Quick gap check
                GAPS=$(curl -s --max-time 3 "$API_BASE/gaps/summary" 2>/dev/null)
                TOTAL_GAP=$(echo "$GAPS" | jq -r '(.ree_prices.gap_hours // 0) + (.weather_data.gap_hours // 0)')

                if (( $(echo "$TOTAL_GAP > 3" | bc -l 2>/dev/null || echo 0) )); then
                    print_info "Gap detectado post-config: ${TOTAL_GAP}h total"
                    curl -s -X POST "$API_BASE/gaps/backfill/auto?max_gap_hours=3.0" >/dev/null 2>&1
                    print_success "Auto backfill post-config ejecutado"
                fi
                ;;
            *)
                # Otros archivos: skip
                print_info "Archivo no crítico - skip backfill"
                ;;
        esac
        ;;

    *)
        # Sin contexto o herramienta no relevante
        print_info "Hook pasivo - sin acción de backfill"
        ;;
esac

# Always allow operation (exit 0)
exit 0
