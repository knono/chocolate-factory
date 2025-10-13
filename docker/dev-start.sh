#!/bin/sh
# =============================================================================
# DEV NODE - TAILSCALE SIDECAR STARTUP SCRIPT
# =============================================================================
# Inicia Tailscale daemon + nginx con SSL para desarrollo
# =============================================================================

set -e

echo "🔧 Dev Node - Tailscale Sidecar Starting..."
echo "📍 Hostname: ${TAILSCALE_HOSTNAME:-chocolate-factory-dev}"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Función de cleanup
cleanup() {
    log "🛑 Shutting down services..."
    if pgrep -f tailscaled > /dev/null; then
        log "Stopping Tailscale daemon..."
        pkill -f tailscaled
    fi
    if pgrep -f nginx > /dev/null; then
        log "Stopping nginx..."
        nginx -s quit || pkill -f nginx
    fi
    exit 0
}

# Configurar trap para shutdown limpio
trap cleanup TERM INT

# Verificar que tenemos authkey
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    log "❌ ERROR: TAILSCALE_AUTHKEY no está configurado"
    log "💡 Genera una authkey en: https://login.tailscale.com/admin/settings/keys"
    exit 1
fi

# Crear directorios necesarios
log "📁 Creating directories..."
mkdir -p /var/lib/tailscale /var/run/tailscale /var/log/nginx

# Iniciar Tailscale daemon
log "🚀 Starting Tailscale daemon..."
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
TAILSCALED_PID=$!

# Esperar a que el daemon esté listo
sleep 3

# Verificar que tailscaled está corriendo
if ! pgrep -f tailscaled > /dev/null; then
    log "❌ ERROR: Tailscale daemon failed to start"
    exit 1
fi

# Conectar a la tailnet
log "🔗 Connecting to Tailscale network..."
tailscale up \
    --authkey="$TAILSCALE_AUTHKEY" \
    --hostname="${TAILSCALE_HOSTNAME:-chocolate-factory-dev}" \
    --accept-routes \
    --accept-dns

# Verificar conexión
sleep 5
if tailscale status > /dev/null 2>&1; then
    log "✅ Successfully connected to Tailscale"
    tailscale status
else
    log "❌ ERROR: Failed to connect to Tailscale"
    exit 1
fi

# Solicitar certificados SSL automáticos
log "🔒 Requesting SSL certificates from Tailscale..."
mkdir -p /var/lib/tailscale/certs
tailscale cert "${TAILSCALE_DOMAIN}"

# Verificar que los certificados se generaron
if [ -f "/var/lib/tailscale/certs/${TAILSCALE_DOMAIN}.crt" ]; then
    log "✅ SSL certificates obtained successfully"
else
    log "❌ ERROR: Failed to obtain SSL certificates"
    exit 1
fi

# Procesar variables de entorno en nginx.conf
log "📝 Processing nginx configuration with envsubst..."
envsubst '${TAILSCALE_DOMAIN}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Verificar configuración nginx
log "🔧 Testing nginx configuration..."
nginx -t -c /etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    log "❌ ERROR: nginx configuration is invalid"
    exit 1
fi

# Iniciar nginx
log "🌐 Starting nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

# Verificar que nginx está corriendo
sleep 2
if ! pgrep -f nginx > /dev/null; then
    log "❌ ERROR: nginx failed to start"
    exit 1
fi

log "✅ All services started successfully!"
log "🌐 Development dashboard available at: https://${TAILSCALE_DOMAIN}/dashboard"
log "📊 Proxying to: chocolate_factory_dev:8000"

# Mantener el contenedor corriendo y monitorear servicios
while true; do
    # Verificar que tailscaled sigue corriendo
    if ! pgrep -f tailscaled > /dev/null; then
        log "❌ ERROR: Tailscale daemon died, restarting..."
        tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
        sleep 3
        tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="${TAILSCALE_HOSTNAME:-chocolate-factory-dev}"
    fi

    # Verificar que nginx sigue corriendo
    if ! pgrep -f nginx > /dev/null; then
        log "❌ ERROR: nginx died, restarting..."
        nginx -g 'daemon off;' &
    fi

    sleep 30
done
