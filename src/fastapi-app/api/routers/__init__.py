"""API Routers Module"""

from .health import router as health_router
from .ree import router as ree_router
from .weather import router as weather_router
from .dashboard import router as dashboard_router
from .optimization import router as optimization_router
from .analysis import router as analysis_router
from .gaps import router as gaps_router
from .insights import router as insights_router
from .chatbot import router as chatbot_router  # Sprint 11

__all__ = [
    "health_router",
    "ree_router",
    "weather_router",
    "dashboard_router",
    "optimization_router",
    "analysis_router",
    "gaps_router",
    "insights_router",
    "chatbot_router",  # Sprint 11
]
