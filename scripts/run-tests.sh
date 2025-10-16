#!/bin/bash
# =============================================================================
# Run Tests - Chocolate Factory Testing Suite
# =============================================================================
# Usage:
#   ./scripts/run-tests.sh              # Run all tests
#   ./scripts/run-tests.sh --coverage   # Run with coverage report
#   ./scripts/run-tests.sh --integration # Run only integration tests
#   ./scripts/run-tests.sh --fast       # Skip slow tests
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to fastapi-app directory
cd "$(dirname "$0")/../src/fastapi-app"

echo -e "${GREEN}🧪 Chocolate Factory - Test Runner${NC}"
echo "======================================"

# Check if pytest is installed
if ! python -c "import pytest" &> /dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found. Installing dependencies...${NC}"
    pip install -e .
    pip install pytest pytest-cov pytest-asyncio httpx
fi

# Parse arguments
COVERAGE=false
MARKERS=""
VERBOSE="-v"

for arg in "$@"; do
    case $arg in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --integration)
            MARKERS="-m integration"
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --ml)
            MARKERS="-m ml"
            shift
            ;;
        --fast)
            MARKERS="-m 'not slow'"
            shift
            ;;
        --quiet)
            VERBOSE=""
            shift
            ;;
        *)
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest tests/ $VERBOSE $MARKERS"

if [ "$COVERAGE" = true ]; then
    echo -e "${GREEN}📊 Running tests with coverage report...${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing --cov-report=html:coverage_html --cov-fail-under=70"
else
    echo -e "${GREEN}🏃 Running tests...${NC}"
fi

# Run tests
eval $PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"

    if [ "$COVERAGE" = true ]; then
        echo -e "${GREEN}📈 Coverage report generated: coverage_html/index.html${NC}"
    fi
else
    echo -e "\n${RED}❌ Tests failed!${NC}"
    exit 1
fi
