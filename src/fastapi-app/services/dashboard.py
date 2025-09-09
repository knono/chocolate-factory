"""
Chocolate Factory - Dashboard Service
====================================

Servicio para consolidar información del dashboard Node-RED:
- Información actual (precios, clima, producción)
- Predicciones ML (energía, producción)
- Recomendaciones operativas
- Alertas y notificaciones
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .ree_client import REEClient
from .openweathermap_client import OpenWeatherMapClient
from .ml_models import ChocolateMLModels
from .feature_engineering import ChocolateFeatureEngine

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """Estructura de datos consolidada para el dashboard"""
    current_info: Dict[str, Any]
    predictions: Dict[str, Any]
    recommendations: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    timestamp: str


class DashboardService:
    """Servicio principal del dashboard completo"""
    
    def __init__(self, ml_models=None, feature_engine=None):
        self.ree_client = REEClient()
        self.weather_client = OpenWeatherMapClient()
        
        # Use provided instances or create new ones (backward compatibility)
        if ml_models is not None:
            self.ml_models = ml_models
        else:
            self.ml_models = ChocolateMLModels()
            
        if feature_engine is not None:
            self.feature_engine = feature_engine
        else:
            self.feature_engine = ChocolateFeatureEngine()
        
    async def get_complete_dashboard_data(self) -> Dict[str, Any]:
        """Obtiene todos los datos consolidados para el dashboard"""
        try:
            # 1. Información actual
            current_info = await self._get_current_info()
            
            # 2. Predicciones ML
            predictions = await self._get_ml_predictions(current_info)
            
            # 3. Recomendaciones
            recommendations = self._generate_recommendations(current_info, predictions)
            
            # 4. Alertas
            alerts = self._generate_alerts(current_info, predictions)
            
            # 5. Pronóstico semanal con heatmap
            weekly_forecast = await self._get_weekly_forecast_heatmap()
            
            dashboard_data = {
                "🏢": "Chocolate Factory - Dashboard Completo",
                "📊": "El Monitor - Información, Predicción y Recomendaciones (Direct ML)",
                "current_info": current_info,
                "predictions": predictions,
                "recommendations": recommendations,
                "alerts": alerts,
                "weekly_forecast": weekly_forecast,
                "system_status": {
                    "status": "✅ Operativo",
                    "last_update": datetime.now().isoformat(),
                    "data_sources": {
                        "ree": "✅ Conectado",
                        "weather": "✅ Conectado", 
                        "ml_models": "✅ Modelos cargados (Direct ML)"
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("✅ Dashboard data consolidated successfully")
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data: {e}")
            raise
    
    async def _get_current_info(self) -> Dict[str, Any]:
        """Obtiene información actual de precios y clima"""
        try:
            # Precios REE actuales (últimas 2 horas)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)
            
            async with self.ree_client as ree:
                ree_data = await ree.get_pvpc_prices(start_date=start_time, end_date=end_time)
            current_price = None
            if ree_data and len(ree_data) > 0:
                current_price = {
                    "price_eur_mwh": ree_data[0].price_eur_mwh,
                    "price_eur_kwh": round(ree_data[0].price_eur_mwh / 1000, 4),
                    "datetime": ree_data[0].timestamp.isoformat(),
                    "trend": self._calculate_price_trend(ree_data)
                }
            
            # Clima actual
            async with self.weather_client as weather:
                weather_data = await weather.get_current_weather()
            current_weather = None
            if weather_data:
                # weather_data is an AEMETWeatherData object
                current_weather = {
                    "temperature": weather_data.temperature,
                    "humidity": weather_data.humidity,
                    "pressure": weather_data.pressure,
                    "description": "Current conditions",
                    "comfort_index": self._calculate_comfort_index(
                        weather_data.temperature, 
                        weather_data.humidity
                    )
                }
            
            current_info = {
                "energy": current_price,
                "weather": current_weather,
                "production_status": "🟢 Operativo",  # TODO: Integrar con datos reales
                "factory_efficiency": 85.2  # TODO: Calcular basado en condiciones
            }
            
            return current_info
            
        except Exception as e:
            logger.error(f"❌ Error getting current info: {e}")
            return {}
    
    async def _get_ml_predictions(self, current_info: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene predicciones ML basadas en datos actuales"""
        try:
            predictions = {}
            
            if current_info.get("energy") and current_info.get("weather"):
                # Preparar datos para predicción
                price = current_info["energy"]["price_eur_kwh"]
                temp = current_info["weather"]["temperature"]
                humidity = current_info["weather"]["humidity"]
                
                # Usar endpoints directos para predicciones ML
                import httpx
                
                # Predicción de optimización energética
                async with httpx.AsyncClient() as client:
                    energy_response = await client.post(
                        "http://localhost:8000/predict/energy-optimization",
                        json={"price_eur_kwh": price, "temperature": temp, "humidity": humidity}
                    )
                    energy_pred = energy_response.json() if energy_response.status_code == 200 else {}
                
                # Predicción de recomendación de producción  
                async with httpx.AsyncClient() as client:
                    prod_response = await client.post(
                        "http://localhost:8000/predict/production-recommendation", 
                        json={"price_eur_kwh": price, "temperature": temp, "humidity": humidity}
                    )
                    production_pred = prod_response.json() if prod_response.status_code == 200 else {}
                
                predictions = {
                    "energy_optimization": {
                        "score": energy_pred.get("prediction", {}).get("energy_optimization_score", 0),
                        # Removed confidence field as it's always "unknown"
                        "recommendation": energy_pred.get("prediction", {}).get("recommendation", "unknown")
                    },
                    "production_recommendation": {
                        "class": production_pred.get("prediction", {}).get("production_recommendation", "Unknown"),
                        "confidence": production_pred.get("analysis", {}).get("overall_score", 0),
                        "action": production_pred.get("prediction", {}).get("description", "Unknown")
                    },
                    "next_hour_forecast": await self._get_next_hour_forecast()
                }
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Error getting ML predictions: {e}")
            return {}
    
    def _generate_recommendations(self, current_info: Dict[str, Any], predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Genera recomendaciones operativas"""
        recommendations = {
            "energy": [],
            "production": [],
            "maintenance": [],
            "priority": []
        }
        
        try:
            # Recomendaciones energéticas unificadas (precio tiene prioridad sobre ML score)
            if current_info.get("energy"):
                price = current_info["energy"]["price_eur_kwh"]
                ml_score = predictions.get("energy_optimization", {}).get("score", 50)
                
                # PRIORIDAD 1: Precio de electricidad (factor más crítico)
                if price > 0.25:  # Luz muy cara
                    recommendations["energy"].append("🔴 PRECIO MUY ALTO ({:.3f} €/kWh): Reducir producción inmediatamente".format(price))
                    recommendations["energy"].append("💡 Programar producción en turno de noche (22:00-06:00)")
                    recommendations["energy"].append("⏰ Considerar turno de madrugada (00:00-07:00) para máximo ahorro")
                elif price > 0.20:  # Precio alto
                    recommendations["energy"].append("⚠️ PRECIO ELEVADO ({:.3f} €/kWh): Evaluar reducir operaciones no críticas".format(price))
                    recommendations["energy"].append("🌙 Turno de noche recomendado para procesos intensivos")
                elif price > 0.15:  # Precio medio
                    recommendations["energy"].append("🟡 PRECIO MEDIO ({:.3f} €/kWh): Producción normal, monitorear evolución".format(price))
                elif price < 0.12:  # Luz barata
                    recommendations["energy"].append("💚 PRECIO BAJO ({:.3f} €/kWh): MAXIMIZAR PRODUCCIÓN".format(price))
                    recommendations["energy"].append("🚀 Momento ideal para procesos energéticamente intensivos")
                    recommendations["energy"].append("⚡ Aprovechar para producción de reservas y stock")
                else:  # Precio normal-bajo (0.12-0.15)
                    recommendations["energy"].append("🟢 PRECIO FAVORABLE ({:.3f} €/kWh): Producción intensiva recomendada".format(price))
                    recommendations["energy"].append("📈 Condiciones buenas para incrementar volumen")
                
                # PRIORIDAD 2: Validación con ML score (solo si no contradice el precio)
                if price < 0.15:  # Solo para precios favorables
                    if ml_score > 80:
                        recommendations["energy"].append("🤖 ML: Score excelente ({:.0f}/100) confirma momento óptimo".format(ml_score))
                    elif ml_score < 40 and price > 0.12:  # Solo advertir si precio no es muy barato
                        recommendations["energy"].append("🤖 ML: Score bajo ({:.0f}/100) - revisar condiciones".format(ml_score))
            
            # Recomendaciones de producción (coherentes con precio energético)
            if predictions.get("production_recommendation"):
                prod_class = predictions["production_recommendation"]["class"]
                confidence = predictions["production_recommendation"].get("confidence", 0)
                price = current_info.get("energy", {}).get("price_eur_kwh", 0.15)
                
                # Normalizar nombre de clase (remover sufijos)
                prod_class_clean = prod_class.replace("_Production", "")
                
                # Ajustar recomendación de producción según precio energético
                if price < 0.12:  # Precio muy bajo - priorizar producción
                    if prod_class_clean == "Optimal":
                        recommendations["production"].append("🚀 CONDICIONES IDEALES: Maximizar producción (precio energético favorable)")
                    elif prod_class_clean == "Moderate":
                        recommendations["production"].append("📈 INCREMENTAR producción - Precio energético muy favorable compensa condiciones")
                    elif prod_class_clean == "Reduced":
                        recommendations["production"].append("⚖️ Mantener producción estándar - Precio energético compensa condiciones subóptimas")
                    else:  # Halt
                        recommendations["production"].append("⚠️ Evaluar producción mínima - Solo por precio energético excepcional")
                elif price > 0.20:  # Precio alto - ser conservador
                    if prod_class_clean == "Optimal":
                        recommendations["production"].append("⚖️ Producción estándar - Precio energético alto limita expansión")
                    elif prod_class_clean == "Moderate":
                        recommendations["production"].append("📉 Reducir producción - Precio energético alto + condiciones moderadas")
                    else:
                        recommendations["production"].append("⛔ REDUCIR/PARAR producción - Costos energéticos prohibitivos")
                else:  # Precio normal (0.12-0.20)
                    if prod_class_clean == "Optimal":
                        recommendations["production"].append("🚀 Condiciones óptimas - Maximizar producción")
                    elif prod_class_clean == "Moderate":
                        recommendations["production"].append("⚖️ Mantener producción estándar")
                    elif prod_class_clean == "Reduced":
                        recommendations["production"].append("📉 Reducir producción - Condiciones subóptimas")
                    else:
                        recommendations["production"].append("⛔ Considerar parar producción")
                
                # Agregar confianza del modelo
                if confidence > 80:
                    recommendations["production"].append("🎯 Alta confianza ML ({:.0f}%) en recomendación".format(confidence))
                elif confidence < 50:
                    recommendations["production"].append("🤔 Baja confianza ML ({:.0f}%) - Validar con operador".format(confidence))
            
            # Recomendaciones de clima
            if current_info.get("weather"):
                temp = current_info["weather"]["temperature"]
                humidity = current_info["weather"]["humidity"]
                
                if temp > 35:
                    recommendations["priority"].append("🌡️ ALTA TEMPERATURA: Activar refrigeración adicional")
                if humidity > 80:
                    recommendations["priority"].append("💧 ALTA HUMEDAD: Verificar sistema de deshumidificación")
                if temp < 15:
                    recommendations["priority"].append("❄️ BAJA TEMPERATURA: Verificar calefacción de áreas críticas")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            return recommendations
    
    def _generate_alerts(self, current_info: Dict[str, Any], predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera alertas basadas en condiciones críticas"""
        alerts = []
        
        try:
            # Alertas de energía
            if current_info.get("energy"):
                price = current_info["energy"]["price_eur_kwh"]
                if price > 0.30:
                    alerts.append({
                        "type": "energy",
                        "level": "high",
                        "message": f"💰 PRECIO ENERGÍA ALTO: {price:.3f} €/kWh",
                        "action": "Considerar reducir producción"
                    })
                elif price < 0.10:
                    alerts.append({
                        "type": "energy", 
                        "level": "info",
                        "message": f"💚 PRECIO ENERGÍA BAJO: {price:.3f} €/kWh",
                        "action": "Oportunidad para producción intensiva"
                    })
            
            # Alertas de clima
            if current_info.get("weather"):
                temp = current_info["weather"]["temperature"]
                humidity = current_info["weather"]["humidity"]
                
                if temp > 40:
                    alerts.append({
                        "type": "weather",
                        "level": "critical",
                        "message": f"🌡️ TEMPERATURA CRÍTICA: {temp}°C",
                        "action": "Activar protocolos de emergencia térmica"
                    })
                
                if humidity > 85:
                    alerts.append({
                        "type": "weather",
                        "level": "warning", 
                        "message": f"💧 HUMEDAD MUY ALTA: {humidity}%",
                        "action": "Monitorear calidad del chocolate"
                    })
            
            # Alertas de predicción
            if predictions.get("production_recommendation"):
                if predictions["production_recommendation"]["class"] == "Halt":
                    alerts.append({
                        "type": "production",
                        "level": "critical",
                        "message": "⛔ RECOMENDACIÓN: PARAR PRODUCCIÓN",
                        "action": "Evaluar condiciones antes de continuar"
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Error generating alerts: {e}")
            return []
    
    def _calculate_price_trend(self, price_data: List) -> str:
        """Calcula tendencia de precios"""
        if len(price_data) < 2:
            return "stable"
        
        current = price_data[0].price_eur_mwh
        previous = price_data[1].price_eur_mwh if len(price_data) > 1 else current
        
        if current > previous * 1.05:
            return "rising"
        elif current < previous * 0.95:
            return "falling"
        else:
            return "stable"
    
    def _calculate_comfort_index(self, temp: float, humidity: float) -> str:
        """Calcula índice de confort para producción de chocolate"""
        # Condiciones óptimas: 18-22°C, 45-65% humedad
        temp_score = 100 - abs(temp - 20) * 5
        humidity_score = 100 - abs(humidity - 55) * 2
        overall = (temp_score + humidity_score) / 2
        
        if overall > 80:
            return "Óptimo"
        elif overall > 60:
            return "Bueno"
        elif overall > 40:
            return "Regular"
        else:
            return "Crítico"
    
    def _interpret_energy_score(self, score: float) -> str:
        """Interpreta puntuación de optimización energética"""
        if score > 80:
            return "Excelente momento para producir"
        elif score > 60:
            return "Momento favorable"
        elif score > 40:
            return "Momento neutro"
        else:
            return "Momento desfavorable"
    
    def _interpret_production_class(self, class_name: str) -> str:
        """Interpreta clase de recomendación de producción"""
        actions = {
            "Optimal": "Maximizar producción",
            "Moderate": "Producción estándar",
            "Reduced": "Reducir producción",
            "Halt": "Parar producción"
        }
        return actions.get(class_name, "Evaluar condiciones")
    
    async def _get_weekly_forecast_heatmap(self) -> Dict[str, Any]:
        """Genera datos de pronóstico semanal con heatmap para calendario"""
        try:
            import httpx
            from .aemet_client import AEMETClient
            from .openweathermap_client import OpenWeatherMapClient
            
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # === 1. OBTENER DATOS DE PRECIOS ELÉCTRICOS ===
            electricity_data = []
            
            try:
                # Intentar obtener precios REE recientes para generar tendencias
                recent_prices = await self.ree_client.get_prices_last_hours(48)
                if recent_prices:
                    recent_avg = sum(p.price_eur_mwh for p in recent_prices) / len(recent_prices)
                    
                    # Generar predicción semanal basada en patrones
                    for day in range(7):
                        forecast_date = start_date + timedelta(days=day)
                        
                        # Simular variación diaria (más alta en días laborables)
                        is_weekend = forecast_date.weekday() >= 5
                        base_factor = 0.85 if is_weekend else 1.0
                        
                        # Variación aleatoria realista (+/- 15%)
                        import random
                        random.seed(forecast_date.day)  # Reproducible
                        variation = 1.0 + (random.random() - 0.5) * 0.3
                        
                        daily_avg_price = (recent_avg * base_factor * variation) / 1000  # Convert to EUR/kWh
                        
                        electricity_data.append({
                            "date": forecast_date.strftime("%Y-%m-%d"),
                            "weekday": forecast_date.strftime("%A")[:3],
                            "avg_price_eur_kwh": round(daily_avg_price, 4),
                            "is_weekend": is_weekend
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to get REE prices for heatmap: {e}")
            
            # === 2. OBTENER DATOS METEOROLÓGICOS ===
            weather_data = []
            
            try:
                # Usar OpenWeatherMap para pronóstico (5 días disponibles)
                async with OpenWeatherMapClient() as owm_client:
                    owm_forecast = await owm_client.get_forecast(120)  # 5 días
                    
                    # Agrupar por días
                    daily_weather = {}
                    for record in owm_forecast:
                        date_key = record.timestamp.strftime("%Y-%m-%d")
                        if date_key not in daily_weather:
                            daily_weather[date_key] = []
                        daily_weather[date_key].append(record)
                    
                    # Calcular promedios diarios
                    for date, records in daily_weather.items():
                        temps = [r.temperature for r in records if r.temperature is not None]
                        humidity = [r.humidity for r in records if r.humidity is not None]
                        
                        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
                        avg_humidity = round(sum(humidity) / len(humidity), 1) if humidity else None
                        
                        weather_data.append({
                            "date": date,
                            "avg_temperature": avg_temp,
                            "avg_humidity": avg_humidity,
                            "records_count": len(records)
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to get weather data for heatmap: {e}")
            
            # === 3. COMBINAR DATOS Y CREAR HEATMAP ===
            calendar_days = []
            
            for day in range(7):
                forecast_date = start_date + timedelta(days=day)
                date_str = forecast_date.strftime("%Y-%m-%d")
                
                # Buscar datos de electricidad
                elec_data = next((e for e in electricity_data if e["date"] == date_str), None)
                
                # Buscar datos meteorológicos
                weather = next((w for w in weather_data if w["date"] == date_str), None)
                
                # Determinar zona de calor basada en precio
                price = elec_data["avg_price_eur_kwh"] if elec_data else 0.15
                if price <= 0.10:
                    heat_zone = "low"
                    heat_color = "#4CAF50"  # Verde
                elif price <= 0.20:
                    heat_zone = "medium"  
                    heat_color = "#FF9800"  # Naranja
                else:
                    heat_zone = "high"
                    heat_color = "#F44336"  # Rojo
                
                # Determinar recomendación operativa
                temp = weather["avg_temperature"] if weather else 20
                if temp < 15 or price <= 0.10:
                    recommendation = "Optimal"
                elif temp > 30 or price >= 0.25:
                    recommendation = "Reduced"
                else:
                    recommendation = "Moderate"
                
                calendar_days.append({
                    "date": date_str,
                    "day_name": forecast_date.strftime("%A"),
                    "day_short": forecast_date.strftime("%a"),
                    "day_number": forecast_date.day,
                    "is_today": day == 0,
                    "is_weekend": forecast_date.weekday() >= 5,
                    
                    # Datos de precio
                    "avg_price_eur_kwh": price,
                    "price_trend": "stable",
                    
                    # Datos meteorológicos
                    "avg_temperature": temp,
                    "avg_humidity": weather["avg_humidity"] if weather else 50,
                    
                    # Heatmap visual
                    "heat_zone": heat_zone,
                    "heat_color": heat_color,
                    "heat_intensity": min(price * 10, 10),  # Scale 0-10
                    
                    # Recomendación
                    "production_recommendation": recommendation,
                    "recommendation_icon": {
                        "Optimal": "🟢",
                        "Moderate": "🟡", 
                        "Reduced": "🟠",
                        "Halt": "🔴"
                    }.get(recommendation, "⚪")
                })
            
            # === 4. ESTADÍSTICAS GENERALES ===
            prices = [day["avg_price_eur_kwh"] for day in calendar_days]
            temps = [day["avg_temperature"] for day in calendar_days if day["avg_temperature"]]
            
            summary = {
                "period": {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": (start_date + timedelta(days=6)).strftime("%Y-%m-%d"),
                    "total_days": 7
                },
                "price_summary": {
                    "min_price": round(min(prices), 4) if prices else 0,
                    "max_price": round(max(prices), 4) if prices else 0,
                    "avg_price": round(sum(prices) / len(prices), 4) if prices else 0
                },
                "weather_summary": {
                    "min_temp": round(min(temps), 1) if temps else 0,
                    "max_temp": round(max(temps), 1) if temps else 0,
                    "avg_temp": round(sum(temps) / len(temps), 1) if temps else 0
                },
                "optimal_days": len([d for d in calendar_days if d["production_recommendation"] == "Optimal"]),
                "warning_days": len([d for d in calendar_days if d["heat_zone"] == "high"])
            }
            
            return {
                "status": "success",
                "title": "📅 Pronóstico Semanal - Mini Calendario Heatmap",
                "calendar_days": calendar_days,
                "summary": summary,
                "heatmap_legend": {
                    "low": {"color": "#4CAF50", "label": "Precio Bajo (≤0.10 €/kWh)", "icon": "🟢"},
                    "medium": {"color": "#FF9800", "label": "Precio Medio (0.10-0.20 €/kWh)", "icon": "🟡"},
                    "high": {"color": "#F44336", "label": "Precio Alto (>0.20 €/kWh)", "icon": "🔴"}
                },
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating weekly forecast heatmap: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate weekly forecast: {str(e)}",
                "calendar_days": [],
                "summary": {}
            }
    
    async def _get_next_hour_forecast(self) -> Dict[str, Any]:
        """Obtiene pronóstico para la próxima hora"""
        try:
            # TODO: Implementar pronóstico de precios y clima
            return {
                "energy_trend": "stable",
                "weather_trend": "stable",
                "production_outlook": "favorable"
            }
        except Exception as e:
            logger.error(f"❌ Error getting forecast: {e}")
            return {}


# Singleton service
_dashboard_service = None

def get_dashboard_service() -> DashboardService:
    """Obtiene instancia singleton del servicio de dashboard"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service