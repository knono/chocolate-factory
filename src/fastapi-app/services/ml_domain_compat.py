"""
ML Domain Compatibility Layer - Sprint 15

Provides backward compatibility for old imports of ML services.

Old code uses: from services.direct_ml import DirectML
New code uses: from domain.ml.direct_ml import DirectML

This module bridges both styles until all imports are migrated.
"""

# Re-export from domain layer under old names
from domain.ml.direct_ml import DirectML, DirectMLConfig
from domain.ml.enhanced_ml_service import EnhancedMLService
from domain.ml.feature_engineering import ChocolateFeatureEngine

__all__ = [
    "DirectML",
    "DirectMLConfig",
    "EnhancedMLService",
    "ChocolateFeatureEngine",
]
