"""
Startup Tasks - Execute on application start
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def ensure_prophet_model():
    """Entrena modelo Prophet si no existe al iniciar."""
    from services.price_forecasting_service import PriceForecastingService

    try:
        service = PriceForecastingService()
        model_path = service.models_dir / "prophet_latest.pkl"

        if model_path.exists():
            logger.info(f"✅ Prophet model exists: {model_path}")
            return

        logger.warning("⚠️  Prophet model missing, training now...")
        result = await service.train_model(months_back=12)

        if result.get('success'):
            logger.info("✅ Prophet model trained successfully")
        else:
            logger.error(f"❌ Training failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"❌ Error ensuring Prophet model: {e}")
