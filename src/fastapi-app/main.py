"""
TFM Chocolate Factory - FastAPI Main Application
=================================================

El Cerebro Autónomo: FastAPI + APScheduler para automatización completa
- Endpoints: /predict y /ingest-now
- Automatización: APScheduler para ingestión y predicciones periódicas
- Simulación: SimPy/SciPy para lógica de fábrica
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    logger.info("🧠 Iniciando El Cerebro Autónomo - Chocolate Factory Brain")
    logger.info("📅 APScheduler: Configuración pendiente")
    logger.info("🏭 SimPy: Simulación pendiente")
    yield
    logger.info("🛑 Deteniendo El Cerebro Autónomo")


# Crear la aplicación FastAPI
app = FastAPI(
    title="TFM Chocolate Factory - El Cerebro Autónomo",
    description="Sistema autónomo de ingestión, predicción y monitoreo para fábrica de chocolate",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Endpoint raíz - Estado del sistema"""
    return {
        "service": "TFM Chocolate Factory Brain",
        "status": "🧠 El Cerebro Autónomo está funcionando",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (pendiente)",
            "ingest": "/ingest-now (pendiente)",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check para Docker"""
    return {
        "status": "healthy",
        "service": "chocolate_factory_brain",
        "message": "🧠 Sistema operativo"
    }


@app.get("/predict")
async def predict():
    """Endpoint de predicción ML (pendiente implementación)"""
    return {
        "status": "pending",
        "message": "🔮 Funcionalidad de predicción pendiente",
        "ml_models": "MLflow integration pending"
    }


@app.post("/ingest-now")
async def ingest_now():
    """Forzar ingestión inmediata de datos (pendiente implementación)"""
    return {
        "status": "pending",
        "message": "📥 Ingestión manual pendiente", 
        "data_sources": ["REE API", "AEMET API"],
        "target": "InfluxDB"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
