"""
OpenWeatherMap API Client for TFM Chocolate Factory
==================================================

Client for accessing real-time weather data from OpenWeatherMap API v2.5 (free tier).
Provides 24/7 weather coverage to complement AEMET data gaps (08:00-23:00).
Uses Current Weather API and 5-day forecast API.

API Documentation: https://openweathermap.org/current
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
import httpx
from pydantic import BaseModel, Field
from loguru import logger

# Reuse AEMET data model for consistency
from .aemet_client import AEMETWeatherData


class OpenWeatherMapConfig(BaseModel):
    """Configuration for OpenWeatherMap API client"""
    # Using free API v2.5 (no subscription required)
    current_weather_url: str = "https://api.openweathermap.org/data/2.5/weather"
    forecast_url: str = "https://api.openweathermap.org/data/2.5/forecast"
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENWEATHERMAP_API_KEY"))
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 1.0  # seconds between requests
    
    # Linares, Jaén coordinates
    default_lat: float = 38.151107
    default_lon: float = -3.629453
    
    # API parameters
    units: str = "metric"  # Celsius, km/h, etc.


class OpenWeatherMapClient:
    """
    Asynchronous client for OpenWeatherMap API v2.5 (free tier)
    
    Provides methods to fetch real-time weather data:
    - Current weather conditions (updated frequently)
    - 5-day/3-hour forecast
    - Compatible data structure with AEMETWeatherData
    """
    
    def __init__(self, config: Optional[OpenWeatherMapConfig] = None):
        self.config = config or OpenWeatherMapConfig()
        self.client = None
        
        if not self.config.api_key:
            logger.warning("OPENWEATHERMAP_API_KEY not configured. API access will be limited.")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    def _get_params(self, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """Get API request parameters"""
        if not self.config.api_key:
            raise ValueError("OpenWeatherMap API key is required")
        
        return {
            "lat": lat or self.config.default_lat,
            "lon": lon or self.config.default_lon,
            "appid": self.config.api_key,
            "units": self.config.units
        }
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to OpenWeatherMap API with retry logic"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"OpenWeatherMap API request: {url} - Attempt {attempt + 1}")
                
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                
                # Rate limiting
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.rate_limit_delay)
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("OpenWeatherMap API key invalid or expired")
                    raise ValueError("Invalid OpenWeatherMap API key")
                elif e.response.status_code == 429:
                    logger.warning("OpenWeatherMap rate limit exceeded")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(60)  # Wait 1 minute for rate limit
                        continue
                
                logger.warning(f"OpenWeatherMap API request failed (attempt {attempt + 1}): HTTP {e.response.status_code}")
                logger.debug(f"Response content: {e.response.text}")
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                
            except httpx.HTTPError as e:
                logger.warning(f"OpenWeatherMap API request failed (attempt {attempt + 1}): {e}")
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                await asyncio.sleep(2 ** attempt)
    
    def _parse_current_weather(self, data: Dict[str, Any], station_id: str = "openweathermap_linares") -> AEMETWeatherData:
        """Parse current weather data from OpenWeatherMap API v2.5 response"""
        main = data.get("main", {})
        wind = data.get("wind", {})
        
        # Convert timestamp
        timestamp = datetime.fromtimestamp(data.get("dt", 0), tz=timezone.utc)
        
        # Extract weather data
        temperature = main.get("temp")  # Already in Celsius
        humidity = main.get("humidity")  # Percentage
        pressure = main.get("pressure")  # hPa
        wind_speed = wind.get("speed")  # m/s -> convert to km/h
        wind_direction = wind.get("deg")  # degrees
        
        # Convert wind speed from m/s to km/h for consistency with AEMET
        wind_speed_kmh = wind_speed * 3.6 if wind_speed is not None else None
        
        return AEMETWeatherData(
            timestamp=timestamp,
            station_id=station_id,
            station_name="Linares (OpenWeatherMap)",
            province="Jaén",
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            wind_speed=wind_speed_kmh,
            wind_direction=wind_direction,
        )
    
    def _parse_forecast_data(self, data: Dict[str, Any], station_id: str = "openweathermap_linares") -> List[AEMETWeatherData]:
        """Parse 5-day forecast data from OpenWeatherMap API v2.5 response"""
        forecast_list = data.get("list", [])
        weather_list = []
        
        for forecast_item in forecast_list:
            main = forecast_item.get("main", {})
            wind = forecast_item.get("wind", {})
            
            timestamp = datetime.fromtimestamp(forecast_item.get("dt", 0), tz=timezone.utc)
            
            temperature = main.get("temp")
            humidity = main.get("humidity")
            pressure = main.get("pressure")
            wind_speed = wind.get("speed")
            wind_direction = wind.get("deg")
            
            # Convert wind speed from m/s to km/h
            wind_speed_kmh = wind_speed * 3.6 if wind_speed is not None else None
            
            weather_list.append(AEMETWeatherData(
                timestamp=timestamp,
                station_id=station_id,
                station_name="Linares (OpenWeatherMap Forecast)",
                province="Jaén",
                temperature=temperature,
                humidity=humidity,
                pressure=pressure,
                wind_speed=wind_speed_kmh,
                wind_direction=wind_direction,
            ))
        
        return weather_list
    
    async def get_current_weather(self, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[AEMETWeatherData]:
        """
        Get current weather data for specified coordinates
        
        Args:
            lat: Latitude (defaults to Linares, Jaén)
            lon: Longitude (defaults to Linares, Jaén)
            
        Returns:
            AEMETWeatherData object or None if no data
        """
        try:
            params = self._get_params(lat, lon)
            data = await self._make_request(self.config.current_weather_url, params)
            
            logger.info(f"Retrieved current weather from OpenWeatherMap for coords ({params['lat']}, {params['lon']})")
            return self._parse_current_weather(data)
                
        except Exception as e:
            logger.error(f"Failed to fetch current weather from OpenWeatherMap: {e}")
            return None
    
    async def get_forecast(self, hours: int = 24, lat: Optional[float] = None, lon: Optional[float] = None) -> List[AEMETWeatherData]:
        """
        Get forecast data (5 days, 3-hour intervals)
        
        Args:
            hours: Number of forecast hours to retrieve (limited by API response)
            lat: Latitude (defaults to Linares, Jaén)
            lon: Longitude (defaults to Linares, Jaén)
            
        Returns:
            List of AEMETWeatherData objects
        """
        try:
            params = self._get_params(lat, lon)
            data = await self._make_request(self.config.forecast_url, params)
            
            forecast_data = self._parse_forecast_data(data)
            
            # Filter to requested timeframe
            now = datetime.now(timezone.utc)
            end_time = now + timedelta(hours=hours)
            filtered_forecast = [
                item for item in forecast_data 
                if item.timestamp <= end_time
            ]
            
            logger.info(f"Retrieved {len(filtered_forecast)} forecast records from OpenWeatherMap")
            return filtered_forecast
                
        except Exception as e:
            logger.error(f"Failed to fetch forecast from OpenWeatherMap: {e}")
            return []
    
    async def get_api_status(self) -> Dict[str, Any]:
        """Get API status and test connectivity"""
        if not self.config.api_key:
            return {
                "status": "no_api_key",
                "message": "OpenWeatherMap API key not configured"
            }
        
        try:
            # Make a minimal request to check API status
            params = self._get_params()
            data = await self._make_request(self.config.current_weather_url, params)
            
            return {
                "status": "active",
                "api_key_configured": True,
                "current_weather_endpoint": self.config.current_weather_url,
                "forecast_endpoint": self.config.forecast_url,
                "coordinates": f"({self.config.default_lat}, {self.config.default_lon})",
                "location": "Linares, Jaén",
                "sample_temp": data.get("main", {}).get("temp"),
                "api_response_time": data.get("dt")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "api_key_configured": bool(self.config.api_key)
            }


# Utility functions
async def get_openweathermap_client() -> OpenWeatherMapClient:
    """Factory function to create OpenWeatherMap client"""
    return OpenWeatherMapClient()


async def fetch_current_weather_owm() -> Optional[AEMETWeatherData]:
    """Convenience function to fetch current weather from OpenWeatherMap"""
    async with OpenWeatherMapClient() as client:
        return await client.get_current_weather()


async def fetch_forecast_owm(hours: int = 24) -> List[AEMETWeatherData]:
    """Convenience function to fetch forecast from OpenWeatherMap"""
    async with OpenWeatherMapClient() as client:
        return await client.get_forecast(hours)


# Example usage and testing
if __name__ == "__main__":
    async def main():
        async with OpenWeatherMapClient() as client:
            # Check API status
            status = await client.get_api_status()
            print(f"API status: {status}")
            
            if status["status"] == "active":
                # Get current weather
                current = await client.get_current_weather()
                if current:
                    print(f"\nCurrent weather in Linares:")
                    print(f"  Temperature: {current.temperature}°C")
                    print(f"  Humidity: {current.humidity}%")
                    print(f"  Pressure: {current.pressure} hPa")
                    print(f"  Wind: {current.wind_speed} km/h")
                    print(f"  Timestamp: {current.timestamp}")
                
                # Get forecast
                forecast = await client.get_forecast(12)  # Next 12 hours
                print(f"\nForecast: {len(forecast)} records")
                for i, item in enumerate(forecast[:3]):  # Show first 3
                    print(f"  {i+1}. {item.timestamp}: {item.temperature}°C, {item.humidity}%")
    
    asyncio.run(main())