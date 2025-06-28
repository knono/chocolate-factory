"""
AEMET API Client for TFM Chocolate Factory
==========================================

Client for accessing Spanish weather data from AEMET (Agencia Estatal de Meteorología).
Handles automatic token renewal every 6 days and provides weather data relevant for
chocolate factory operations (temperature, humidity, pressure).

API Documentation: https://opendata.aemet.es/centrodedescargas/inicio
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import httpx
from pydantic import BaseModel, Field, validator
from loguru import logger


class AEMETConfig(BaseModel):
    """Configuration for AEMET API client"""
    base_url: str = "https://opendata.aemet.es/opendata/api"
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("AEMET_API_KEY"))
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 1.0  # seconds between requests
    token_validity_days: int = 6  # AEMET tokens expire every 6 days
    token_file_path: str = "/app/data/aemet_token_cache.json"


class AEMETTokenInfo(BaseModel):
    """Model for AEMET token information"""
    token: str
    created_at: datetime
    expires_at: datetime
    api_key_hash: str  # To detect if API key changed
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def expires_soon(self) -> bool:
        """Check if token expires within 1 hour"""
        one_hour = datetime.now(timezone.utc) + timedelta(hours=1)
        return one_hour >= self.expires_at


class AEMETWeatherData(BaseModel):
    """Model for AEMET weather data"""
    timestamp: datetime
    station_id: str
    station_name: Optional[str] = None
    province: Optional[str] = None
    altitude: Optional[float] = None
    
    # Temperature data
    temperature: Optional[float] = None  # °C
    temperature_max: Optional[float] = None  # °C
    temperature_min: Optional[float] = None  # °C
    
    # Humidity data
    humidity: Optional[float] = None  # %
    humidity_max: Optional[float] = None  # %
    humidity_min: Optional[float] = None  # %
    
    # Pressure data
    pressure: Optional[float] = None  # hPa
    pressure_max: Optional[float] = None  # hPa
    pressure_min: Optional[float] = None  # hPa
    
    # Wind data
    wind_speed: Optional[float] = None  # km/h
    wind_direction: Optional[float] = None  # degrees
    wind_gust: Optional[float] = None  # km/h
    
    # Precipitation
    precipitation: Optional[float] = None  # mm
    
    # Solar radiation (important for chocolate production)
    solar_radiation: Optional[float] = None  # W/m²
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v


class AEMETClient:
    """
    Asynchronous client for AEMET (Spanish Weather Service) API
    
    Provides methods to fetch weather data with automatic token management:
    - Automatic token renewal every 6 days
    - Token caching to disk
    - Weather station data
    - Historical and current weather data
    """
    
    def __init__(self, config: Optional[AEMETConfig] = None):
        self.config = config or AEMETConfig()
        self.client = None
        self._current_token: Optional[str] = None
        
        if not self.config.api_key:
            logger.warning("AEMET_API_KEY not configured. API access will be limited.")
        
        # Create data directory if needed
        os.makedirs(os.path.dirname(self.config.token_file_path), exist_ok=True)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=self.config.timeout)
        await self._ensure_valid_token()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    def _get_api_key_hash(self) -> str:
        """Get hash of API key for cache validation"""
        import hashlib
        if not self.config.api_key:
            return ""
        return hashlib.md5(self.config.api_key.encode()).hexdigest()[:8]
    
    def _load_cached_token(self) -> Optional[AEMETTokenInfo]:
        """Load cached token from disk"""
        try:
            if os.path.exists(self.config.token_file_path):
                with open(self.config.token_file_path, 'r') as f:
                    data = json.load(f)
                    
                token_info = AEMETTokenInfo(
                    token=data['token'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    expires_at=datetime.fromisoformat(data['expires_at']),
                    api_key_hash=data.get('api_key_hash', '')
                )
                
                # Validate token is for current API key
                if token_info.api_key_hash != self._get_api_key_hash():
                    logger.warning("Cached token is for different API key, ignoring")
                    return None
                
                return token_info
        
        except Exception as e:
            logger.warning(f"Failed to load cached token: {e}")
        
        return None
    
    def _save_token_cache(self, token_info: AEMETTokenInfo) -> None:
        """Save token to disk cache"""
        try:
            data = {
                'token': token_info.token,
                'created_at': token_info.created_at.isoformat(),
                'expires_at': token_info.expires_at.isoformat(),
                'api_key_hash': token_info.api_key_hash
            }
            
            with open(self.config.token_file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Token cached to {self.config.token_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save token cache: {e}")
    
    async def _request_new_token(self) -> str:
        """Request new token from AEMET API"""
        if not self.config.api_key:
            raise ValueError("AEMET API key is required for token generation")
        
        logger.info("Using AEMET API key as token (AEMET uses API key directly)")
        
        # For AEMET OpenData, the API key itself IS the token
        # No separate token request is needed
        token = self.config.api_key
        logger.info("AEMET token set successfully")
        return token
    
    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid token, renewing if necessary"""
        
        # Check cached token first
        cached_token = self._load_cached_token()
        
        if cached_token and not cached_token.is_expired and not cached_token.expires_soon:
            logger.debug("Using valid cached AEMET token")
            self._current_token = cached_token.token
            return self._current_token
        
        if cached_token and cached_token.expires_soon:
            logger.info("AEMET token expires soon, renewing...")
        elif cached_token and cached_token.is_expired:
            logger.info("AEMET token expired, renewing...")
        else:
            logger.info("No valid cached AEMET token found, requesting new one...")
        
        # Request new token
        new_token = await self._request_new_token()
        
        # Create token info and cache it
        now = datetime.now(timezone.utc)
        token_info = AEMETTokenInfo(
            token=new_token,
            created_at=now,
            expires_at=now + timedelta(days=self.config.token_validity_days),
            api_key_hash=self._get_api_key_hash()
        )
        
        self._save_token_cache(token_info)
        self._current_token = new_token
        
        logger.info(f"New AEMET token valid until: {token_info.expires_at}")
        return self._current_token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for AEMET API requests"""
        headers = {
            "Accept": "application/json",
            "User-Agent": "TFM-Chocolate-Factory/1.0",
            "cache-control": "no-cache"
        }
        
        # Add API key to headers if available
        if self._current_token:
            headers["Authorization"] = f"Bearer {self._current_token}"
        
        return headers
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to AEMET API with retry logic"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Ensure we have a valid token
        await self._ensure_valid_token()
        
        url = f"{self.config.base_url}/{endpoint}"
        
        # API key is now in headers, not params
        if params is None:
            params = {}
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"AEMET API request: {url} - Attempt {attempt + 1}")
                
                response = await self.client.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                
                # Rate limiting
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.rate_limit_delay)
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.warning("AEMET token invalid, requesting new one...")
                    await self._request_new_token()
                
                logger.warning(f"AEMET API request failed (attempt {attempt + 1}): HTTP {e.response.status_code} - {e}")
                logger.debug(f"Response content: {e.response.text}")
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                
            except httpx.HTTPError as e:
                logger.warning(f"AEMET API request failed (attempt {attempt + 1}): {e}")
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                await asyncio.sleep(2 ** attempt)
    
    async def get_weather_stations(self, province_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of weather stations
        
        Args:
            province_code: Optional province code to filter stations
            
        Returns:
            List of weather station information
        """
        # Use conventional observation stations endpoint
        endpoint = "maestros/observacion/convencional/estaciones"
        
        try:
            data = await self._make_request(endpoint)
            
            # AEMET returns a 'datos' URL that needs to be fetched
            if 'datos' in data:
                datos_response = await self.client.get(data['datos'])
                datos_response.raise_for_status()
                stations = datos_response.json()
                
                logger.info(f"Retrieved {len(stations)} weather stations from AEMET")
                return stations
            else:
                logger.warning("No 'datos' field in stations response")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch weather stations: {e}")
            raise
    
    async def get_current_weather(self, station_id: str) -> Optional[AEMETWeatherData]:
        """
        Get current weather data for a specific station
        
        Args:
            station_id: Weather station identifier
            
        Returns:
            AEMETWeatherData object or None if no data
        """
        endpoint = f"observacion/convencional/datos/estacion/{station_id}"
        
        try:
            data = await self._make_request(endpoint)
            
            if 'datos' in data:
                datos_response = await self.client.get(data['datos'])
                datos_response.raise_for_status()
                weather_data = datos_response.json()
                
                if weather_data:
                    # Parse the most recent record
                    latest_record = weather_data[-1] if weather_data else {}
                    
                    # Debug: Log the raw response structure
                    logger.error(f"Raw AEMET record for station {station_id}: {latest_record}")
                    
                    # Parse timestamp safely
                    timestamp_str = latest_record.get('fint', datetime.now().isoformat())
                    if timestamp_str and timestamp_str != "":
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            timestamp = datetime.now()
                    else:
                        timestamp = datetime.now()
                    
                    # Parse all string fields safely - convert numbers to None
                    def safe_string(value):
                        if isinstance(value, (int, float)):
                            return None
                        return value
                    
                    # Check all field values before creating the object
                    field_values = {
                        'timestamp': timestamp,
                        'station_id': station_id,
                        'station_name': safe_string(latest_record.get('ubi')),
                        'province': "Jaén",
                        'temperature': latest_record.get('ta'),
                        'temperature_max': latest_record.get('tamax'),
                        'temperature_min': latest_record.get('tamin'),
                        'humidity': latest_record.get('hr'),
                        'pressure': latest_record.get('pres'),
                        'wind_speed': latest_record.get('vv'),
                        'wind_direction': latest_record.get('dv'),
                        'precipitation': latest_record.get('prec')
                    }
                    
                    logger.error(f"Field values before creating AEMETWeatherData: {field_values}")
                    
                    # Create the weather data object with safer field handling
                    try:
                        return AEMETWeatherData(**field_values)
                    except Exception as validation_error:
                        logger.error(f"Validation error for AEMET data: {validation_error}")
                        logger.error(f"Field values causing validation error: {field_values}")
                        raise
                
        except Exception as e:
            logger.error(f"Failed to fetch current weather for station {station_id}: {e}")
            return None
    
    async def get_daily_weather(self, start_date: datetime, end_date: datetime,
                               station_id: Optional[str] = None) -> List[AEMETWeatherData]:
        """
        Get daily weather data for a date range
        
        Args:
            start_date: Start date for data query
            end_date: End date for data query
            station_id: Optional specific station ID
            
        Returns:
            List of AEMETWeatherData objects
        """
        # Format dates for AEMET API
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SUTC")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SUTC")
        
        if station_id:
            endpoint = f"valores/climatologicos/diarios/datos/fechaini/{start_str}/fechafin/{end_str}/estacion/{station_id}"
        else:
            endpoint = f"valores/climatologicos/diarios/datos/fechaini/{start_str}/fechafin/{end_str}/todasestaciones"
        
        try:
            data = await self._make_request(endpoint)
            
            if 'datos' in data:
                datos_response = await self.client.get(data['datos'])
                datos_response.raise_for_status()
                weather_records = datos_response.json()
                
                weather_data = []
                for record in weather_records:
                    weather_data.append(AEMETWeatherData(
                        timestamp=datetime.fromisoformat(record.get('fecha', datetime.now().isoformat())),
                        station_id=record.get('indicativo', ''),
                        station_name=record.get('nombre'),
                        province=record.get('provincia'),
                        altitude=record.get('altitud'),
                        temperature=record.get('tmed'),
                        temperature_max=record.get('tmax'),
                        temperature_min=record.get('tmin'),
                        humidity=record.get('hrMedia'),
                        pressure=record.get('presMedia'),
                        wind_speed=record.get('vvMedia'),
                        precipitation=record.get('prec'),
                        solar_radiation=record.get('sol')
                    ))
                
                logger.info(f"Retrieved {len(weather_data)} daily weather records")
                return weather_data
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch daily weather data: {e}")
            raise
    
    async def get_token_status(self) -> Dict[str, Any]:
        """Get current token status for monitoring"""
        cached_token = self._load_cached_token()
        
        if cached_token:
            return {
                "status": "valid" if not cached_token.is_expired else "expired",
                "created_at": cached_token.created_at.isoformat(),
                "expires_at": cached_token.expires_at.isoformat(),
                "expires_soon": cached_token.expires_soon,
                "days_until_expiry": (cached_token.expires_at - datetime.now(timezone.utc)).days
            }
        else:
            return {
                "status": "no_token",
                "message": "No cached token found"
            }


# Utility functions
async def get_aemet_client() -> AEMETClient:
    """Factory function to create AEMET client"""
    return AEMETClient()


async def fetch_current_weather(station_id: str = "5279X") -> Optional[AEMETWeatherData]:
    """Convenience function to fetch current weather (default: Linares, Jaén)"""
    async with AEMETClient() as client:
        return await client.get_current_weather(station_id)


# Example usage
if __name__ == "__main__":
    async def main():
        async with AEMETClient() as client:
            # Check token status
            token_status = await client.get_token_status()
            print(f"Token status: {token_status}")
            
            # Get weather stations
            stations = await client.get_weather_stations()
            print(f"Found {len(stations)} weather stations")
            
            # Get current weather for Madrid
            weather = await client.get_current_weather("3195")
            if weather:
                print(f"Madrid weather: {weather.temperature}°C, {weather.humidity}% humidity")
    
    asyncio.run(main())