# src/api/dependencies.py
"""Dependency injection for FastAPI application."""

from typing import Generator
from repositories.production_repository import ProductionRepository
from src_services.production_service import ProductionService
from core.config import settings

# Global instances (singleton pattern)
_production_repository = None
_production_service = None


def get_production_repository() -> ProductionRepository:
    """
    Get production repository instance (singleton).
    
    Returns:
        ProductionRepository instance
    """
    global _production_repository
    if _production_repository is None:
        _production_repository = ProductionRepository()
    return _production_repository


def get_production_service() -> ProductionService:
    """
    Get production service instance with injected repository.
    
    Returns:
        ProductionService instance
    """
    global _production_service
    if _production_service is None:
        repository = get_production_repository()
        _production_service = ProductionService(repository)
    return _production_service


def get_settings():
    """
    Get application settings.
    
    Returns:
        Settings instance
    """
    return settings


# Reset functions for testing
def reset_dependencies():
    """Reset all dependency singletons (useful for testing)."""
    global _production_repository, _production_service
    _production_repository = None
    _production_service = None