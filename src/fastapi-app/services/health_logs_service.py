"""
Health Logs Service

Genera logs de eventos basados en el estado actual y cambios de nodos.
Más pragmático que leer logs históricos del container.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from services.tailscale_health_service import TailscaleHealthService
from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class HealthLogEntry:
    """Representa un evento de log de health monitoring."""
    timestamp: str
    event_type: str  # node_online, node_offline, health_check, alert
    severity: str  # ok, warning, critical
    hostname: str
    node_type: str
    message: str


class HealthLogsService:
    """
    Servicio para generar logs de eventos de health monitoring.

    Genera eventos basados en:
    - Estado actual de nodos (online/offline)
    - Cambios detectados desde último check
    - Alertas activas
    """

    def __init__(self, health_service: TailscaleHealthService):
        """
        Initialize Health Logs Service.

        Args:
            health_service: TailscaleHealthService instance
        """
        self.health_service = health_service

    def generate_current_events(self) -> List[HealthLogEntry]:
        """
        Generate log entries based on current node states.

        Returns:
            List of HealthLogEntry objects representing current events
        """
        events = []
        now = datetime.utcnow()

        try:
            # Get current nodes health
            nodes = self.health_service.get_nodes_health()

            # Filter to project nodes only
            project_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]

            # Generate events for each node
            for node in project_nodes:
                if node.online:
                    events.append(HealthLogEntry(
                        timestamp=now.isoformat(),
                        event_type="node_online",
                        severity="ok",
                        hostname=node.hostname,
                        node_type=node.node_type,
                        message=f"Node '{node.hostname}' ({node.node_type}) is online and healthy"
                    ))
                else:
                    # Offline node - warning or critical
                    severity = "critical" if node.node_type == "production" else "warning"
                    events.append(HealthLogEntry(
                        timestamp=node.last_seen or now.isoformat(),
                        event_type="node_offline",
                        severity=severity,
                        hostname=node.hostname,
                        node_type=node.node_type,
                        message=f"Node '{node.hostname}' ({node.node_type}) is OFFLINE. Last seen: {node.last_seen or 'Unknown'}"
                    ))

            # Add summary event
            critical_online = sum(1 for n in project_nodes if n.online)
            health_percentage = round((critical_online / len(project_nodes) * 100), 2) if project_nodes else 100

            summary_severity = "ok" if health_percentage == 100 else "warning" if health_percentage >= 66 else "critical"

            events.insert(0, HealthLogEntry(
                timestamp=now.isoformat(),
                event_type="health_check",
                severity=summary_severity,
                hostname="system",
                node_type="system",
                message=f"Health check completed: {critical_online}/{len(project_nodes)} critical nodes online ({health_percentage}% healthy)"
            ))

            logger.debug(f"Generated {len(events)} health events")
            return events

        except Exception as e:
            logger.error(f"Failed to generate health events: {e}", exc_info=True)
            return []

    def generate_historical_events(self, hours: int = 48) -> List[HealthLogEntry]:
        """
        Generate simulated historical events for demonstration.

        In production, this would read from InfluxDB or a persistent log store.
        For now, generates synthetic events based on current state.

        Args:
            hours: Hours to look back

        Returns:
            List of synthetic historical events
        """
        events = []
        now = datetime.utcnow()

        try:
            nodes = self.health_service.get_nodes_health()
            project_nodes = [n for n in nodes if n.node_type in ["production", "development", "git"]]

            # Generate periodic health checks (every 5 minutes for last 48h)
            intervals = min(hours * 12, 100)  # Max 100 entries to avoid overwhelming

            for i in range(intervals):
                check_time = now - timedelta(minutes=5 * i)

                # Simulate health check event every 12 intervals (1 hour)
                if i % 12 == 0:
                    online_count = len([n for n in project_nodes if n.online])
                    health_pct = round((online_count / len(project_nodes) * 100), 2) if project_nodes else 100

                    events.append(HealthLogEntry(
                        timestamp=check_time.isoformat(),
                        event_type="health_check",
                        severity="ok" if health_pct == 100 else "warning",
                        hostname="system",
                        node_type="system",
                        message=f"Periodic health check: {online_count}/{len(project_nodes)} nodes online ({health_pct}%)"
                    ))

            logger.debug(f"Generated {len(events)} historical events")
            return events

        except Exception as e:
            logger.error(f"Failed to generate historical events: {e}", exc_info=True)
            return []

    def get_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        hours: int = 48,
        severity: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get paginated health logs.

        Args:
            page: Page number (1-indexed)
            page_size: Entries per page
            hours: Hours to look back (for historical simulation)
            severity: Filter by severity (ok, warning, critical)
            event_type: Filter by event type (node_online, node_offline, health_check, alert)

        Returns:
            Dict with paginated logs, metadata, and summary
        """
        # Generate current + historical events
        current_events = self.generate_current_events()
        historical_events = self.generate_historical_events(hours=hours)

        # Combine and deduplicate
        all_events = current_events + historical_events

        # Filter by severity if specified
        if severity:
            all_events = [e for e in all_events if e.severity == severity]

        # Filter by event type if specified
        if event_type:
            all_events = [e for e in all_events if e.event_type == event_type]

        # Sort by timestamp (newest first)
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        # Calculate pagination
        total_entries = len(all_events)
        total_pages = (total_entries + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_entries)

        # Get page slice
        page_events = all_events[start_idx:end_idx]

        # Calculate summary
        summary = {
            "total": total_entries,
            "critical": sum(1 for e in all_events if e.severity == "critical"),
            "warning": sum(1 for e in all_events if e.severity == "warning"),
            "ok": sum(1 for e in all_events if e.severity == "ok")
        }

        return {
            "logs": [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "hostname": e.hostname,
                    "node_type": e.node_type,
                    "message": e.message
                }
                for e in page_events
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_entries": total_entries,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "filters": {
                "hours": hours,
                "severity": severity,
                "event_type": event_type
            },
            "summary": summary
        }
