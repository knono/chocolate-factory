"""
REE Pydantic Schemas
====================

Request/Response models for REE electricity price endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class REEIngestRequest(BaseModel):
    """Request model for REE price ingestion."""
    target_date: Optional[date] = Field(None, description="Date to ingest (defaults to today)")
    force_refresh: bool = Field(False, description="Overwrite existing data")


class REEPriceRecord(BaseModel):
    """Single REE price record."""
    timestamp: datetime = Field(..., description="Timestamp")
    price_eur_kwh: float = Field(..., description="Price in €/kWh")
    source: str = Field(..., description="Data source")


class REEPricesResponse(BaseModel):
    """Response model for REE prices query."""
    prices: List[REEPriceRecord]
    count: int = Field(..., description="Number of records returned")


class REEStatsResponse(BaseModel):
    """Response model for REE price statistics."""
    count: int
    min: Optional[float] = Field(None, description="Minimum price (€/kWh)")
    max: Optional[float] = Field(None, description="Maximum price (€/kWh)")
    avg: Optional[float] = Field(None, description="Average price (€/kWh)")
    median: Optional[float] = Field(None, description="Median price (€/kWh)")
    start_date: str
    end_date: str
