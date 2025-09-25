#!/bin/bash

# =============================================================================
# Quick Backfill - Chocolate Factory
# =============================================================================
# Script rápido para backfill automático sin confirmaciones
# Uso: ./quick-backfill.sh [auto|ree|weather|check]
# =============================================================================

API_BASE="http://localhost:8000"
MODE=${1:-auto}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🍫 Chocolate Factory - Quick Backfill${NC}"

case $MODE in
    "check")
        echo "📊 Checking data gaps..."
        curl -s "$API_BASE/gaps/summary" | jq -r '
            "🏭 " + .["🏭"] + "\n" +
            "• REE: " + .ree_prices.status + " (gap: " + (.ree_prices.gap_hours | tostring) + "h)" +
            "\n• Weather: " + .weather_data.status + " (gap: " + (.weather_data.gap_hours | tostring) + "h)"
        '
        ;;
    "auto")
        echo "🚀 Executing auto backfill..."
        curl -s -X POST "$API_BASE/gaps/backfill/auto" \
            -H "Content-Type: application/json" \
            -d '{"max_gap_hours": 6.0}' | jq -r '.status // .'
        echo -e "${GREEN}✅ Auto backfill completed${NC}"
        ;;
    "ree")
        echo "⚡ Executing REE backfill..."
        curl -s -X POST "$API_BASE/gaps/backfill" \
            -H "Content-Type: application/json" \
            -d '{"days_back": 7, "data_types": ["ree"]}' | jq -r '.status // .'
        echo -e "${GREEN}✅ REE backfill completed${NC}"
        ;;
    "weather")
        echo "🌤️ Executing weather backfill..."
        curl -s -X POST "$API_BASE/gaps/backfill" \
            -H "Content-Type: application/json" \
            -d '{"days_back": 7, "data_types": ["weather"]}' | jq -r '.status // .'
        echo -e "${GREEN}✅ Weather backfill completed${NC}"
        ;;
    *)
        echo "Usage: $0 [auto|ree|weather|check]"
        echo "  auto    - Automatic intelligent backfill"
        echo "  ree     - REE data only"
        echo "  weather - Weather data only"
        echo "  check   - Check gaps only"
        ;;
esac