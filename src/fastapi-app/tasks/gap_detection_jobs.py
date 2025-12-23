"""
Gap Detection Scheduled Jobs
=============================

Automatic gap detection, alerting, and backfill for data gaps.

Sprint 18: Telegram alerts for gaps >12h
Sprint 22: Auto-backfill with AEMET hourly forecast for gaps <48h
"""

import logging
from dependencies import get_gap_detector, get_backfill_service

logger = logging.getLogger(__name__)


async def automatic_gap_detection():
    """
    Scheduled job: Automatic gap detection with Telegram alerts and auto-backfill.

    Frequency: Every 2 hours

    Detects gaps in REE and Weather data for the last 2 days.
    - Sends Telegram alert if gaps >12h are detected
    - Automatically fills gaps <48h using AEMET hourly forecast by municipality

    This allows the system to recover data gaps when equipment is turned on,
    reducing the need to have equipment running 24/7.

    Sprint 18: Critical gap alerting via Telegram
    Sprint 22: Auto-backfill with AEMET hourly forecast (up to 48h)
    """
    try:
        logger.info("🔍 Starting automatic gap detection with auto-backfill...")

        gap_detector = get_gap_detector()

        # Analyze last 2 days (48h)
        # This triggers _check_and_alert_critical_gaps() internally
        analysis = await gap_detector.detect_all_gaps(days_back=2)

        total_gaps = analysis.total_gaps_found
        critical_gaps = sum(
            1 for gap in (analysis.ree_gaps + analysis.weather_gaps)
            if gap.gap_duration_hours > 12
        )

        # Check for gaps that can be auto-filled (<48h)
        fillable_gaps = sum(
            1 for gap in (analysis.ree_gaps + analysis.weather_gaps)
            if gap.gap_duration_hours <= 48
        )

        if critical_gaps > 0:
            logger.warning(
                f"⚠️ Automatic gap detection: {critical_gaps}/{total_gaps} "
                f"critical gaps (>12h) detected. Telegram alert sent."
            )

        # Auto-backfill if there are fillable gaps
        if fillable_gaps > 0 and total_gaps > 0:
            logger.info(
                f"🔄 Auto-backfill triggered: {fillable_gaps} gaps can be filled (<48h)"
            )
            try:
                backfill_service = get_backfill_service()
                # Execute backfill for gaps up to 48h (uses AEMET forecast for weather)
                result = await backfill_service.check_and_execute_auto_backfill(
                    max_gap_hours=48.0
                )

                if result.get("status") == "success":
                    records_written = result.get("records", {}).get("total_written", 0)
                    logger.info(
                        f"✅ Auto-backfill completed: {records_written} records written"
                    )
                elif result.get("status") == "no_action_needed":
                    logger.info("✅ Auto-backfill: Data is up to date, no action needed")
                else:
                    logger.warning(
                        f"⚠️ Auto-backfill partial: {result.get('status')} - {result.get('message', '')}"
                    )

            except Exception as backfill_error:
                logger.error(f"❌ Auto-backfill failed: {backfill_error}")
                # Continue - don't fail the whole job
        else:
            logger.info(
                f"✅ Automatic gap detection: {total_gaps} gaps found, "
                f"none critical (all <12h), no auto-backfill needed"
            )

    except Exception as e:
        logger.error(f"❌ Automatic gap detection failed: {e}")
        # Don't raise - let scheduler continue
