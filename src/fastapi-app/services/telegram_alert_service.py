"""
Telegram Alert Service (Sprint 18)
===================================

Proactive alerting system for critical failures via Telegram bot.

Alerts:
1. REE ingestion failures (>3 consecutive in 1h)
2. Backfill completion/failure
3. Gap detection (>12h)
4. Critical nodes offline (>5min)
5. ML training failures (sklearn/Prophet)

Rate limiting: Max 1 alert per topic per 15min (prevents spam).
"""

import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class TelegramAlertService:
    """
    Telegram alerting service with rate limiting.

    Usage:
        service = TelegramAlertService(bot_token="...", chat_id="...")
        await service.send_alert(
            message="REE ingestion failed",
            severity=AlertSeverity.WARNING,
            topic="ree_ingestion"
        )
    """

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Initialize Telegram alert service.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat/channel ID
            enabled: Enable/disable alerts
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

        # Rate limiting: topic -> last alert timestamp
        self._last_alerts: Dict[str, datetime] = {}
        self._rate_limit_minutes = 15

        # Statistics
        self.total_alerts = 0
        self.alerts_sent = 0
        self.alerts_rate_limited = 0

        logger.info(f"TelegramAlertService initialized (enabled={enabled})")

    def _should_rate_limit(self, topic: Optional[str]) -> bool:
        """
        Check if alert should be rate limited.

        Args:
            topic: Alert topic (e.g., 'ree_ingestion', 'backfill')

        Returns:
            True if should be rate limited, False otherwise
        """
        if not topic:
            return False

        if topic not in self._last_alerts:
            return False

        last_alert = self._last_alerts[topic]
        elapsed = datetime.utcnow() - last_alert
        rate_limit = elapsed < timedelta(minutes=self._rate_limit_minutes)

        if rate_limit:
            logger.debug(f"Rate limiting alert for topic '{topic}' (last alert {elapsed.total_seconds():.0f}s ago)")

        return rate_limit

    def _get_emoji(self, severity: AlertSeverity) -> str:
        """Get emoji for severity level."""
        emojis = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨"
        }
        return emojis.get(severity, "📢")

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        topic: Optional[str] = None
    ) -> bool:
        """
        Send alert to Telegram.

        Args:
            message: Alert message
            severity: Alert severity (INFO, WARNING, CRITICAL)
            topic: Alert topic for rate limiting

        Returns:
            True if sent successfully, False otherwise
        """
        self.total_alerts += 1

        # Check if disabled
        if not self.enabled:
            logger.debug(f"Telegram alerts disabled, skipping: {message}")
            return False

        # Check rate limiting
        if self._should_rate_limit(topic):
            self.alerts_rate_limited += 1
            logger.debug(f"Alert rate limited: {topic}")
            return False

        # Format message with emoji
        emoji = self._get_emoji(severity)
        formatted_message = f"{emoji} **{severity.value}**\n\n{message}"

        # Send to Telegram
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": formatted_message,
                        "parse_mode": "Markdown"
                    }
                )

                if response.status_code == 200:
                    self.alerts_sent += 1
                    if topic:
                        self._last_alerts[topic] = datetime.utcnow()
                    logger.info(f"Telegram alert sent: {severity.value} - {topic or 'no-topic'}")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                    return False

        except httpx.TimeoutException:
            logger.error("Telegram API timeout")
            return False
        except httpx.RequestError as e:
            logger.error(f"Telegram API request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram alert: {e}")
            return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get alert statistics.

        Returns:
            Dict with total_alerts, alerts_sent, alerts_rate_limited
        """
        return {
            "total_alerts": self.total_alerts,
            "alerts_sent": self.alerts_sent,
            "alerts_rate_limited": self.alerts_rate_limited,
            "rate_limit_topics": len(self._last_alerts)
        }

    def reset_rate_limit(self, topic: str):
        """Reset rate limit for specific topic."""
        if topic in self._last_alerts:
            del self._last_alerts[topic]
            logger.info(f"Rate limit reset for topic: {topic}")
