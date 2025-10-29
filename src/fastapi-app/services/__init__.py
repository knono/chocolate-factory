# Services package for TFM Chocolate Factory

# ========================================================================
# COMPATIBILITY LAYER - Sprint 15 Migration
# ========================================================================
# Provides backward compatibility for old imports while transitioning
# to infrastructure/external_apis as the single source of truth.
#
# Old code uses: from services.ree_client import REEClient
# New code uses: from infrastructure.external_apis import REEAPIClient
#
# This layer bridges both styles until all imports are migrated.
# ========================================================================

try:
    # Re-export infrastructure clients under their OLD names for backward compatibility
    from infrastructure.external_apis import REEAPIClient as REEClient
    from infrastructure.external_apis import AEMETAPIClient as AEMETClient
    from infrastructure.external_apis import OpenWeatherMapAPIClient as OpenWeatherMapClient
except ImportError:
    # Fallback if infrastructure clients not yet migrated
    pass

__all__ = ["REEClient", "AEMETClient", "OpenWeatherMapClient"]