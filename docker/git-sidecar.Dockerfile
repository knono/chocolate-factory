# =============================================================================
# DOCKERFILE - GIT TAILSCALE SIDECAR WITH NGINX
# =============================================================================
# Sidecar que combina Tailscale + nginx para exponer Forgejo en la Tailnet
# =============================================================================

FROM alpine:3.19

# Instalar Tailscale + nginx
RUN apk add --no-cache \
    ca-certificates \
    iptables \
    ip6tables \
    iproute2 \
    nginx \
    curl \
    gettext \
    && mkdir -p /var/lib/tailscale /var/log/nginx /run/nginx

# Instalar Tailscale
RUN wget https://pkgs.tailscale.com/stable/tailscale_1.56.1_amd64.tgz -O /tmp/tailscale.tgz \
    && tar xzf /tmp/tailscale.tgz -C /tmp \
    && mv /tmp/tailscale_1.56.1_amd64/tailscale /usr/local/bin/ \
    && mv /tmp/tailscale_1.56.1_amd64/tailscaled /usr/local/bin/ \
    && rm -rf /tmp/tailscale*

# Script de inicio (patrón igual a producción)
COPY docker/git-start.sh /usr/local/bin/git-start.sh
RUN chmod +x /usr/local/bin/git-start.sh

# Exponer puertos
EXPOSE 80

CMD ["/usr/local/bin/git-start.sh"]
