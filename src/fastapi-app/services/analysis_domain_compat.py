"""
Analysis Domain Compatibility Layer - Sprint 15

Provides backward compatibility for old imports of analysis services.

Old code uses: from services.siar_analysis_service import SIARAnalysisService
New code uses: from domain.analysis.siar_analysis_service import SIARAnalysisService

This module bridges both styles until all imports are migrated.
"""

# Re-export from domain layer under old names
from domain.analysis.siar_analysis_service import SIARAnalysisService

__all__ = [
    "SIARAnalysisService",
]
