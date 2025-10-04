# =============================================================================
# TFM CHOCOLATE FACTORY - TAILSCALE SIDECAR DOCKERFILE
# =============================================================================
# Sidecar que se une a la tailnet como 'chocolate-factory' y expone solo /dashboard
# Base: Alpine Linux con Tailscale + nginx (contenedor ligero)
# =============================================================================

FROM alpine:3.18

# Variables de entorno
ENV TAILSCALE_USE_WIP_CODE=1

# Instalar dependencias base
RUN apk add --no-cache \
    curl \
    wget \
    nginx \
    ca-certificates \
    iptables \
    bash \
    procps \
    gettext

# Instalar Tailscale versión 1.86.2 (latest with security fixes)
# Using official Tailscale packages from pkgs.tailscale.com
RUN wget -O /tmp/tailscale.tgz https://pkgs.tailscale.com/stable/tailscale_1.86.2_amd64.tgz && \
    tar -xzf /tmp/tailscale.tgz -C /tmp && \
    cp /tmp/tailscale_1.86.2_amd64/tailscale /usr/local/bin/ && \
    cp /tmp/tailscale_1.86.2_amd64/tailscaled /usr/local/bin/ && \
    chmod +x /usr/local/bin/tailscale /usr/local/bin/tailscaled && \
    rm -rf /tmp/tailscale.tgz /tmp/tailscale_1.86.2_amd64

# Crear directorios necesarios
RUN mkdir -p /var/lib/tailscale /var/run/tailscale /etc/nginx/conf.d /var/log/nginx

# Crear usuario nginx (si no existe)
RUN adduser -D -s /sbin/nologin -G www-data nginx 2>/dev/null || true

# Copiar configuración nginx específica para sidecar
COPY docker/sidecar-nginx.conf /etc/nginx/nginx.conf

# Copiar script de inicio
COPY docker/tailscale-start.sh /usr/local/bin/tailscale-start.sh
RUN chmod +x /usr/local/bin/tailscale-start.sh

# Variables de entorno
ENV TAILSCALE_HOSTNAME=factory-chocolate
ENV TAILSCALE_STATE_DIR=/var/lib/tailscale
ENV NGINX_UPSTREAM=chocolate_factory_brain:8000

# Exponer solo para debug local (no se mapea al host)
EXPOSE 80 443

# Ejecutar script de inicio que maneja Tailscale + nginx
CMD ["/usr/local/bin/tailscale-start.sh"]