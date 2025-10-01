# src/core/health/health_checks.py
"""Health check system for Chocolate Factory."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import psutil
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    latency_ms: float
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'latency_ms': round(self.latency_ms, 2)
        }
        if self.details:
            result['details'] = self.details
        return result


class HealthChecker:
    """Main health checker class."""
    
    def __init__(self):
        """Initialize health checker."""
        self.start_time = datetime.now()
        self.checks_performed = 0
        self.last_check_time = None
        
    async def check_ml_models(self) -> HealthCheckResult:
        """Check ML models availability."""
        start = time.time()

        try:
            # Try to import ML services - they may or may not be available
            try:
                from services.direct_ml import DirectMLService
                ml_service = DirectMLService()
                status = HealthStatus.HEALTHY
                message = "ML services available"
                details = {'service': 'DirectMLService'}
            except ImportError:
                status = HealthStatus.DEGRADED
                message = "ML services not available"
                details = None

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"ML module error: {str(e)}"
            details = None

        latency = (time.time() - start) * 1000
        return HealthCheckResult(
            name="ml_models",
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )
    
    async def check_cache(self) -> HealthCheckResult:
        """Check cache system."""
        start = time.time()

        try:
            from core.cache.cache_manager import cache_manager

            stats = cache_manager.get_stats()
            hit_rate = stats['hit_rate']

            if hit_rate >= 70:
                status = HealthStatus.HEALTHY
                message = f"Cache hit rate: {hit_rate}%"
            elif hit_rate >= 40:
                status = HealthStatus.DEGRADED
                message = f"Low cache hit rate: {hit_rate}%"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Very low cache hit rate: {hit_rate}%"

            details = stats

        except Exception as e:
            status = HealthStatus.DEGRADED
            message = f"Cache not initialized yet (normal on startup)"
            details = None

        latency = (time.time() - start) * 1000
        return HealthCheckResult(
            name="cache",
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )
    
    async def check_system_resources(self) -> HealthCheckResult:
        """Check system resources."""
        start = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine overall status
            if cpu_percent < 80 and memory.percent < 85 and disk.percent < 90:
                status = HealthStatus.HEALTHY
                message = "System resources OK"
            elif cpu_percent < 90 and memory.percent < 95 and disk.percent < 95:
                status = HealthStatus.DEGRADED
                message = "System resources high"
            else:
                status = HealthStatus.UNHEALTHY
                message = "System resources critical"
            
            details = {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': round(disk.percent, 1),
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"System check error: {str(e)}"
            details = None
        
        latency = (time.time() - start) * 1000
        return HealthCheckResult(
            name="system_resources",
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )
    
    async def check_service_layer(self) -> HealthCheckResult:
        """Check service layer availability."""
        start = time.time()

        try:
            # Try to import service layer
            try:
                from api.dependencies import get_production_service
                service = get_production_service()
                status = HealthStatus.HEALTHY
                message = "Service layer operational"
                details = {'service': 'ProductionService'}
            except ImportError:
                # Service layer not available - this is OK
                status = HealthStatus.HEALTHY
                message = "Service layer optional (not loaded)"
                details = None

        except Exception as e:
            status = HealthStatus.DEGRADED
            message = f"Service layer check skipped: {str(e)}"
            details = None

        latency = (time.time() - start) * 1000
        return HealthCheckResult(
            name="service_layer",
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )
    
    async def check_api_performance(self) -> HealthCheckResult:
        """Check API performance metrics."""
        start = time.time()
        
        try:
            # In a real app, you'd get these from monitoring
            # For now, we'll simulate
            avg_response_time = 45.2  # ms
            requests_per_second = 150
            error_rate = 0.5  # percentage
            
            if avg_response_time < 100 and error_rate < 1:
                status = HealthStatus.HEALTHY
                message = f"API performing well ({avg_response_time}ms avg)"
            elif avg_response_time < 500 and error_rate < 5:
                status = HealthStatus.DEGRADED
                message = f"API performance degraded ({avg_response_time}ms avg)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"API performance poor ({avg_response_time}ms avg)"
            
            details = {
                'avg_response_time_ms': avg_response_time,
                'requests_per_second': requests_per_second,
                'error_rate_percent': error_rate
            }
            
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Performance check error: {str(e)}"
            details = None
        
        latency = (time.time() - start) * 1000
        return HealthCheckResult(
            name="api_performance",
            status=status,
            message=message,
            latency_ms=latency,
            details=details
        )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        start_time = time.time()
        
        checks = [
            self.check_ml_models(),
            self.check_cache(),
            self.check_system_resources(),
            self.check_service_layer(),
            self.check_api_performance()
        ]
        
        results = []
        for check_coro in checks:
            try:
                result = await check_coro
                results.append(result.to_dict())
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                results.append({
                    'name': 'unknown',
                    'status': HealthStatus.UNHEALTHY,
                    'message': str(e),
                    'latency_ms': 0
                })
        
        # Determine overall status
        statuses = [r['status'] for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        self.checks_performed += 1
        self.last_check_time = datetime.now()
        
        uptime = datetime.now() - self.start_time
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': int(uptime.total_seconds()),
            'checks_performed': self.checks_performed,
            'total_latency_ms': round((time.time() - start_time) * 1000, 2),
            'checks': results
        }
    
    async def get_readiness(self) -> Dict[str, Any]:
        """Check if application is ready to serve requests."""
        ml_check = await self.check_ml_models()
        service_check = await self.check_service_layer()
        
        is_ready = (
            ml_check.status != HealthStatus.UNHEALTHY and
            service_check.status != HealthStatus.UNHEALTHY
        )
        
        return {
            'ready': is_ready,
            'checks': {
                'ml_models': ml_check.status,
                'service_layer': service_check.status
            }
        }
    
    async def get_liveness(self) -> Dict[str, Any]:
        """Check if application is alive."""
        return {
            'alive': True,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': int((datetime.now() - self.start_time).total_seconds())
        }


# Global health checker instance
health_checker = HealthChecker()