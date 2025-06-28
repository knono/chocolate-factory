"""
TFM Chocolate Factory - FastAPI Main Application
=================================================

El Cerebro Autónomo: FastAPI + APScheduler para automatización completa
- Endpoints: /predict y /ingest-now
- Automatización: APScheduler para ingestión y predicciones periódicas
- Simulación: SimPy/SciPy para lógica de fábrica
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from services.scheduler import get_scheduler_service, start_scheduler, stop_scheduler
from services.data_ingestion import DataIngestionService, run_current_ingestion, run_daily_ingestion
from services.ree_client import REEClient
from services.aemet_client import AEMETClient
from services.openweathermap_client import OpenWeatherMapClient

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
    title="TFM Chocolate Factory - El Cerebro Autónomo",
    description="Sistema autónomo de ingestión, predicción y monitoreo para fábrica de chocolate",
    version="0.1.0",
    lifespan=lifespan
)

# Configurar CORS para Node-RED dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/aemet/raw-data")
async def get_raw_aemet_data():
    """🌤️ VER DATOS REALES de AEMET Linares - Para verificar con móvil"""
    try:
        async with AEMETClient() as client:
            # Obtener datos de Linares (5279X)
            data = await client._make_request("observacion/convencional/datos/estacion/5279X")
            if 'datos' in data:
                response = await client.client.get(data['datos'])
                response.raise_for_status()
                raw_data = response.json()
                
                if raw_data:
                    latest = raw_data[-1]
                    return {
                        "🏭": "TFM Chocolate Factory",
                        "📍": "Linares, Jaén, Andalucía", 
                        "🌡️": f"{latest.get('ta', 'N/A')}°C",
                        "💧": f"{latest.get('hr', 'N/A')}%",
                        "🌬️": f"{latest.get('vv', 'N/A')} km/h",
                        "☔": f"{latest.get('prec', 0)} mm",
                        "📊": f"{latest.get('pres', 'N/A')} hPa",
                        "🕐": latest.get('fint', 'N/A'),
                        "📡": "AEMET 5279X - LINARES VOR",
                        "raw_complete_data": latest,
                        "total_records_today": len(raw_data),
                        "status": "✅ Datos reales AEMET"
                    }
        
        return {"error": "No data found"}
    except Exception as e:
        return {"error": str(e)}


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
                        "🏭": "TFM Chocolate Factory - OpenWeatherMap",
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
                    "🏭": "TFM Chocolate Factory - OpenWeatherMap",
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
                        "🏭": "TFM Chocolate Factory - OpenWeatherMap Forecast",
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
                    "🏭": "TFM Chocolate Factory - OpenWeatherMap Forecast",
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
                "🏭": "TFM Chocolate Factory - OpenWeatherMap API Status",
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
        use_aemet = (0 <= current_hour <= 7) and not force_openweathermap
        
        async with DataIngestionService() as service:
            if use_aemet:
                # Try AEMET first
                try:
                    aemet_data = await service.ingest_aemet_weather()
                    if aemet_data.successful_writes > 0:
                        return {
                            "🏭": "TFM Chocolate Factory - Estrategia Híbrida",
                            "📍": "Linares, Jaén",
                            "⚡": "AEMET (datos oficiales)",
                            "🕐": f"Hora {current_hour:02d}:xx - Ventana de observación oficial",
                            "status": "✅ Datos AEMET ingestados",
                            "records": aemet_data.successful_writes,
                            "strategy": "aemet_official",
                            "fallback": "OpenWeatherMap disponible si falla AEMET"
                        }
                except Exception:
                    pass  # Fall through to OpenWeatherMap
            
            # Use OpenWeatherMap
            owm_data = await service.ingest_openweathermap_weather()
            source_reason = "ventana tiempo real" if not use_aemet else "fallback por fallo AEMET"
            
            return {
                "🏭": "TFM Chocolate Factory - Estrategia Híbrida", 
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
async def get_weather_comparison():
    """📊 Comparación AEMET vs OpenWeather vs Observaciones reales"""
    return {
        "location": "Linares, Jaén, Andalucía",
        "comparison": {
            "🏭 TU OBSERVACIÓN": {
                "temperature": "35°C actual",
                "max_today": "39°C previsto",
                "conditions": "Ola de calor extrema",
                "humidity": "Muy baja (~15%)",
                "reliability": "⭐⭐⭐⭐⭐ REAL"
            },
            "🇪🇸 AEMET": {
                "temperature": "25.6°C (desfasado)",
                "timestamp": "07:00 AM",
                "conditions": "Datos históricos",
                "humidity": "32%",
                "reliability": "⭐⭐⭐ Oficial pero lento"
            },
            "🌍 OpenWeather": {
                "temperature": "35°C (estimado)",
                "conditions": "Tiempo real",
                "humidity": "~15%",
                "reliability": "⭐⭐⭐⭐ Rápido y actual"
            }
        },
        "recommendation": "Para TFM: AEMET (oficial) + OpenWeather (actualidad) + validación manual",
        "best_for_chocolate": "Usar predicción AEMET para planificación + OpenWeather para ajustes en tiempo real"
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
                                "🏭": "TFM Chocolate Factory - Datos Reales",
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


@app.get("/aemet/test-linares")
async def test_linares_data():
    """PRUEBA: Obtener datos reales de AEMET para Linares sin validación"""
    try:
        async with AEMETClient() as client:
            # Direct API call
            data = await client._make_request("observacion/convencional/datos/estacion/5279X")
            if 'datos' in data:
                datos_response = await client.client.get(data['datos'])
                datos_response.raise_for_status()
                raw_data = datos_response.json()
                
                if raw_data:
                    latest = raw_data[-1] if raw_data else {}
                    return {
                        "status": "success",
                        "message": "🎉 DATOS REALES DE LINARES, JAÉN",
                        "station": "5279X - LINARES, VOR",
                        "data": latest,
                        "total_records": len(raw_data),
                        "timestamp": datetime.now().isoformat()
                    }
        
        return {"status": "error", "message": "No data found"}
    except Exception as e:
        logger.error(f"Test error: {e}")
        return {"status": "error", "message": str(e)}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
