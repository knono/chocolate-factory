"""
Analysis Domain Logic - Sprint 15

Historical weather analysis and statistics:
- siar_analysis_service: SIAR historical analysis (88k records, 25 years)
"""

from .siar_analysis_service import SIARAnalysisService

__all__ = [
    "SIARAnalysisService",
]
