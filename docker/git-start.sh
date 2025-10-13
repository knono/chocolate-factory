#!/bin/sh
# =============================================================================
# GIT SIDECAR STARTUP SCRIPT
# =============================================================================
# Inicia Tailscale + nginx para exponer Forgejo en la Tailnet
# =============================================================================

set -e

echo "🚀 Starting Git Tailscale Sidecar..."

# Validar variables de entorno requeridas
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "❌ ERROR: TAILSCALE_AUTHKEY no está definida"
    exit 1
fi

# Iniciar Tailscaled en background
echo "📡 Starting Tailscaled..."
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
sleep 3

# Autenticarse en Tailscale
echo "🔐 Authenticating with Tailscale..."
tailscale up \
    --authkey="${TAILSCALE_AUTHKEY}" \
    --hostname="${TAILSCALE_HOSTNAME:-git}" \
    --accept-routes \
    --accept-dns=true

echo "✅ Tailscale connected"
tailscale status

# Procesar template de nginx con variables de entorno (si existe)
echo "⚙️  Configuring nginx..."
if [ -f /etc/nginx/nginx.conf.template ]; then
    envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
fi

# Test nginx config
nginx -t

# Iniciar nginx en foreground
echo "🌐 Starting nginx..."
exec nginx -g 'daemon off;'
