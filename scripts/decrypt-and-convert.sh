#!/bin/bash
# =============================================================================
# CHOCOLATE FACTORY - DECRYPT & CONVERT SECRETS
# =============================================================================
# Desencripta secrets.enc.yaml y convierte a formato .env para Docker Compose
# Convierte snake_case → UPPER_CASE y YAML → dotenv format
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🍫 Chocolate Factory - Secret Manager${NC}"
echo ""

# Verificar prerequisitos
if [ ! -f ".sops/age-key.txt" ]; then
    echo -e "${RED}❌ Error: .sops/age-key.txt not found${NC}"
    echo "   Generate with: age-keygen -o .sops/age-key.txt"
    exit 1
fi

if [ ! -f "secrets.enc.yaml" ]; then
    echo -e "${RED}❌ Error: secrets.enc.yaml not found${NC}"
    exit 1
fi

if ! command -v sops &> /dev/null; then
    echo -e "${RED}❌ Error: sops not found${NC}"
    echo "   Install with: sudo apt-get install -y sops"
    exit 1
fi

# Desencriptar
echo -e "${YELLOW}🔓 Decrypting secrets...${NC}"
export SOPS_AGE_KEY_FILE=.sops/age-key.txt

# Desencriptar a temporal
sops --decrypt secrets.enc.yaml > /tmp/secrets-plain.yaml 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Decryption failed${NC}"
    rm -f /tmp/secrets-plain.yaml
    exit 1
fi

# Convertir YAML a .env format manualmente (sin yq)
echo -e "${YELLOW}🔄 Converting to .env format...${NC}"

# Limpiar .env anterior
> .env

# Procesar línea por línea
while IFS=': ' read -r key value; do
    # Ignorar comentarios, líneas vacías y metadata SOPS
    if [[ "$key" == \#* ]] || [[ -z "$key" ]] || [[ "$key" == "sops" ]] || [[ "$key" == *"age"* ]] || [[ "$key" == *"lastmodified"* ]] || [[ "$key" == *"mac"* ]] || [[ "$key" == *"version"* ]] || [[ "$key" == *"unencrypted_suffix"* ]]; then
        continue
    fi

    # Limpiar comillas del valor
    value=$(echo "$value" | sed 's/^"//;s/"$//' | tr -d '\r')

    # Mantener snake_case (docker-compose usa ${snake_case})
    key_clean=$(echo "$key" | tr '-' '_')

    # Escribir en formato dotenv
    if [ -n "$value" ] && [ "$value" != "null" ]; then
        echo "${key_clean}=${value}" >> .env
    fi
done < /tmp/secrets-plain.yaml

# Agregar variables adicionales que no están en secrets
echo "" >> .env
echo "# Additional configuration variables" >> .env
echo "TAILSCALE_HOSTNAME=chocolate-factory" >> .env
echo "TAILSCALE_DOMAIN=chocolate-factory.azules-elver.ts.net" >> .env
echo "TAILSCALE_HOSTNAME_DEV=chocolate-factory-dev" >> .env
echo "TAILSCALE_DOMAIN_DEV=chocolate-factory-dev.azules-elver.ts.net" >> .env
echo "TAILSCALE_HOSTNAME_GIT=git" >> .env
echo "TAILSCALE_DOMAIN_GIT=git.azules-elver.ts.net" >> .env
echo "" >> .env
echo "# Tailscale auth keys (UPPER_CASE for docker-compose.override.yml)" >> .env
# Read snake_case values and create UPPER_CASE aliases
TAILSCALE_AUTHKEY_VALUE=$(grep "^tailscale_authkey=" .env | cut -d= -f2)
TAILSCALE_AUTHKEY_DEV_VALUE=$(grep "^tailscale_authkey_dev=" .env | cut -d= -f2)
TAILSCALE_AUTHKEY_GIT_VALUE=$(grep "^tailscale_authkey_git=" .env | cut -d= -f2)
echo "TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY_VALUE}" >> .env
echo "TAILSCALE_AUTHKEY_DEV=${TAILSCALE_AUTHKEY_DEV_VALUE}" >> .env
echo "TAILSCALE_AUTHKEY_GIT=${TAILSCALE_AUTHKEY_GIT_VALUE}" >> .env
echo "" >> .env
echo "# Tailscale authentication" >> .env
TAILSCALE_ADMINS_VALUE=$(grep "^tailscale_admins=" .env | cut -d= -f2)
TAILSCALE_AUTH_ENABLED_VALUE=$(grep "^tailscale_auth_enabled=" .env | cut -d= -f2)
echo "TAILSCALE_ADMINS=${TAILSCALE_ADMINS_VALUE}" >> .env
echo "TAILSCALE_AUTH_ENABLED=${TAILSCALE_AUTH_ENABLED_VALUE}" >> .env
echo "" >> .env
echo "# Telegram alerts" >> .env
TELEGRAM_BOT_TOKEN_VALUE=$(grep "^telegram_bot_token=" .env | cut -d= -f2)
TELEGRAM_CHAT_ID_VALUE=$(grep "^telegram_chat_id=" .env | cut -d= -f2)
TELEGRAM_ALERTS_ENABLED_VALUE=$(grep "^telegram_alerts_enabled=" .env | cut -d= -f2)
echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN_VALUE}" >> .env
echo "TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID_VALUE}" >> .env
echo "TELEGRAM_ALERTS_ENABLED=${TELEGRAM_ALERTS_ENABLED_VALUE}" >> .env
echo "" >> .env
echo "# InfluxDB configuration" >> .env
echo "INFLUXDB_URL_DOCKER=http://chocolate_factory_storage:8086" >> .env
echo "INFLUXDB_ORG=chocolate_factory" >> .env
echo "INFLUXDB_BUCKET=energy_data" >> .env
echo "INFLUXDB_ADMIN_USER=admin" >> .env
echo "INFLUXDB_PORT=8086" >> .env
echo "" >> .env
echo "# Application configuration" >> .env
echo "ENVIRONMENT=development" >> .env
echo "LOG_LEVEL=INFO" >> .env
echo "TZ=Europe/Madrid" >> .env
echo "FASTAPI_PORT=8000" >> .env

# Limpiar temporal
rm -f /tmp/secrets-plain.yaml

# Verificar resultado
if [ ! -s .env ]; then
    echo -e "${RED}❌ Conversion failed - .env is empty${NC}"
    exit 1
fi

SECRET_COUNT=$(grep -c "=" .env || true)
echo -e "${GREEN}✅ Secrets decrypted and converted successfully${NC}"
echo -e "${BLUE}📝 Generated ${SECRET_COUNT} environment variables${NC}"
echo ""
echo -e "${BLUE}🔍 Preview (first 10 variables):${NC}"
head -10 .env | sed 's/=.*/=***/' # Ocultar valores
echo ""
echo -e "${GREEN}✅ Ready! You can now run: docker compose up -d${NC}"
