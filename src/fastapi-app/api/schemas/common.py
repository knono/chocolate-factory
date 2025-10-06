"""
Common Pydantic Schemas
========================

Shared request/response models used across multiple endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Timestamp (ISO format)")
    version: str = Field(..., description="API version")


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool = Field(..., description="Whether system is ready")
    timestamp: str = Field(..., description="Timestamp (ISO format)")
    checks: Dict[str, str] = Field(..., description="Individual service checks")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "DATA_INGESTION_ERROR",
                "message": "Failed to fetch REE prices",
                "details": {"source": "ree_api", "status_code": 500}
            }
        }


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(100, ge=1, le=1000, description="Maximum records to return")
    offset: int = Field(0, ge=0, description="Number of records to skip")


class DateRangeParams(BaseModel):
    """Date range parameters."""
    start_date: datetime = Field(..., description="Start date (ISO format)")
    end_date: Optional[datetime] = Field(None, description="End date (defaults to now)")
