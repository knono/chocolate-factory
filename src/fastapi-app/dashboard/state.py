"""
Estado global del Dashboard Reflex
"""

import reflex as rx
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import asyncio


class DashboardState(rx.State):
    """Estado principal del dashboard con datos en tiempo real"""
    
    # Datos actuales
    current_energy_price: float = 0.0
    current_temperature: float = 0.0
    current_humidity: float = 0.0
    price_trend: str = "stable"
    
    # Predicciones ML
    energy_optimization_score: float = 0.0
    production_recommendation: str = "Unknown"
    production_confidence: float = 0.0
    
    # Alertas y estado
    alerts: List[Dict[str, Any]] = []
    last_update: str = ""
    system_status: str = "🔄 Conectando..."
    
    # Datos históricos para gráficas (últimas 24h)
    price_history: List[Dict[str, Any]] = []
    temp_history: List[Dict[str, Any]] = []
    
    # Estado de conexión
    is_connected: bool = False
    error_message: str = ""
    
    async def load_dashboard_data(self):
        """Carga datos completos del dashboard desde FastAPI"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8000/dashboard/complete")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Actualizar información actual
                    current_info = data.get("current_info", {})
                    if current_info.get("energy"):
                        self.current_energy_price = current_info["energy"].get("price_eur_kwh", 0.0)
                        self.price_trend = current_info["energy"].get("trend", "stable")
                        
                    if current_info.get("weather"):
                        self.current_temperature = current_info["weather"].get("temperature", 0.0)
                        self.current_humidity = current_info["weather"].get("humidity", 0.0)
                    
                    # Actualizar predicciones ML
                    predictions = data.get("predictions", {})
                    if predictions.get("energy_optimization"):
                        self.energy_optimization_score = predictions["energy_optimization"].get("score", 0.0)
                        
                    if predictions.get("production_recommendation"):
                        self.production_recommendation = predictions["production_recommendation"].get("class", "Unknown")
                        self.production_confidence = predictions["production_recommendation"].get("confidence", 0.0)
                    
                    # Actualizar alertas
                    self.alerts = data.get("alerts", [])
                    
                    # Estado del sistema
                    self.system_status = "✅ Operativo"
                    self.is_connected = True
                    self.error_message = ""
                    self.last_update = datetime.now().strftime("%H:%M:%S")
                    
                else:
                    self.is_connected = False
                    self.system_status = "❌ Error conexión"
                    self.error_message = f"HTTP {response.status_code}"
                    
        except Exception as e:
            self.is_connected = False
            self.system_status = "❌ Sin conexión"
            self.error_message = str(e)
            
    async def load_historical_data(self):
        """Carga datos históricos para gráficas"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Datos de precios últimas 24h
                price_response = await client.get(
                    "http://localhost:8000/influxdb/query",
                    params={"measurement": "ree_prices", "hours_back": 24}
                )
                
                if price_response.status_code == 200:
                    price_data = price_response.json()
                    self.price_history = [
                        {
                            "time": point.get("time", ""),
                            "price": point.get("price_eur_kwh", 0.0)
                        }
                        for point in price_data.get("data", [])[-24:]  # Últimas 24 horas
                    ]
                
                # Datos de temperatura últimas 24h
                temp_response = await client.get(
                    "http://localhost:8000/influxdb/query", 
                    params={"measurement": "weather_data", "hours_back": 24}
                )
                
                if temp_response.status_code == 200:
                    temp_data = temp_response.json()
                    self.temp_history = [
                        {
                            "time": point.get("time", ""),
                            "temperature": point.get("temperature", 0.0)
                        }
                        for point in temp_data.get("data", [])[-24:]  # Últimas 24 horas
                    ]
                    
        except Exception as e:
            # Silenciar errores de datos históricos - no críticos
            pass
            
    def get_price_color(self) -> str:
        """Retorna color según precio de energía"""
        if self.current_energy_price > 0.25:
            return "red"
        elif self.current_energy_price > 0.15:
            return "yellow"
        else:
            return "green"
            
    def get_temp_status(self) -> str:
        """Retorna estado según temperatura"""
        if self.current_temperature > 35:
            return "🌡️ Alta"
        elif self.current_temperature < 15:
            return "❄️ Baja"
        else:
            return "✅ Óptima"
            
    def get_humidity_status(self) -> str:
        """Retorna estado según humedad"""
        if self.current_humidity > 80:
            return "💧 Alta"
        elif self.current_humidity < 30:
            return "🏜️ Baja"
        else:
            return "✅ Óptima"
            
    def get_production_status_icon(self) -> str:
        """Retorna icono según recomendación de producción"""
        status_icons = {
            "Optimal": "🚀",
            "Moderate": "⚖️", 
            "Reduced": "📉",
            "Halt": "⛔"
        }
        return status_icons.get(self.production_recommendation, "❓")
        
    def get_alert_count_by_level(self, level: str) -> int:
        """Cuenta alertas por nivel de criticidad"""
        return len([alert for alert in self.alerts if alert.get("level") == level])
        
    @rx.background
    async def auto_refresh_data(self):
        """Refresco automático de datos cada 5 minutos"""
        while True:
            await asyncio.sleep(300)  # 5 minutos
            async with self:
                await self.load_dashboard_data()
                await self.load_historical_data()