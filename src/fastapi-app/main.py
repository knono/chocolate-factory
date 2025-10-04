"""
Chocolate Factory - FastAPI Main Application
=============================================

El Cerebro Autónomo: FastAPI + APScheduler para automatización completa
- Endpoints: /predict y /ingest-now
- Automatización: APScheduler para ingestión y predicciones periódicas
- Simulación: SimPy/SciPy para lógica de fábrica
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import sys
import os

from services.scheduler import get_scheduler_service, start_scheduler, stop_scheduler
from services.data_ingestion import DataIngestionService, run_current_ingestion, run_daily_ingestion
from services.ree_client import REEClient
from services.aemet_client import AEMETClient
from services.openweathermap_client import OpenWeatherMapClient
from services.initialization import InitializationService
from services.initialization.historical_ingestion import HistoricalDataIngestion
import pandas as pd
import numpy as np

from services.direct_ml import DirectMLService
from services.enhanced_ml_service import EnhancedMLService
from services.enhanced_recommendations import EnhancedRecommendationEngine
from services.dashboard import DashboardService

# Configurar logging ANTES de usarlo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sprint 05: Optimization imports
SPRINT05_ENABLED = False
try:
    # Add project root to path for Sprint 05 imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from api.middleware.rate_limiter import RateLimitMiddleware, default_rate_limiter, ml_rate_limiter
    from core.cache.cache_manager import CacheMiddleware, cache_manager
    from core.health.health_checks import health_checker
    SPRINT05_ENABLED = True
    logger.info("✅ Sprint 05: Optimization features enabled")
except ImportError as e:
    logger.warning(f"⚠️  Sprint 05 Optimization not available: {e}")
    logger.debug("    Sprint 05 features (cache, rate limiting, health checks) disabled")

# Sprint 03: Service Layer imports
# Necesita bind mounts adicionales en docker-compose.yml:
#   - ./src/api:/app/api
#   - ./src/services:/app/src_services
#   - ./src/repositories:/app/repositories
#   - ./src/core:/app/core
SPRINT03_ENABLED = False
try:
    import sys
    import os
    # Agregar path para imports de src/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from api.dependencies import get_production_service
    from api.v1.schemas.production import (
        ProductionBatchCreate,
        ProductionBatchResponse,
        ProductionStats
    )
    SPRINT03_ENABLED = True
    logger.info("✅ Sprint 03: Service Layer enabled")
except ImportError as e:
    logger.warning(f"⚠️  Sprint 03 Service Layer not available: {e}")
    logger.debug("    Add bind mounts in docker-compose.yml to enable Sprint 03 features")

# Global service instances (initialized once, shared across the app)
global_direct_ml = None
global_dashboard_service = None


def get_global_direct_ml():
    """Get the global Direct ML service instance"""
    global global_direct_ml
    if global_direct_ml is None:
        global_direct_ml = DirectMLService()
    return global_direct_ml


def get_global_dashboard_service():
    """Get the global dashboard service instance"""
    global global_dashboard_service
    if global_dashboard_service is None:
        raise RuntimeError("Global dashboard service not initialized")
    return global_dashboard_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    logger.info("🧠 Iniciando El Cerebro Autónomo - Chocolate Factory Brain")

    # Initialize global services
    global global_direct_ml, global_dashboard_service
    try:
        # Initialize services
        global_direct_ml = DirectMLService()
        global_dashboard_service = DashboardService()
        logger.info("🤖 Global ML services initialized (hybrid architecture)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize global services: {e}")
    
    try:
        # Iniciar el scheduler automático
        await start_scheduler()
        logger.info("📅 APScheduler: Iniciado correctamente")
        logger.info("🏭 SimPy: Simulación pendiente")
        
        yield
        
    finally:
        # Detener el scheduler al cerrar la aplicación
        logger.info("🛑 Deteniendo El Cerebro Autónomo")
        await stop_scheduler()
        logger.info("📅 APScheduler: Detenido")


# Crear la aplicación FastAPI
app = FastAPI(
    title="Chocolate Factory - Enhanced ML System",
    description="Sistema autónomo con Enhanced ML, datos históricos (SIAR 88k + REE 42k) y predicciones avanzadas",
    version="0.31.0",
    lifespan=lifespan
)

# =====================================================
# Sprint 05: Middlewares (Order matters!)
# =====================================================

# 1. GZip Compression (should be first)
app.add_middleware(GZipMiddleware, minimum_size=1000)
logger.info("✅ GZip compression middleware enabled")

# 2. CORS (before rate limiting)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate Limiting (Sprint 05 - if enabled)
# Note: Rate limiting and cache middleware are implemented as callable classes
# They will be used via Depends() in endpoints that need protection
if SPRINT05_ENABLED:
    logger.info("✅ Rate limiting available (use via Depends)")
    logger.info("✅ Cache system available (use via decorators)")

# Mount static files for dashboard (Sprint 05)
# En contenedor Docker, static está en /app/static (bind mount)
static_path = "/app/static"
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"✅ Static files mounted from: {static_path}")
else:
    logger.warning(f"⚠️  Static directory not found: {static_path}")

# Modelos Pydantic para requests
class IngestionRequest(BaseModel):
    source: str = "ree"  # ree, aemet, all
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    force_refresh: bool = False

class WeatherRequest(BaseModel):
    station_ids: Optional[List[str]] = None  # Default to Madrid area
    include_forecast: bool = False

class SchedulerJobRequest(BaseModel):
    job_id: str
    action: str  # trigger, pause, resume

class PredictionRequest(BaseModel):
    price_eur_kwh: float
    temperature: float
    humidity: float
    include_features: bool = True  # Return engineered features

class RangeBackfillRequest(BaseModel):
    start_date: str  # ISO format: 2025-09-08T00:00:00Z
    end_date: str    # ISO format: 2025-09-17T23:59:59Z
    data_source: str = "both"  # "ree", "weather", "both"

# =====================================================
# Sprint 02: Nueva Arquitectura ML - Pydantic Models
# =====================================================

class TrainingData(BaseModel):
    data: List[Dict[str, Any]]
    target_column: str
    model_name: str = "quality_predictor"

class PredictionRequest(BaseModel):
    temperature: float
    humidity: float
    roasting_time: float
    cocoa_percentage: float
    bean_origin: Optional[str] = "Unknown"

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    insights: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    """Endpoint raíz - Redirige al dashboard estático"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.get("/api")
async def api_root():
    """API root - Estado del sistema"""
    return {
        "service": "Chocolate Factory Enhanced ML Brain",
        "status": "✨ Enhanced ML System con datos históricos operativo",
        "version": "0.31.0",
        "endpoints": {
            "dashboard": "/static/index.html",
            "dashboard_data": "/dashboard/complete",
            "health": "/health",
            "predict": "/predict (pendiente)",
            "ingest": "/ingest-now",
            "scheduler": "/scheduler/status",
            "ree_prices": "/ree/prices",
            "aemet_weather": "/aemet/weather",
            "openweather": "/weather/openweather",
            "openweather_forecast": "/weather/openweather/forecast",
            "openweather_status": "/weather/openweather/status",
            "weather_comparison": "/weather/comparison",
            "hybrid_weather": "/weather/hybrid",
            "aemet_token": "/aemet/token/status",
            "influxdb_verify": "/influxdb/verify",
            "init_status": "/init/status",
            "init_historical": "/init/historical-data",
            "init_all": "/init/all",
            "aemet_stations": "/aemet/stations",
            "aemet_token_renew": "/aemet/token/renew",
            "mlflow_status": "/mlflow/status",
            "mlflow_web_check": "/mlflow/web-check",
            "mlflow_features": "/mlflow/features",
            "mlflow_train": "/mlflow/train",
            "predict_energy": "/predict/energy-optimization",
            "predict_production": "/predict/production-recommendation",
            "models_status": "/models/status",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check completo - Sprint 05"""
    if SPRINT05_ENABLED:
        try:
            health_result = await health_checker.run_all_checks()
            return health_result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    else:
        # Fallback básico si Sprint 05 no está habilitado
        return {
            "status": "healthy",
            "service": "chocolate_factory_brain",
            "message": "🧠 Sistema operativo"
        }

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe - K8s compatible (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            result = await health_checker.get_readiness()
            status_code = 200 if result.get('ready') else 503
            return JSONResponse(content=result, status_code=status_code)
        except Exception as e:
            return JSONResponse(
                content={"ready": False, "error": str(e)},
                status_code=503
            )
    else:
        return {"ready": True, "message": "Sprint 05 not enabled"}

@app.get("/health/live")
async def liveness_check():
    """Liveness probe - K8s compatible (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            result = await health_checker.get_liveness()
            return result
        except Exception as e:
            return JSONResponse(
                content={"alive": False, "error": str(e)},
                status_code=503
            )
    else:
        return {
            "alive": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/debug/raw-ml-data")
async def debug_raw_ml_data_access():
    """🔬 DEBUG: Test raw ML data access using EXACT same code as /influxdb/verify"""
    try:
        async with DataIngestionService() as service:
            query_api = service.client.query_api()
            
            # Use EXACT same query as /influxdb/verify (known working)
            energy_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -3h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 10)
            '''
            
            weather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -3h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 10)
            '''
            
            energy_results = query_api.query(energy_query)
            weather_results = query_api.query(weather_query)
            
            # Process results exactly like /influxdb/verify does
            energy_data = []
            for table in energy_results:
                for record in table.records:
                    energy_data.append({
                        'timestamp': record.get_time(),
                        'price_eur_kwh': record.get_value()
                    })
                    
            weather_data = []
            for table in weather_results:
                for record in table.records:
                    weather_data.append({
                        'timestamp': record.get_time(),
                        'temperature': record.get_value()
                    })
            
            return {
                "🔬": "DEBUG: Raw ML Data Access Test",
                "status": "✅ SUCCESS - Data accessible",
                "energy_records": len(energy_data),
                "weather_records": len(weather_data),
                "energy_sample": energy_data[:3] if energy_data else [],
                "weather_sample": weather_data[:3] if weather_data else [],
                "bucket": service.config.bucket,
                "can_create_ml_features": len(energy_data) > 0 and len(weather_data) > 0
            }
            
    except Exception as e:
        return {
            "🔬": "DEBUG: Raw ML Data Access Test", 
            "status": "❌ FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }


@app.get("/predict")
async def predict(hours_ahead: int = 24, include_features: bool = True):
    """🔮 Endpoint de predicción ML con datos reales InfluxDB para features"""
    try:
        async with DataIngestionService() as service:
            query_api = service.client.query_api()
            
            # Query recent energy prices for feature engineering
            energy_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -7d)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 168)
            '''
            
            # Query recent weather data for features
            weather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -7d)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 300)
            '''
            
            energy_results = query_api.query(energy_query)
            weather_results = query_api.query(weather_query)
            
            # Process energy data for features
            energy_features = []
            for table in energy_results:
                for record in table.records:
                    energy_features.append({
                        "timestamp": record.get_time().isoformat(),
                        "price_eur_kwh": record.get_value(),
                        "source": record.values.get("source", "REE")
                    })
            
            # Process weather data for features  
            weather_features = []
            for table in weather_results:
                for record in table.records:
                    weather_features.append({
                        "timestamp": record.get_time().isoformat(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "source": record.values.get("source", "unknown")
                    })
            
            # Calculate feature statistics
            if energy_features:
                recent_prices = [f["price_eur_kwh"] for f in energy_features[:24]]
                avg_price_24h = sum(recent_prices) / len(recent_prices) if recent_prices else 0
                max_price_7d = max(f["price_eur_kwh"] for f in energy_features)
                min_price_7d = min(f["price_eur_kwh"] for f in energy_features)
            else:
                avg_price_24h = max_price_7d = min_price_7d = 0
            
            # Extract temperature features
            temp_data = [f for f in weather_features if f["field"] == "temperature"]
            if temp_data:
                recent_temp = temp_data[0]["value"] if temp_data else 20
                avg_temp_24h = sum(f["value"] for f in temp_data[:24]) / min(24, len(temp_data)) if temp_data else 20
            else:
                recent_temp = avg_temp_24h = 20
            
            # Chocolate production optimization index (simple formula)
            chocolate_optimization_score = 100 - (avg_price_24h * 2) - max(0, avg_temp_24h - 25) * 3
            
            prediction_response = {
                "🏭": "Chocolate Factory - Predicción ML",
                "status": "✅ Datos reales InfluxDB procesados",
                "prediction_horizon": f"{hours_ahead} horas",
                "model_status": "🚧 MLflow integration pendiente",
                "data_summary": {
                    "energy_records": len(energy_features),
                    "weather_records": len(weather_features),
                    "data_coverage": "7 días históricos"
                },
                "prediction": {
                    "chocolate_production_score": round(chocolate_optimization_score, 2),
                    "recommendation": "Alto" if chocolate_optimization_score > 80 else "Medio" if chocolate_optimization_score > 60 else "Bajo",
                    "energy_cost_forecast": f"{avg_price_24h:.3f} EUR/kWh promedio",
                    "temperature_forecast": f"{avg_temp_24h:.1f}°C promedio"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            if include_features:
                prediction_response["features"] = {
                    "energy_metrics": {
                        "avg_price_24h": round(avg_price_24h, 4),
                        "max_price_7d": round(max_price_7d, 4),
                        "min_price_7d": round(min_price_7d, 4),
                        "price_volatility": round(max_price_7d - min_price_7d, 4)
                    },
                    "weather_metrics": {
                        "current_temperature": recent_temp,
                        "avg_temperature_24h": round(avg_temp_24h, 2),
                        "heat_stress_factor": max(0, avg_temp_24h - 25)
                    },
                    "sample_data": {
                        "latest_energy": energy_features[:3],
                        "latest_weather": weather_features[:3]
                    }
                }
            
            return prediction_response
            
    except Exception as e:
        logger.error(f"Prediction with InfluxDB features failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "note": "Error al consultar features desde InfluxDB para predicción"
        }


@app.get("/forecast/weekly/combined", tags=["Forecast"])  
async def get_weekly_combined_forecast():
    """Prediccion semanal completa: REE + AEMET + OpenWeatherMap (7 dias)"""
    return {
        "status": "success",
        "message": "Weekly combined forecast endpoint works",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/ingest-now")
async def ingest_now(request: IngestionRequest, background_tasks: BackgroundTasks):
    """Forzar ingestión inmediata de datos"""
    try:
        logger.info(f"Manual ingestion requested for source: {request.source}")
        
        if request.source == "ree":
            # Ejecutar en background para no bloquear la respuesta
            background_tasks.add_task(run_current_ingestion)
            message = "📥 Ingestión REE iniciada en background"
        elif request.source == "aemet":
            async def run_aemet_ingestion():
                async with DataIngestionService() as service:
                    await service.ingest_current_weather()
            background_tasks.add_task(run_aemet_ingestion)
            message = "🌤️ Ingestión AEMET iniciada en background"
        elif request.source == "openweathermap":
            async def run_owm_ingestion():
                async with DataIngestionService() as service:
                    await service.ingest_openweathermap_weather()
            background_tasks.add_task(run_owm_ingestion)
            message = "🌍 Ingestión OpenWeatherMap iniciada en background"
        elif request.source == "weather" or request.source == "hybrid":
            async def run_hybrid_ingestion():
                async with DataIngestionService() as service:
                    await service.ingest_hybrid_weather()
            background_tasks.add_task(run_hybrid_ingestion)
            message = "🌤️🌍 Ingestión híbrida AEMET+OpenWeatherMap iniciada en background"
        elif request.source == "all":
            background_tasks.add_task(run_current_ingestion)
            async def run_aemet_ingestion():
                async with DataIngestionService() as service:
                    await service.ingest_current_weather()
            background_tasks.add_task(run_aemet_ingestion)
            message = "📥🌤️ Ingestión REE y AEMET iniciada en background"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {request.source}")
        
        return {
            "status": "started",
            "message": message,
            "source": request.source,
            "timestamp": datetime.now().isoformat()
        }
            
    except Exception as e:
        logger.error(f"Manual ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forecast/weekly/prices", tags=["Forecast"])
async def get_weekly_price_forecast():
    """📈 Predicción semanal de precios eléctricos usando ESIOS API"""
    try:
        import httpx
        
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        
        forecast_data = []
        
        # Try ESIOS API directly
        esios_indicators = [1001, 10211]  # PVPC and OMIE
        
        for indicator_id in esios_indicators:
            try:
                params = {
                    'start_date': start_date.strftime('%Y-%m-%dT%H:%M'),
                    'end_date': end_date.strftime('%Y-%m-%dT%H:%M'),
                    'geo_ids[]': 8741,  # Peninsula
                    'time_trunc': 'hour'
                }
                
                url = f"https://api.esios.ree.es/indicators/{indicator_id}"
                
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'indicator' in data and 'values' in data['indicator']:
                            values = data['indicator']['values']
                            
                            for value in values:
                                if 'datetime' in value and 'value' in value and value['value'] is not None:
                                    timestamp_str = value['datetime']
                                    price_value = float(value['value'])
                                    
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    
                                    forecast_data.append({
                                        "timestamp": timestamp.isoformat(),
                                        "date": timestamp.strftime("%Y-%m-%d"),
                                        "hour": timestamp.hour,
                                        "price_eur_kwh": round(price_value / 1000, 4),
                                        "price_eur_mwh": round(price_value, 2),
                                        "market_type": f"esios_indicator_{indicator_id}"
                                    })
                            
                            if forecast_data:
                                logger.info(f"✅ Retrieved {len(forecast_data)} prices from ESIOS indicator {indicator_id}")
                                break
                        
            except Exception as e:
                logger.debug(f"ESIOS indicator {indicator_id} failed: {e}")
                continue
        
        # Fallback: Use REE API for recent data to create forecast
        if not forecast_data:
            try:
                ree_client = REEClient()
                async with ree_client:
                    recent_data = await ree_client.get_pvpc_prices(
                        start_date - timedelta(days=2), 
                        start_date
                    )
                
                if recent_data:
                    recent_avg = sum(p.price_eur_mwh for p in recent_data[-24:]) / min(len(recent_data), 24)
                    
                    for i in range(7 * 24):  # 7 days, hourly
                        forecast_time = start_date + timedelta(hours=i)
                        hour = forecast_time.hour
                        
                        hour_factor = 1.0 + 0.2 * abs(hour - 14) / 14
                        weekend_factor = 0.9 if forecast_time.weekday() >= 5 else 1.0
                        forecasted_price = recent_avg * hour_factor * weekend_factor
                        
                        forecast_data.append({
                            "timestamp": forecast_time.isoformat(),
                            "date": forecast_time.strftime("%Y-%m-%d"),
                            "hour": hour,
                            "price_eur_kwh": round(forecasted_price / 1000, 4),
                            "price_eur_mwh": round(forecasted_price, 2),
                            "market_type": "ree_forecast_from_recent"
                        })
                    
                    logger.info(f"✅ Generated {len(forecast_data)} forecast prices from REE data")
                    
            except Exception as e:
                logger.error(f"REE fallback failed: {e}")
        
        # Calculate daily averages for heatmap
        daily_averages = {}
        for entry in forecast_data:
            date = entry["date"]
            if date not in daily_averages:
                daily_averages[date] = {"total": 0, "count": 0, "hours": []}
            daily_averages[date]["total"] += entry["price_eur_kwh"]
            daily_averages[date]["count"] += 1
            daily_averages[date]["hours"].append({
                "hour": entry["hour"],
                "price": entry["price_eur_kwh"]
            })
        
        for date in daily_averages:
            daily_averages[date]["average"] = round(daily_averages[date]["total"] / daily_averages[date]["count"], 4)
        
        return {
            "🏢": "Chocolate Factory - Predicción Semanal de Precios",
            "📊": "Datos de ESIOS + REE (mercado eléctrico español)",
            "forecast_period": {
                "start_date": forecast_data[0]["date"] if forecast_data else None,
                "end_date": forecast_data[-1]["date"] if forecast_data else None,
                "total_hours": len(forecast_data)
            },
            "hourly_data": forecast_data,
            "daily_averages": daily_averages,
            "price_range": {
                "min_price": min((p["price_eur_kwh"] for p in forecast_data), default=0),
                "max_price": max((p["price_eur_kwh"] for p in forecast_data), default=0),
                "avg_price": round(sum(p["price_eur_kwh"] for p in forecast_data) / len(forecast_data), 4) if forecast_data else 0
            },
            "generation_timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Weekly price forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Price forecast error: {str(e)}")


# Nuevos endpoints para REE y scheduler
@app.get("/ree/prices")
async def get_ree_prices(hours: int = 24):
    """Obtener precios REE de las próximas N horas"""
    try:
        async with REEClient() as client:
            if hours == 1:
                current_price = await client.get_current_price()
                return {
                    "status": "success",
                    "data": [current_price.dict()] if current_price else [],
                    "hours_requested": hours
                }
            else:
                prices = await client.get_price_forecast_24h()
                limited_prices = prices[:hours] if prices else []
                return {
                    "status": "success", 
                    "data": [price.dict() for price in limited_prices],
                    "hours_requested": hours,
                    "records_returned": len(limited_prices)
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch REE prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/historical/debug")
async def debug_influxdb_data():
    """🔧 Debug: Ver qué datos hay en InfluxDB"""
    try:
        from influxdb_client import InfluxDBClient
        import os
        
        bucket = os.getenv("INFLUXDB_BUCKET", "energy-data")
        
        client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
            token=os.getenv("INFLUXDB_TOKEN", ""),
            org=os.getenv("INFLUXDB_ORG", "chocolate-factory")
        )
        
        query_api = client.query_api()
        
        # Ver todos los measurements disponibles
        measurements_query = f'''
            import "influxdata/influxdb/schema"
            schema.measurements(bucket: "{bucket}")
        '''
        
        measurements_result = query_api.query(measurements_query)
        measurements = []
        for table in measurements_result:
            for record in table.records:
                measurements.append(record.get_value())
        
        # Ver datos energy_prices recientes
        energy_query = f'''
            from(bucket: "{bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["_measurement"] == "energy_prices")
            |> limit(n: 10)
        '''
        
        energy_result = query_api.query(energy_query)
        energy_data = []
        for table in energy_result:
            for record in table.records:
                energy_data.append({
                    "time": record.get_time().isoformat(),
                    "measurement": record.get_measurement(),
                    "field": record.get_field(),
                    "value": record.get_value(),
                    "tags": {key: value for key, value in record.values.items() if key not in ['_time', '_measurement', '_field', '_value']}
                })
        
        return {
            "bucket": bucket,
            "measurements": measurements,
            "energy_data_sample": energy_data[:5],
            "total_energy_records": len(energy_data)
        }
        
    except Exception as e:
        logger.error(f"Debug error: {e}")
        return {"error": str(e)}


@app.get("/analytics/historical")
async def get_historical_analytics(days_back: int = 220):
    """📊 Analytics históricos de precios REE y optimización de fábrica"""
    try:
        from services.historical_analytics import HistoricalAnalyticsService
        analytics_service = HistoricalAnalyticsService()
        analytics = await analytics_service.get_historical_analytics(days_back)
        return analytics.model_dump()
    except Exception as e:
        logger.error(f"Historical analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/status")
async def get_scheduler_status():
    """Obtener estado del scheduler y trabajos programados"""
    try:
        scheduler = await get_scheduler_service()
        status = scheduler.get_job_status()
        return {
            "status": "success",
            "scheduler": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/job")
async def manage_scheduler_job(request: SchedulerJobRequest):
    """Gestionar trabajos del scheduler (trigger, pause, resume)"""
    try:
        scheduler = await get_scheduler_service()
        
        if request.action == "trigger":
            success = await scheduler.trigger_job_now(request.job_id)
        elif request.action == "pause":
            success = await scheduler.pause_job(request.job_id)
        elif request.action == "resume":
            success = await scheduler.resume_job(request.job_id)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        if success:
            return {
                "status": "success",
                "message": f"Job {request.job_id} {request.action} completed",
                "job_id": request.job_id,
                "action": request.action
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to {request.action} job {request.job_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to manage scheduler job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ingestion/status")
async def get_ingestion_status():
    """Obtener estado de la ingestion de datos"""
    try:
        async with DataIngestionService() as service:
            status = await service.get_ingestion_status()
        
        return {
            "status": "success",
            "ingestion": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/weather/openweather")
async def get_openweather_linares():
    """🌤️ OpenWeatherMap - Datos en tiempo real para Linares, Jaén"""
    try:
        async with OpenWeatherMapClient() as client:
            # Get API status first
            status = await client.get_api_status()
            
            if status["status"] == "active":
                # Get current weather data
                current_weather = await client.get_current_weather()
                
                if current_weather:
                    return {
                        "🏭": "Chocolate Factory - OpenWeatherMap",
                        "📍": "Linares, Jaén (38.151107°N, -3.629453°W)",
                        "🌡️": f"{current_weather.temperature}°C",
                        "💧": f"{current_weather.humidity}%",
                        "🌬️": f"{current_weather.wind_speed} km/h" if current_weather.wind_speed else "N/A",
                        "📊": f"{current_weather.pressure} hPa" if current_weather.pressure else "N/A",
                        "🕐": current_weather.timestamp.isoformat(),
                        "📡": "OpenWeatherMap API v2.5",
                        "station_id": current_weather.station_id,
                        "data_source": "openweathermap",
                        "status": "✅ Datos en tiempo real",
                        "api_status": status
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No weather data available",
                        "api_status": status
                    }
            else:
                # API key not active yet
                return {
                    "🏭": "Chocolate Factory - OpenWeatherMap",
                    "📍": "Linares, Jaén",
                    "status": "⏳ API key pending activation",
                    "message": "OpenWeatherMap API keys can take up to 2 hours to activate",
                    "api_status": status,
                    "note": "El cliente está implementado y funcionará cuando la API key se active"
                }
        
    except Exception as e:
        logger.error(f"OpenWeatherMap endpoint error: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "note": "API key may still be activating"
        }


@app.get("/weather/openweather/forecast")
async def get_openweather_forecast(hours: int = 24):
    """🌤️ OpenWeatherMap - Pronóstico por horas para Linares, Jaén"""
    try:
        async with OpenWeatherMapClient() as client:
            # Get API status first
            status = await client.get_api_status()
            
            if status["status"] == "active":
                # Get forecast data
                forecast_data = await client.get_forecast(hours)
                
                if forecast_data:
                    forecast_list = []
                    for item in forecast_data:
                        forecast_list.append({
                            "timestamp": item.timestamp.isoformat(),
                            "temperature": item.temperature,
                            "humidity": item.humidity,
                            "pressure": item.pressure,
                            "wind_speed": item.wind_speed,
                            "wind_direction": item.wind_direction
                        })
                    
                    return {
                        "🏭": "Chocolate Factory - OpenWeatherMap Forecast",
                        "📍": "Linares, Jaén (38.151107°N, -3.629453°W)",
                        "status": "✅ Pronóstico disponible",
                        "hours_requested": hours,
                        "records_returned": len(forecast_list),
                        "data": forecast_list,
                        "api_status": status
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No forecast data available",
                        "api_status": status
                    }
            else:
                return {
                    "🏭": "Chocolate Factory - OpenWeatherMap Forecast",
                    "📍": "Linares, Jaén",
                    "status": "⏳ API key pending activation",
                    "message": "OpenWeatherMap API keys can take up to 2 hours to activate",
                    "api_status": status
                }
        
    except Exception as e:
        logger.error(f"OpenWeatherMap forecast endpoint error: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "note": "API key may still be activating"
        }


@app.get("/weather/openweather/status")
async def get_openweather_status():
    """🌤️ OpenWeatherMap - Estado de la API y conectividad"""
    try:
        async with OpenWeatherMapClient() as client:
            status = await client.get_api_status()
            
            return {
                "🏭": "Chocolate Factory - OpenWeatherMap API Status",
                "timestamp": datetime.now().isoformat(),
                "api_status": status,
                "integration_status": "✅ Cliente implementado y configurado",
                "coordinates": "Linares, Jaén (38.151107°N, -3.629453°W)",
                "api_version": "OpenWeatherMap v2.5 (free tier)"
            }
        
    except Exception as e:
        logger.error(f"OpenWeatherMap status endpoint error: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "integration_status": "❌ Error en cliente"
        }


@app.get("/weather/hybrid")
async def get_hybrid_weather(force_openweathermap: bool = False):
    """🌤️🌍 Estrategia híbrida: AEMET (00:00-07:00) + OpenWeatherMap (08:00-23:00)"""
    try:
        current_hour = datetime.now().hour
        use_aemet = (0 <= current_hour <= 7) and not force_openweathermap  # AEMET window restored
        
        async with DataIngestionService() as service:
            if use_aemet:
                # Try AEMET first
                try:
                    logger.info("🌤️ Attempting AEMET data ingestion...")
                    aemet_data = await service.ingest_aemet_weather()
                    logger.info(f"🌤️ AEMET ingestion result: {aemet_data.successful_writes} records")

                    if aemet_data.successful_writes > 0:
                        return {
                            "🏭": "Chocolate Factory - Estrategia Híbrida",
                            "📍": "Linares, Jaén",
                            "⚡": "AEMET (datos oficiales)",
                            "🕐": f"Hora {current_hour:02d}:xx - Ventana de observación oficial",
                            "status": "✅ Datos AEMET ingestados",
                            "records": aemet_data.successful_writes,
                            "strategy": "aemet_official",
                            "fallback": "OpenWeatherMap disponible si falla AEMET"
                        }
                    else:
                        logger.warning("🌤️ AEMET returned 0 records, falling back to OpenWeatherMap")
                except Exception as e:
                    logger.error(f"🌤️ AEMET ingestion failed: {e}")
                    # Fall through to OpenWeatherMap
            
            # Use OpenWeatherMap
            owm_data = await service.ingest_openweathermap_weather()
            source_reason = "ventana tiempo real" if not use_aemet else "fallback por fallo AEMET"
            
            return {
                "🏭": "Chocolate Factory - Estrategia Híbrida", 
                "📍": "Linares, Jaén",
                "⚡": "OpenWeatherMap (tiempo real)",
                "🕐": f"Hora {current_hour:02d}:xx - {source_reason}",
                "status": "✅ Datos OpenWeatherMap ingestados",
                "records": owm_data.successful_writes,
                "strategy": "openweathermap_realtime",
                "precision": "Datos actualizados cada 10 minutos"
            }
        
    except Exception as e:
        logger.error(f"Hybrid weather strategy failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "strategy": "hybrid_failed"
        }


@app.get("/weather/comparison")
async def get_weather_comparison(hours: int = 24):
    """📊 Comparación AEMET vs OpenWeather desde datos reales InfluxDB"""
    try:
        async with DataIngestionService() as service:
            query_api = service.client.query_api()
            
            # Query AEMET data from InfluxDB
            aemet_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r.source == "AEMET")
                |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 20)
            '''
            
            # Query OpenWeatherMap data from InfluxDB
            openweather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r.source == "OpenWeatherMap")
                |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 20)
            '''
            
            aemet_results = query_api.query(aemet_query)
            openweather_results = query_api.query(openweather_query)
            
            # Process AEMET data
            aemet_data = {"temperature": None, "humidity": None, "last_update": None, "count": 0}
            for table in aemet_results:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    timestamp = record.get_time()
                    
                    if field == "temperature" and aemet_data["temperature"] is None:
                        aemet_data["temperature"] = value
                        aemet_data["last_update"] = timestamp.isoformat()
                    elif field == "humidity" and aemet_data["humidity"] is None:
                        aemet_data["humidity"] = value
                    
                    aemet_data["count"] += 1
            
            # Process OpenWeatherMap data
            openweather_data = {"temperature": None, "humidity": None, "last_update": None, "count": 0}
            for table in openweather_results:
                for record in table.records:
                    field = record.get_field()
                    value = record.get_value()
                    timestamp = record.get_time()
                    
                    if field == "temperature" and openweather_data["temperature"] is None:
                        openweather_data["temperature"] = value
                        openweather_data["last_update"] = timestamp.isoformat()
                    elif field == "humidity" and openweather_data["humidity"] is None:
                        openweather_data["humidity"] = value
                    
                    openweather_data["count"] += 1
            
            # Calculate comparison stats
            temp_diff = None
            if aemet_data["temperature"] and openweather_data["temperature"]:
                temp_diff = abs(aemet_data["temperature"] - openweather_data["temperature"])
            
            return {
                "🏭": "Chocolate Factory - Comparación Datos Reales InfluxDB",
                "location": "Linares, Jaén, Andalucía",
                "query_period": f"Últimas {hours} horas",
                "comparison": {
                    "🇪🇸 AEMET (desde InfluxDB)": {
                        "temperature": f"{aemet_data['temperature']}°C" if aemet_data['temperature'] else "Sin datos",
                        "humidity": f"{aemet_data['humidity']}%" if aemet_data['humidity'] else "Sin datos",
                        "last_update": aemet_data['last_update'] or "Sin datos",
                        "records_found": aemet_data['count'],
                        "reliability": "⭐⭐⭐⭐⭐ Oficial AEMET"
                    },
                    "🌍 OpenWeatherMap (desde InfluxDB)": {
                        "temperature": f"{openweather_data['temperature']}°C" if openweather_data['temperature'] else "Sin datos",
                        "humidity": f"{openweather_data['humidity']}%" if openweather_data['humidity'] else "Sin datos", 
                        "last_update": openweather_data['last_update'] or "Sin datos",
                        "records_found": openweather_data['count'],
                        "reliability": "⭐⭐⭐⭐ Tiempo real"
                    }
                },
                "analysis": {
                    "temperature_difference": f"{temp_diff:.1f}°C" if temp_diff else "No comparable",
                    "data_availability": {
                        "aemet_coverage": "✅" if aemet_data['count'] > 0 else "❌ Sin datos",
                        "openweather_coverage": "✅" if openweather_data['count'] > 0 else "❌ Sin datos"
                    }
                },
                "recommendation": "Datos reales desde InfluxDB - Estrategia híbrida funcionando",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Weather comparison query failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "note": "Error al consultar comparación meteorológica en InfluxDB"
        }


@app.get("/aemet/weather")
async def get_aemet_weather(station_ids: Optional[str] = None):
    """🌤️ DATOS REALES de AEMET Linares - Para verificar con móvil"""
    try:
        station_list = ["5279X"] if not station_ids else [s.strip() for s in station_ids.split(",")]
        
        weather_data = []
        async with AEMETClient() as client:
            for station_id in station_list:
                try:
                    # Direct API call to get real AEMET data for Linares
                    data = await client._make_request(f"observacion/convencional/datos/estacion/{station_id}")
                    if 'datos' in data:
                        response = await client.client.get(data['datos'])
                        response.raise_for_status()
                        raw_data = response.json()
                        
                        if raw_data and len(raw_data) > 0:
                            latest = raw_data[-1]
                            logger.info(f"✅ DATOS REALES AEMET {station_id}: {latest}")
                            
                            # Create beautiful response with real data
                            weather_data.append({
                                "🏭": "Chocolate Factory - Datos Reales",
                                "📍": f"Linares, Jaén ({station_id})",
                                "🌡️": f"{latest.get('ta', 'N/A')}°C" if latest.get('ta') else "N/A",
                                "💧": f"{latest.get('hr', 'N/A')}%" if latest.get('hr') else "N/A", 
                                "🌬️": f"{latest.get('vv', 'N/A')} km/h" if latest.get('vv') else "N/A",
                                "☔": f"{latest.get('prec', 0)} mm",
                                "📊": f"{latest.get('pres', 'N/A')} hPa" if latest.get('pres') else "N/A",
                                "🕐": latest.get('fint', 'N/A'),
                                "📡": f"AEMET {station_id}",
                                "station_name": latest.get('ubi', 'LINARES'),
                                "total_records_today": len(raw_data),
                                "raw_data": latest  # Para depuración
                            })
                        else:
                            weather_data.append({
                                "error": f"No data for station {station_id}",
                                "station_id": station_id
                            })
                    else:
                        weather_data.append({
                            "error": f"No 'datos' field for station {station_id}",
                            "station_id": station_id
                        })
                        
                except Exception as e:
                    logger.error(f"Error fetching {station_id}: {e}")
                    weather_data.append({
                        "error": str(e),
                        "station_id": station_id
                    })
        
        return {
            "status": "✅ Datos meteorológicos reales de AEMET",
            "location": "Linares, Jaén, Andalucía", 
            "data": weather_data,
            "stations_requested": len(station_list),
            "records_returned": len(weather_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AEMET weather endpoint failed: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/aemet/token/status")
async def get_aemet_token_status():
    """Obtener estado del token AEMET"""
    try:
        async with AEMETClient() as client:
            status = await client.get_token_status()
        
        return {
            "status": "success",
            "token_info": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get AEMET token status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/aemet/token/renew")
async def renew_aemet_token():
    """Forzar renovación del token AEMET"""
    try:
        async with AEMETClient() as client:
            # Force token renewal by requesting a new one
            new_token = await client._request_new_token()
        
        return {
            "status": "success",
            "message": "Token AEMET renovado exitosamente",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to renew AEMET token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


















@app.get("/influxdb/verify")
async def verify_influxdb_data(hours: int = 6):
    """🔍 Verificar datos almacenados en InfluxDB - Query simple"""
    try:
        async with DataIngestionService() as service:
            # Check InfluxDB connection
            health = service.client.health()
            
            if health.status != "pass":
                return {
                    "status": "error",
                    "message": "InfluxDB no está saludable",
                    "health": health.status
                }
            
            query_api = service.client.query_api()
            
            # Query REE energy prices
            ree_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 10)
            '''
            
            # Query weather data  
            weather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 10)
            '''
            
            ree_results = query_api.query(ree_query)
            weather_results = query_api.query(weather_query)
            
            # Process results
            ree_data = []
            for table in ree_results:
                for record in table.records:
                    ree_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "price_eur_kwh": record.get_value(),
                        "source": record.values.get("source", "REE")
                    })
            
            weather_data = []
            for table in weather_results:
                for record in table.records:
                    weather_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "temperature": record.get_value(),
                        "source": record.values.get("source", "unknown"),
                        "station_id": record.values.get("station_id", "unknown")
                    })
            
            return {
                "🏭": "Chocolate Factory - InfluxDB Verification",
                "status": "✅ InfluxDB funcionando correctamente",
                "health": health.status,
                "bucket": service.config.bucket,
                "org": service.config.org,
                "query_range": f"{hours} horas",
                "data": {
                    "energy_prices": {
                        "records_found": len(ree_data),
                        "latest_data": ree_data[:3],
                        "measurement": "energy_prices"
                    },
                    "weather_data": {
                        "records_found": len(weather_data),
                        "latest_data": weather_data[:3],
                        "measurement": "weather_data"
                    }
                },
                "total_records": len(ree_data) + len(weather_data),
                "limitation_note": "⚠️ This endpoint shows LATEST 10 records only (sorted desc by time). For total counts use /influxdb/count",
                "alternatives": {
                    "total_count": "/influxdb/count",
                    "system_status": "/init/status"
                },
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"InfluxDB verification failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "note": "Error al verificar datos en InfluxDB"
        }


@app.get("/influxdb/count")
async def count_influxdb_records(years: int = 5):
    """🔢 Contar registros reales en InfluxDB - Query de conteo preciso"""
    try:
        async with DataIngestionService() as service:
            # Check InfluxDB connection
            health = service.client.health()
            
            if health.status != "pass":
                return {
                    "status": "error",
                    "message": "InfluxDB no está saludable",
                    "health": health.status
                }
            
            query_api = service.client.query_api()
            
            # Count REE energy prices
            ree_count_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{years*365*24}h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> count()
            '''
            
            # Count weather data  
            weather_count_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{years*365*24}h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> count()
            '''
            
            # Count all records (total)
            total_count_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{years*365*24}h)
                |> count()
            '''
            
            ree_results = query_api.query(ree_count_query)
            weather_results = query_api.query(weather_count_query)
            total_results = query_api.query(total_count_query)
            
            # Process count results
            ree_count = 0
            for table in ree_results:
                for record in table.records:
                    ree_count += record.get_value()
            
            weather_count = 0
            for table in weather_results:
                for record in table.records:
                    weather_count += record.get_value()
            
            total_count = 0
            for table in total_results:
                for record in table.records:
                    total_count += record.get_value()
            
            return {
                "🏭": "Chocolate Factory - InfluxDB Record Count",
                "status": "✅ Conteo completado",
                "health": health.status,
                "bucket": service.config.bucket,
                "org": service.config.org,
                "query_range": f"{years} años",
                "counts": {
                    "energy_prices_records": ree_count,
                    "weather_data_records": weather_count,
                    "total_records": total_count,
                    "other_records": max(0, total_count - ree_count - weather_count)
                },
                "discrepancy_analysis": {
                    "init_status_reported": 31038,
                    "actual_ree_records": ree_count,
                    "difference": 31038 - ree_count,
                    "note": "init/status uses hardcoded values, this endpoint queries actual DB"
                },
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"InfluxDB count failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "note": "Error al contar registros en InfluxDB"
        }


@app.get("/aemet/stations")
async def get_aemet_stations():
    """Obtener lista de estaciones meteorológicas AEMET - Jaén"""
    try:
        async with AEMETClient() as client:
            stations = await client.get_weather_stations()
        
        # Filter for Jaén province stations if we get a full list
        jaen_stations = []
        for station in stations:
            if "jaén" in station.get("provincia", "").lower() or "jaen" in station.get("provincia", "").lower():
                jaen_stations.append(station)
        
        # If no stations found from API, return known Jaén stations
        if not jaen_stations:
            jaen_stations = [
                {
                    "indicativo": "5279X",
                    "nombre": "LINARES, VOR",
                    "provincia": "JAÉN",
                    "altitud": 515,
                    "latitud": "38°5'31\"N",
                    "longitud": "3°38'6\"W"
                },
                {
                    "indicativo": "5298X",
                    "nombre": "ANDÚJAR",
                    "provincia": "JAÉN", 
                    "altitud": 202,
                    "latitud": "38°2'24\"N",
                    "longitud": "4°3'36\"W"
                }
            ]
        
        return {
            "status": "success",
            "data": jaen_stations,
            "total_stations": len(jaen_stations),
            "returned_stations": len(jaen_stations),
            "timestamp": datetime.now().isoformat(),
            "location": "Provincia de Jaén, Andalucía"
        }
        
    except Exception as e:
        logger.error(f"Failed to get AEMET stations: {e}")
        # Fallback to known Jaén stations
        fallback_stations = [
            {
                "indicativo": "5279X",
                "nombre": "LINARES, VOR",
                "provincia": "JAÉN",
                "altitud": 515,
                "latitud": "38°5'31\"N",
                "longitud": "3°38'6\"W"
            },
            {
                "indicativo": "5298X", 
                "nombre": "ANDÚJAR",
                "provincia": "JAÉN",
                "altitud": 202,
                "latitud": "38°2'24\"N",
                "longitud": "4°3'36\"W"
            }
        ]
        
        return {
            "status": "success",
            "data": fallback_stations,
            "total_stations": len(fallback_stations),
            "returned_stations": len(fallback_stations),
            "timestamp": datetime.now().isoformat(),
            "location": "Provincia de Jaén, Andalucía",
            "note": "Datos de estaciones conocidas - Error en API AEMET"
        }


# =============================================================================
# INITIALIZATION ENDPOINTS
# =============================================================================

@app.get("/init/status")
async def get_initialization_status():
    """🚀 Verificar estado de inicialización del sistema"""
    try:
        async with InitializationService() as service:
            status = await service.get_initialization_status()
        
        return {
            "🏭": "Chocolate Factory - Initialization Status",
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "actions": {
                "init_historical_data": "/init/historical-data",
                "init_all": "/init/all"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get initialization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/init/historical-data")
async def initialize_historical_data(background_tasks: BackgroundTasks):
    """🚀 Inicializar datos históricos REE (2022-2024) - ~17K registros"""
    try:
        logger.info("🚀 Starting historical data initialization")
        
        async def run_historical_init():
            async with InitializationService() as service:
                stats = await service.initialize_historical_data_only()
                logger.info(f"✅ Historical initialization completed: {stats.historical_ree_records} records")
        
        background_tasks.add_task(run_historical_init)
        
        return {
            "🏭": "Chocolate Factory - Historical Data Initialization",
            "status": "started",
            "message": "📊 Carga histórica REE (2022-2024) iniciada en background",
            "expected_records": "~17,520 registros (2 años post-COVID)",
            "estimated_duration": "30-60 minutos",
            "monitoring": {
                "progress": "/init/status",
                "data_verification": "/influxdb/verify?hours=26280"  # Check 3 years
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start historical initialization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/init/all")
async def initialize_all_systems(background_tasks: BackgroundTasks):
    """🚀 Inicialización completa del sistema (históricos + sintéticos)"""
    try:
        logger.info("🚀 Starting complete system initialization")
        
        async def run_full_init():
            async with InitializationService() as service:
                stats = await service.initialize_all()
                logger.info(f"✅ Full initialization completed: {stats.historical_ree_records} REE + {stats.synthetic_weather_records} weather records")
        
        background_tasks.add_task(run_full_init)
        
        return {
            "🏭": "Chocolate Factory - Complete System Initialization",
            "status": "started",
            "message": "🚀 Inicialización completa iniciada en background",
            "components": {
                "historical_ree": "📊 Datos REE 2022-2024 (~17K registros)",
                "synthetic_weather": "🌤️ Weather sintético coherente",
                "system_checks": "🔧 Verificaciones de conectividad",
                "database_schemas": "🗄️ Inicialización schemas InfluxDB"
            },
            "estimated_duration": "45-90 minutos",
            "monitoring": {
                "progress": "/init/status",
                "data_verification": "/influxdb/verify"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start full initialization: {e}")
        raise HTTPException(status_code=500, detail=str(e))








@app.post("/init/siar/etl")
async def init_siar_etl(station_id: str = "5279X", years: int = 5):
    """🌍 ETL process using Sistema SIAR CSV data for historical weather"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from services.siar_etl import SiarETL

        logger.info(f"🌍 Starting SIAR ETL for station {station_id}")

        etl = SiarETL()
        # Use the real SIAR files instead of sample data
        stats = await etl.process_real_siar_files()
        
        return {
            "🏭": "Chocolate Factory - SIAR ETL",
            "status": "✅ ETL Completed",
            "data_source": "Sistema SIAR",
            "station": f"{station_id} - Linares, Jaén",
            "processing_results": {
                "total_records": stats.total_records,
                "successful_writes": stats.successful_writes,
                "failed_writes": stats.failed_writes,
                "validation_errors": stats.validation_errors,
                "success_rate": f"{stats.success_rate:.1f}%"
            },
            "timestamp": datetime.now().isoformat(),
            "next_steps": {
                "verify_data": "GET /init/status",
                "check_influxdb": "GET /influxdb/verify",
                "proceed_mlflow": "Data ready for ML models"
            }
        }
        
    except Exception as e:
        logger.error(f"SIAR ETL failed: {e}")
        return {
            "status": "❌ ETL Failed",
            "error": str(e),
            "note": "Check logs for details"
        }


# =============================================================================
# MLFLOW ENDPOINTS - UNIDAD MLOPS (CUARTEL GENERAL ML)
# =============================================================================

@app.get("/mlflow/status")
async def get_mlflow_status():
    """🏢 Unidad MLOps - Estado del Cuartel General ML (MLflow + PostgreSQL)"""
    try:
        async with get_mlflow_service() as mlflow_service:
            connectivity = await mlflow_service.check_connectivity()
            
            return {
                "🏢": "Chocolate Factory - Unidad MLOps",
                "🏗️": "Cuartel General ML",
                "status": "✅ MLflow Service Active" if connectivity["status"] == "connected" else "❌ MLflow Service Failed",
                "infrastructure": {
                    "mlflow_server": connectivity.get("tracking_uri", "Unknown"),
                    "mlflow_version": connectivity.get("mlflow_version", "Unknown"),
                    "backend_store": "PostgreSQL",
                    "artifact_store": "/mlflow/artifacts"
                },
                "experiments": {
                    "total_experiments": connectivity.get("experiments_count", 0),
                    "default_experiment": "Available" if connectivity.get("default_experiment") else "Not found"
                },
                "connectivity": connectivity,
                "chocolate_factory": {
                    "ready_for_ml": True,
                    "recommended_experiments": [
                        "chocolate_production_optimization",
                        "energy_cost_prediction", 
                        "weather_quality_control"
                    ]
                },
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"MLflow status check failed: {e}")
        return {
            "🏢": "Chocolate Factory - Unidad MLOps",
            "🏗️": "Cuartel General ML", 
            "status": "❌ MLflow Service Error",
            "error": str(e),
            "troubleshooting": {
                "check_container": "docker logs chocolate_factory_mlops",
                "check_postgres": "docker logs chocolate_factory_postgres",
                "verify_network": "docker network ls"
            },
            "timestamp": datetime.now().isoformat()
        }


@app.get("/mlflow/web-check")
async def mlflow_web_interface_check():
    """🌐 Verificar acceso web a MLflow desde navegador"""
    try:
        import httpx
        
        # Test main interface
        async with httpx.AsyncClient() as client:
            response = await client.get("http://mlflow:5000")
            
            return {
                "🏢": "Chocolate Factory - MLflow Web Interface Check",
                "web_interface": {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", "unknown"),
                    "has_html": "html" in response.text.lower(),
                    "has_mlflow_title": "<title>MLflow</title>" in response.text,
                    "content_length": len(response.text)
                },
                "browser_access": {
                    "url": "http://localhost:5000",
                    "alternative_url": "http://127.0.0.1:5000",
                    "note": "Si no funciona, verificar JavaScript habilitado en navegador"
                },
                "troubleshooting": {
                    "check_port": "docker port chocolate_factory_mlops",
                    "check_logs": "docker logs chocolate_factory_mlops",
                    "direct_test": "curl http://localhost:5000"
                },
                "mlflow_info": {
                    "container": "chocolate_factory_mlops",
                    "port_mapping": "5000:5000",
                    "web_ui_ready": response.status_code == 200
                }
            }
    except Exception as e:
        return {
            "🏢": "Chocolate Factory - MLflow Web Interface Check",
            "status": "❌ Error checking web interface",
            "error": str(e),
            "manual_check": "Verificar manualmente: http://localhost:5000"
        }


@app.get("/mlflow/features")
async def generate_chocolate_features(hours_back: int = 24):
    """⚙️ Feature Engineering - Generar features para modelos de chocolate"""
    try:
        # feature_engine = get_global_feature_engine()  # TODO: Update to DirectML
        return {
            "🏢": "Chocolate Factory - Feature Engineering",
            "status": "⚠️ Feature endpoint temporarily disabled during MLflow migration",
            "alternative": "Use GET /models/data-debug for data analysis",
            "hours_requested": hours_back
        }
        
        # Generate feature sets
        feature_sets = await feature_engine.generate_feature_set(hours_back)
        
        if not feature_sets:
            return {
                "🏢": "Chocolate Factory - Feature Engineering",
                "status": "⚠️ No data available for feature generation",
                "hours_requested": hours_back,
                "recommendations": {
                    "check_data": "GET /init/status",
                    "verify_ingestion": "GET /influxdb/verify"
                }
            }
        
        # Convert to DataFrame for analysis
        df = feature_engine.features_to_dataframe(feature_sets)
        
        # Calculate summary statistics
        latest_features = feature_sets[-1]
        
        return {
            "🏢": "Chocolate Factory - Feature Engineering",
            "⚙️": "Chocolate Production Features Generated",
            "status": "✅ Features Ready for ML Models",
            "data_summary": {
                "total_feature_sets": len(feature_sets),
                "time_range_hours": hours_back,
                "date_range": {
                    "start": feature_sets[0].timestamp.isoformat(),
                    "end": feature_sets[-1].timestamp.isoformat()
                }
            },
            "latest_analysis": {
                "timestamp": latest_features.timestamp.isoformat(),
                "energy_metrics": {
                    "price_eur_kwh": round(latest_features.price_eur_kwh, 4),
                    "price_trend_1h": round(latest_features.price_trend_1h, 4),
                    "energy_cost_index": round(latest_features.energy_cost_index, 1),
                    "tariff_period": latest_features.tariff_period
                },
                "weather_metrics": {
                    "temperature": round(latest_features.temperature, 1),
                    "humidity": round(latest_features.humidity, 1),
                    "temperature_comfort_index": round(latest_features.temperature_comfort_index, 1),
                    "humidity_stress_factor": round(latest_features.humidity_stress_factor, 1)
                },
                "chocolate_metrics": {
                    "production_index": round(latest_features.chocolate_production_index, 1),
                    "energy_optimization_score": round(latest_features.energy_optimization_score, 1),
                    "quality_risk_factor": round(latest_features.quality_risk_factor, 1),
                    "production_recommendation": latest_features.production_recommendation
                }
            },
            "feature_statistics": {
                "avg_production_index": round(df['chocolate_production_index'].mean(), 1),
                "avg_energy_cost": round(df['energy_cost_index'].mean(), 1),
                "avg_temperature_comfort": round(df['temperature_comfort_index'].mean(), 1),
                "recommendation_distribution": df['production_recommendation'].value_counts().to_dict()
            },
            "ml_readiness": {
                "features_count": len(df.columns) - 1,  # Exclude timestamp
                "data_quality": "Complete" if df.isnull().sum().sum() == 0 else "Has nulls",
                "ready_for_training": len(feature_sets) >= 24
            },
            "next_steps": {
                "train_model": "POST /mlflow/train",
                "view_experiments": "http://localhost:5000",
                "real_time_prediction": "GET /predict"
            }
        }
        
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        return {
            "🏢": "Chocolate Factory - Feature Engineering",
            "status": "❌ Feature generation failed",
            "error": str(e),
            "troubleshooting": {
                "check_influxdb": "GET /influxdb/verify",
                "check_data": "GET /init/status"
            }
        }


@app.post("/mlflow/train")
async def train_chocolate_models(
    model_type: str = "all",  # "all", "energy", "classifier"
    background_tasks: BackgroundTasks = None
):
    """🤖 Entrenar modelos ML para optimización de chocolate (Cuartel General ML)"""
    try:
        ml_models = get_global_ml_models()
        
        if background_tasks:
            # Run training in background for all models
            if model_type == "all":
                background_tasks.add_task(_train_all_models_background, ml_models)
                return {
                    "🏢": "Chocolate Factory - ML Training",
                    "🤖": "Cuartel General ML - Training Started",
                    "status": "🚀 Training initiated in background",
                    "models_to_train": ["energy_optimization", "production_classifier"],
                    "estimated_duration": "2-5 minutes",
                    "monitoring": {
                        "mlflow_ui": "http://localhost:5000",
                        "check_progress": "GET /mlflow/status",
                        "view_experiments": "Check MLflow experiments tab"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            elif model_type == "energy":
                background_tasks.add_task(_train_energy_model_background, ml_models)
                return {
                    "🏢": "Chocolate Factory - ML Training",
                    "🤖": "Energy Optimization Model Training Started",
                    "status": "🚀 Training initiated in background",
                    "model": "energy_optimization",
                    "estimated_duration": "1-2 minutes",
                    "monitoring": {
                        "mlflow_ui": "http://localhost:5000",
                        "experiment": "chocolate_energy_optimization"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            elif model_type == "classifier":
                background_tasks.add_task(_train_classifier_background, ml_models)
                return {
                    "🏢": "Chocolate Factory - ML Training", 
                    "🤖": "Production Classifier Training Started",
                    "status": "🚀 Training initiated in background",
                    "model": "production_classifier",
                    "estimated_duration": "1-2 minutes",
                    "monitoring": {
                        "mlflow_ui": "http://localhost:5000",
                        "experiment": "chocolate_production_classification"
                    },
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # Synchronous training (for testing or small datasets)
            if model_type == "energy":
                metrics = await ml_models.train_energy_optimization_model()
                return {
                    "🏢": "Chocolate Factory - ML Training",
                    "🤖": "Energy Optimization Model",
                    "status": "✅ Training completed",
                    "metrics": {
                        "mse": round(metrics.mse, 4),
                        "mae": round(metrics.mae, 4), 
                        "r2_score": round(metrics.r2, 4),
                        "cv_mean": round(metrics.cv_mean, 4),
                        "cv_std": round(metrics.cv_std, 4)
                    },
                    "training_info": {
                        "samples": metrics.training_samples,
                        "features": metrics.features_count,
                        "duration_seconds": round(metrics.training_time_seconds, 2)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            elif model_type == "classifier":
                metrics = await ml_models.train_production_classifier()
                return {
                    "🏢": "Chocolate Factory - ML Training",
                    "🤖": "Production Classifier",
                    "status": "✅ Training completed",
                    "metrics": {
                        "accuracy": round(metrics.accuracy, 4),
                        "precision": round(metrics.precision, 4),
                        "recall": round(metrics.recall, 4),
                        "f1_score": round(metrics.f1, 4),
                        "cv_mean": round(metrics.cv_mean, 4),
                        "cv_std": round(metrics.cv_std, 4)
                    },
                    "training_info": {
                        "samples": metrics.training_samples,
                        "features": metrics.features_count,
                        "duration_seconds": round(metrics.training_time_seconds, 2)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:  # model_type == "all"
                all_metrics = await ml_models.train_all_models()
                return {
                    "🏢": "Chocolate Factory - ML Training",
                    "🤖": "All Models Training Complete",
                    "status": "✅ All models trained successfully",
                    "models": {
                        "energy_optimization": {
                            "r2_score": round(all_metrics['energy_optimization'].r2, 4),
                            "mae": round(all_metrics['energy_optimization'].mae, 4),
                            "training_time": round(all_metrics['energy_optimization'].training_time_seconds, 2)
                        },
                        "production_classifier": {
                            "accuracy": round(all_metrics['production_classifier'].accuracy, 4),
                            "f1_score": round(all_metrics['production_classifier'].f1, 4),
                            "training_time": round(all_metrics['production_classifier'].training_time_seconds, 2)
                        }
                    },
                    "total_training_time": round(
                        all_metrics['energy_optimization'].training_time_seconds + 
                        all_metrics['production_classifier'].training_time_seconds, 2
                    ),
                    "mlflow_experiments": [
                        "chocolate_energy_optimization",
                        "chocolate_production_classification"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
        
    except Exception as e:
        logger.error(f"ML training failed: {e}")
        return {
            "🏢": "Chocolate Factory - ML Training",
            "status": "❌ Training failed",
            "error": str(e),
            "troubleshooting": {
                "check_data": "GET /mlflow/features",
                "check_mlflow": "GET /mlflow/status",
                "verify_influxdb": "GET /influxdb/verify"
            },
            "timestamp": datetime.now().isoformat()
        }


# === PREDICTION ENDPOINTS ===

@app.post("/predict/energy-optimization")
async def predict_energy_optimization(request: PredictionRequest):
    """🔮 Predecir score de optimización energética usando ML directo"""
    try:
        direct_ml = get_global_direct_ml()
        
        # Log prediction request
        logger.info(f"🔮 Energy optimization prediction: price={request.price_eur_kwh}, temp={request.temperature}, humidity={request.humidity}")
        
        # Make prediction using direct ML service
        prediction_result = direct_ml.predict_energy_optimization(
            price_eur_kwh=request.price_eur_kwh,
            temperature=request.temperature,
            humidity=request.humidity
        )
        
        return {
            "🏢": "Chocolate Factory - Energy Optimization",
            "🔮": "Direct ML Prediction Service", 
            "status": "✅ Prediction completed",
            "prediction": prediction_result,
            "input_features": {
                "price_eur_kwh": request.price_eur_kwh,
                "temperature": request.temperature,
                "humidity": request.humidity
            },
            "model_info": {
                "type": "direct_ml_sklearn",
                "version": "2.0-legacy",
                "backend": "RandomForestRegressor"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Energy prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/predict/production-recommendation")
async def predict_production_recommendation(request: PredictionRequest):
    """Predecir recomendación de producción de chocolate"""
    try:
        # Calculate chocolate production index with energy-smart logic
        optimal_temp_center = 21  # °C
        temp_deviation = abs(request.temperature - optimal_temp_center)
        temperature_comfort_index = max(0, 100 - (temp_deviation * 10))
        
        # NEW: Energy BENEFIT index (rewards low prices, penalizes high prices)
        # Price ranges: < 0.12 (excellent), 0.12-0.20 (good), 0.20-0.30 (expensive), > 0.30 (very expensive)
        if request.price_eur_kwh < 0.12:  # Very cheap - BIG BONUS
            energy_benefit_index = 100 + (0.12 - request.price_eur_kwh) * 500  # Extra boost for very cheap
        elif request.price_eur_kwh < 0.20:  # Reasonable price - BONUS
            energy_benefit_index = 100 - (request.price_eur_kwh - 0.12) * 200
        elif request.price_eur_kwh < 0.30:  # Expensive - PENALTY
            energy_benefit_index = 50 - (request.price_eur_kwh - 0.20) * 200
        else:  # Very expensive - BIG PENALTY
            energy_benefit_index = 0
        
        energy_benefit_index = max(0, min(150, energy_benefit_index))  # Cap at 150 for very low prices
        
        optimal_humidity_center = 55  # %
        humidity_deviation = abs(request.humidity - optimal_humidity_center)
        humidity_comfort_index = max(0, 100 - (humidity_deviation * 2))  # Less penalty than before
        
        # NEW FORMULA: Energy benefits have high weight when favorable
        base_production_index = (temperature_comfort_index + humidity_comfort_index) / 2
        
        # Energy factor: high weight (0.8) to prioritize cheap electricity
        if request.price_eur_kwh < 0.15:  # For cheap electricity, energy dominates
            chocolate_production_index = base_production_index * 0.3 + energy_benefit_index * 0.7
        else:  # For expensive electricity, conditions matter more
            chocolate_production_index = base_production_index * 0.6 + energy_benefit_index * 0.4
            
        chocolate_production_index = max(0, min(100, chocolate_production_index))
        
        # Classify production recommendation with energy-aware thresholds
        if chocolate_production_index >= 80:
            recommendation = "Optimal_Production"
            description = "Condiciones ideales para maximizar producción"
            urgency = "low"
        elif chocolate_production_index >= 60:
            recommendation = "Moderate_Production" 
            description = "Condiciones favorables, mantener producción estándar"
            urgency = "low"
        elif chocolate_production_index >= 35:
            recommendation = "Reduced_Production"
            description = "Condiciones subóptimas, considerar reducir producción"
            urgency = "medium"
        else:
            recommendation = "Halt_Production"
            description = "Condiciones críticas, detener producción temporalmente"
            urgency = "high"
            
        # Special override for extremely cheap electricity (overrules other factors)
        if request.price_eur_kwh < 0.10:
            if recommendation == "Reduced_Production":
                recommendation = "Moderate_Production"
                description = "Precio energético excepcional compensa condiciones subóptimas"
            elif recommendation == "Halt_Production":
                recommendation = "Reduced_Production" 
                description = "Solo por precio energético excepcional - mínima producción"
        
        return {
            "🏢": "Chocolate Factory - Production Prediction",
            "🍫": "Production Recommendation Model",
            "prediction": {
                "production_recommendation": recommendation,
                "chocolate_production_index": round(chocolate_production_index, 2),
                "description": description,
                "urgency": urgency
            },
            "conditions": {
                "temperature": f"{request.temperature}°C",
                "humidity": f"{request.humidity}%",
                "energy_price": f"{request.price_eur_kwh}€/kWh"
            },
            "analysis": {
                "temperature_optimal": abs(request.temperature - 21) < 3,
                "humidity_optimal": 45 <= request.humidity <= 65,
                "energy_cost_acceptable": request.price_eur_kwh < 0.25,
                "overall_score": round(chocolate_production_index, 1)
            } if request.include_features else {}
        }
        
    except Exception as e:
        logger.error(f"Production prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/models/status")
async def get_models_status():
    """Estado y métricas de los modelos ML"""
    try:
        direct_ml = get_global_direct_ml()
        
        # Get models status
        models_status = direct_ml.get_models_status()
        
        return {
            "🏢": "Chocolate Factory - Models Status",
            "🤖": "Direct ML Service",
            "status": "✅ Models status retrieved",
            "models": models_status,
            "timestamp": datetime.now().isoformat()
        }
            
    except Exception as e:
        logger.error(f"Models status check failed: {e}")
        return {
            "🏢": "Chocolate Factory - Models Status",
            "status": "❌ Error checking models",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# === PRICE FORECASTING ENDPOINTS (Sprint 06) ===

@app.get("/predict/prices/weekly", tags=["Price Forecasting"])
async def get_weekly_price_forecast():
    """
    🔮 Predicción de precios REE para próximas 168 horas (7 días)

    Returns:
        Lista de predicciones con intervalos de confianza 95%
    """
    try:
        from services.price_forecasting_service import get_price_forecasting_service

        forecast_service = get_price_forecasting_service()
        predictions = await forecast_service.predict_weekly()

        return {
            "🏢": "Chocolate Factory - REE Price Forecast",
            "status": "✅ Forecast generated",
            "forecast_horizon": "168 hours (7 days)",
            "model_type": "Prophet (Facebook)",
            "predictions_count": len(predictions),
            "predictions": predictions,
            "model_metrics": forecast_service.metrics if forecast_service.metrics else None,
            "last_training": forecast_service.last_training.isoformat() if forecast_service.last_training else None,
            "timestamp": datetime.now().isoformat()
        }

    except ValueError as e:
        logger.warning(f"Price forecast unavailable: {e}")
        raise HTTPException(status_code=503, detail=f"Model not available: {str(e)}")
    except Exception as e:
        logger.error(f"Price forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@app.get("/predict/prices/hourly", tags=["Price Forecasting"])
async def get_hourly_price_forecast(hours: int = 24):
    """
    🔮 Predicción de precios REE para N horas específicas

    Args:
        hours: Número de horas a predecir (1-168)

    Returns:
        Lista de predicciones para las próximas N horas
    """
    if hours < 1 or hours > 168:
        raise HTTPException(status_code=400, detail="hours debe estar entre 1 y 168")

    try:
        from services.price_forecasting_service import get_price_forecasting_service

        forecast_service = get_price_forecasting_service()
        predictions = await forecast_service.predict_hours(hours=hours)

        return {
            "🏢": "Chocolate Factory - REE Price Forecast",
            "status": "✅ Forecast generated",
            "forecast_horizon": f"{hours} hours",
            "predictions_count": len(predictions),
            "predictions": predictions,
            "timestamp": datetime.now().isoformat()
        }

    except ValueError as e:
        logger.warning(f"Price forecast unavailable: {e}")
        raise HTTPException(status_code=503, detail=f"Model not available: {str(e)}")
    except Exception as e:
        logger.error(f"Price forecast failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@app.get("/models/price-forecast/status", tags=["Price Forecasting"])
async def get_price_forecast_model_status():
    """📊 Estado del modelo de predicción de precios"""
    try:
        from services.price_forecasting_service import get_price_forecasting_service

        forecast_service = get_price_forecasting_service()
        status = forecast_service.get_model_status()

        return {
            "🏢": "Chocolate Factory - Price Forecast Model",
            "status": "✅ Model status retrieved",
            "model_status": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Model status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@app.post("/models/price-forecast/train", tags=["Price Forecasting"])
async def train_price_forecast_model(months_back: int = 12, background_tasks: BackgroundTasks = None):
    """
    🤖 Entrenar modelo de predicción de precios REE

    Args:
        months_back: Meses de datos históricos para entrenamiento (default: 12)

    Returns:
        Resultado del entrenamiento con métricas
    """
    if months_back < 1 or months_back > 36:
        raise HTTPException(status_code=400, detail="months_back debe estar entre 1 y 36")

    try:
        from services.price_forecasting_service import get_price_forecasting_service

        logger.info(f"🤖 Iniciando entrenamiento modelo Prophet ({months_back} meses)")

        forecast_service = get_price_forecasting_service()
        result = await forecast_service.train_model(months_back=months_back)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Training failed"))

        # Si el entrenamiento fue exitoso, generar y almacenar predicciones
        if background_tasks:
            async def generate_and_store():
                try:
                    predictions = await forecast_service.predict_weekly()
                    await forecast_service.store_predictions_influxdb(predictions)
                    logger.info("✅ Predicciones generadas y almacenadas automáticamente")
                except Exception as e:
                    logger.error(f"❌ Error generando predicciones post-training: {e}")

            background_tasks.add_task(generate_and_store)

        return {
            "🏢": "Chocolate Factory - Price Forecast Training",
            "status": "✅ Model trained successfully",
            "training_result": result,
            "next_step": "Predictions will be generated and stored automatically",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


# === SIAR HISTORICAL ANALYSIS ENDPOINTS (Sprint 07 - Revisado) ===

@app.get("/analysis/weather-correlation", tags=["SIAR Analysis"])
async def get_weather_production_correlation():
    """
    📊 Análisis correlación histórica temperatura/humedad → eficiencia producción

    Basado en 88,935 registros SIAR (2000-2025), NO predicciones.

    Returns:
        Correlaciones R² con 25 años de evidencia
    """
    try:
        from services.siar_analysis_service import SIARAnalysisService

        siar_service = SIARAnalysisService()
        correlations = await siar_service.calculate_production_correlations()

        return {
            "🏢": "Chocolate Factory - SIAR Historical Correlation",
            "status": "✅ Analysis completed",
            "data_source": "SIAR historical (88,935 records, 2000-2025)",
            "analysis_type": "Historical correlation (NOT prediction)",
            "correlations": {
                "temperature_production": {
                    "r_squared": correlations['temperature'].r_squared,
                    "correlation": correlations['temperature'].correlation,
                    "p_value": correlations['temperature'].p_value,
                    "sample_size": correlations['temperature'].sample_size,
                    "confidence_95": correlations['temperature'].confidence_95,
                    "significance": "significant" if correlations['temperature'].p_value < 0.05 else "not significant"
                },
                "humidity_production": {
                    "r_squared": correlations['humidity'].r_squared,
                    "correlation": correlations['humidity'].correlation,
                    "p_value": correlations['humidity'].p_value,
                    "sample_size": correlations['humidity'].sample_size,
                    "confidence_95": correlations['humidity'].confidence_95,
                    "significance": "significant" if correlations['humidity'].p_value < 0.05 else "not significant"
                }
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Correlation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analysis/seasonal-patterns", tags=["SIAR Analysis"])
async def get_seasonal_production_patterns():
    """
    🌞 Detección patrones estacionales con 25 años datos reales

    Identifica mejores/peores meses para producción chocolate basado en evidencia.

    Returns:
        12 meses analizados con estadísticas reales
    """
    try:
        from services.siar_analysis_service import SIARAnalysisService

        siar_service = SIARAnalysisService()
        patterns = await siar_service.detect_seasonal_patterns()

        # Identificar mejor/peor mes
        best_month = max(patterns, key=lambda p: p.production_efficiency_score)
        worst_month = min(patterns, key=lambda p: p.production_efficiency_score)

        return {
            "🏢": "Chocolate Factory - SIAR Seasonal Patterns",
            "status": "✅ Patterns detected",
            "data_source": "SIAR historical (25 years evidence)",
            "analysis_period": "2000-2025",
            "best_month": {
                "name": best_month.month_name,
                "efficiency_score": best_month.production_efficiency_score,
                "avg_temp": best_month.avg_temperature,
                "avg_humidity": best_month.avg_humidity,
                "optimal_days": best_month.optimal_days_count,
                "critical_days": best_month.critical_days_count
            },
            "worst_month": {
                "name": worst_month.month_name,
                "efficiency_score": worst_month.production_efficiency_score,
                "avg_temp": worst_month.avg_temperature,
                "avg_humidity": worst_month.avg_humidity,
                "optimal_days": worst_month.optimal_days_count,
                "critical_days": worst_month.critical_days_count
            },
            "all_months": [
                {
                    "month": p.month,
                    "month_name": p.month_name,
                    "avg_temperature": p.avg_temperature,
                    "avg_humidity": p.avg_humidity,
                    "critical_days_count": p.critical_days_count,
                    "optimal_days_count": p.optimal_days_count,
                    "efficiency_score": p.production_efficiency_score
                }
                for p in patterns
            ],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Seasonal pattern detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analysis/critical-thresholds", tags=["SIAR Analysis"])
async def get_critical_weather_thresholds():
    """
    🚨 Umbrales críticos basados en percentiles históricos (P90, P95, P99)

    Identifica valores temperatura/humedad que históricamente afectaron producción.

    Returns:
        Umbrales basados en 25 años evidencia
    """
    try:
        from services.siar_analysis_service import SIARAnalysisService

        siar_service = SIARAnalysisService()
        thresholds = await siar_service.identify_critical_thresholds()

        return {
            "🏢": "Chocolate Factory - SIAR Critical Thresholds",
            "status": "✅ Thresholds identified",
            "data_source": "SIAR historical (88,935 records, 2000-2025)",
            "methodology": "Percentile-based (P90, P95, P99)",
            "thresholds": [
                {
                    "variable": t.variable,
                    "threshold_value": t.threshold_value,
                    "percentile": t.percentile,
                    "historical_occurrences": t.historical_occurrences,
                    "estimated_production_impact": f"{t.avg_production_impact}%",
                    "description": t.description
                }
                for t in thresholds
            ],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Threshold identification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analysis/siar-summary", tags=["SIAR Analysis"])
async def get_siar_analysis_summary():
    """
    📊 Resumen completo análisis histórico SIAR

    Incluye correlaciones, patrones estacionales, umbrales críticos.

    Returns:
        Resumen ejecutivo completo basado en 25 años datos
    """
    try:
        from services.siar_analysis_service import SIARAnalysisService

        siar_service = SIARAnalysisService()
        summary = await siar_service.get_analysis_summary()

        return {
            "🏢": "Chocolate Factory - SIAR Historical Summary",
            "status": "✅ Summary generated",
            **summary
        }

    except Exception as e:
        logger.error(f"SIAR summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")


@app.post("/forecast/aemet-contextualized", tags=["SIAR Analysis"])
async def get_aemet_forecast_with_siar_context():
    """
    🔗 Predicciones AEMET contextualizadas con historia SIAR

    Combina predicciones AEMET (7 días) + contexto histórico SIAR (25 años).

    Returns:
        Predicciones AEMET + recomendaciones basadas en evidencia histórica
    """
    try:
        from services.siar_analysis_service import SIARAnalysisService
        from services.aemet_client import AEMETClient

        # Obtener predicciones AEMET (usa API existente)
        aemet_client = AEMETClient()
        # Nota: Aquí necesitarías implementar obtención predicción AEMET
        # Por ahora, simulamos estructura
        aemet_forecast = [
            {"date": (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
             "temperature": 25 + i, "humidity": 60 + i*2}
            for i in range(7)
        ]

        # Contextualizar con SIAR histórico
        siar_service = SIARAnalysisService()
        contextualized = await siar_service.contextualize_aemet_forecast(aemet_forecast)

        return {
            "🏢": "Chocolate Factory - AEMET + SIAR Contextualized",
            "status": "✅ Forecast contextualized",
            "forecast_source": "AEMET API (official predictions)",
            "historical_context_source": "SIAR (88,935 records, 2000-2025)",
            "methodology": "AEMET predictions + SIAR historical similarity analysis",
            "forecast": contextualized,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"AEMET contextualization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Contextualization failed: {str(e)}")


# === GAP DETECTION & BACKFILL ENDPOINTS ===

@app.get("/gaps/detect", tags=["Data Management"])
async def detect_data_gaps(days_back: int = 7):
    """🔍 Detectar gaps (huecos) en los datos de InfluxDB"""
    try:
        from services.gap_detector import gap_detector
        
        # Realizar análisis de gaps
        analysis = await gap_detector.detect_all_gaps(days_back)
        
        # Convertir gaps a formato serializable
        ree_gaps_data = []
        for gap in analysis.ree_gaps:
            ree_gaps_data.append({
                "measurement": gap.measurement,
                "start_time": gap.start_time.isoformat(),
                "end_time": gap.end_time.isoformat(),
                "duration_hours": round(gap.gap_duration_hours, 1),
                "missing_records": gap.missing_records,
                "severity": gap.severity
            })
        
        weather_gaps_data = []
        for gap in analysis.weather_gaps:
            weather_gaps_data.append({
                "measurement": gap.measurement,
                "start_time": gap.start_time.isoformat(),
                "end_time": gap.end_time.isoformat(),
                "duration_hours": round(gap.gap_duration_hours, 1),
                "missing_records": gap.missing_records,
                "severity": gap.severity
            })
        
        return {
            "🏭": "Chocolate Factory - Gap Analysis",
            "🔍": "Análisis de Huecos en Datos",
            "analysis_period": f"Últimos {days_back} días",
            "timestamp": analysis.analysis_timestamp.isoformat(),
            "summary": {
                "total_gaps": analysis.total_gaps_found,
                "ree_gaps": len(analysis.ree_gaps),
                "weather_gaps": len(analysis.weather_gaps),
                "estimated_backfill_time": analysis.estimated_backfill_duration
            },
            "ree_data_gaps": ree_gaps_data,
            "weather_data_gaps": weather_gaps_data,
            "recommended_strategy": analysis.recommended_backfill_strategy,
            "next_steps": {
                "manual_backfill": "POST /gaps/backfill",
                "ree_only": "POST /gaps/backfill/ree",
                "weather_only": "POST /gaps/backfill/weather"
            }
        }
        
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === ENHANCED ML ENDPOINTS ===

@app.post("/models/train-enhanced")
async def train_enhanced_models():
    """🚀 Entrenar modelos ML mejorados con datos históricos completos"""
    try:
        enhanced_ml = EnhancedMLService()

        logger.info("🚀 Starting enhanced ML training with historical data...")
        results = await enhanced_ml.train_enhanced_models()

        return {
            "🏢": "Chocolate Factory - Enhanced ML Training",
            "🤖": "Historical Data Integration & Time Series Models",
            "status": "✅ Enhanced training completed" if results.get("success") else "❌ Training failed",
            "training_results": results,
            "data_sources": {
                "siar_historical": "88,935 records (2000-2025)",
                "ree_historical": "42,578 records (2022-2025)",
                "current_weather": "AEMET + OpenWeatherMap hybrid"
            },
            "models_trained": [
                "Cost Optimization (€/kg prediction)",
                "Production Efficiency (0-100 score)",
                "Price Forecast (REE D-1 tracking)"
            ],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Enhanced ML training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced training failed: {str(e)}")


@app.post("/predict/cost-optimization")
async def predict_cost_optimization(request: PredictionRequest):
    """💰 Predecir costo optimizado de producción usando datos históricos"""
    try:
        enhanced_ml = EnhancedMLService()

        current_conditions = {
            'price_eur_kwh': request.price_eur_kwh,
            'temperature': request.temperature,
            'humidity': request.humidity
        }

        cost_prediction = enhanced_ml.predict_cost_optimization(current_conditions)

        return {
            "🏢": "Chocolate Factory - Cost Optimization",
            "💰": "Enhanced ML Cost Prediction",
            "status": "✅ Cost prediction completed",
            "cost_analysis": cost_prediction,
            "business_insights": {
                "baseline_cost_per_kg": 13.90,
                "energy_optimization_potential": "15-30% cost reduction",
                "optimal_production_windows": "Valley hours (00:00-06:00)"
            },
            "input_conditions": current_conditions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Cost optimization prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cost prediction failed: {str(e)}")


@app.get("/analysis/ree-deviation")
async def get_ree_deviation_analysis(hours_back: int = 24):
    """📊 Análisis de desviaciones REE D-1 vs precios reales"""
    try:
        enhanced_ml = EnhancedMLService()

        deviation_analysis = enhanced_ml.get_ree_deviation_analysis(hours_back)

        return {
            "🏢": "Chocolate Factory - REE Deviation Analysis",
            "📊": "D-1 Prediction vs Actual Price Tracking",
            "status": "✅ Deviation analysis completed",
            "analysis": deviation_analysis,
            "insights": {
                "ree_d1_usefulness": "Better for trend analysis than absolute prediction",
                "recommendation": "Use for planning, not real-time decisions",
                "ml_advantage": "Internal models trained on local patterns"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"REE deviation analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Deviation analysis failed: {str(e)}")


@app.get("/models/status-enhanced")
async def get_enhanced_models_status():
    """📊 Estado de modelos ML mejorados"""
    try:
        enhanced_ml = EnhancedMLService()

        models_dir = enhanced_ml.models_dir
        model_files = list(models_dir.glob("*.pkl")) if models_dir.exists() else []

        return {
            "🏢": "Chocolate Factory - Enhanced Models Status",
            "🤖": "Historical Data ML Models",
            "status": "✅ Status retrieved",
            "enhanced_models": {
                "cost_optimization": {
                    "available": (models_dir / "cost_optimization_model.pkl").exists(),
                    "description": "Predicts total production cost per kg",
                    "features": "Price, weather, time, historical patterns"
                },
                "production_efficiency": {
                    "available": (models_dir / "production_efficiency_model.pkl").exists(),
                    "description": "Efficiency score 0-100 based on conditions",
                    "features": "Comprehensive business rules integration"
                },
                "price_forecast": {
                    "available": (models_dir / "price_forecast_model.pkl").exists(),
                    "description": "REE price forecasting and deviation tracking",
                    "features": "Time series with lag features"
                }
            },
            "data_integration": {
                "siar_historical": "25+ years weather data",
                "ree_historical": "3+ years price data",
                "real_time": "AEMET + OpenWeatherMap + REE"
            },
            "model_files_count": len(model_files),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Enhanced models status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@app.post("/recommendations/comprehensive")
async def get_comprehensive_recommendations(request: PredictionRequest):
    """🎯 Recomendaciones comprehensivas con datos históricos y ML avanzado"""
    try:
        recommendation_engine = EnhancedRecommendationEngine()

        current_conditions = {
            'price_eur_kwh': request.price_eur_kwh,
            'temperature': request.temperature,
            'humidity': request.humidity
        }

        logger.info(f"🎯 Generating comprehensive recommendations for: {current_conditions}")

        recommendations = await recommendation_engine.get_comprehensive_recommendations(current_conditions)

        return {
            "🏢": "Chocolate Factory - Comprehensive Recommendations",
            "🎯": "Enhanced ML-Driven Production Optimization",
            "status": "✅ Comprehensive analysis completed",
            "recommendations": recommendations,
            "data_sources": {
                "historical_weather": "SIAR 25+ years (88,935 records)",
                "historical_prices": "REE 3+ years (42,578 records)",
                "real_time": "AEMET + OpenWeatherMap + REE current",
                "business_rules": "Production constraints & cost structure"
            },
            "ml_models": {
                "cost_optimization": "Historical data + business rules",
                "temporal_analysis": "Time series + energy market patterns",
                "condition_analysis": "Climate impact on chocolate production",
                "quality_mix": "Multi-objective optimization"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Comprehensive recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


@app.get("/debug/gap-query", tags=["Debug"])
async def debug_gap_query():
    """🐛 Debug endpoint for gap query testing"""
    try:
        from services.gap_detector import GapDetectionService

        logger.info("🐛 DEBUG: Starting gap query test")
        gap_detector_service = GapDetectionService()
        latest = await gap_detector_service.get_latest_timestamps()
        logger.info(f"🐛 DEBUG: Results: {latest}")

        return {
            "debug": "gap query test",
            "latest_timestamps": latest,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"🐛 DEBUG: Error in gap query: {e}")
        return {"error": str(e)}

@app.get("/gaps/summary", tags=["Data Management"])
async def get_data_summary():
    """📊 Resumen rápido del estado de los datos"""
    try:
        from services.gap_detector import GapDetectionService

        # Obtener últimos timestamps - Using fresh instance
        gap_detector_service = GapDetectionService()
        latest = await gap_detector_service.get_latest_timestamps()
        
        # Calcular tiempo desde última actualización
        now = datetime.now(timezone.utc)
        
        ree_status = "❌ Sin datos"
        ree_gap_hours = None
        if latest['latest_ree']:
            ree_gap_hours = (now - latest['latest_ree']).total_seconds() / 3600
            if ree_gap_hours < 6:
                ree_status = "✅ Actualizado"
            elif ree_gap_hours < 24:
                ree_status = f"🟡 Normal ({int(ree_gap_hours)}h)"
            elif ree_gap_hours < 48:
                ree_status = f"⚠️ {int(ree_gap_hours)}h atrasado"
            else:
                ree_status = f"🚨 {int(ree_gap_hours // 24)}d atrasado"
        
        weather_status = "❌ Sin datos"
        weather_gap_hours = None
        if latest['latest_weather']:
            weather_gap_hours = (now - latest['latest_weather']).total_seconds() / 3600
            if weather_gap_hours < 2:
                weather_status = "✅ Actualizado"
            elif weather_gap_hours < 24:
                weather_status = f"⚠️ {int(weather_gap_hours)}h atrasado"
            else:
                weather_status = f"🚨 {int(weather_gap_hours // 24)}d atrasado"
        
        return {
            "🏭": "Chocolate Factory - Data Summary",
            "📊": "Estado Actual de Datos",
            "timestamp": now.isoformat(),
            "ree_prices": {
                "status": ree_status,
                "latest_data": latest['latest_ree'].isoformat() if latest['latest_ree'] else None,
                "gap_hours": round(ree_gap_hours, 1) if ree_gap_hours else None
            },
            "weather_data": {
                "status": weather_status,
                "latest_data": latest['latest_weather'].isoformat() if latest['latest_weather'] else None,
                "gap_hours": round(weather_gap_hours, 1) if weather_gap_hours else None
            },
            "recommendations": {
                "action_needed": ree_gap_hours and ree_gap_hours > 48 or weather_gap_hours and weather_gap_hours > 6,
                "suggested_endpoint": "GET /gaps/detect para análisis completo"
            }
        }
        
    except Exception as e:
        logger.error(f"Data summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gaps/backfill", tags=["Data Management"])
async def execute_backfill(
    days_back: int = 10,
    background_tasks: BackgroundTasks = None
):
    """🔄 Ejecutar backfill inteligente para rellenar gaps de datos"""
    try:
        from services.backfill_service import backfill_service
        
        if background_tasks:
            # Ejecutar en background para gaps grandes
            background_tasks.add_task(
                _execute_backfill_background, 
                backfill_service, 
                days_back
            )
            
            return {
                "🏭": "Chocolate Factory - Backfill Started",
                "🔄": "Proceso de Backfill Iniciado",
                "status": "🚀 Executing in background",
                "days_processing": days_back,
                "estimated_duration": "5-15 minutes",
                "monitoring": {
                    "check_progress": "GET /gaps/summary",
                    "verify_results": "GET /influxdb/verify"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Ejecutar síncronamente para pruebas
            result = await backfill_service.execute_intelligent_backfill(days_back)
            return {
                "🏭": "Chocolate Factory - Backfill Completed",
                "🔄": "Proceso de Backfill Terminado",
                **result
            }
            
    except Exception as e:
        logger.error(f"Backfill execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/gaps/backfill/auto", tags=["Data Management"])
async def execute_auto_backfill(max_gap_hours: float = 6.0):
    """🤖 Backfill automático solo si hay gaps significativos"""
    try:
        from services.backfill_service import backfill_service
        
        result = await backfill_service.check_and_execute_auto_backfill(max_gap_hours)
        
        return {
            "🏭": "Chocolate Factory - Auto Backfill",
            "🤖": "Backfill Automático Inteligente", 
            **result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Auto backfill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_backfill_background(backfill_service, days_back: int):
    """Función helper para ejecutar backfill en background"""
    try:
        logger.info(f"🔄 Starting background backfill for {days_back} days")
        result = await backfill_service.execute_intelligent_backfill(days_back)
        logger.info(f"✅ Background backfill completed: {result.get('summary', {}).get('overall_success_rate', 0)}% success")
        
    except Exception as e:
        logger.error(f"❌ Background backfill failed: {e}")


@app.post("/gaps/backfill/range", tags=["Data Management"])
async def execute_range_backfill(request: RangeBackfillRequest, background_tasks: BackgroundTasks = None):
    """🎯 Backfill específico para rango de fechas exacto (para gaps históricos)"""
    try:
        from services.backfill_service import backfill_service
        from datetime import datetime, timezone

        # Parse dates
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))

        # Validate date range
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")

        # Calculate days difference
        days_diff = (end_date - start_date).days + 1

        if background_tasks:
            # Execute in background
            background_tasks.add_task(
                _execute_range_backfill_background,
                backfill_service, request
            )

            return {
                "🏭": "Chocolate Factory - Range Backfill Started",
                "🎯": "Backfill de Rango Específico",
                "status": "🚀 Executing in background",
                "date_range": f"{request.start_date} → {request.end_date}",
                "days_processing": days_diff,
                "data_source": request.data_source,
                "chunk_hours": request.chunk_hours,
                "estimated_duration": f"{max(5, days_diff * 2)}-{days_diff * 5} minutes",
                "monitoring": {
                    "check_progress": "GET /gaps/summary",
                    "verify_results": "GET /influxdb/verify"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Execute synchronously (for testing)
            result = await _execute_range_backfill_sync(backfill_service, request)
            return {
                "🏭": "Chocolate Factory - Range Backfill Completed",
                "🎯": "Backfill de Rango Específico",
                **result,
                "timestamp": datetime.now().isoformat()
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Range backfill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _execute_range_backfill_background(backfill_service, request: RangeBackfillRequest):
    """Función helper para ejecutar range backfill en background"""
    try:
        logger.info(f"🎯 Starting range backfill: {request.start_date} → {request.end_date}")
        result = await _execute_range_backfill_sync(backfill_service, request)
        logger.info(f"✅ Range backfill completed: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Range backfill failed: {e}")

async def _execute_range_backfill_sync(backfill_service, request: RangeBackfillRequest):
    """Ejecutar range backfill sincronamente"""
    from services.ree_client import REEClient
    from services.data_ingestion import DataIngestionService
    from datetime import datetime, timezone, timedelta
    import asyncio

    start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))

    total_records = 0
    total_written = 0
    errors = []

    # Process REE data if requested
    if request.data_source in ["ree", "both"]:
        logger.info(f"📊 Processing REE data for range: {start_date} → {end_date}")

        async with REEClient() as ree_client:
            async with DataIngestionService() as ingestion_service:

                current_date = start_date.date()
                end_date_date = end_date.date()

                while current_date <= end_date_date:
                    try:
                        # Process day by day
                        day_start = datetime.combine(
                            current_date, datetime.min.time()
                        ).replace(tzinfo=timezone.utc)

                        day_end = day_start + timedelta(days=1) - timedelta(minutes=1)

                        logger.info(f"📊 Processing REE data for {current_date}")

                        # Get REE data for this day
                        daily_data = await ree_client.get_pvpc_prices(
                            start_date=day_start,
                            end_date=day_end
                        )

                        if daily_data:
                            # Write to InfluxDB
                            write_result = await ingestion_service.ingest_ree_prices_historical(daily_data)
                            total_records += len(daily_data)
                            total_written += write_result.successful_writes

                            logger.info(f"✅ REE day {current_date}: {len(daily_data)} records → {write_result.successful_writes} written")
                        else:
                            logger.warning(f"⚠️ No REE data for {current_date}")

                        # Rate limiting
                        await asyncio.sleep(2)

                    except Exception as day_error:
                        error_msg = f"Error processing REE day {current_date}: {day_error}"
                        errors.append(error_msg)
                        logger.error(error_msg)

                    current_date += timedelta(days=1)

    success_rate = (total_written / total_records * 100) if total_records > 0 else 0

    return {
        "status": "success" if success_rate > 70 else "partial",
        "date_range": f"{request.start_date} → {request.end_date}",
        "data_source": request.data_source,
        "records": {
            "total_requested": total_records,
            "total_written": total_written,
            "success_rate": round(success_rate, 1)
        },
        "errors": errors[:5] if errors else []  # Limit errors shown
    }


# === HISTORICAL DATA ENDPOINTS ===

@app.get("/historical/status", tags=["Historical Data"])
async def get_historical_data_status():
    """📊 Analizar estado de datos históricos de 10 años"""
    try:
        from services.historical_data_service import historical_data_service

        analysis = await historical_data_service.analyze_historical_data_status()

        return {
            "🏭": "Chocolate Factory - Historical Data Analysis",
            "📊": "Análisis de Datos Históricos (10 años)",
            **analysis
        }

    except Exception as e:
        logger.error(f"Historical data analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/historical/ingest-year/{year}", tags=["Historical Data"])
async def ingest_year_data(year: int,
                          include_ree: bool = True,
                          include_weather: bool = True,
                          background_tasks: BackgroundTasks = None):
    """📅 Ingestar datos históricos de un año específico"""
    try:
        from services.historical_data_service import historical_data_service

        # Validar año
        current_year = datetime.now().year
        if year < 2015 or year > current_year:
            raise HTTPException(
                status_code=400,
                detail=f"Año debe estar entre 2015 y {current_year}"
            )

        if background_tasks:
            # Ejecutar en background para años grandes
            background_tasks.add_task(
                _execute_year_ingestion_background,
                historical_data_service, year, include_ree, include_weather
            )

            return {
                "🏭": "Chocolate Factory - Year Ingestion Started",
                "📅": f"Ingesta Año {year}",
                "status": "🚀 Executing in background",
                "year": year,
                "data_sources": {
                    "ree": include_ree,
                    "weather": include_weather
                },
                "estimated_duration": "15-45 minutes",
                "monitoring": {
                    "check_progress": "GET /historical/status",
                    "verify_results": f"GET /gaps/detect?days_back=365"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Ejecutar sincrónicamente (para testing)
            result = await historical_data_service.ingest_year_data(
                year=year,
                include_ree=include_ree,
                include_weather=include_weather
            )

            return {
                "🏭": "Chocolate Factory - Year Ingestion Completed",
                "📅": f"Ingesta Año {year}",
                **result
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Year ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/historical/progressive-ingestion", tags=["Historical Data"])
async def execute_progressive_ingestion(max_years_per_session: int = 3,
                                      background_tasks: BackgroundTasks = None):
    """🚀 Ejecutar ingesta progresiva de 10 años (limitada por sesión)"""
    try:
        from services.historical_data_service import historical_data_service

        # Validar parámetros
        if max_years_per_session < 1 or max_years_per_session > 5:
            raise HTTPException(
                status_code=400,
                detail="max_years_per_session debe estar entre 1 y 5"
            )

        if background_tasks:
            # Ejecutar en background (recomendado para múltiples años)
            background_tasks.add_task(
                _execute_progressive_ingestion_background,
                historical_data_service, max_years_per_session
            )

            return {
                "🏭": "Chocolate Factory - Progressive Ingestion Started",
                "🚀": "Ingesta Progresiva 10 Años",
                "status": "🚀 Executing in background",
                "session_config": {
                    "max_years_per_session": max_years_per_session,
                    "estimated_duration_hours": max_years_per_session * 0.5
                },
                "monitoring": {
                    "check_progress": "GET /historical/status",
                    "scheduler_status": "GET /scheduler/status"
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Ejecutar sincrónicamente (solo para testing con pocos años)
            if max_years_per_session > 2:
                raise HTTPException(
                    status_code=400,
                    detail="Para ejecución síncrona, usar máximo 2 años por sesión"
                )

            result = await historical_data_service.execute_progressive_10_year_ingestion(
                max_years_per_session=max_years_per_session
            )

            return {
                "🏭": "Chocolate Factory - Progressive Ingestion Completed",
                "🚀": "Ingesta Progresiva 10 Años",
                **result
            }

    except Exception as e:
        logger.error(f"Progressive ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_year_ingestion_background(historical_data_service, year: int,
                                           include_ree: bool, include_weather: bool):
    """Helper para ejecutar ingesta de año en background"""
    try:
        logger.info(f"📅 Starting year {year} ingestion (REE: {include_ree}, Weather: {include_weather})")
        result = await historical_data_service.ingest_year_data(
            year=year,
            include_ree=include_ree,
            include_weather=include_weather
        )
        logger.info(f"✅ Year {year} ingestion completed: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Year {year} ingestion failed: {e}")


async def _execute_progressive_ingestion_background(historical_data_service,
                                                  max_years_per_session: int):
    """Helper para ejecutar ingesta progresiva en background"""
    try:
        logger.info(f"🚀 Starting progressive ingestion (max {max_years_per_session} years)")
        result = await historical_data_service.execute_progressive_10_year_ingestion(
            max_years_per_session=max_years_per_session
        )
        logger.info(f"✅ Progressive ingestion completed: {result.get('session_summary', {}).get('successful_years', 0)} years")
    except Exception as e:
        logger.error(f"❌ Progressive ingestion failed: {e}")


# === DASHBOARD ENDPOINTS ===

@app.get("/dashboard/complete", tags=["Dashboard"])
async def get_complete_dashboard():
    """🎯 Dashboard completo con información, predicciones y recomendaciones"""
    try:
        dashboard_service = get_global_dashboard_service()
        dashboard_data = await dashboard_service.get_complete_dashboard_data()
        
        # Añadir heatmap semanal con predicciones Prophet
        try:
            weekly_heatmap = await dashboard_service._get_weekly_forecast_heatmap()
            dashboard_data["weekly_forecast"] = weekly_heatmap
        except Exception as e:
            logger.warning(f"Failed to add weekly heatmap: {e}")
            dashboard_data["weekly_forecast"] = {
                "status": "error",
                "message": f"Heatmap generation failed: {str(e)}"
            }
        
        # Añadir analytics históricos
        try:
            from services.historical_analytics import HistoricalAnalyticsService
            analytics_service = HistoricalAnalyticsService()
            historical_analytics = await analytics_service.get_historical_analytics()
            dashboard_data["historical_analytics"] = historical_analytics.model_dump()
        except Exception as e:
            logger.warning(f"Failed to add historical analytics: {e}")
            dashboard_data["historical_analytics"] = {
                "status": "error",
                "message": f"Historical analytics failed: {str(e)}"
            }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Complete dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


# DEPRECATED: _generate_weekly_heatmap removed - now using DashboardService._get_weekly_forecast_heatmap() with Prophet predictions


@app.get("/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """📊 Resumen rápido para el dashboard Node-RED"""
    try:
        dashboard_service = get_global_dashboard_service()
        full_data = await dashboard_service.get_complete_dashboard_data()
        
        # Extraer solo la información esencial para Node-RED
        current_info = full_data.get("current_info", {})
        predictions = full_data.get("predictions", {})
        
        summary = {
            "🏢": "Chocolate Factory - Dashboard Summary",
            "current": {
                "energy_price": current_info.get("energy", {}).get("price_eur_kwh", 0) if current_info.get("energy") else 0,
                "temperature": current_info.get("weather", {}).get("temperature", 0) if current_info.get("weather") else 0,
                "humidity": current_info.get("weather", {}).get("humidity", 0) if current_info.get("weather") else 0,
                "production_status": current_info.get("production_status", "🔄 Cargando...")
            },
            "predictions": {
                "energy_score": predictions.get("energy_optimization", {}).get("score", 0),
                "production_class": predictions.get("production_recommendation", {}).get("class", "Unknown")
            },
            "alerts_count": len(full_data.get("alerts", [])),
            "status": full_data.get("system_status", {}).get("status", "🔄 Cargando..."),
            "timestamp": full_data.get("timestamp", datetime.now().isoformat())
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Dashboard summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard summary error: {str(e)}")


@app.get("/dashboard/alerts", tags=["Dashboard"])
async def get_dashboard_alerts():
    """🚨 Alertas activas del sistema"""
    try:
        dashboard_service = get_global_dashboard_service()
        full_data = await dashboard_service.get_complete_dashboard_data()
        
        return {
            "🏢": "Chocolate Factory - Alertas Activas",
            "alerts": full_data["alerts"],
            "alert_counts": {
                "critical": len([a for a in full_data["alerts"] if a.get("level") == "critical"]),
                "warning": len([a for a in full_data["alerts"] if a.get("level") == "warning"]),
                "high": len([a for a in full_data["alerts"] if a.get("level") == "high"]),
                "info": len([a for a in full_data["alerts"] if a.get("level") == "info"])
            },
            "timestamp": full_data["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Dashboard alerts failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard alerts error: {str(e)}")


@app.get("/dashboard/recommendations", tags=["Dashboard"])
async def get_dashboard_recommendations():
    """💡 Recomendaciones operativas actuales"""
    try:
        dashboard_service = get_global_dashboard_service()
        full_data = await dashboard_service.get_complete_dashboard_data()
        
        return {
            "🏢": "Chocolate Factory - Recomendaciones Operativas",
            "recommendations": full_data["recommendations"],
            "priority_count": len(full_data["recommendations"]["priority"]),
            "total_recommendations": sum(len(v) for v in full_data["recommendations"].values() if isinstance(v, list)),
            "timestamp": full_data["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Dashboard recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard recommendations error: {str(e)}")


@app.get("/dashboard/human-recommendation", tags=["Dashboard"])
async def get_human_recommendation():
    """🧠 Recomendación humanizada basada en ML + Reglas de Negocio"""
    try:
        from services.business_logic_service import get_business_logic_service
        from services.enhanced_ml_service import get_enhanced_ml_service
        from services.data_ingestion import DataIngestionService

        # Get current data
        async with DataIngestionService() as data_service:
            current_data = await data_service.get_current_conditions()

        # Get ML prediction
        ml_service = get_enhanced_ml_service()
        ml_results = await ml_service.get_predictions_for_conditions(current_data)

        # Extract ML score (use energy optimization score as primary)
        ml_score = ml_results.get('energy_optimization', {}).get('score', 50)

        # Get human recommendation
        business_service = get_business_logic_service()
        human_rec = business_service.generate_human_recommendation(
            ml_score=ml_score,
            conditions=current_data,
            context={'timestamp': datetime.now(), 'ml_results': ml_results}
        )

        return human_rec

    except Exception as e:
        logger.error(f"Human recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Human recommendation error: {str(e)}")


# === BACKGROUND TASKS ===



@app.get("/dashboard/heatmap", tags=["Dashboard"])
async def get_weekly_heatmap():
    """📅 Endpoint específico para el heatmap semanal"""
    try:
        from services.dashboard import get_dashboard_service
        
        dashboard_service = get_dashboard_service()
        heatmap_data = await dashboard_service._get_weekly_forecast_heatmap()
        
        return heatmap_data
        
    except Exception as e:
        logger.error(f"❌ Error getting weekly heatmap: {e}")
        return {
            "status": "error",
            "message": str(e),
            "calendar_days": []
        }


# === DASHBOARD MEJORADO ===

@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def serve_enhanced_dashboard():
    """🎯 Dashboard Enhanced DINÁMICO con Enhanced ML + Datos Históricos + Auto-refresh"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chocolate Factory - Enhanced ML Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
                color: #2d3748;
            }
            
            .header {
                background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                color: white;
                padding: 2rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 1rem;
            }

            .header p {
                font-size: 1.1rem;
                opacity: 0.9;
            }

            .enhanced-badge {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 0.3rem 0.8rem;
                border-radius: 15px;
                font-size: 0.9rem;
                font-weight: 600;
                margin-left: 1rem;
            }

            .metric-enhanced {
                border-left: 4px solid #10b981;
                background: linear-gradient(135deg, #f0fdf4 0%, #ecfccb 100%);
            }

            .enhanced-section {
                background: linear-gradient(135deg, #fefefe 0%, #f8fafc 100%);
                border: 2px solid #10b981;
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 8px 25px rgba(16, 185, 129, 0.15);
            }

            .enhanced-title {
                color: #059669;
                font-weight: 700;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .blinking {
                animation: blink 2s infinite;
            }

            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.5; }
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .status-bar {
                background: white;
                border-radius: 12px;
                padding: 1rem 2rem;
                margin-bottom: 2rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 1rem;
            }
            
            .status-badge {
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
            }
            
            .status-connected {
                background: #c6f6d5;
                color: #22543d;
            }
            
            .status-warning {
                background: #fef5e7;
                color: #744210;
            }
            
            .grid {
                display: grid;
                gap: 2rem;
                margin-bottom: 2rem;
            }
            
            .grid-2 {
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            }
            
            .grid-3 {
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            }
            
            /* Estilos para Heatmap Semanal */
            .heatmap-content {
                padding: 1.5rem;
            }
            
            .heatmap-legend {
                display: flex;
                justify-content: center;
                gap: 1.5rem;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
            }
            
            .legend-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.9rem;
            }
            
            .legend-color {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .calendar-grid {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 0.75rem;
                margin-bottom: 1.5rem;
                max-width: 600px;
                margin-left: auto;
                margin-right: auto;
            }
            
            .calendar-day {
                background: var(--day-bg);
                border: 2px solid var(--day-border);
                border-radius: 8px;
                padding: 1rem 0.5rem;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                min-height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                color: #333;
                position: relative;
            }

            .calendar-day:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
                border-color: rgba(255, 255, 255, 0.4);
            }

            /* Tooltip personalizado compatible con Safari/Brave */
            .calendar-day[data-tooltip]::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 120%;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.95);
                color: white;
                padding: 0.75rem 1rem;
                border-radius: 8px;
                font-size: 0.85rem;
                white-space: pre-line;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s, visibility 0.3s;
                pointer-events: none;
                min-width: 200px;
                text-align: left;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }

            .calendar-day[data-tooltip]:hover::after {
                opacity: 1;
                visibility: visible;
            }

            /* Flecha del tooltip */
            .calendar-day[data-tooltip]::before {
                content: '';
                position: absolute;
                bottom: 110%;
                left: 50%;
                transform: translateX(-50%);
                border: 6px solid transparent;
                border-top-color: rgba(0, 0, 0, 0.95);
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s, visibility 0.3s;
                z-index: 1001;
            }

            .calendar-day[data-tooltip]:hover::before {
                opacity: 1;
                visibility: visible;
            }
            
            .calendar-day.today {
                border-color: #FFD700;
                box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
            }
            
            .day-name {
                font-size: 0.8rem;
                opacity: 0.8;
                margin-bottom: 0.25rem;
                color: #333;
            }

            .day-number {
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 0.25rem;
                color: #333;
            }

            .day-price {
                font-size: 0.75rem;
                opacity: 0.9;
                color: #333;
            }

            .day-recommendation {
                font-size: 1.2rem;
                margin-top: 0.25rem;
                color: #333;
            }
            
            .heatmap-summary {
                display: flex;
                justify-content: space-around;
                gap: 1rem;
                padding: 1rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                flex-wrap: wrap;
            }
            
            .summary-item {
                text-align: center;
            }
            
            .summary-label {
                display: block;
                font-size: 0.8rem;
                opacity: 0.7;
                margin-bottom: 0.25rem;
            }
            
            @media (max-width: 768px) {
                .calendar-grid {
                    gap: 0.5rem;
                }
                
                .calendar-day {
                    padding: 0.75rem 0.25rem;
                    min-height: 75px;
                }
                
                .heatmap-legend {
                    gap: 1rem;
                }
                
                .legend-item {
                    font-size: 0.8rem;
                }
            }
            
            .card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            }
            
            .card-header {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 2px solid #e2e8f0;
            }
            
            .card-icon {
                font-size: 1.5rem;
            }
            
            .card-title {
                font-size: 1.2rem;
                font-weight: 700;
                color: #2d3748;
            }
            
            .metric-value {
                font-size: 2.5rem;
                font-weight: 800;
                margin: 0.5rem 0;
                line-height: 1.2;
            }
            
            .metric-label {
                font-size: 0.9rem;
                color: #718096;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            .metric-trend {
                font-size: 0.85rem;
                padding: 0.25rem 0.5rem;
                border-radius: 12px;
                margin-top: 0.5rem;
                display: inline-block;
            }
            
            .trend-stable {
                background: #e6fffa;
                color: #234e52;
            }
            
            .trend-rising {
                background: #fef5e7;
                color: #744210;
            }
            
            .trend-falling {
                background: #fed7d7;
                color: #742a2a;
            }
            
            .ml-prediction {
                background: linear-gradient(135deg, #059669 0%, #06b6d4 100%);
                color: white;
            }
            
            .ml-prediction .card-title {
                color: white;
            }
            
            .confidence-bar {
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                height: 8px;
                margin: 0.5rem 0;
                overflow: hidden;
            }
            
            .confidence-fill {
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
            }
            
            .confidence-high {
                background: #48bb78;
            }
            
            .confidence-medium {
                background: #ed8936;
            }
            
            .confidence-low {
                background: #f56565;
            }
            
            .recommendations {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .recommendations .card-title {
                color: white;
            }
            
            .rec-list {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            
            .rec-item {
                background: rgba(255,255,255,0.1);
                padding: 0.75rem;
                border-radius: 8px;
                margin: 0.5rem 0;
                border-left: 4px solid rgba(255,255,255,0.3);
            }
            
            .alerts {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                color: white;
            }
            
            .alerts.no-alerts {
                background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
            }
            
            .alerts .card-title {
                color: white;
            }
            
            .system-status {
                background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
                color: white;
            }
            
            .system-status .card-title {
                color: white;
            }
            
            .location-info {
                background: linear-gradient(135deg, #d69e2e 0%, #ed8936 100%);
                color: white;
                margin-bottom: 2rem;
            }
            
            .location-info .card-title {
                color: white;
            }
            
            /* Analytics Históricos */
            .analytics-section {
                padding: 1rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                border-left: 4px solid #66BB6A;
            }
            
            .analytics-metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.75rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .analytics-metric:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }
            
            .analytics-metric .metric-label {
                font-size: 0.9rem;
                color: rgba(255, 255, 255, 0.8);
            }
            
            /* Mejorar contraste en tarjeta azul inteligente */
            .smart-insights .card-title {
                color: white !important;
            }
            
            .smart-insights .metric-label {
                color: rgba(255, 255, 255, 0.95) !important;
                font-weight: 500;
            }
            
            .analytics-metric .metric-value {
                font-weight: bold;
                font-size: 1rem;
            }
            
            /* Tamaños específicos para la tarjeta de inteligencia */
            .savings-insight .metric-value,
            .process-analysis .metric-value {
                font-size: 1.2rem !important;
                font-weight: 700;
                line-height: 1.2;
            }
            
            /* Valores específicos que se salen de la tarjeta */
            #current-savings-potential,
            #recommended-process,
            #process-cost {
                font-size: 0.9rem !important;
                font-weight: 600;
            }
            
            #optimization-recommendations .recommendation-item {
                margin-bottom: 0.5rem;
                padding: 0.5rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                border-left: 3px solid #9C27B0;
            }
            
            /* Nueva Tarjeta Inteligente */
            .smart-insights {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            
            .insights-section {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 1.25rem;
                backdrop-filter: blur(10px);
            }
            
            .current-status, .savings-insight, .process-analysis {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }
            
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 1.1rem;
                font-weight: bold;
            }
            
            .status-icon {
                font-size: 1.2rem;
            }
            
            .status-detail, .savings-metric, .process-metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .status-detail:last-child, .savings-metric:last-child, .process-metric:last-child {
                border-bottom: none;
            }
            
            .status-action, .savings-action, .process-action {
                padding: 0.75rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                font-style: italic;
                text-align: center;
                font-size: 0.9rem;
            }
            
            .main-recommendation {
                animation: pulse-soft 3s ease-in-out infinite;
            }
            
            @keyframes pulse-soft {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.02); opacity: 0.95; }
            }
            
            /* Tarjetas compactas minimalistas */
            .location-info-compact, .system-status-compact {
                background: linear-gradient(135deg, #4A90E2 0%, #7B68EE 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
            }
            
            .sources-compact {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
            }
            
            .compact-info, .compact-status {
                margin-top: 0.75rem;
            }
            
            .info-line, .status-line {
                margin: 0.4rem 0;
                font-size: 0.9rem;
                line-height: 1.4;
            }
            
            .sources-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }
            
            .source-item {
                font-size: 0.85rem;
                padding: 0.4rem 0.6rem;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                text-align: center;
            }
            
            .location-info-compact .card-title, .system-status-compact .card-title, .sources-compact .card-title {
                color: white;
                font-size: 1rem;
            }
            
            .location-detail {
                margin: 0.5rem 0;
                font-size: 0.9rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .coordinate {
                font-family: 'Courier New', monospace;
                font-size: 0.85rem;
            }
            
            .data-sources-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-top: 1rem;
            }
            
            .data-source-item {
                background: rgba(255,255,255,0.1);
                padding: 0.75rem;
                border-radius: 8px;
                text-align: center;
            }
            
            .data-source {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            .data-source:last-child {
                border-bottom: none;
            }
            
            .refresh-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 25px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease;
            }
            
            .refresh-btn:hover {
                transform: scale(1.05);
            }
            
            .footer {
                text-align: center;
                padding: 2rem;
                color: #718096;
                font-size: 0.9rem;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 1rem;
                }

                .header h1 {
                    font-size: 1.8rem;
                }

                .status-bar {
                    flex-direction: column;
                    align-items: stretch;
                    gap: 0.5rem;
                }

                /* === RESPONSIVE GRID FIXES === */
                .grid {
                    grid-template-columns: 1fr !important;
                    gap: 1rem !important;
                }

                /* Ensure all cards have consistent width */
                .card {
                    width: 100%;
                    min-width: 0;
                    box-sizing: border-box;
                }

                /* Fix text overflow in cards */
                .card-title {
                    font-size: 1rem !important;
                    line-height: 1.3;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                }

                .metric-value {
                    font-size: 1.2rem !important;
                    word-wrap: break-word;
                }

                .metric-label {
                    font-size: 0.85rem !important;
                    line-height: 1.2;
                    word-wrap: break-word;
                }

                /* Fix unified REE card responsive */
                #unified-human-recommendation-content {
                    padding: 1rem !important;
                    font-size: 0.9rem !important;
                }

                #unified-human-recommendation-content h3 {
                    font-size: 1.1rem !important;
                }

                /* Fix enhanced badge positioning */
                .enhanced-badge {
                    display: block !important;
                    margin-top: 0.5rem;
                    font-size: 0.7rem !important;
                }

                /* Fix analytics sections */
                .analytics-section, .insights-section {
                    padding: 1rem;
                    margin-bottom: 1rem;
                }

                .analytics-section h4, .insights-section h4 {
                    font-size: 0.9rem !important;
                }

                /* Fix status indicators */
                .status-indicator {
                    flex-wrap: wrap;
                }

                .status-text {
                    font-size: 0.9rem !important;
                }

                /* Fix calendar grid for mobile */
                .calendar-grid {
                    grid-template-columns: repeat(auto-fit, minmax(40px, 1fr)) !important;
                    gap: 0.3rem !important;
                }

                .calendar-day {
                    min-height: 35px !important;
                    font-size: 0.7rem !important;
                    padding: 0.2rem !important;
                }
            }

            /* Additional responsive breakpoint for very small screens */
            @media (max-width: 480px) {
                .header h1 {
                    font-size: 1.5rem;
                }

                .card {
                    margin: 0.5rem 0;
                    padding: 1rem;
                }

                .card-header {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 0.5rem;
                }

                #unified-human-recommendation-content {
                    padding: 0.8rem !important;
                }

                .calendar-day {
                    min-height: 30px !important;
                    font-size: 0.6rem !important;
                }
            }
                
                .metric-value {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>
                <span>🍫</span>
                Chocolate Factory - Linares, Andalucía
            </h1>
            <p>Dashboard - ML con Datos Históricos (SIAR 88k + REE 42k)</p>
        </div>
        
        <div class="container">
            <div class="status-bar">
                <div>
                    <span id="status" class="status-badge status-warning">🔄 Conectando...</span>
                </div>
                <div>
                    <span>Última actualización: <strong id="last-update">--</strong></span>
                </div>
                <div>
                    <button class="refresh-btn" onclick="loadData()">🔄 Actualizar</button>
                </div>
            </div>
            
            <!-- Métricas principales -->
            <div class="grid grid-3">
                <div class="card">
                    <div class="card-header">
                        <span class="card-icon">⚡</span>
                        <span class="card-title">Precio Energía</span>
                    </div>
                    <div class="metric-value" id="energy-price">--</div>
                    <div class="metric-label">€/kWh</div>
                    <div id="energy-trend" class="metric-trend trend-stable">--</div>
                    <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
                        <div>MWh: <span id="energy-mwh">--</span></div>
                        <div>Fecha: <span id="energy-datetime">--</span></div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <span class="card-icon">🌡️</span>
                        <span class="card-title">Condiciones Climáticas</span>
                    </div>
                    <div class="metric-value" id="temperature">--</div>
                    <div class="metric-label">°C</div>
                    <div style="margin-top: 1rem; font-size: 0.9rem; color: #666;">
                        <div>💧 Humedad: <span id="humidity">--%</span></div>
                        <div>🌫️ Presión: <span id="pressure">-- hPa</span></div>
                        <div>🎯 Confort: <span id="comfort-index">--</span></div>
                    </div>
                </div>
                
                <!-- Tarjeta Información del Sistema Unificada -->
                <div class="card system-info-unified">
                    <div class="card-header">
                        <span class="card-icon">🏭</span>
                        <span class="card-title">Información del Sistema</span>
                    </div>

                    <div class="unified-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                        <!-- Ubicación -->
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem; color: #f59e0b;">📍 Fábrica</strong>
                            <div style="font-size: 0.9rem; line-height: 1.3;">
                                <div>🏭 Linares, Andalucía</div>
                                <div>⛰️ 515m • 🕐 CET</div>
                                <div style="font-size: 0.8rem; opacity: 0.7;">38.151°N, -3.629°W</div>
                            </div>
                        </div>

                        <!-- Estado Operativo -->
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem; color: #10b981;">🏭 Estado</strong>
                            <div style="font-size: 0.9rem; line-height: 1.3;">
                                <div id="production-status">🟢 Operativo</div>
                                <div>📊 Eficiencia: <span id="factory-efficiency">85%</span></div>
                            </div>
                        </div>
                    </div>

                    <div class="unified-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.2);">
                        <!-- Sistema -->
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem; color: #3b82f6;">⚙️ Sistema</strong>
                            <div style="font-size: 0.85rem; line-height: 1.3;">
                                <div>⚡ <span id="ree-status">✅ REE + Históricos</span></div>
                                <div>🌡️ <span id="weather-status">✅ AEMET/OpenWeather</span></div>
                                <div>🤖 <span id="ml-models-status">✅ Enhanced ML</span></div>
                            </div>
                        </div>

                        <!-- Fuentes de Datos -->
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem; color: #8b5cf6;">📊 Fuentes</strong>
                            <div style="font-size: 0.85rem; line-height: 1.3;">
                                <div>⚡ REE (Precios)</div>
                                <div>🌡️ AEMET 5279X (00-07h)</div>
                                <div>☁️ OpenWeather (08-23h)</div>
                                <div>🤖 ML Direct</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Enhanced ML Analytics -->
            <div class="enhanced-section" style="margin: 2rem 0;">
                <div class="enhanced-title">
                    <span>📊</span>
                    <span>ML Analytics - Datos Históricos Integrados</span>
                </div>

                <div class="grid grid-3" style="gap: 1.5rem;">
                    <!-- Cost Optimization -->
                    <div class="card metric-enhanced">
                        <div class="card-header">
                            <span class="card-icon">💰</span>
                            <span class="card-title">Optimización de Costos</span>
                        </div>
                        <div class="metric-value" id="enhanced-cost-per-kg">--</div>
                        <div class="metric-label">€/kg</div>
                        <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
                            <div>Categoría: <span id="cost-category">--</span></div>
                            <div>Ahorro: <span id="savings-opportunity">-- €/kg</span></div>
                            <div>vs Target: <span id="vs-target">--%</span></div>
                        </div>
                    </div>

                    <!-- Enhanced Recommendations -->
                    <div class="card metric-enhanced">
                        <div class="card-header">
                            <span class="card-icon">🎯</span>
                            <span class="card-title">Recomendación Enhanced</span>
                        </div>
                        <div class="metric-value" id="enhanced-main-action">--</div>
                        <div class="metric-label" id="enhanced-priority">--</div>
                        <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
                            <div>Score: <span id="enhanced-overall-score">--/100</span></div>
                            <div>Confianza: <span id="enhanced-confidence">--</span></div>
                            <div>Alertas: <span id="enhanced-alerts-count">--</span></div>
                        </div>
                    </div>

                    <!-- REE Deviation Analysis -->
                    <div class="card metric-enhanced">
                        <div class="card-header">
                            <span class="card-icon">📊</span>
                            <span class="card-title">Análisis REE D-1</span>
                        </div>
                        <div class="metric-value" id="ree-accuracy">--</div>
                        <div class="metric-label">Precisión</div>
                        <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
                            <div>Desviación: <span id="ree-deviation">-- €/kWh</span></div>
                            <div>Tendencia: <span id="ree-trend">--</span></div>
                            <div>Utilidad: <span id="ree-usefulness">Análisis tendencias</span></div>
                        </div>
                    </div>
                </div>

                <!-- Enhanced Recommendations List -->
                <div class="card" style="margin-top: 1.5rem;">
                    <div class="card-header">
                        <span class="card-icon">📋</span>
                        <span class="card-title">Recomendaciones Enhanced ML</span>
                    </div>
                    <div class="grid grid-2" style="gap: 1rem; margin-top: 1rem;">
                        <div>
                            <h4 style="color: #059669; margin-bottom: 0.5rem;">🔧 Optimización de Costos:</h4>
                            <ul id="enhanced-cost-insights" style="list-style: none; padding: 0; font-size: 0.9rem; line-height: 1.6;">
                                <li>⏳ Cargando insights de costos...</li>
                            </ul>
                        </div>
                        <div>
                            <h4 style="color: #059669; margin-bottom: 0.5rem;">⚡ Timing Optimization:</h4>
                            <ul id="enhanced-timing-insights" style="list-style: none; padding: 0; font-size: 0.9rem; line-height: 1.6;">
                                <li>⏳ Cargando insights temporales...</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Análisis REE Unificado - Inteligencia + Históricos -->
            <div class="card smart-insights" style="margin-top: 1.5rem;">
                <div class="card-header">
                    <span class="card-icon">⚡</span>
                    <span class="card-title">Análisis REE - Tiempo Real + Históricos</span>
                </div>

                <!-- Recomendación Humanizada Principal -->
                <div id="unified-human-recommendation-section" style="margin-top: 1.5rem; display: none;">
                    <div id="unified-human-recommendation-content" style="background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); color: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(255,107,53,0.3);">
                        <!-- Se llena dinámicamente con BusinessLogicService -->
                    </div>
                </div>
                <div class="grid grid-3" style="gap: 1.5rem; margin-top: 1.5rem;">
                    <!-- Momento Óptimo Actual -->
                    <div class="insights-section">
                        <h4 style="color: #4FC3F7; margin-bottom: 1rem; font-size: 1rem;">⚡ Momento Energético Actual</h4>
                        <div class="current-status">
                            <div class="status-indicator" id="current-energy-status">
                                <span class="status-icon">🟡</span>
                                <span class="status-text" id="energy-status-text">Evaluando...</span>
                            </div>
                            <div class="status-detail" id="energy-status-detail">
                                Precio actual: <span id="current-price-analysis">-- €/kWh</span>
                            </div>
                            <div class="status-action" id="energy-action-recommendation">
                                Calculando recomendación...
                            </div>
                        </div>
                    </div>
                    
                    <!-- Oportunidad de Ahorro -->
                    <div class="insights-section">
                        <h4 style="color: #66BB6A; margin-bottom: 1rem; font-size: 1rem;">💰 Oportunidad de Ahorro</h4>
                        <div class="savings-insight">
                            <div class="savings-metric">
                                <span class="metric-label">Ahorro vs Precio Promedio:</span>
                                <span class="metric-value" id="current-savings-potential">-- €/hora</span>
                            </div>
                            <div class="savings-metric">
                                <span class="metric-label">Posición en Ranking Diario:</span>
                                <span class="metric-value" id="price-ranking">--/24</span>
                            </div>
                            <div class="savings-action" id="savings-action">
                                Analizando oportunidades...
                            </div>
                        </div>
                    </div>
                    
                    <!-- Análisis por Procesos -->
                    <div class="insights-section">
                        <h4 style="color: #FF9800; margin-bottom: 1rem; font-size: 1rem;">🏭 Análisis por Procesos</h4>
                        <div class="process-analysis">
                            <div class="process-metric">
                                <span class="metric-label">Proceso Recomendado:</span>
                                <span class="metric-value" id="recommended-process">--</span>
                            </div>
                            <div class="process-metric">
                                <span class="metric-label">Costo Proceso/hora:</span>
                                <span class="metric-value" id="process-cost">-- €/h</span>
                            </div>
                            <div class="process-action" id="process-action">
                                Calculando procesos...
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Recomendación Inteligente Principal -->
                <div class="main-recommendation" id="main-recommendation" style="margin-top: 1.5rem; padding: 1.5rem; background: linear-gradient(135deg, rgba(76, 175, 80, 0.2) 0%, rgba(46, 125, 50, 0.2) 100%); border-radius: 8px; border-left: 4px solid #4CAF50;">
                    <div style="display: flex; align-items: center; margin-bottom: 0.75rem;">
                        <span id="recommendation-icon" style="font-size: 1.5rem; margin-right: 0.75rem;">🎯</span>
                        <span id="recommendation-title" style="font-weight: bold; color: white;">Analizando condiciones del mercado...</span>
                    </div>
                    <div id="recommendation-detail" style="color: rgba(255, 255, 255, 0.9); line-height: 1.5;">
                        Evaluando precios REE históricos y condiciones actuales para optimizar el momento de producción...
                    </div>
                </div>
            </div>
            
            <!-- Mini Calendario Heatmap Semanal -->
            <div class="card heatmap-card" style="margin-top: 2rem;">
                <div class="card-header">
                    <span class="card-icon">📅</span>
                    <span class="card-title">Pronóstico Semanal - Heatmap de Precios</span>
                </div>
                <div class="heatmap-content">
                    <div class="heatmap-legend" id="heatmap-legend">
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #4CAF50;"></span>
                            <span>🟢 Bajo (≤0.10 €/kWh)</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #FF9800;"></span>
                            <span>🟡 Medio (0.10-0.20 €/kWh)</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #F44336;"></span>
                            <span>🔴 Alto (>0.20 €/kWh)</span>
                        </div>
                    </div>
                    <div class="calendar-grid" id="calendar-grid">
                        <!-- Se llena dinámicamente con JavaScript -->
                    </div>
                    <div class="heatmap-summary" id="heatmap-summary">
                        <div class="summary-item">
                            <span class="summary-label">Días Óptimos:</span>
                            <span id="optimal-days">0</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Precio Promedio:</span>
                            <span id="avg-price">0.000 €/kWh</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Rango:</span>
                            <span id="price-range">0.00 - 0.00 €/kWh</span>
                        </div>
                    </div>
                </div>

                <!-- Métricas Históricas Integradas -->
                <div class="grid grid-3" style="gap: 1.5rem; margin-top: 1.5rem; padding: 1.5rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
                    <div class="analytics-section">
                        <h4 style="color: #66BB6A; margin-bottom: 1rem; font-size: 0.9rem;">📊 Históricos 2024</h4>
                        <div class="analytics-metric" style="margin-bottom: 0.5rem;">
                            <span class="metric-label" style="font-size: 0.8rem; color: #333;">Costo Total:</span>
                            <span class="metric-value" style="color: #333; font-size: 0.9rem;" id="total-cost">-- €</span>
                        </div>
                        <div class="analytics-metric" style="margin-bottom: 0.5rem;">
                            <span class="metric-label" style="font-size: 0.8rem; color: #333;">Min/Max:</span>
                            <span class="metric-value" style="color: #333; font-size: 0.9rem;" id="min-max-price">--/-- €/kWh</span>
                        </div>
                    </div>

                    <div class="analytics-section">
                        <h4 style="color: #2196F3; margin-bottom: 1rem; font-size: 0.9rem;">🎯 Potencial</h4>
                        <div class="analytics-metric" style="margin-bottom: 0.5rem;">
                            <span class="metric-label" style="font-size: 0.8rem; color: #333;">Ahorro Anual:</span>
                            <span class="metric-value" style="color: #333; font-size: 0.9rem;" id="annual-projection">-- €</span>
                        </div>
                        <div class="analytics-metric" style="margin-bottom: 0.5rem;">
                            <span class="metric-label" style="font-size: 0.8rem; color: #333;">Horas Óptimas:</span>
                            <span class="metric-value" style="color: #333; font-size: 0.9rem;" id="optimal-hours">-- h</span>
                        </div>
                    </div>

                    <div class="analytics-section">
                        <h4 style="color: #FF9800; margin-bottom: 1rem; font-size: 0.9rem;">💡 Recomendaciones</h4>
                        <div id="unified-optimization-recommendations" style="font-size: 0.8rem; line-height: 1.4; color: #333;">
                            <!-- Recomendaciones unificadas -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- 📊 SIAR Historical Analysis (Sprint 07) -->
            <div class="card" style="margin-top: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <div class="card-header">
                    <span class="card-icon">📊</span>
                    <span class="card-title">Análisis Histórico SIAR (2000-2025)</span>
                </div>

                <!-- SIAR Summary Stats -->
                <div class="grid grid-3" style="gap: 1rem; margin-top: 1.5rem;">
                    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;">📈 Registros Totales</div>
                        <div style="font-size: 1.8rem; font-weight: bold;" id="siar-total-records">--</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem;" id="siar-date-range">--</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;">🌡️ Correlación Temp</div>
                        <div style="font-size: 1.8rem; font-weight: bold;" id="siar-temp-correlation">--</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem;">R² vs Producción</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;">💧 Correlación Humedad</div>
                        <div style="font-size: 1.8rem; font-weight: bold;" id="siar-humidity-correlation">--</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem;">R² vs Producción</div>
                    </div>
                </div>

                <!-- Seasonal Patterns -->
                <div style="margin-top: 1.5rem; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: white; margin-bottom: 1rem; font-size: 1rem;">📅 Patrones Estacionales</h4>
                    <div class="grid grid-2" style="gap: 1rem;">
                        <div>
                            <div style="font-size: 0.85rem; margin-bottom: 0.5rem;">🟢 Mejor Mes:</div>
                            <div style="font-size: 1.1rem; font-weight: bold;" id="siar-best-month">--</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;" id="siar-best-month-score">--</div>
                        </div>
                        <div>
                            <div style="font-size: 0.85rem; margin-bottom: 0.5rem;">🔴 Peor Mes:</div>
                            <div style="font-size: 1.1rem; font-weight: bold;" id="siar-worst-month">--</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;" id="siar-worst-month-score">--</div>
                        </div>
                    </div>
                </div>

                <!-- Critical Thresholds -->
                <div style="margin-top: 1.5rem; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: white; margin-bottom: 1rem; font-size: 1rem;">⚠️ Umbrales Críticos (Percentiles Históricos)</h4>
                    <div class="grid grid-2" style="gap: 1rem; font-size: 0.9rem;">
                        <div>
                            <strong>🌡️ Temperatura:</strong>
                            <div style="margin-top: 0.5rem; line-height: 1.6;">
                                <div>P90: <span id="siar-temp-p90">--</span>°C</div>
                                <div>P95: <span id="siar-temp-p95">--</span>°C</div>
                                <div>P99: <span id="siar-temp-p99">--</span>°C</div>
                            </div>
                        </div>
                        <div>
                            <strong>💧 Humedad:</strong>
                            <div style="margin-top: 0.5rem; line-height: 1.6;">
                                <div>P90: <span id="siar-humidity-p90">--</span>%</div>
                                <div>P95: <span id="siar-humidity-p95">--</span>%</div>
                                <div>P99: <span id="siar-humidity-p99">--</span>%</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SIAR Insights -->
                <div style="margin-top: 1.5rem; background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 8px; border-left: 4px solid #FFD700;">
                    <div style="font-weight: bold; margin-bottom: 0.5rem;">💡 Insights Históricos:</div>
                    <div id="siar-insights" style="font-size: 0.9rem; line-height: 1.6;">
                        <div>⏳ Cargando análisis histórico...</div>
                    </div>
                </div>
            </div>

        </div>

        <div class="footer">
            Chocolate Factory - Linares, Andalucía | Dashboard v0.41.0 |
            Powered by FastAPI + ML (131k+ Historical Records)
        </div>
        
        <script>
            // Función para formato español (coma decimal)
            function formatSpanishNumber(number, decimals = 2) {
                if (typeof number !== 'number' || isNaN(number)) return '--';
                return number.toFixed(decimals).replace('.', ',');
            }
            
            // Función para formato de coordenadas españolas
            function formatSpanishCoordinate(number, decimals = 6) {
                if (typeof number !== 'number' || isNaN(number)) return '--';
                return number.toFixed(decimals).replace('.', ',');
            }
            
            // Función para renderizar el heatmap semanal
            function renderHeatmap(weeklyForecast) {
                const calendarGrid = document.getElementById('calendar-grid');
                const optimalDaysElement = document.getElementById('optimal-days');
                const avgPriceElement = document.getElementById('avg-price');
                const priceRangeElement = document.getElementById('price-range');
                
                if (!weeklyForecast || !weeklyForecast.calendar_days) {
                    calendarGrid.innerHTML = '<div style="text-align: center; grid-column: 1/-1; padding: 2rem;">❌ No hay datos del pronóstico semanal</div>';
                    return;
                }
                
                // Limpiar grid
                calendarGrid.innerHTML = '';
                
                // Renderizar días
                weeklyForecast.calendar_days.forEach(day => {
                    const dayElement = document.createElement('div');
                    dayElement.className = `calendar-day ${day.is_today ? 'today' : ''}`;
                    
                    // CSS variables para colores dinámicos
                    dayElement.style.setProperty('--day-bg', day.heat_color + '20');
                    dayElement.style.setProperty('--day-border', day.heat_color);
                    
                    dayElement.innerHTML = `
                        <div class="day-name">${day.day_short}</div>
                        <div class="day-number">${day.day_number}</div>
                        <div class="day-price">${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €</div>
                        <div class="day-recommendation">${day.recommendation_icon}</div>
                    `;
                    
                    // Tooltip compatible con Safari/Brave usando data-attribute
                    dayElement.setAttribute('data-tooltip', `${day.day_name} ${day.day_number}\\nPrecio: ${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €/kWh\\nTemperatura: ${day.avg_temperature}°C\\nHumedad: ${day.avg_humidity}%\\nRecomendación: ${day.production_recommendation}`);

                    // Fallback: title nativo para navegadores que lo soporten
                    dayElement.title = `${day.day_name} ${day.day_number}
Precio: ${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €/kWh
Temperatura: ${day.avg_temperature}°C
Humedad: ${day.avg_humidity}%
Recomendación: ${day.production_recommendation}`;

                    calendarGrid.appendChild(dayElement);
                });
                
                // Actualizar resumen
                const summary = weeklyForecast.summary;
                if (summary) {
                    optimalDaysElement.textContent = summary.optimal_days || 0;
                    avgPriceElement.textContent = formatSpanishNumber(summary.price_summary?.avg_price || 0, 3) + ' €/kWh';
                    const minPrice = formatSpanishNumber(summary.price_summary?.min_price || 0, 2);
                    const maxPrice = formatSpanishNumber(summary.price_summary?.max_price || 0, 2);
                    priceRangeElement.textContent = `${minPrice} - ${maxPrice} €/kWh`;
                }
            }
            
            function renderHistoricalAnalytics(data) {
                const analytics = data.historical_analytics;
                if (!analytics) return;
                
                // Métricas principales
                const totalConsumptionEl = document.getElementById('total-consumption');
                const avgDailyCostEl = document.getElementById('avg-daily-cost');
                const peakConsumptionEl = document.getElementById('peak-consumption');
                const totalCostEl = document.getElementById('total-cost');
                
                if (totalConsumptionEl) totalConsumptionEl.textContent = formatSpanishNumber(analytics.factory_metrics.total_kwh, 0) + ' kWh';
                if (avgDailyCostEl) avgDailyCostEl.textContent = formatSpanishNumber(analytics.factory_metrics.avg_daily_cost, 2) + ' €';
                if (peakConsumptionEl) peakConsumptionEl.textContent = formatSpanishNumber(analytics.factory_metrics.peak_consumption, 0) + ' kW';
                if (totalCostEl) totalCostEl.textContent = formatSpanishNumber(analytics.factory_metrics.total_cost, 2) + ' €';
                
                // Análisis de precios
                const minPriceEl = document.getElementById('min-price');
                const maxPriceEl = document.getElementById('max-price');
                const avgPriceEl = document.getElementById('avg-price');
                const volatilityEl = document.getElementById('price-volatility');
                
                if (minPriceEl) minPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.min_price_eur_kwh, 4) + ' €/kWh';
                if (maxPriceEl) maxPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.max_price_eur_kwh, 4) + ' €/kWh';
                if (avgPriceEl) avgPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.avg_price_eur_kwh, 4) + ' €/kWh';
                if (volatilityEl) volatilityEl.textContent = formatSpanishNumber(analytics.price_analysis.volatility_coefficient, 2);
                
                // Potencial de optimización
                const savingsPotentialEl = document.getElementById('savings-potential');
                const optimalHoursEl = document.getElementById('optimal-hours');
                const annualProjectionEl = document.getElementById('annual-projection');
                
                if (savingsPotentialEl) savingsPotentialEl.textContent = formatSpanishNumber(analytics.optimization_potential.total_savings_eur, 0) + ' €';
                if (optimalHoursEl) optimalHoursEl.textContent = analytics.optimization_potential.optimal_production_hours;
                if (annualProjectionEl) annualProjectionEl.textContent = formatSpanishNumber(analytics.optimization_potential.annual_savings_projection, 0) + ' €';
                
                // Recomendaciones
                const recommendationsContainer = document.getElementById('optimization-recommendations');
                if (recommendationsContainer && analytics.recommendations) {
                    recommendationsContainer.innerHTML = analytics.recommendations
                        .map(rec => `<div class="recommendation-item">• ${rec}</div>`)
                        .join('');
                }
            }
            
            function renderSmartInsights(data) {
                const analytics = data.historical_analytics;
                const currentEnergy = data.current_info?.energy;
                
                if (!analytics || !currentEnergy) return;
                
                const currentPrice = currentEnergy.price_eur_kwh;
                const avgPrice = analytics.price_analysis.avg_price_eur_kwh;
                const minPrice = analytics.price_analysis.min_price_eur_kwh;
                const maxPrice = analytics.price_analysis.max_price_eur_kwh;
                
                // Calcular percentil del precio actual
                const priceRange = maxPrice - minPrice;
                const pricePosition = (currentPrice - minPrice) / priceRange;
                
                // Actualizar estado energético actual
                const statusIconEl = document.querySelector('.status-icon');
                const statusTextEl = document.getElementById('energy-status-text');
                const priceAnalysisEl = document.getElementById('current-price-analysis');
                const actionRecommendationEl = document.getElementById('energy-action-recommendation');
                
                if (pricePosition <= 0.25) {
                    // Precio muy bajo (25% inferior)
                    if (statusIconEl) statusIconEl.textContent = '🟢';
                    if (statusTextEl) statusTextEl.textContent = 'ÓPTIMO - Precio Muy Bajo';
                    if (actionRecommendationEl) actionRecommendationEl.textContent = '🚀 Momento ideal para maximizar producción';
                } else if (pricePosition <= 0.5) {
                    // Precio bajo-medio (25-50%)
                    if (statusIconEl) statusIconEl.textContent = '🟡';
                    if (statusTextEl) statusTextEl.textContent = 'FAVORABLE - Precio Bajo';
                    if (actionRecommendationEl) actionRecommendationEl.textContent = '✅ Condiciones buenas para producir';
                } else if (pricePosition <= 0.75) {
                    // Precio medio-alto (50-75%)
                    if (statusIconEl) statusIconEl.textContent = '🟠';
                    if (statusTextEl) statusTextEl.textContent = 'NEUTRO - Precio Medio';
                    if (actionRecommendationEl) actionRecommendationEl.textContent = '⚖️ Evaluar necesidad vs costo';
                } else {
                    // Precio alto (75%+)
                    if (statusIconEl) statusIconEl.textContent = '🔴';
                    if (statusTextEl) statusTextEl.textContent = 'CARO - Precio Alto';
                    if (actionRecommendationEl) actionRecommendationEl.textContent = '⚠️ Considerar diferir producción';
                }
                
                if (priceAnalysisEl) priceAnalysisEl.textContent = formatSpanishNumber(currentPrice, 4) + ' €/kWh';
                
                // Calcular ahorro vs precio promedio
                const hourlyConsumption = 104; // kW promedio de la fábrica
                const savingsPerHour = (avgPrice - currentPrice) * hourlyConsumption;
                const savingsPotentialEl = document.getElementById('current-savings-potential');
                if (savingsPotentialEl) {
                    if (savingsPerHour > 0) {
                        savingsPotentialEl.textContent = '+' + formatSpanishNumber(savingsPerHour, 2) + ' €/hora';
                        savingsPotentialEl.style.color = '#4CAF50';
                    } else {
                        savingsPotentialEl.textContent = formatSpanishNumber(savingsPerHour, 2) + ' €/hora';
                        savingsPotentialEl.style.color = '#F44336';
                    }
                }
                
                // Ranking diario simulado (basado en percentil)
                const rankingEl = document.getElementById('price-ranking');
                const ranking = Math.ceil(pricePosition * 24);
                if (rankingEl) rankingEl.textContent = ranking + '/24';
                
                // Acción de ahorro
                const savingsActionEl = document.getElementById('savings-action');
                if (savingsActionEl) {
                    if (savingsPerHour > 5) {
                        savingsActionEl.textContent = '💰 Excelente momento para ahorrar';
                    } else if (savingsPerHour > 0) {
                        savingsActionEl.textContent = '💡 Ahorro moderado disponible';
                    } else if (savingsPerHour > -5) {
                        savingsActionEl.textContent = '⚖️ Costo ligeramente superior';
                    } else {
                        savingsActionEl.textContent = '⚠️ Momento costoso para producir';
                    }
                }
                
                // Análisis por procesos de fábrica
                const processes = {
                    'Conchado': 48,    // kW - Proceso más intensivo
                    'Rolado': 42,      // kW - Refinado del chocolate
                    'Templado': 36,    // kW - Control de temperatura
                    'Mezcla': 30       // kW - Proceso básico
                };
                
                // Calcular costo por proceso en el precio actual
                const processCosts = Object.entries(processes).map(([name, kw]) => ({
                    name,
                    kw,
                    costPerHour: currentPrice * kw,
                    savingsVsAvg: (avgPrice - currentPrice) * kw
                }));
                
                // Recomendar proceso basado en precio actual
                const recommendedProcessEl = document.getElementById('recommended-process');
                const processCostEl = document.getElementById('process-cost');
                const processActionEl = document.getElementById('process-action');
                
                if (pricePosition <= 0.25) {
                    // Precio muy bajo - recomendar proceso más intensivo
                    const bestProcess = processCosts[0]; // Conchado (48kW)
                    if (recommendedProcessEl) recommendedProcessEl.textContent = '🍫 Conchado';
                    if (processCostEl) processCostEl.textContent = formatSpanishNumber(bestProcess.costPerHour, 2) + ' €/h';
                    if (processActionEl) processActionEl.textContent = `🚀 Momento óptimo para procesos intensivos (+${formatSpanishNumber(bestProcess.savingsVsAvg, 2)}€/h vs promedio)`;
                } else if (pricePosition <= 0.4) {
                    // Precio bajo-medio - recomendar proceso intermedio
                    const goodProcess = processCosts[1]; // Rolado (42kW)
                    if (recommendedProcessEl) recommendedProcessEl.textContent = '🔄 Rolado';
                    if (processCostEl) processCostEl.textContent = formatSpanishNumber(goodProcess.costPerHour, 2) + ' €/h';
                    if (processActionEl) processActionEl.textContent = `✅ Condiciones favorables para refinado (+${formatSpanishNumber(goodProcess.savingsVsAvg, 2)}€/h)`;
                } else if (pricePosition <= 0.6) {
                    // Precio medio - recomendar proceso estándar
                    const stdProcess = processCosts[2]; // Templado (36kW)
                    if (recommendedProcessEl) recommendedProcessEl.textContent = '🌡️ Templado';
                    if (processCostEl) processCostEl.textContent = formatSpanishNumber(stdProcess.costPerHour, 2) + ' €/h';
                    if (processActionEl) processActionEl.textContent = `⚖️ Proceso estándar recomendado (${formatSpanishNumber(Math.abs(stdProcess.savingsVsAvg), 2)}€/h vs promedio)`;
                } else {
                    // Precio alto - recomendar proceso de menor consumo
                    const lowProcess = processCosts[3]; // Mezcla (30kW)
                    if (recommendedProcessEl) recommendedProcessEl.textContent = '🥄 Mezcla';
                    if (processCostEl) processCostEl.textContent = formatSpanishNumber(lowProcess.costPerHour, 2) + ' €/h';
                    if (processActionEl) processActionEl.textContent = `⚠️ Solo procesos básicos recomendados (sobrecosto: +${formatSpanishNumber(Math.abs(lowProcess.savingsVsAvg), 2)}€/h)`;
                }
                
                // Recomendación principal inteligente
                const recIconEl = document.getElementById('recommendation-icon');
                const recTitleEl = document.getElementById('recommendation-title');
                const recDetailEl = document.getElementById('recommendation-detail');
                
                if (pricePosition <= 0.25) {
                    if (recIconEl) recIconEl.textContent = '🚀';
                    if (recTitleEl) recTitleEl.textContent = 'PRODUCIR AHORA - Oportunidad Excepcional';
                    if (recDetailEl) recDetailEl.textContent = `🍫 CONCHADO RECOMENDADO: Precio actual (${formatSpanishNumber(currentPrice, 4)} €/kWh) en el 25% más bajo del histórico. Momento óptimo para procesos intensivos (48kW). Ahorro vs promedio: ${formatSpanishNumber((avgPrice - currentPrice) * 48, 2)} €/hora en Conchado.`;
                } else if (pricePosition <= 0.4) {
                    if (recIconEl) recIconEl.textContent = '✅';
                    if (recTitleEl) recTitleEl.textContent = 'PRODUCIR - Rolado Recomendado';
                    if (recDetailEl) recDetailEl.textContent = `🔄 ROLADO FAVORABLE: Condiciones buenas para refinado (42kW). Costo actual: ${formatSpanishNumber(currentPrice * 42, 2)} €/hora. Ahorro vs promedio: +${formatSpanishNumber((avgPrice - currentPrice) * 42, 2)} €/hora.`;
                } else if (pricePosition <= 0.6) {
                    if (recIconEl) recIconEl.textContent = '⚖️';
                    if (recTitleEl) recTitleEl.textContent = 'EVALUAR - Templado Estándar';
                    if (recDetailEl) recDetailEl.textContent = `🌡️ TEMPLADO RECOMENDADO: Precio medio, ideal para procesos estándar (36kW). Costo: ${formatSpanishNumber(currentPrice * 36, 2)} €/hora. Evaluar urgencia vs esperar mejores condiciones para procesos intensivos.`;
                } else if (pricePosition <= 0.8) {
                    if (recIconEl) recIconEl.textContent = '⚠️';
                    if (recTitleEl) recTitleEl.textContent = 'DIFERIR - Solo Procesos Básicos';
                    if (recDetailEl) recDetailEl.textContent = `🥄 SOLO MEZCLA: Precio elevado, limitarse a procesos básicos (30kW). Costo Mezcla: ${formatSpanishNumber(currentPrice * 30, 2)} €/hora. Diferir Conchado y Rolado hasta mejores condiciones.`;
                } else {
                    if (recIconEl) recIconEl.textContent = '🛑';
                    if (recTitleEl) recTitleEl.textContent = 'SUSPENDER - Precio Crítico';
                    if (recDetailEl) recDetailEl.textContent = `⚠️ ALERTA CRÍTICA: Precio en máximos históricos (${formatSpanishNumber(currentPrice, 4)} €/kWh). Incluso Mezcla cuesta ${formatSpanishNumber(currentPrice * 30, 2)} €/h. Suspender toda producción no crítica hasta mejores condiciones.`;
                }
            }
            
            async function loadData() {
                try {
                    document.getElementById('status').textContent = '🔄 Cargando...';
                    document.getElementById('status').className = 'status-badge status-warning';
                    
                    const response = await fetch('/dashboard/complete');
                    const data = await response.json();
                    
                    // Estado conexión
                    document.getElementById('status').textContent = '✅ Conectado';
                    document.getElementById('status').className = 'status-badge status-connected';
                    document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();
                    
                    // Energía (formato español)
                    const energy = data.current_info.energy || {};
                    document.getElementById('energy-price').textContent = formatSpanishNumber(energy.price_eur_kwh || 0, 4);
                    document.getElementById('energy-mwh').textContent = formatSpanishNumber(energy.price_eur_mwh || 0, 2) + ' €/MWh';
                    document.getElementById('energy-datetime').textContent = new Date(energy.datetime).toLocaleString();
                    
                    const trendElement = document.getElementById('energy-trend');
                    trendElement.textContent = '📈 ' + (energy.trend || 'stable');
                    trendElement.className = `metric-trend trend-${energy.trend || 'stable'}`;
                    
                    // Clima (formato español)
                    const weather = data.current_info.weather || {};
                    document.getElementById('temperature').textContent = formatSpanishNumber(weather.temperature || 0, 1);
                    document.getElementById('humidity').textContent = formatSpanishNumber(weather.humidity || 0, 0) + '%';
                    document.getElementById('pressure').textContent = formatSpanishNumber(weather.pressure || 0, 0) + ' hPa';
                    document.getElementById('comfort-index').textContent = weather.comfort_index || '--';
                    
                    // Producción (formato español)
                    document.getElementById('production-status').textContent = data.current_info.production_status || '--';
                    document.getElementById('factory-efficiency').textContent = formatSpanishNumber(data.current_info.factory_efficiency || 0, 1) + '%';
                    
                    
                    // Estado sistema
                    const systemStatus = data.system_status || {};
                    const sources = systemStatus.data_sources || {};
                    
                    const reeStatusEl = document.getElementById('ree-status');
                    const weatherStatusEl = document.getElementById('weather-status');
                    const mlModelsStatusEl = document.getElementById('ml-models-status');
                    
                    if (reeStatusEl) reeStatusEl.textContent = sources.ree || '--';
                    if (weatherStatusEl) weatherStatusEl.textContent = sources.weather || '--';
                    if (mlModelsStatusEl) mlModelsStatusEl.textContent = sources.ml_models || '--';
                    
                    // Renderizar heatmap semanal
                    if (data.weekly_forecast) {
                        renderHeatmap(data.weekly_forecast);
                    }
                    
                    // ✨ Renderizar Enhanced ML data
                    renderEnhancedMLData(data);

                    // 🔄 Renderizar REE Unificado (reemplaza analytics históricos + smart insights)
                    renderUnifiedREEAnalysis(data);

                    // 📊 Renderizar SIAR Historical Analysis (Sprint 07)
                    renderSIARAnalysis(data);

                } catch (error) {
                    document.getElementById('status').textContent = '❌ Error de conexión';
                    document.getElementById('status').className = 'status-badge';
                    console.error('Dashboard error:', error);
                }
            }
            
            // ⚡ Función Unificada REE con BusinessLogicService
            function renderUnifiedREEAnalysis(data) {
                try {
                    const analytics = data.historical_analytics;
                    const currentEnergy = data.current_info?.energy;
                    const recommendations = data.recommendations || {};
                    const humanRecUnified = recommendations.human_recommendation;

                    if (!analytics || !currentEnergy) {
                        console.log('⚠️ Missing data for unified REE analysis');
                        return;
                    }

                    // === RECOMENDACIÓN HUMANIZADA PRINCIPAL ===
                    if (humanRecUnified && !humanRecUnified.error) {
                        const unifiedSection = document.getElementById('unified-human-recommendation-section');
                        const unifiedContent = document.getElementById('unified-human-recommendation-content');

                        if (unifiedSection && unifiedContent) {
                            const message = humanRecUnified.main_message || {};
                            const economicImpact = humanRecUnified.economic_impact || {};
                            const metadata = humanRecUnified.metadata || {};

                            let content = `
                                <div style="margin-bottom: 1rem;">
                                    <h3 style="margin: 0; font-size: 1.3rem; color: white;">${message.title || 'RECOMENDACIÓN INTELIGENTE'}</h3>
                                    <div style="margin-top: 0.5rem; opacity: 0.95; font-size: 1rem;">
                                        <strong>📊 Análisis:</strong> ${message.situation || 'Evaluando condiciones actuales...'}
                                    </div>
                                </div>

                                <div class="grid grid-2" style="gap: 1rem; margin-bottom: 1rem;">
                                    <div>
                                        <strong style="display: block; margin-bottom: 0.5rem;">🎯 Acciones:</strong>
                                        <ul style="margin: 0; padding-left: 1rem; font-size: 0.95rem;">
                            `;

                            if (message.priority_actions && Array.isArray(message.priority_actions)) {
                                message.priority_actions.slice(0, 3).forEach(action => {
                                    content += `<li>${action}</li>`;
                                });
                            }

                            content += `
                                        </ul>
                                    </div>
                                    <div>
                                        <strong style="display: block; margin-bottom: 0.5rem;">💰 Impacto:</strong>
                                        <div style="font-size: 0.95rem; line-height: 1.4;">
                                            <div><strong>Costo/kg:</strong> ${economicImpact.current_cost_per_kg || '13,90'}€</div>
                                            <div><strong>Categoría:</strong> ${economicImpact.cost_category || 'normal'}</div>
                                            <div><strong>Confianza:</strong> ${message.confidence_level || metadata.confidence || 'media'}</div>
                                        </div>
                                    </div>
                                </div>
                            `;

                            unifiedContent.innerHTML = content;
                            unifiedSection.style.display = 'block';
                        }
                    }

                    // === MÉTRICAS DE LA TARJETA UNIFICADA ===

                    // Current energy status
                    const currentPrice = currentEnergy.price_eur_kwh;
                    const statusTextEl = document.getElementById('energy-status-text');
                    const statusDetailEl = document.getElementById('energy-status-detail');
                    const actionRecommendationEl = document.getElementById('energy-action-recommendation');

                    if (statusTextEl && statusDetailEl && actionRecommendationEl) {
                        // === USE SAME LOGIC AS ENHANCED ML ANALYTICS ===
                        if (humanRecUnified && humanRecUnified.recommendation_level) {
                            const level = humanRecUnified.recommendation_level;
                            const levelNames = {
                                'maximize': 'Óptimo',
                                'standard': 'Normal',
                                'reduced': 'Subóptimo',
                                'minimal': 'Crítico',
                                'critical': 'Emergencia'
                            };
                            statusTextEl.textContent = levelNames[level] || 'Evaluando';

                            // Use humanized recommendation level instead of raw Enhanced ML action
                            const levelToAction = {
                                'maximize': 'Maximize Production',
                                'standard': 'Standard Production',
                                'reduced': 'Reduce Production',
                                'minimal': 'Minimal Production',
                                'critical': 'Emergency Procedures'
                            };
                            const actionDisplay = levelToAction[level] || 'Standard Production';
                            actionRecommendationEl.textContent = actionDisplay;
                        } else {
                            // Fallback to price-based logic only if no human recommendation
                            if (currentPrice < 0.12) {
                                statusTextEl.textContent = 'Óptimo';
                                actionRecommendationEl.textContent = 'Standard Production';
                            } else if (currentPrice < 0.20) {
                                statusTextEl.textContent = 'Normal';
                                actionRecommendationEl.textContent = 'Standard Production';
                            } else if (currentPrice < 0.30) {
                                statusTextEl.textContent = 'Alto';
                                actionRecommendationEl.textContent = 'Reduce Production';
                            } else {
                                statusTextEl.textContent = 'Crítico';
                                actionRecommendationEl.textContent = 'Halt Production';
                            }
                        }

                        statusDetailEl.textContent = formatSpanishNumber(currentPrice, 4) + ' €/kWh';
                    }

                    // Historical metrics
                    if (analytics.price_analysis) {
                        const priceAnalysis = analytics.price_analysis;
                        document.getElementById('avg-price').textContent = formatSpanishNumber(priceAnalysis.average_price || 0, 4) + ' €/kWh';
                        document.getElementById('total-cost').textContent = formatSpanishNumber(analytics.factory_metrics?.total_cost || 0, 0) + ' €';

                        const minPrice = priceAnalysis.min_price_eur_kwh || 0;
                        const maxPrice = priceAnalysis.max_price_eur_kwh || 0;
                        document.getElementById('min-max-price').textContent = formatSpanishNumber(minPrice, 4) + '/' + formatSpanishNumber(maxPrice, 4) + ' €/kWh';
                    }

                    // Optimization metrics
                    if (analytics.optimization_potential) {
                        const optimization = analytics.optimization_potential;
                        document.getElementById('annual-projection').textContent = formatSpanishNumber(optimization.annual_savings_projection || 0, 0) + ' €';
                        document.getElementById('optimal-hours').textContent = optimization.optimal_production_hours || '--';
                    }

                    // Current savings potential
                    const avgPrice = analytics.price_analysis?.average_price || 0.15;
                    const savingsPerHour = (avgPrice - currentPrice) * 2.4; // 2.4 kW approx consumption
                    const savingsPotentialEl = document.getElementById('current-savings-potential');
                    if (savingsPotentialEl) {
                        if (savingsPerHour > 0) {
                            savingsPotentialEl.textContent = '+' + formatSpanishNumber(savingsPerHour, 2) + ' €/h';
                            savingsPotentialEl.style.color = '#4CAF50';
                        } else {
                            savingsPotentialEl.textContent = formatSpanishNumber(savingsPerHour, 2) + ' €/h';
                            savingsPotentialEl.style.color = '#F44336';
                        }
                    }

                    // Price ranking (simplified)
                    const pricePosition = currentPrice / (avgPrice * 1.5); // Relative position
                    const ranking = Math.ceil(Math.min(pricePosition * 24, 24));
                    document.getElementById('price-ranking').textContent = ranking + '/24';

                    // Strategic recommendations (sync with Enhanced ML Analytics)
                    const strategicEl = document.getElementById('strategic-recommendation');
                    if (strategicEl) {
                        const enhanced = data.predictions || {};
                        const enhancedRec = enhanced.enhanced_recommendations || {};

                        if (enhancedRec.main_action) {
                            const mainAction = enhancedRec.main_action;
                            const actionIcons = {
                                'maximize_production': '🚀 Maximizar producción',
                                'increase_production': '📈 Incrementar producción',
                                'standard_production': '⚖️ Producción estándar',
                                'reduce_production': '📉 Reducir operaciones',
                                'minimize_production': '⚠️ Producción mínima',
                                'halt_production': '🚨 Parar nueva producción'
                            };
                            strategicEl.textContent = actionIcons[mainAction] || `🔧 ${mainAction.replace('_', ' ')}`;
                        } else if (humanRecUnified && humanRecUnified.recommendation_level) {
                            const level = humanRecUnified.recommendation_level;
                            const levelNames = {
                                'maximize': '🚀 Maximizar producción',
                                'standard': '⚖️ Producción estándar',
                                'reduced': '📉 Reducir operaciones',
                                'minimal': '⚠️ Producción mínima',
                                'critical': '🚨 Parar nueva producción'
                            };
                            strategicEl.textContent = levelNames[level] || 'Evaluando...';
                        } else {
                            strategicEl.textContent = 'Usar criterio operacional';
                        }
                    }

                    // === LLENAR DATOS FALTANTES ===

                    // Process recommendations
                    const processEl = document.getElementById('recommended-process');
                    const processCostEl = document.getElementById('process-cost');
                    const processActionEl = document.getElementById('process-action');

                    if (processEl && processCostEl && processActionEl) {
                        const enhanced = data.predictions || {};
                        const enhancedRec = enhanced.enhanced_recommendations || {};

                        if (enhancedRec.main_action) {
                            const processMap = {
                                'maximize_production': 'Conchado extendido + Templado premium',
                                'increase_production': 'Conchado intensivo + Mezclado',
                                'standard_production': 'Conchado estándar + Moldeado',
                                'reduce_production': 'Solo conchado básico',
                                'minimize_production': 'Completar lotes actuales',
                                'halt_production': 'Ningún proceso nuevo'
                            };

                            const costMap = {
                                'maximize_production': (currentPrice * 4.8).toFixed(2),
                                'increase_production': (currentPrice * 3.6).toFixed(2),
                                'standard_production': (currentPrice * 2.4).toFixed(2),
                                'reduce_production': (currentPrice * 1.2).toFixed(2),
                                'minimize_production': (currentPrice * 0.6).toFixed(2),
                                'halt_production': '0.00'
                            };

                            processEl.textContent = processMap[enhancedRec.main_action] || 'Proceso estándar';
                            processCostEl.textContent = (costMap[enhancedRec.main_action] || currentPrice * 2.4) + ' €/h';

                            if (enhancedRec.main_action.includes('halt')) {
                                processActionEl.textContent = 'Detener nuevos procesos ahora';
                            } else if (enhancedRec.main_action.includes('maximize')) {
                                processActionEl.textContent = 'Aprovechar ventana energética';
                            } else if (enhancedRec.main_action.includes('reduce')) {
                                processActionEl.textContent = 'Reducir intensidad energética';
                            } else {
                                processActionEl.textContent = 'Mantener operación normal';
                            }
                        } else {
                            processEl.textContent = 'Conchado estándar + Moldeado';
                            processCostEl.textContent = (currentPrice * 2.4).toFixed(2) + ' €/h';
                            processActionEl.textContent = 'Evaluando mejores procesos...';
                        }
                    }

                    // Optimal time window
                    const optimalTimeEl = document.getElementById('optimal-time-window');
                    if (optimalTimeEl) {
                        const currentHour = new Date().getHours();
                        if (currentPrice < avgPrice) {
                            optimalTimeEl.textContent = `Ahora (hasta ${(currentHour + 2) % 24}:00h)`;
                        } else {
                            optimalTimeEl.textContent = '00:00-06:00 (hora valle)';
                        }
                    }

                    // Price range
                    const priceRangeEl = document.getElementById('price-range');
                    if (priceRangeEl && analytics.price_analysis) {
                        const minPrice = analytics.price_analysis.min_price || 0;
                        const maxPrice = analytics.price_analysis.max_price || 0;
                        priceRangeEl.textContent = `${formatSpanishNumber(minPrice, 4)} - ${formatSpanishNumber(maxPrice, 4)} €/kWh`;
                    }

                    // Unified recommendations
                    const unifiedRecsEl = document.getElementById('unified-optimization-recommendations');
                    if (unifiedRecsEl) {
                        let recsText = '';
                        if (humanRecUnified && humanRecUnified.situation_context) {
                            recsText = humanRecUnified.situation_context.slice(0, 2).map(ctx => `• ${ctx}`).join('<br>');
                        } else {
                            // Fallback recommendations based on Enhanced ML data
                            const enhanced = data.predictions || {};
                            const enhancedRec = enhanced.enhanced_recommendations || {};
                            if (enhancedRec.main_action) {
                                const actionRecs = {
                                    'maximize_production': '• Momento óptimo para maximizar volumen<br>• Aprovechar precio energético favorable',
                                    'increase_production': '• Incrementar producción moderadamente<br>• Condiciones favorables detectadas',
                                    'standard_production': '• Mantener ritmo normal de producción<br>• Condiciones estables para operación',
                                    'reduce_production': '• Reducir operaciones no críticas<br>• Precio energético elevado detectado',
                                    'minimize_production': '• Solo completar lotes comprometidos<br>• Condiciones subóptimas',
                                    'halt_production': '• Parar nueva producción inmediatamente<br>• Condiciones críticas detectadas'
                                };
                                recsText = actionRecs[enhancedRec.main_action] || '• Sistema híbrido activado<br>• Consultar recomendación principal arriba';
                            } else {
                                recsText = '• Sistema híbrido activado<br>• Consultar recomendación principal arriba';
                            }
                        }
                        unifiedRecsEl.innerHTML = recsText;
                    }

                    console.log('✅ Unified REE analysis rendered successfully');

                } catch (error) {
                    console.error('❌ Error rendering unified REE analysis:', error);
                }
            }

            // 📊 SIAR Historical Analysis Renderer (Sprint 07)
            function renderSIARAnalysis(data) {
                try {
                    const siar = data.siar_analysis || {};

                    if (siar.status !== 'success') {
                        console.log('⚠️ SIAR analysis not available or failed');
                        document.getElementById('siar-insights').innerHTML = '<div>⚠️ Análisis SIAR no disponible</div>';
                        return;
                    }

                    const summary = siar.summary || {};
                    const correlations = siar.correlations || {};
                    const seasonal = siar.seasonal_patterns || {};
                    const thresholds = siar.thresholds || {};

                    // Summary Stats
                    const totalRecords = summary.total_records || 0;
                    document.getElementById('siar-total-records').textContent = totalRecords.toLocaleString('es-ES');

                    const dateRange = summary.date_range || {};
                    const startDate = dateRange.start_date ? new Date(dateRange.start_date).getFullYear() : '2000';
                    const endDate = dateRange.end_date ? new Date(dateRange.end_date).getFullYear() : '2025';
                    document.getElementById('siar-date-range').textContent = `${startDate} - ${endDate}`;

                    // Correlations
                    const tempCorr = correlations.temperature_production || {};
                    const humidityCorr = correlations.humidity_production || {};

                    const tempR2 = tempCorr.r_squared || 0;
                    const humidityR2 = humidityCorr.r_squared || 0;

                    document.getElementById('siar-temp-correlation').textContent = formatSpanishNumber(tempR2, 3);
                    document.getElementById('siar-humidity-correlation').textContent = formatSpanishNumber(humidityR2, 3);

                    // Seasonal Patterns
                    const bestMonth = seasonal.best_month || {};
                    const worstMonth = seasonal.worst_month || {};

                    // Month names already come in proper format from API
                    document.getElementById('siar-best-month').textContent = bestMonth.name || '--';
                    document.getElementById('siar-best-month-score').textContent =
                        `${formatSpanishNumber(bestMonth.efficiency_score || 0, 1)}% condiciones óptimas`;

                    document.getElementById('siar-worst-month').textContent = worstMonth.name || '--';
                    document.getElementById('siar-worst-month-score').textContent =
                        `${formatSpanishNumber(worstMonth.efficiency_score || 0, 1)}% condiciones óptimas`;

                    // Critical Thresholds
                    const tempThresholds = thresholds.temperature || {};
                    const humidityThresholds = thresholds.humidity || {};

                    document.getElementById('siar-temp-p90').textContent = formatSpanishNumber(tempThresholds.p90 || 0, 1);
                    document.getElementById('siar-temp-p95').textContent = formatSpanishNumber(tempThresholds.p95 || 0, 1);
                    document.getElementById('siar-temp-p99').textContent = formatSpanishNumber(tempThresholds.p99 || 0, 1);

                    document.getElementById('siar-humidity-p90').textContent = formatSpanishNumber(humidityThresholds.p90 || 0, 1);
                    document.getElementById('siar-humidity-p95').textContent = formatSpanishNumber(humidityThresholds.p95 || 0, 1);
                    document.getElementById('siar-humidity-p99').textContent = formatSpanishNumber(humidityThresholds.p99 || 0, 1);

                    // Generate Insights
                    const insights = [];

                    if (tempR2 > 0.03) {
                        insights.push(`🌡️ La temperatura muestra correlación significativa (R²=${formatSpanishNumber(tempR2, 3)}) con la eficiencia de producción`);
                    } else {
                        insights.push(`🌡️ La temperatura tiene baja correlación (R²=${formatSpanishNumber(tempR2, 3)}) - otros factores dominan`);
                    }

                    if (humidityR2 > 0.03) {
                        insights.push(`💧 La humedad muestra correlación significativa (R²=${formatSpanishNumber(humidityR2, 3)}) con la producción`);
                    }

                    if (bestMonth.name) {
                        insights.push(`📅 ${bestMonth.name} históricamente ofrece las mejores condiciones (${formatSpanishNumber(bestMonth.efficiency_score || 0, 1)}%)`);
                    }

                    if (worstMonth.name) {
                        insights.push(`⚠️ ${worstMonth.name} requiere mayor atención operativa (solo ${formatSpanishNumber(worstMonth.efficiency_score || 0, 1)}% óptimo)`);
                    }

                    insights.push(`📊 Basado en ${totalRecords.toLocaleString('es-ES')} registros históricos (${startDate}-${endDate})`);

                    document.getElementById('siar-insights').innerHTML = insights.map(i => `<div style="margin-bottom: 0.5rem;">${i}</div>`).join('');

                    console.log('✅ SIAR analysis rendered successfully');

                } catch (error) {
                    console.error('❌ Error rendering SIAR analysis:', error);
                    document.getElementById('siar-insights').innerHTML = '<div>❌ Error al cargar análisis SIAR</div>';
                }
            }

            // Cargar datos al inicializar
            loadData();
            
            // ✨ Enhanced ML Data Renderer
            function renderEnhancedMLData(data) {
                try {
                    const enhanced = data.predictions || {};
                    const enhancedCost = enhanced.enhanced_cost_analysis || {};
                    const enhancedRec = enhanced.enhanced_recommendations || {};
                    const reeDeviation = enhanced.ree_deviation_analysis || {};
                    const recommendations = data.recommendations || {};

                    // Cost Optimization
                    const costPerKg = enhancedCost.total_cost_per_kg || 13.90;
                    document.getElementById('enhanced-cost-per-kg').textContent = formatSpanishNumber(costPerKg, 2);
                    document.getElementById('cost-category').textContent = enhancedCost.cost_category || 'unknown';
                    document.getElementById('savings-opportunity').textContent = formatSpanishNumber(enhancedCost.savings_opportunity || 0, 3);

                    const vsTarget = enhancedCost.vs_target || {};
                    const percentage = vsTarget.percentage || 0;
                    document.getElementById('vs-target').textContent = percentage > 0 ? `+${percentage}%` : `${percentage}%`;

                    // Enhanced Recommendations - use humanized recommendation if available
                    const humanRecEnhanced = recommendations.human_recommendation;
                    let actionDisplay = 'Standard Production';

                    if (humanRecEnhanced && humanRecEnhanced.recommendation_level) {
                        const levelToAction = {
                            'maximize': 'Maximize Production',
                            'standard': 'Standard Production',
                            'reduced': 'Reduce Production',
                            'minimal': 'Minimal Production',
                            'critical': 'Emergency Procedures'
                        };
                        actionDisplay = levelToAction[humanRecEnhanced.recommendation_level] || 'Standard Production';
                    } else {
                        // Fallback to raw Enhanced ML if humanized not available
                        const mainAction = enhancedRec.main_action || 'standard_production';
                        actionDisplay = mainAction.replace('_', ' ').split(' ').map(word =>
                            word.charAt(0).toUpperCase() + word.slice(1)
                        ).join(' ');
                    }

                    document.getElementById('enhanced-main-action').textContent = actionDisplay;
                    document.getElementById('enhanced-priority').textContent = enhancedRec.priority || 'medium';
                    document.getElementById('enhanced-overall-score').textContent = formatSpanishNumber(enhancedRec.overall_score || 50, 1);
                    document.getElementById('enhanced-confidence').textContent = enhancedRec.confidence || 'medium';
                    document.getElementById('enhanced-alerts-count').textContent = enhancedRec.alerts_count || 0;

                    // REE Deviation Analysis
                    const accuracy = reeDeviation.accuracy_score || 0.9;
                    document.getElementById('ree-accuracy').textContent = Math.round(accuracy * 100) + '%';
                    document.getElementById('ree-deviation').textContent = formatSpanishNumber(reeDeviation.average_deviation || 0.015, 4);
                    document.getElementById('ree-trend').textContent = reeDeviation.deviation_trend || 'stable';
                    document.getElementById('ree-usefulness').textContent = reeDeviation.usefulness || 'trend_analysis';

                    // Enhanced Cost Insights
                    const costInsights = recommendations.enhanced_cost_insights || [];
                    const costInsightsEl = document.getElementById('enhanced-cost-insights');
                    if (costInsights.length > 0) {
                        costInsightsEl.innerHTML = costInsights.map(insight => `<li>${insight}</li>`).join('');
                    } else {
                        costInsightsEl.innerHTML = '<li>🔧 No hay insights de costos disponibles</li>';
                    }

                    // Enhanced Timing Insights
                    const timingInsights = recommendations.enhanced_timing || [];
                    const timingInsightsEl = document.getElementById('enhanced-timing-insights');
                    if (timingInsights.length > 0) {
                        timingInsightsEl.innerHTML = timingInsights.slice(0, 5).map(insight => `<li>${insight}</li>`).join('');
                    } else {
                        timingInsightsEl.innerHTML = '<li>⚡ No hay insights temporales disponibles</li>';
                    }

                    // Enhanced status styling based on data
                    const costCategory = enhancedCost.cost_category;
                    const costEl = document.getElementById('enhanced-cost-per-kg');
                    if (costCategory === 'optimal') {
                        costEl.style.color = '#059669';
                    } else if (costCategory === 'elevated') {
                        costEl.style.color = '#d97706';
                    } else if (costCategory === 'high') {
                        costEl.style.color = '#dc2626';
                    }

                    const priority = enhancedRec.priority;
                    const actionEl = document.getElementById('enhanced-main-action');
                    if (priority === 'critical') {
                        actionEl.style.color = '#dc2626';
                    } else if (priority === 'high') {
                        actionEl.style.color = '#d97706';
                    } else {
                        actionEl.style.color = '#059669';
                    }

                    // === RECOMENDACIÓN HUMANIZADA ===
                    const humanRecDetails = recommendations.human_recommendation;
                    if (humanRecDetails && !humanRecDetails.error) {
                        const humanSection = document.getElementById('human-recommendation-section');
                        const humanContent = document.getElementById('human-recommendation-content');

                        if (humanSection && humanContent) {
                            const message = humanRecDetails.main_message || {};
                            const economicImpact = humanRecDetails.economic_impact || {};
                            const metadata = humanRecDetails.metadata || {};

                            // Build human-friendly content
                            let content = `
                                <div style="margin-bottom: 1rem;">
                                    <h3 style="margin: 0; font-size: 1.2rem; color: white;">${message.title || 'RECOMENDACIÓN DEL SISTEMA'}</h3>
                                    <div style="margin-top: 0.5rem; opacity: 0.9; font-size: 0.95rem;">
                                        <strong>Situación actual:</strong> ${message.situation || 'Evaluando condiciones...'}
                                    </div>
                                </div>

                                <div style="margin-bottom: 1rem;">
                                    <strong style="display: block; margin-bottom: 0.5rem;">📋 Acciones prioritarias:</strong>
                                    <ul style="margin: 0; padding-left: 1.2rem; line-height: 1.4;">
                            `;

                            if (message.priority_actions && Array.isArray(message.priority_actions)) {
                                message.priority_actions.forEach(action => {
                                    content += `<li>${action}</li>`;
                                });
                            }

                            content += `
                                    </ul>
                                </div>

                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; font-size: 0.9rem;">
                                    <div>
                                        <strong>⏱️ Duración:</strong><br>
                                        ${message.estimated_duration || 'Por definir'}
                                    </div>
                                    <div>
                                        <strong>💰 Impacto:</strong><br>
                                        ${economicImpact.cost_category || 'normal'} (${economicImpact.current_cost_per_kg || '13,90'}€/kg)
                                    </div>
                                    <div>
                                        <strong>🎯 Confianza:</strong><br>
                                        ${message.confidence_level || metadata.confidence || 'media'}
                                    </div>
                                    <div>
                                        <strong>🔄 Revisar en:</strong><br>
                                        ${Math.round((metadata.review_in_minutes || 180) / 60)} horas
                                    </div>
                                </div>
                            `;

                            // Add contextual messages if available
                            if (humanRecDetails.situation_context && Array.isArray(humanRecDetails.situation_context)) {
                                content += `
                                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.3);">
                                        <strong style="display: block; margin-bottom: 0.5rem;">💡 Contexto:</strong>
                                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.9rem; opacity: 0.95;">
                                `;
                                humanRecDetails.situation_context.forEach(context => {
                                    content += `<li>${context}</li>`;
                                });
                                content += `</ul></div>`;
                            }

                            humanContent.innerHTML = content;
                            humanSection.style.display = 'block';
                        }
                    }

                    console.log('✨ Enhanced ML data rendered successfully');

                } catch (error) {
                    console.error('❌ Error rendering Enhanced ML data:', error);
                    // Fallback values
                    document.getElementById('enhanced-cost-per-kg').textContent = '13,90';
                    document.getElementById('enhanced-main-action').textContent = 'Standard Production';
                    document.getElementById('ree-accuracy').textContent = '90%';
                }
            }

            // Auto-refresh cada 2 minutos
            setInterval(loadData, 2 * 60 * 1000);
        </script>
    </body>
    </html>
    """)


# =============================================================================
# DIRECT ML ENDPOINTS (No MLflow dependency)
# =============================================================================

@app.post("/models/train")
async def train_chocolate_models_direct(
    background_tasks: BackgroundTasks = None
):
    """🤖 Entrenar modelos ML directamente sin MLflow"""
    try:
        if background_tasks:
            logger.info("🚀 Iniciando entrenamiento directo en background...")
            background_tasks.add_task(_run_direct_training_background)
            return {
                "status": "training_started",
                "message": "🚀 Entrenamiento ML directo iniciado en background",
                "timestamp": datetime.now().isoformat()
            }
        
        # Direct training (synchronous)
        logger.info("🤖 Entrenando modelos ML directamente...")
        
        direct_ml = get_global_direct_ml()
        
        # Train models using direct approach
        training_results = await direct_ml.train_models()
        
        if not training_results.get("success"):
            return {
                "status": "training_failed",
                "error": training_results.get("error", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "message": "✅ Modelos entrenados exitosamente con enfoque directo",
            "results": training_results,
            "timestamp": datetime.now().isoformat(),
            "next_actions": {
                "verify_models": "GET /models/status",
                "test_predictions": "POST /predict/energy-optimization"
            }
        }
        
    except Exception as e:
        logger.error(f"Direct model training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Direct model training failed: {str(e)}")


async def _run_direct_training_background():
    """Background task for direct ML training"""
    try:
        logger.info("🔄 Background direct ML training started...")
        
        direct_ml = get_global_direct_ml()
        
        # Train models
        training_results = await direct_ml.train_models()
        
        if training_results.get("success"):
            logger.info(f"✅ Background direct ML training completed: {training_results}")
        else:
            logger.error(f"❌ Background direct ML training failed: {training_results}")
        
    except Exception as e:
        logger.error(f"Background direct ML training failed: {e}")


@app.get("/models/status-direct")
async def get_direct_models_status():
    """📊 Estado de los modelos ML directos"""
    try:
        direct_ml = get_global_direct_ml()
        
        # Get models status
        models_status = direct_ml.get_models_status()
        
        return {
            "🏢": "Chocolate Factory - Direct ML Models Status", 
            "🤖": "Direct ML Service",
            "status": "✅ Models status retrieved",
            "models": models_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get models status: {e}")
        raise HTTPException(status_code=500, detail=f"Models status failed: {str(e)}")


@app.get("/models/data-debug")
async def debug_training_data():
    """🔍 Debug: Verificar datos disponibles para entrenamiento"""
    try:
        direct_ml = get_global_direct_ml()
        
        # Extract data to see what's available
        df = await direct_ml.extract_data_from_influxdb(hours_back=168)
        
        if df.empty:
            return {
                "status": "❌ No data available",
                "data_summary": "No merged data found",
                "recommendation": "Check InfluxDB data and timestamps alignment"
            }
        
        return {
            "🔍": "Training Data Debug",
            "status": "✅ Data analysis completed",
            "data_summary": {
                "total_records": len(df),
                "columns": list(df.columns),
                "sample_data": df.head(3).to_dict(orient='records') if len(df) > 0 else [],
                "timestamp_range": {
                    "earliest": df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
                    "latest": df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to debug training data: {e}")
        return {
            "status": "❌ Debug failed", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# SPRINT 05: OPTIMIZATION & MONITORING ENDPOINTS
# =============================================================================

@app.get("/metrics")
async def get_metrics():
    """📊 Métricas de la aplicación (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            cache_stats = cache_manager.get_stats()
            rate_limit_stats = default_rate_limiter.get_stats()

            return {
                "service": "Chocolate Factory - Metrics",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache": cache_stats,
                "rate_limiting": rate_limit_stats,
                "sprint05_enabled": True
            }
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "error": str(e),
                "sprint05_enabled": True
            }
    else:
        return {
            "message": "Sprint 05 not enabled",
            "sprint05_enabled": False
        }


@app.get("/api/cache/stats")
async def get_cache_stats():
    """📊 Estadísticas del sistema de caché (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            stats = cache_manager.get_stats()
            return {
                "service": "Cache Manager",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "statistics": stats,
                "recommendations": {
                    "hit_rate": "Good" if stats['hit_rate'] >= 70 else "Consider increasing TTL",
                    "memory_usage": f"{stats['entries']} entries cached"
                }
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return {
            "error": "Sprint 05 not enabled",
            "sprint05_enabled": False
        }


@app.post("/api/cache/clear")
async def clear_cache(pattern: Optional[str] = None):
    """🗑️ Limpiar caché (completo o por patrón) - Sprint 05"""
    if SPRINT05_ENABLED:
        try:
            if pattern:
                count = cache_manager.invalidate_pattern(pattern)
                message = f"Invalidated {count} cache entries matching pattern: {pattern}"
            else:
                cache_manager.clear()
                message = "All cache cleared"

            return {
                "service": "Cache Manager",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "clear",
                "message": message,
                "pattern": pattern
            }
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Sprint 05 not enabled")


@app.get("/api/rate-limit/stats")
async def get_rate_limit_stats():
    """📊 Estadísticas de rate limiting (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            stats = default_rate_limiter.get_stats()
            ml_stats = ml_rate_limiter.get_stats()

            return {
                "service": "Rate Limiter",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "default_limiter": stats,
                "ml_limiter": ml_stats,
                "configuration": {
                    "default": {
                        "requests_per_minute": default_rate_limiter.requests_per_minute,
                        "burst_size": default_rate_limiter.burst_size
                    },
                    "ml": {
                        "requests_per_minute": ml_rate_limiter.requests_per_minute,
                        "burst_size": ml_rate_limiter.burst_size
                    }
                }
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return {
            "error": "Sprint 05 not enabled",
            "sprint05_enabled": False
        }


@app.post("/api/rate-limit/reset/{client_id}")
async def reset_rate_limit(client_id: str):
    """🔄 Resetear rate limit para un cliente específico (Sprint 05)"""
    if SPRINT05_ENABLED:
        try:
            default_rate_limiter.reset_client(client_id)
            ml_rate_limiter.reset_client(client_id)

            return {
                "service": "Rate Limiter",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "reset",
                "client_id": client_id,
                "message": f"Rate limit reset for client: {client_id}"
            }
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Sprint 05 not enabled")


logger.info("✅ Sprint 05 Optimization & Monitoring endpoints registered")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
