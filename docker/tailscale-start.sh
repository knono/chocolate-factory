#!/bin/bash
# =============================================================================
# TFM CHOCOLATE FACTORY - TAILSCALE SIDECAR STARTUP SCRIPT
# =============================================================================
# Inicia Tailscale daemon + nginx en el mismo contenedor
# Se une a la tailnet como 'factory-chocolate'
# =============================================================================

set -e

echo "🍫 TFM Chocolate Factory - Tailscale Sidecar Starting..."
echo "📍 Hostname: ${TAILSCALE_HOSTNAME:-factory-chocolate}"

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
trap cleanup SIGTERM SIGINT

# Verificar que tenemos authkey
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    log "❌ ERROR: TAILSCALE_AUTHKEY no está configurado"
    log "💡 Genera una authkey en: https://login.tailscale.com/admin/settings/keys"
    exit 1
fi

# Crear directorios necesarios
log "📁 Creating Tailscale directories..."
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
    --hostname="${TAILSCALE_HOSTNAME:-chocolate-factory}" \
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
tailscale cert "${TAILSCALE_HOSTNAME:-chocolate-factory}.azules-elver.ts.net"

# Verificar que los certificados se generaron
if [ -f "/var/lib/tailscale/certs/${TAILSCALE_HOSTNAME:-chocolate-factory}.azules-elver.ts.net.crt" ]; then
    log "✅ SSL certificates obtained successfully"
else
    log "❌ ERROR: Failed to obtain SSL certificates"
    exit 1
fi

# Verificar configuración nginx
log "🔧 Testing nginx configuration..."
nginx -t

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
log "🌐 Dashboard available at: https://${TAILSCALE_HOSTNAME:-chocolate-factory}.azules-elver.ts.net/dashboard"
log "📊 Proxying to: ${NGINX_UPSTREAM:-chocolate_factory_brain:8000}"
log "🔒 Only /dashboard endpoint is exposed"

# Mantener el contenedor corriendo y monitorear servicios
while true; do
    # Verificar que tailscaled sigue corriendo
    if ! pgrep -f tailscaled > /dev/null; then
        log "❌ ERROR: Tailscale daemon died, restarting..."
        tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
        sleep 3
        tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="${TAILSCALE_HOSTNAME:-chocolate-factory}"
    fi
    
    # Verificar que nginx sigue corriendo
    if ! pgrep -f nginx > /dev/null; then
        log "❌ ERROR: nginx died, restarting..."
        nginx -g 'daemon off;' &
    fi
    
    sleep 30
done