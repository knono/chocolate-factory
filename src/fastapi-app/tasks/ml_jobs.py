"""
ML Training Jobs (Sprint 18: Telegram alerts, Sprint 20: Model monitoring)
===========================================================================

Background jobs for ML model training and maintenance.
"""

import logging
from pathlib import Path

from services.price_forecasting_service import PriceForecastingService
from dependencies import get_telegram_alert_service
from services.telegram_alert_service import AlertSeverity

logger = logging.getLogger(__name__)


async def ensure_prophet_model_job():
    """
    Reentrena el modelo Prophet diariamente a las 15:00h.

    Mantiene el modelo actualizado con datos recientes para mejorar
    la precisión de las predicciones.
    """
    telegram_service = get_telegram_alert_service()
    logger.info("🔄 Iniciando reentrenamiento programado de Prophet...")

    try:
        forecast_service = PriceForecastingService()

        # Entrenar modelo con datos de los últimos 36 meses (3 años completos)
        result = await forecast_service.train_model(months_back=36)

        if result.get('success'):
            logger.info("✅ Modelo Prophet entrenado exitosamente")
            logger.info(f"   MAE: {result['metrics']['mae']:.4f} €/kWh")
            logger.info(f"   R²: {result['metrics']['r2']:.4f}")

            # Sprint 20: Check for model degradation
            current_metrics = result['metrics']
            degradation = forecast_service.metrics_tracker.detect_degradation(
                model_name="prophet_price_forecast",
                current_metrics=current_metrics,
                threshold_multiplier=2.0
            )

            # Alert if degradation detected
            if degradation['degradation_detected'] and telegram_service:
                alert_messages = [alert['message'] for alert in degradation['alerts']]
                await telegram_service.send_alert(
                    message=f"⚠️ Prophet model degradation detected:\n" + "\n".join(alert_messages),
                    severity=AlertSeverity.WARNING,
                    topic="prophet_model_degradation"
                )
                logger.warning(f"⚠️ Model degradation alert sent to Telegram")
        else:
            logger.error(f"❌ Error entrenando modelo: {result.get('error')}")

            # Alert: Prophet training failure
            if telegram_service:
                await telegram_service.send_alert(
                    message=f"Prophet training failed: {result.get('error')}. Forecast unavailable.",
                    severity=AlertSeverity.CRITICAL,
                    topic="prophet_training"
                )

    except Exception as e:
        logger.error(f"❌ Error en ensure_prophet_model_job: {e}")

        # Alert: Prophet training exception
        if telegram_service:
            await telegram_service.send_alert(
                message=f"Prophet training exception: {str(e)}. Forecast unavailable.",
                severity=AlertSeverity.CRITICAL,
                topic="prophet_training"
            )
