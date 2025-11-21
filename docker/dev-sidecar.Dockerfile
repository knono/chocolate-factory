# =============================================================================
# DOCKERFILE - DEV TAILSCALE SIDECAR WITH NGINX
# =============================================================================
# Sidecar que combina Tailscale + nginx para exponer dev environment
# =============================================================================

FROM alpine:3.19

# Instalar Tailscale + nginx + gettext (envsubst)
RUN apk add --no-cache \
    ca-certificates \
    iptables \
    ip6tables \
    iproute2 \
    nginx \
    curl \
    gettext \
    && mkdir -p /var/lib/tailscale /var/log/nginx /run/nginx

# Instalar Tailscale 1.90.8 (App Capabilities support - Sprint 18)
RUN wget https://pkgs.tailscale.com/stable/tailscale_1.90.8_amd64.tgz -O /tmp/tailscale.tgz \
    && tar xzf /tmp/tailscale.tgz -C /tmp \
    && mv /tmp/tailscale_1.90.8_amd64/tailscale /usr/local/bin/ \
    && mv /tmp/tailscale_1.90.8_amd64/tailscaled /usr/local/bin/ \
    && rm -rf /tmp/tailscale*

# Script de inicio
COPY docker/dev-start.sh /usr/local/bin/dev-start.sh
RUN chmod +x /usr/local/bin/dev-start.sh

# Exponer puertos HTTP y HTTPS
EXPOSE 80 443

CMD ["/usr/local/bin/dev-start.sh"]
