"""
Recommendation Domain Compatibility Layer - Sprint 15

Provides backward compatibility for old imports of recommendation services.

Old code uses: from services.business_logic_service import BusinessLogicService
New code uses: from domain.recommendations.business_logic_service import BusinessLogicService

This module bridges both styles until all imports are migrated.
"""

# Re-export from domain layer under old names
from domain.recommendations.business_logic_service import (
    get_business_logic_service,
    BusinessLogicService,
)
from domain.recommendations.enhanced_recommendations import (
    get_enhanced_recommendations_service,
)

__all__ = [
    "get_business_logic_service",
    "BusinessLogicService",
    "get_enhanced_recommendations_service",
]
