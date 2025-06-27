"""
APScheduler Service for TFM Chocolate Factory
===========================================

Automated scheduling service for periodic data ingestion and optimization tasks.
Manages the autonomous operation of the chocolate factory system.

Key Features:
- REE price data ingestion (every hour)
- Daily data backfill and validation
- Production optimization scheduling
- Error handling and recovery
- Health monitoring and alerts
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from pydantic import BaseModel, Field
from loguru import logger

from .data_ingestion import DataIngestionService, DataIngestionStats


class SchedulerConfig(BaseModel):
    """Configuration for the APScheduler service"""
    timezone: str = Field(default="Europe/Madrid")
    max_workers: int = Field(default=3)
    coalesce: bool = Field(default=True)  # Combine missed jobs
    max_instances: int = Field(default=1)  # Max concurrent instances per job
    misfire_grace_time: int = Field(default=300)  # seconds
    
    # Job scheduling configuration
    ree_ingestion_interval_minutes: int = Field(default=60)  # Every hour
    daily_backfill_hour: int = Field(default=1)  # 1 AM daily backfill
    health_check_interval_minutes: int = Field(default=15)  # Health checks
    optimization_interval_minutes: int = Field(default=30)  # Production optimization


class JobStats(BaseModel):
    """Statistics for scheduled jobs"""
    job_id: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_duration_seconds: Optional[float] = None
    average_duration_seconds: Optional[float] = None


class SchedulerService:
    """
    APScheduler-based service for automated factory operations
    
    Manages:
    - Data ingestion scheduling (REE prices, weather data)
    - Production optimization triggers
    - System health monitoring
    - Error recovery and alerting
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_stats: Dict[str, JobStats] = {}
        self.is_running = False
        
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': self.config.coalesce,
            'max_instances': self.config.max_instances,
            'misfire_grace_time': self.config.misfire_grace_time
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.config.timezone
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._job_missed_listener, EVENT_JOB_MISSED)
    
    def _job_executed_listener(self, event):
        """Handle successful job execution"""
        job_id = event.job_id
        duration = (event.scheduled_run_time - event.scheduled_run_time).total_seconds()
        
        if job_id not in self.job_stats:
            self.job_stats[job_id] = JobStats(job_id=job_id)
        
        stats = self.job_stats[job_id]
        stats.last_run = event.scheduled_run_time
        stats.run_count += 1
        stats.success_count += 1
        stats.last_duration_seconds = duration
        
        # Update average duration
        if stats.average_duration_seconds is None:
            stats.average_duration_seconds = duration
        else:
            stats.average_duration_seconds = (
                (stats.average_duration_seconds * (stats.run_count - 1) + duration) / stats.run_count
            )
        
        logger.info(f"Job {job_id} completed successfully in {duration:.2f}s")
    
    def _job_error_listener(self, event):
        """Handle job execution errors"""
        job_id = event.job_id
        
        if job_id not in self.job_stats:
            self.job_stats[job_id] = JobStats(job_id=job_id)
        
        stats = self.job_stats[job_id]
        stats.run_count += 1
        stats.error_count += 1
        stats.last_error = str(event.exception)
        
        logger.error(f"Job {job_id} failed: {event.exception}")
    
    def _job_missed_listener(self, event):
        """Handle missed job executions"""
        logger.warning(f"Job {event.job_id} missed scheduled execution at {event.scheduled_run_time}")
    
    async def start(self):
        """Start the scheduler and add jobs"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting APScheduler service")
        
        try:
            # Add scheduled jobs
            await self._add_jobs()
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("APScheduler service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping APScheduler service")
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("APScheduler service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def _add_jobs(self):
        """Add all scheduled jobs"""
        
        # 1. REE Price Data Ingestion - Every hour at minute 5
        self.scheduler.add_job(
            func=self._ingest_ree_prices_job,
            trigger=CronTrigger(minute=5),  # Every hour at :05
            id="ree_price_ingestion",
            name="REE Price Data Ingestion",
            replace_existing=True
        )
        logger.info("Added REE price ingestion job (hourly at :05)")
        
        # 2. Daily Data Backfill - 1 AM daily
        self.scheduler.add_job(
            func=self._daily_backfill_job,
            trigger=CronTrigger(hour=self.config.daily_backfill_hour, minute=0),
            id="daily_backfill",
            name="Daily Data Backfill",
            replace_existing=True
        )
        logger.info(f"Added daily backfill job ({self.config.daily_backfill_hour}:00 AM)")
        
        # 3. System Health Check - Every 15 minutes
        self.scheduler.add_job(
            func=self._health_check_job,
            trigger=IntervalTrigger(minutes=self.config.health_check_interval_minutes),
            id="health_check",
            name="System Health Check",
            replace_existing=True
        )
        logger.info(f"Added health check job (every {self.config.health_check_interval_minutes} minutes)")
        
        # 4. Production Optimization - Every 30 minutes
        self.scheduler.add_job(
            func=self._production_optimization_job,
            trigger=IntervalTrigger(minutes=self.config.optimization_interval_minutes),
            id="production_optimization",
            name="Production Optimization",
            replace_existing=True
        )
        logger.info(f"Added production optimization job (every {self.config.optimization_interval_minutes} minutes)")
        
        # 5. Weekly Data Cleanup - Sundays at 2 AM
        self.scheduler.add_job(
            func=self._weekly_cleanup_job,
            trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # Sunday = 6
            id="weekly_cleanup",
            name="Weekly Data Cleanup",
            replace_existing=True
        )
        logger.info("Added weekly cleanup job (Sundays at 2:00 AM)")
    
    async def _ingest_ree_prices_job(self):
        """Scheduled job for REE price data ingestion"""
        job_start = datetime.now()
        
        try:
            logger.info("Starting scheduled REE price ingestion")
            
            async with DataIngestionService() as service:
                stats = await service.ingest_current_prices()
            
            logger.info(f"REE ingestion completed: {stats.successful_writes} records, "
                       f"{stats.success_rate:.1f}% success rate")
            
            # Alert on low success rate
            if stats.success_rate < 90 and stats.total_records > 0:
                await self._send_alert(
                    "REE Ingestion Warning",
                    f"Low success rate: {stats.success_rate:.1f}% ({stats.successful_writes}/{stats.total_records})"
                )
            
        except Exception as e:
            logger.error(f"REE price ingestion job failed: {e}")
            await self._send_alert("REE Ingestion Error", str(e))
            raise
    
    async def _daily_backfill_job(self):
        """Scheduled job for daily data backfill and validation"""
        try:
            logger.info("Starting daily backfill job")
            
            async with DataIngestionService() as service:
                # Backfill previous day to handle any missed data
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                stats = await service.ingest_daily_prices(yesterday)
            
            logger.info(f"Daily backfill completed: {stats.successful_writes} records")
            
        except Exception as e:
            logger.error(f"Daily backfill job failed: {e}")
            await self._send_alert("Daily Backfill Error", str(e))
            raise
    
    async def _health_check_job(self):
        """Scheduled job for system health monitoring"""
        try:
            logger.debug("Running system health check")
            
            async with DataIngestionService() as service:
                status = await service.get_ingestion_status()
            
            if status.get("status") != "connected":
                await self._send_alert(
                    "System Health Alert",
                    f"InfluxDB connection issue: {status.get('error', 'Unknown error')}"
                )
            
            # Check for stale data
            latest_record = status.get("latest_price_record")
            if latest_record:
                latest_time = latest_record.get("timestamp")
                if latest_time:
                    age_hours = (datetime.now(timezone.utc) - latest_time).total_seconds() / 3600
                    if age_hours > 2:  # Alert if data is older than 2 hours
                        await self._send_alert(
                            "Stale Data Alert",
                            f"Latest price data is {age_hours:.1f} hours old"
                        )
            
        except Exception as e:
            logger.error(f"Health check job failed: {e}")
            # Don't re-raise to avoid cascading alerts
    
    async def _production_optimization_job(self):
        """Scheduled job for production optimization"""
        try:
            logger.info("Running production optimization")
            
            # TODO: Implement production optimization logic
            # This would integrate with the optimization engine
            # For now, just a placeholder
            
            logger.info("Production optimization completed")
            
        except Exception as e:
            logger.error(f"Production optimization job failed: {e}")
            await self._send_alert("Optimization Error", str(e))
            raise
    
    async def _weekly_cleanup_job(self):
        """Scheduled job for weekly data cleanup and maintenance"""
        try:
            logger.info("Starting weekly cleanup")
            
            # TODO: Implement data cleanup logic
            # - Archive old data
            # - Clean up temporary files
            # - Database maintenance
            
            logger.info("Weekly cleanup completed")
            
        except Exception as e:
            logger.error(f"Weekly cleanup job failed: {e}")
            await self._send_alert("Cleanup Error", str(e))
            raise
    
    async def _send_alert(self, subject: str, message: str):
        """Send alert notification (placeholder for actual alerting system)"""
        logger.warning(f"ALERT - {subject}: {message}")
        
        # TODO: Implement actual alerting mechanism
        # - Email notifications
        # - Slack/Teams integration
        # - Push to Node-RED dashboard
        # - SMS alerts for critical issues
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        if not self.scheduler:
            return {"status": "not_initialized"}
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            job_stats = self.job_stats.get(job.id)
            
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
                "trigger": str(job.trigger),
                "stats": job_stats.dict() if job_stats else None
            })
        
        return {
            "status": "running" if self.is_running else "stopped",
            "total_jobs": len(jobs_info),
            "jobs": jobs_info
        }
    
    async def trigger_job_now(self, job_id: str) -> bool:
        """Manually trigger a job immediately"""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            logger.info(f"Manually triggering job: {job_id}")
            job.modify(next_run_time=datetime.now())
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return False
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} paused")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False


# Global scheduler instance
_scheduler_service: Optional[SchedulerService] = None


async def get_scheduler_service() -> SchedulerService:
    """Get or create the global scheduler service instance"""
    global _scheduler_service
    
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    
    return _scheduler_service


async def start_scheduler():
    """Start the global scheduler service"""
    scheduler = await get_scheduler_service()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler service"""
    global _scheduler_service
    
    if _scheduler_service:
        await _scheduler_service.stop()
        _scheduler_service = None


# Example usage
if __name__ == "__main__":
    async def main():
        # Test scheduler
        scheduler = SchedulerService()
        
        try:
            await scheduler.start()
            
            # Let it run for a bit
            await asyncio.sleep(10)
            
            # Check status
            status = scheduler.get_job_status()
            print(f"Scheduler status: {status}")
            
        finally:
            await scheduler.stop()
    
    asyncio.run(main())