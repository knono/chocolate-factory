# =============================================================================
# TFM CHOCOLATE FACTORY - FASTAPI DOCKERFILE
# =============================================================================
# Dockerfile optimizado para FastAPI con SimPy, SciPy y ML dependencies
# =============================================================================

FROM python:3.11-slim

# Metadatos
LABEL maintainer="TFM Chocolate Factory"
LABEL description="FastAPI Brain - Chocolate Factory Autonomous System"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Dependencias del sistema necesarias para compilar paquetes científicos
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Sprint 13: Instalar Tailscale CLI para analytics
RUN wget -O /tmp/tailscale.tgz https://pkgs.tailscale.com/stable/tailscale_1.86.2_amd64.tgz && \
    tar -xzf /tmp/tailscale.tgz -C /tmp && \
    cp /tmp/tailscale_1.86.2_amd64/tailscale /usr/local/bin/ && \
    chmod +x /usr/local/bin/tailscale && \
    rm -rf /tmp/tailscale.tgz /tmp/tailscale_1.86.2_amd64

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Directorio de trabajo
WORKDIR /app

# Copiar código fuente primero (necesario para pip install -e)
COPY src/fastapi-app/ ./
COPY src/configs/ ./configs/
COPY src/ml/ ./ml/

# Instalar dependencias
RUN pip install --upgrade pip
RUN pip install -e .
COPY static/ ./static/
COPY .claude/ ./.claude/

# Crear directorios necesarios y ajustar permisos
RUN mkdir -p /app/data /app/logs /app/models/forecasting && \
    chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Puerto de la aplicación
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
# Sprint 18: Enable proxy headers for Tailscale sidecar auth
# --proxy-headers: Enable X-Forwarded-For, X-Real-IP, etc.
# --forwarded-allow-ips: Trust headers from sidecar (192.168.100.8) and Docker network
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "192.168.100.0/24"]