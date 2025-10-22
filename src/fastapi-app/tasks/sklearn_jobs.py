"""sklearn ML Training Jobs"""
import logging
from services.direct_ml import DirectMLService

logger = logging.getLogger(__name__)

async def sklearn_training_job():
    """Train sklearn models (energy + production) every 30 minutes"""
    try:
        logger.info("🤖 Starting sklearn training job...")
        direct_ml = DirectMLService()
        results = await direct_ml.train_models()

        if results.get("success"):
            logger.info(f"✅ sklearn training completed: {results.get('models_trained', [])} models")
        else:
            logger.error(f"❌ sklearn training failed: {results.get('error')}")

    except Exception as e:
        logger.error(f"❌ sklearn training job error: {e}")
