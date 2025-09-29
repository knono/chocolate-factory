# src/api/v1/schemas/production.py
"""Pydantic schemas for production endpoints."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class QualityGrade(str, Enum):
    """Quality grade enumeration."""
    GRADE_A = "Grade_A"
    GRADE_B = "Grade_B" 
    GRADE_C = "Grade_C"
    GRADE_D = "Grade_D"


class ProductionBatchBase(BaseModel):
    """Base schema for production batch."""
    batch: str = Field(..., description="Batch identifier")
    temperature: float = Field(..., ge=15, le=35, description="Temperature in Celsius")
    humidity: float = Field(..., ge=30, le=80, description="Humidity percentage")
    roasting_time: Optional[float] = Field(None, ge=10, le=40, description="Roasting time in minutes")
    cocoa_percentage: Optional[float] = Field(None, ge=30, le=100, description="Cocoa percentage")
    

class ProductionBatchCreate(ProductionBatchBase):
    """Schema for creating a production batch."""
    pass


class ProductionBatchResponse(ProductionBatchBase):
    """Schema for production batch response."""
    quality: QualityGrade
    timestamp: datetime
    quality_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class QualityMetrics(BaseModel):
    """Schema for quality metrics."""
    average: float = Field(..., ge=0, le=100)
    trend: str = Field(..., pattern="^(up|down|stable)$")
    batches_processed: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=100)


class ProductionStats(BaseModel):
    """Schema for production statistics."""
    total_batches: int
    average_quality: float
    best_batch: Optional[str] = None
    worst_batch: Optional[str] = None
    period_start: datetime
    period_end: datetime