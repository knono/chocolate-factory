"""
REE API Client for TFM Chocolate Factory
========================================

Client for accessing Spanish electricity market data from Red Eléctrica de España (REE).
Provides methods to fetch real-time and historical electricity prices, demand data,
and renewable generation statistics.

API Documentation: https://www.ree.es/es/apidatos
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
import httpx
from pydantic import BaseModel, Field, validator
from loguru import logger
import os


class REEConfig(BaseModel):
    """Configuration for REE API client"""
    base_url: str = "https://apidatos.ree.es/es/datos"
    token: Optional[str] = Field(default_factory=lambda: os.getenv("REE_API_TOKEN"))
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 1.0  # seconds between requests


class REEPriceData(BaseModel):
    """Model for REE electricity price data"""
    timestamp: datetime
    price_eur_mwh: float
    market_type: str = "spot"
    provider: str = "ree"
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v


class REEDemandData(BaseModel):
    """Model for REE electricity demand data"""
    timestamp: datetime
    demand_mw: float
    renewable_generation_mw: Optional[float] = None
    renewable_percentage: Optional[float] = None


class REEClient:
    """
    Asynchronous client for REE (Red Eléctrica de España) API
    
    Provides methods to fetch electricity market data including:
    - Real-time and historical prices (PVPC)
    - Electricity demand data
    - Renewable generation statistics
    """
    
    def __init__(self, config: Optional[REEConfig] = None):
        self.config = config or REEConfig()
        self.client = None
        
        if not self.config.token:
            logger.warning("REE_API_TOKEN not configured. Some endpoints may be limited.")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for REE API requests"""
        headers = {
            "Accept": "application/json",
            "User-Agent": "TFM-Chocolate-Factory/1.0"
        }
        
        if self.config.token:
            headers["Authorization"] = f"Token token={self.config.token}"
        
        return headers
    
    def _format_date(self, date: Union[datetime, str]) -> str:
        """Format date for REE API (YYYY-MM-DDTHH:MM)"""
        if isinstance(date, str):
            return date
        return date.strftime("%Y-%m-%dT%H:%M")
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to REE API with retry logic"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = f"{self.config.base_url}/{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"REE API request: {url} - Attempt {attempt + 1}")
                
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                
                # Rate limiting
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.rate_limit_delay)
                
                return response.json()
                
            except httpx.HTTPError as e:
                logger.warning(f"REE API request failed (attempt {attempt + 1}): {e}")
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def get_pvpc_prices(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[REEPriceData]:
        """
        Get PVPC (Precio Voluntario Pequeño Consumidor) electricity prices
        
        Args:
            start_date: Start date for data query (defaults to today)
            end_date: End date for data query (defaults to tomorrow)
            
        Returns:
            List of REEPriceData objects with hourly prices
        """
        # Default to current day if no dates provided
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
            "time_trunc": "hour"
        }
        
        # PVPC prices endpoint
        endpoint = "mercados/precios-mercados-tiempo-real"
        
        try:
            data = await self._make_request(endpoint, params)
            
            prices = []
            
            # Navigate REE API response structure
            if "included" in data:
                for item in data["included"]:
                    if item.get("type") == "PVPC" and "attributes" in item:
                        values = item["attributes"].get("values", [])
                        
                        for value in values:
                            timestamp_str = value.get("datetime")
                            price_value = value.get("value")
                            
                            if timestamp_str and price_value is not None:
                                # Parse REE timestamp format
                                timestamp = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                
                                prices.append(REEPriceData(
                                    timestamp=timestamp,
                                    price_eur_mwh=float(price_value)
                                ))
            
            logger.info(f"Retrieved {len(prices)} PVPC price records from REE")
            return sorted(prices, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to fetch PVPC prices: {e}")
            raise
    
    async def get_demand_data(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[REEDemandData]:
        """
        Get electricity demand and renewable generation data
        
        Args:
            start_date: Start date for data query
            end_date: End date for data query
            
        Returns:
            List of REEDemandData objects
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
            "time_trunc": "hour"
        }
        
        endpoint = "demanda/evolucion"
        
        try:
            data = await self._make_request(endpoint, params)
            
            demand_records = []
            
            if "included" in data:
                for item in data["included"]:
                    if "attributes" in item:
                        values = item["attributes"].get("values", [])
                        
                        for value in values:
                            timestamp_str = value.get("datetime")
                            demand_value = value.get("value")
                            
                            if timestamp_str and demand_value is not None:
                                timestamp = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                
                                demand_records.append(REEDemandData(
                                    timestamp=timestamp,
                                    demand_mw=float(demand_value)
                                ))
            
            logger.info(f"Retrieved {len(demand_records)} demand records from REE")
            return sorted(demand_records, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to fetch demand data: {e}")
            raise
    
    async def get_renewable_generation(self, 
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get renewable energy generation data by technology
        
        Args:
            start_date: Start date for data query
            end_date: End date for data query
            
        Returns:
            List of renewable generation records
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
            "time_trunc": "hour"
        }
        
        endpoint = "generacion/estructura-renovables"
        
        try:
            data = await self._make_request(endpoint, params)
            
            # Process renewable generation data
            renewables = []
            
            if "included" in data:
                for item in data["included"]:
                    if "attributes" in item:
                        technology = item["attributes"].get("title", "unknown")
                        values = item["attributes"].get("values", [])
                        
                        for value in values:
                            timestamp_str = value.get("datetime")
                            generation_value = value.get("value")
                            percentage = value.get("percentage")
                            
                            if timestamp_str and generation_value is not None:
                                timestamp = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                
                                renewables.append({
                                    "timestamp": timestamp,
                                    "technology": technology,
                                    "generation_mw": float(generation_value),
                                    "percentage": float(percentage) if percentage else None
                                })
            
            logger.info(f"Retrieved {len(renewables)} renewable generation records")
            return renewables
            
        except Exception as e:
            logger.error(f"Failed to fetch renewable generation: {e}")
            raise
    
    async def get_current_price(self) -> Optional[REEPriceData]:
        """Get current hour electricity price"""
        try:
            now = datetime.now()
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            next_hour = current_hour + timedelta(hours=1)
            
            prices = await self.get_pvpc_prices(current_hour, next_hour)
            
            if prices:
                return prices[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current price: {e}")
            return None
    
    async def get_price_forecast_24h(self) -> List[REEPriceData]:
        """Get 24-hour price forecast starting from current hour"""
        try:
            now = datetime.now()
            start_time = now.replace(minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(hours=24)
            
            return await self.get_pvpc_prices(start_time, end_time)
            
        except Exception as e:
            logger.error(f"Failed to get 24h price forecast: {e}")
            return []


# Utility functions
async def get_ree_client() -> REEClient:
    """Factory function to create REE client"""
    return REEClient()


async def fetch_latest_prices() -> List[REEPriceData]:
    """Convenience function to fetch latest prices"""
    async with REEClient() as client:
        return await client.get_pvpc_prices()


# Example usage
if __name__ == "__main__":
    async def main():
        async with REEClient() as client:
            # Get current price
            current = await client.get_current_price()
            if current:
                print(f"Current price: {current.price_eur_mwh:.2f} €/MWh")
            
            # Get 24h forecast
            forecast = await client.get_price_forecast_24h()
            print(f"24h forecast: {len(forecast)} hourly prices")
    
    asyncio.run(main())