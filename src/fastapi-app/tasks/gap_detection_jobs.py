"""
Gap Detection Scheduled Jobs
=============================

Automatic gap detection and alerting for critical data gaps.

Sprint 18: Telegram alerts for gaps >12h
"""

import logging
from dependencies import get_gap_detector

logger = logging.getLogger(__name__)


async def automatic_gap_detection():
    """
    Scheduled job: Automatic gap detection with Telegram alerts.

    Frequency: Every 2 hours

    Detects gaps in REE and Weather data for the last 2 days.
    Sends Telegram alert if gaps >12h are detected.

    Sprint 18: Critical gap alerting via Telegram
    """
    try:
        logger.info("🔍 Starting automatic gap detection...")

        gap_detector = get_gap_detector()

        # Analyze last 2 days (48h)
        # This triggers _check_and_alert_critical_gaps() internally
        analysis = await gap_detector.detect_all_gaps(days_back=2)

        total_gaps = analysis.total_gaps_found
        critical_gaps = sum(
            1 for gap in (analysis.ree_gaps + analysis.weather_gaps)
            if gap.gap_duration_hours > 12
        )

        if critical_gaps > 0:
            logger.warning(
                f"⚠️ Automatic gap detection: {critical_gaps}/{total_gaps} "
                f"critical gaps (>12h) detected. Telegram alert sent."
            )
        else:
            logger.info(
                f"✅ Automatic gap detection: {total_gaps} gaps found, "
                f"none critical (all <12h)"
            )

    except Exception as e:
        logger.error(f"❌ Automatic gap detection failed: {e}")
        # Don't raise - let scheduler continue
