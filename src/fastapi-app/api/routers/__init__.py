"""API Routers Module"""

from .health import router as health_router
from .ree import router as ree_router
from .weather import router as weather_router

__all__ = [
    "health_router",
    "ree_router",
    "weather_router",
]
