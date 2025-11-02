"""sklearn ML Training Jobs (Sprint 18: Telegram alerts)"""
import logging
from domain.ml.direct_ml import DirectMLService
from dependencies import get_telegram_alert_service
from services.telegram_alert_service import AlertSeverity

logger = logging.getLogger(__name__)

async def sklearn_training_job():
    """Train sklearn models (energy + production) every 30 minutes"""
    telegram_service = get_telegram_alert_service()

    try:
        logger.info("🤖 Starting sklearn training job...")
        direct_ml = DirectMLService()
        results = await direct_ml.train_models()

        if results.get("success"):
            logger.info(f"✅ sklearn training completed: {results.get('models_trained', [])} models")
        else:
            logger.error(f"❌ sklearn training failed: {results.get('error')}")

            # Alert: sklearn training failure
            if telegram_service:
                await telegram_service.send_alert(
                    message=f"sklearn training failed: {results.get('error')}",
                    severity=AlertSeverity.CRITICAL,
                    topic="sklearn_training"
                )

    except Exception as e:
        logger.error(f"❌ sklearn training job error: {e}")

        # Alert: sklearn training exception
        if telegram_service:
            await telegram_service.send_alert(
                message=f"sklearn training exception: {str(e)}",
                severity=AlertSeverity.CRITICAL,
                topic="sklearn_training"
            )
