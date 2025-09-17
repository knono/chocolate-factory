#!/bin/bash
# =============================================================================
# CHOCOLATE FACTORY - DEVELOPMENT HELPER SCRIPT
# =============================================================================
# Script de ayuda para gestionar el entorno de desarrollo
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}🏭 Chocolate Factory - Development Helper${NC}"
    echo ""
    echo "Uso: ./dev.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo -e "  ${GREEN}start${NC}     - Iniciar entorno de desarrollo con hot reload"
    echo -e "  ${GREEN}stop${NC}      - Detener entorno de desarrollo"
    echo -e "  ${GREEN}restart${NC}   - Reiniciar entorno de desarrollo"
    echo -e "  ${GREEN}logs${NC}      - Ver logs del servicio FastAPI"
    echo -e "  ${GREEN}status${NC}    - Ver estado de los contenedores"
    echo -e "  ${GREEN}prod${NC}      - Cambiar a modo producción"
    echo -e "  ${GREEN}build${NC}     - Rebuild imagen para producción"
    echo -e "  ${GREEN}clean${NC}     - Limpiar contenedores e imágenes"
    echo ""
    echo "Ejemplos:"
    echo "  ./dev.sh start    # Iniciar desarrollo"
    echo "  ./dev.sh logs -f  # Ver logs en tiempo real"
    echo "  ./dev.sh prod     # Cambiar a producción"
}

# Función para iniciar desarrollo
dev_start() {
    echo -e "${GREEN}🚀 Iniciando entorno de desarrollo...${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    echo -e "${GREEN}✅ Entorno de desarrollo iniciado${NC}"
    echo -e "${YELLOW}📍 Dashboard: http://localhost:8000/dashboard${NC}"
    echo -e "${YELLOW}📊 API Docs: http://localhost:8000/docs${NC}"
    echo -e "${YELLOW}🔍 Ver logs: scripts/dev.sh logs${NC}"
}

# Función para detener desarrollo
dev_stop() {
    echo -e "${YELLOW}🛑 Deteniendo entorno de desarrollo...${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    echo -e "${GREEN}✅ Entorno de desarrollo detenido${NC}"
}

# Función para reiniciar desarrollo
dev_restart() {
    echo -e "${YELLOW}🔄 Reiniciando entorno de desarrollo...${NC}"
    dev_stop
    dev_start
}

# Función para ver logs
dev_logs() {
    echo -e "${BLUE}📋 Logs del entorno de desarrollo:${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs "${@}" fastapi-app
}

# Función para ver estado
dev_status() {
    echo -e "${BLUE}📊 Estado de contenedores:${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
}

# Función para cambiar a producción
prod_mode() {
    echo -e "${YELLOW}🏭 Cambiando a modo producción...${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml up -d
    echo -e "${GREEN}✅ Modo producción activado${NC}"
    echo -e "${YELLOW}📍 Dashboard: http://localhost:8000/dashboard${NC}"
}

# Función para build de producción
prod_build() {
    echo -e "${YELLOW}🔨 Rebuilding imagen para producción...${NC}"
    cd "$(dirname "$0")/.." && docker-compose build --no-cache fastapi-app
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml up -d
    echo -e "${GREEN}✅ Imagen reconstruida y producción iniciada${NC}"
}

# Función para limpiar
clean_env() {
    echo -e "${RED}🧹 Limpiando entorno...${NC}"
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    cd "$(dirname "$0")/.." && docker-compose -f docker-compose.yml down
    docker system prune -f
    echo -e "${GREEN}✅ Entorno limpio${NC}"
}

# Procesar argumentos
case "${1}" in
    start)
        dev_start
        ;;
    stop)
        dev_stop
        ;;
    restart)
        dev_restart
        ;;
    logs)
        shift
        dev_logs "$@"
        ;;
    status)
        dev_status
        ;;
    prod)
        prod_mode
        ;;
    build)
        prod_build
        ;;
    clean)
        clean_env
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Comando desconocido: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac