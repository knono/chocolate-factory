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
            logger.error("❌ REE Client Error: Client not initialized. Use async context manager.")
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.config.base_url}/{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"🌐 REE API Request: {url} - Attempt {attempt + 1}/{self.config.max_retries}")
                logger.debug(f"🔧 REE Request Params: {params}")

                response = await self.client.get(url, params=params)

                logger.debug(f"📊 REE Response: Status {response.status_code}, Size {len(response.content)} bytes")

                response.raise_for_status()

                # Rate limiting
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.rate_limit_delay)

                data = response.json()
                logger.success(f"✅ REE API Success: {endpoint} - Response received")

                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"❌ REE HTTP Error (attempt {attempt + 1}): Status {e.response.status_code}")
                logger.error(f"🔍 REE Error Response: {e.response.text[:500]}...")

                if attempt == self.config.max_retries - 1:
                    logger.error(f"🚨 REE Final Failure: All {self.config.max_retries} attempts failed for {endpoint}")
                    raise

                # Exponential backoff
                backoff_time = 2 ** attempt
                logger.info(f"⏳ REE Retry Backoff: Waiting {backoff_time}s before retry")
                await asyncio.sleep(backoff_time)

            except httpx.RequestError as e:
                logger.error(f"❌ REE Request Error (attempt {attempt + 1}): {e}")

                if attempt == self.config.max_retries - 1:
                    logger.error(f"🚨 REE Network Failure: Unable to reach REE API after {self.config.max_retries} attempts")
                    raise

                # Exponential backoff
                backoff_time = 2 ** attempt
                logger.info(f"⏳ REE Network Retry: Waiting {backoff_time}s before retry")
                await asyncio.sleep(backoff_time)

            except Exception as e:
                logger.error(f"❌ REE Unexpected Error (attempt {attempt + 1}): {type(e).__name__}: {e}")

                if attempt == self.config.max_retries - 1:
                    logger.error(f"🚨 REE Critical Failure: Unexpected error after {self.config.max_retries} attempts")
                    raise

                # Exponential backoff
                backoff_time = 2 ** attempt
                logger.info(f"⏳ REE Error Retry: Waiting {backoff_time}s before retry")
                await asyncio.sleep(backoff_time)
    
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
            logger.info(f"📊 REE PVPC Request: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")

            data = await self._make_request(endpoint, params)

            prices = []

            # Navigate REE API response structure
            if "included" in data:
                logger.debug(f"🔍 REE Response Analysis: Found {len(data['included'])} items in response")

                pvpc_items = 0
                for item in data["included"]:
                    if item.get("type") == "PVPC" and "attributes" in item:
                        pvpc_items += 1
                        values = item["attributes"].get("values", [])
                        logger.debug(f"📈 REE PVPC Item: Found {len(values)} price values")

                        for value in values:
                            timestamp_str = value.get("datetime")
                            price_value = value.get("value")

                            if timestamp_str and price_value is not None:
                                try:
                                    # Parse REE timestamp format
                                    timestamp = datetime.fromisoformat(
                                        timestamp_str.replace("Z", "+00:00")
                                    )

                                    prices.append(REEPriceData(
                                        timestamp=timestamp,
                                        price_eur_mwh=float(price_value)
                                    ))
                                except (ValueError, TypeError) as parse_error:
                                    logger.warning(f"⚠️ REE Parse Warning: Invalid data point - timestamp: {timestamp_str}, value: {price_value}, error: {parse_error}")

                logger.debug(f"🔍 REE PVPC Summary: {pvpc_items} PVPC items processed")
            else:
                logger.warning("⚠️ REE Response Warning: No 'included' field in API response")
                logger.debug(f"🔍 REE Response Keys: {list(data.keys()) if data else 'Empty response'}")

            if prices:
                earliest = min(p.timestamp for p in prices)
                latest = max(p.timestamp for p in prices)
                avg_price = sum(p.price_eur_mwh for p in prices) / len(prices)

                logger.success(f"✅ REE PVPC Success: {len(prices)} records retrieved")
                logger.info(f"📈 REE Data Range: {earliest.strftime('%Y-%m-%d %H:%M')} to {latest.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"💰 REE Price Stats: Avg {avg_price:.2f} €/MWh, Min {min(p.price_eur_mwh for p in prices):.2f} €/MWh, Max {max(p.price_eur_mwh for p in prices):.2f} €/MWh")
            else:
                logger.error(f"❌ REE PVPC Empty: No valid price data found in response")
                logger.debug(f"🔍 REE Response Debug: {data}")

            return sorted(prices, key=lambda x: x.timestamp)

        except Exception as e:
            logger.error(f"❌ REE PVPC Error: Failed to fetch PVPC prices from {start_date} to {end_date}: {e}")
            logger.error(f"🔍 REE Exception Details: Type={type(e).__name__}, Message={str(e)}")
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
    
    async def get_price_range(self, start_date: datetime, end_date: datetime) -> List[REEPriceData]:
        """
        Get historical price data for a specific date range

        Args:
            start_date: Start datetime for historical data
            end_date: End datetime for historical data

        Returns:
            List of REEPriceData objects for the specified range
        """
        try:
            logger.info(f"📊 REE Historical Request: {start_date.date()} to {end_date.date()}")

            # Use existing PVPC method which supports date ranges
            prices = await self.get_pvpc_prices(start_date, end_date)

            if prices:
                logger.success(f"✅ REE Historical Success: {len(prices)} records retrieved ({start_date.date()} to {end_date.date()})")
            else:
                logger.warning(f"⚠️ REE Historical Empty: No data found for {start_date.date()} to {end_date.date()}")

            return prices

        except Exception as e:
            logger.error(f"❌ REE Historical Error: Failed to fetch data {start_date.date()} to {end_date.date()}: {e}")
            logger.error(f"🔍 REE Error Details: Type={type(e).__name__}, Message={str(e)}")
            raise

    async def get_prices_last_hours(self, hours: int = 24) -> List[REEPriceData]:
        """
        Get electricity prices for the last N hours

        Args:
            hours: Number of hours back to fetch (default: 24)

        Returns:
            List of REEPriceData objects for the last N hours
        """
        try:
            logger.info(f"📊 REE Last Hours Request: {hours}h back")

            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=hours)
            end_time = now + timedelta(hours=1)  # Include current hour

            prices = await self.get_pvpc_prices(start_time, end_time)

            if prices:
                latest_time = max(p.timestamp for p in prices)
                hours_gap = (now - latest_time).total_seconds() / 3600

                logger.success(f"✅ REE Last Hours Success: {len(prices)} records, latest data {hours_gap:.1f}h ago")

                if hours_gap > 6:
                    logger.warning(f"⚠️ REE Data Lag Alert: Latest data is {hours_gap:.1f}h old (threshold: 6h)")
            else:
                logger.error(f"❌ REE Last Hours Empty: No data found for last {hours}h")

            return prices

        except Exception as e:
            logger.error(f"❌ REE Last Hours Error: Failed to fetch last {hours}h: {e}")
            logger.error(f"🔍 REE Error Details: Type={type(e).__name__}, Message={str(e)}")
            return []

    async def get_weekly_market_prices(self, start_date: Optional[datetime] = None) -> List[REEPriceData]:
        """
        Get weekly electricity market prices using ESIOS API
        
        Uses indicator 1001 (PVPC 2.0TD) and 10211 (OMIE hourly price) from ESIOS API
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_date = start_date + timedelta(days=7)
        weekly_prices = []
        
        # ESIOS API endpoints to try (different indicators)
        esios_indicators = [
            1001,   # PVPC 2.0TD (main residential tariff)
            10211,  # OMIE final hourly average price
        ]
        
        esios_base_url = "https://api.esios.ree.es/indicators"
        
        for indicator_id in esios_indicators:
            try:
                # Build ESIOS API URL
                params = {
                    'start_date': start_date.strftime('%Y-%m-%dT%H:%M'),
                    'end_date': end_date.strftime('%Y-%m-%dT%H:%M'),
                    'geo_ids[]': 8741,  # Peninsula
                    'time_trunc': 'hour'
                }
                
                url = f"{esios_base_url}/{indicator_id}"
                
                # Headers for ESIOS API (token would be needed for authenticated endpoints)
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'ChocolateFactory/1.0'
                }
                
                logger.debug(f"Trying ESIOS indicator {indicator_id}: {url}")
                
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse ESIOS response format
                        if 'indicator' in data and 'values' in data['indicator']:
                            values = data['indicator']['values']
                            
                            for value in values:
                                if 'datetime' in value and 'value' in value:
                                    timestamp_str = value['datetime']
                                    price_value = value['value']
                                    
                                    if price_value is not None:
                                        # Parse ESIOS datetime format
                                        timestamp = datetime.fromisoformat(
                                            timestamp_str.replace('Z', '+00:00')
                                        )
                                        
                                        weekly_prices.append(REEPriceData(
                                            timestamp=timestamp,
                                            price_eur_mwh=float(price_value),
                                            market_type=f"esios_indicator_{indicator_id}"
                                        ))
                        
                        if weekly_prices:
                            logger.info(f"✅ Retrieved {len(weekly_prices)} prices from ESIOS indicator {indicator_id}")
                            break
                    
                    else:
                        logger.debug(f"ESIOS indicator {indicator_id} returned {response.status_code}")
                        
            except Exception as e:
                logger.debug(f"ESIOS indicator {indicator_id} failed: {e}")
                continue
        
        # If no ESIOS data found, try REE API as fallback
        if not weekly_prices:
            logger.info("No ESIOS data available, trying REE API fallback")
            try:
                # Use existing PVPC method for recent data to create forecast
                recent_data = await self.get_pvpc_prices(
                    start_date - timedelta(days=2), 
                    start_date
                )
                
                if recent_data:
                    # Create forecast based on recent patterns
                    recent_avg = sum(p.price_eur_mwh for p in recent_data[-24:]) / min(len(recent_data), 24)
                    
                    for i in range(7 * 24):  # 7 days, hourly
                        forecast_time = start_date + timedelta(hours=i)
                        hour = forecast_time.hour
                        
                        # Apply realistic hourly patterns
                        hour_factor = 1.0 + 0.2 * abs(hour - 14) / 14  # Peak at 2 PM
                        weekend_factor = 0.9 if forecast_time.weekday() >= 5 else 1.0
                        
                        forecasted_price = recent_avg * hour_factor * weekend_factor
                        
                        weekly_prices.append(REEPriceData(
                            timestamp=forecast_time,
                            price_eur_mwh=forecasted_price,
                            market_type="ree_forecast_from_recent"
                        ))
                    
                    logger.info(f"✅ Generated {len(weekly_prices)} forecast prices from REE data")
                    
            except Exception as e:
                logger.error(f"REE fallback also failed: {e}")
        
        return sorted(weekly_prices, key=lambda x: x.timestamp)


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