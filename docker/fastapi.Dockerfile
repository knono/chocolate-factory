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
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias primero (mejor cache de Docker)
COPY src/fastapi-app/pyproject.toml ./

# Instalar dependencias
RUN pip install --upgrade pip
RUN pip install -e .

# Copiar código fuente
COPY src/fastapi-app/ ./
COPY src/configs/ ./configs/
COPY src/ml/ ./ml/
COPY static/ ./static/
COPY .claude/ ./.claude/

# Crear directorios necesarios y ajustar permisos
RUN mkdir -p /app/data /app/logs /app/models && \
    chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Puerto de la aplicación
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]