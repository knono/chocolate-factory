"""
APScheduler Service for Chocolate Factory
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
        # 🚀 TEMPORARY ACCELERATION MODE (24-48h for MLflow data collection)
        # TODO: Revert to normal frequency after data collection:
        # - REE: CronTrigger(minute=5) [hourly at :05]  
        # - Weather: CronTrigger(minute=15) [hourly at :15]
        
        # 1. REE Price Data Ingestion - ACCELERATED: Every 5 minutes for maximum data collection
        self.scheduler.add_job(
            func=self._ingest_ree_prices_job,
            trigger=IntervalTrigger(minutes=5),  # ACCELERATED: Every 5 minutes
            id="ree_price_ingestion",
            name="REE Price Data Ingestion (ACCELERATED)",
            replace_existing=True
        )
        logger.info("🚀 Added REE price ingestion job (ACCELERATED: every 5 minutes)")
        
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
        
        # 5. Hybrid Weather Data Ingestion - ACCELERATED: Every 5 minutes for maximum data collection
        self.scheduler.add_job(
            func=self._hybrid_weather_ingestion_job,
            trigger=IntervalTrigger(minutes=5),  # ACCELERATED: Every 5 minutes
            id="hybrid_weather_ingestion",
            name="Hybrid Weather Data Ingestion",
            replace_existing=True
        )
        logger.info("🚀 Added hybrid weather ingestion job (ACCELERATED: every 5 minutes)")
        
        # 6. AEMET Token Renewal Check - Daily at 3 AM
        self.scheduler.add_job(
            func=self._aemet_token_check_job,
            trigger=CronTrigger(hour=3, minute=0),
            id="aemet_token_check",
            name="AEMET Token Renewal Check",
            replace_existing=True
        )
        logger.info("Added AEMET token check job (daily at 3:00 AM)")
        
        # 7. Weekly Data Cleanup - Sundays at 2 AM
        self.scheduler.add_job(
            func=self._weekly_cleanup_job,
            trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # Sunday = 6
            id="weekly_cleanup",
            name="Weekly Data Cleanup",
            replace_existing=True
        )
        logger.info("Added weekly cleanup job (Sundays at 2:00 AM)")
        
        # 8. ML Predictions Job - Every 30 minutes
        self.scheduler.add_job(
            func=self._ml_predictions_job,
            trigger=IntervalTrigger(minutes=30),
            id="ml_predictions",
            name="ML Production Predictions",
            replace_existing=True
        )
        logger.info("Added ML predictions job (every 30 minutes)")
        
        # 9. ML Model Training/Retraining Job - Every 30 minutes
        self.scheduler.add_job(
            func=self._ml_training_job,
            trigger=IntervalTrigger(minutes=30),
            id="ml_training",
            name="ML Model Training/Retraining",
            replace_existing=True
        )
        logger.info("Added ML training job (every 30 minutes)")
        
        # 10. Auto Backfill Check - Every 2 hours
        self.scheduler.add_job(
            func=self._auto_backfill_check_job,
            trigger=IntervalTrigger(hours=2),
            id="auto_backfill_check",
            name="Auto Backfill Detection",
            replace_existing=True
        )
        logger.info("Added auto backfill check job (every 2 hours)")
    
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
    
    async def _hybrid_weather_ingestion_job(self):
        """Scheduled job for hybrid weather data ingestion (AEMET + OpenWeatherMap)"""
        job_start = datetime.now()
        current_hour = job_start.hour
        
        try:
            logger.info(f"Starting scheduled hybrid weather ingestion (hour {current_hour:02d}:xx)")
            
            async with DataIngestionService() as service:
                stats = await service.ingest_hybrid_weather()
            
            data_source = "AEMET" if (0 <= current_hour <= 7) else "OpenWeatherMap"
            logger.info(f"Hybrid ingestion completed using {data_source}: {stats.successful_writes} records, "
                       f"{stats.success_rate:.1f}% success rate")
            
            # Alert on low success rate
            if stats.success_rate < 80 and stats.total_records > 0:
                await self._send_alert(
                    "Hybrid Weather Ingestion Warning",
                    f"Low success rate using {data_source}: {stats.success_rate:.1f}% ({stats.successful_writes}/{stats.total_records})"
                )
            
        except Exception as e:
            logger.error(f"Hybrid weather ingestion job failed: {e}")
            await self._send_alert("Hybrid Weather Ingestion Error", str(e))
            raise
    
    async def _aemet_token_check_job(self):
        """Scheduled job to check and renew AEMET token if needed"""
        try:
            logger.info("Checking AEMET token status")
            
            from .aemet_client import AEMETClient
            
            async with AEMETClient() as client:
                token_status = await client.get_token_status()
            
            if token_status.get("status") == "expired":
                logger.warning("AEMET token expired, will be renewed on next API call")
                await self._send_alert(
                    "AEMET Token Expired",
                    "Token has expired and will be renewed automatically on next API request"
                )
            elif token_status.get("expires_soon"):
                days_left = token_status.get("days_until_expiry", 0)
                logger.info(f"AEMET token expires in {days_left} days")
                if days_left <= 1:
                    await self._send_alert(
                        "AEMET Token Expiring Soon",
                        f"Token expires in {days_left} days"
                    )
            else:
                logger.debug("AEMET token is valid")
                
        except Exception as e:
            logger.error(f"AEMET token check job failed: {e}")
            await self._send_alert("AEMET Token Check Error", str(e))
    
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
    
    async def _ml_predictions_job(self):
        """Scheduled job for ML predictions and production optimization"""
        job_start = datetime.now()
        
        try:
            logger.info("🤖 Starting scheduled ML predictions job")
            
            # Get current conditions from latest data
            from services.data_ingestion import DataIngestionService
            
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Get latest data (last 2 hours)
                price_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -2h)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> last()
                '''
                
                temp_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -2h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> last()
                '''
                
                humidity_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -2h)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "humidity")
                |> last()
                '''
                
                # Execute queries
                price_results = query_api.query(price_query)
                temp_results = query_api.query(temp_query)
                humidity_results = query_api.query(humidity_query)
                
                # Extract values
                price = None
                temperature = None
                humidity = None
                
                for table in price_results:
                    for record in table.records:
                        price = record.get_value()
                        break
                
                for table in temp_results:
                    for record in table.records:
                        temperature = record.get_value()
                        break
                
                for table in humidity_results:
                    for record in table.records:
                        humidity = record.get_value()
                        break
                
                # Only proceed if we have all required data
                if price is not None and temperature is not None and humidity is not None:
                    # Calculate predictions using same logic as prediction endpoints
                    
                    # Energy features
                    energy_cost_index = min(100, max(0, (price - 0.05) / (0.35 - 0.05) * 100))
                    temp_deviation = abs(temperature - 21)
                    temperature_comfort_index = max(0, 100 - (temp_deviation * 10))
                    
                    energy_optimization_score = (
                        (100 - energy_cost_index) * 0.7 + 
                        temperature_comfort_index * 0.3
                    )
                    energy_optimization_score = max(0, min(100, energy_optimization_score))
                    
                    # Production features
                    humidity_deviation = abs(humidity - 55)
                    humidity_stress_factor = humidity_deviation / 55 * 100
                    
                    chocolate_production_index = (
                        temperature_comfort_index - 
                        energy_cost_index * 0.5 - 
                        humidity_stress_factor * 0.3
                    )
                    chocolate_production_index = max(0, min(100, chocolate_production_index))
                    
                    # Classify recommendation
                    if chocolate_production_index >= 75:
                        recommendation = "Optimal_Production"
                        urgency = "low"
                    elif chocolate_production_index >= 50:
                        recommendation = "Moderate_Production"
                        urgency = "medium"
                    elif chocolate_production_index >= 25:
                        recommendation = "Reduced_Production"
                        urgency = "high"
                    else:
                        recommendation = "Halt_Production"
                        urgency = "critical"
                    
                    # Log predictions
                    logger.info(f"🤖 ML Prediction Results:")
                    logger.info(f"   📊 Energy Score: {energy_optimization_score:.1f}")
                    logger.info(f"   🍫 Recommendation: {recommendation}")
                    logger.info(f"   📈 Production Index: {chocolate_production_index:.1f}")
                    logger.info(f"   ⚠️  Urgency: {urgency}")
                    logger.info(f"   🌡️  Conditions: {temperature}°C, {humidity}%, {price}€/kWh")
                    
                    # Send alerts for critical conditions
                    if urgency == "critical":
                        await self._send_alert(
                            "🚨 Critical Production Alert",
                            f"HALT production - Score: {chocolate_production_index:.1f}"
                        )
                    elif urgency == "high":
                        await self._send_alert(
                            "⚠️ Production Warning", 
                            f"REDUCE production - Score: {chocolate_production_index:.1f}"
                        )
                    
                    job_duration = (datetime.now() - job_start).total_seconds()
                    logger.info(f"✅ ML predictions completed in {job_duration:.2f}s")
                    
                else:
                    logger.warning("⚠️ ML predictions skipped - insufficient data")
                    
        except Exception as e:
            logger.error(f"❌ ML predictions job failed: {e}")
            await self._send_alert(
                "ML Predictions Error", 
                f"Scheduled predictions failed: {str(e)}"
            )
    
    async def _ml_training_job(self):
        """Scheduled job for direct ML model training (no MLflow)"""
        job_start = datetime.now()
        
        try:
            logger.info("🤖 Starting scheduled direct ML training job")
            
            # Import direct ML service
            from services.direct_ml import DirectMLService
            
            # Initialize direct ML service
            direct_ml = DirectMLService()
            
            # Train models using direct approach
            training_results = await direct_ml.train_models()
            
            if not training_results.get("success"):
                logger.error(f"❌ ML training failed: {training_results.get('error', 'Unknown error')}")
                return
            
            # Log training results
            logger.info("🎯 Direct ML Training Results:")
            
            # Energy model results
            if "energy_model" in training_results:
                energy_metrics = training_results["energy_model"]
                logger.info(f"   🔋 Energy Model: R² = {energy_metrics.get('r2_score', 0):.4f}")
                logger.info(f"   📊 Training samples: {energy_metrics.get('training_samples', 0)}")
                logger.info(f"   ✅ Model saved: {energy_metrics.get('saved', False)}")
            
            # Production model results  
            if "production_model" in training_results:
                prod_metrics = training_results["production_model"]
                logger.info(f"   🍫 Production Model: Accuracy = {prod_metrics.get('accuracy', 0):.4f}")
                logger.info(f"   📊 Training samples: {prod_metrics.get('training_samples', 0)}")
                logger.info(f"   🎯 Classes: {prod_metrics.get('classes', [])}")
                logger.info(f"   ✅ Model saved: {prod_metrics.get('saved', False)}")
            
            logger.info(f"   📈 Total samples used: {training_results.get('total_samples', 0)}")
            logger.info(f"   🔧 Features: {training_results.get('features_used', [])}")
            
            # Send success alert for significant training improvements
            energy_metrics = training_results.get("energy_model")
            if energy_metrics and energy_metrics.get("r2_score", 0) > 0.85:
                await self._send_alert(
                    "🎯 ML Training Success",
                    f"High-performance models trained - Energy R²: {energy_metrics.get('r2_score'):.3f}"
                )
            
            job_duration = (datetime.now() - job_start).total_seconds()
            logger.info(f"✅ ML training completed in {job_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ ML training job failed: {e}")
            await self._send_alert(
                "ML Training Error", 
                f"Scheduled model training failed: {str(e)}"
            )
    
    async def _auto_backfill_check_job(self):
        """Scheduled job to detect gaps and execute automatic backfill"""
        job_start = datetime.now()
        
        try:
            logger.info("🤖 Starting auto backfill detection job")
            
            # Import backfill service
            from services.backfill_service import backfill_service
            
            # Verificar si hay gaps significativos (más de 3 horas)
            result = await backfill_service.check_and_execute_auto_backfill(max_gap_hours=3.0)
            
            if result.get("status") == "no_action_needed":
                logger.debug("✅ Auto backfill check: No action needed, data is up to date")
            
            elif result.get("trigger") == "automatic":
                # Se ejecutó backfill automático
                summary = result.get("summary", {})
                success_rate = summary.get("overall_success_rate", 0)
                
                logger.info(f"🔄 Auto backfill executed: {success_rate}% success rate")
                
                # Alertar sobre backfill exitoso
                if success_rate > 80:
                    await self._send_alert(
                        "🔄 Auto Backfill Success",
                        f"Sistema recuperado automáticamente - {success_rate:.1f}% datos restaurados"
                    )
                else:
                    await self._send_alert(
                        "⚠️ Auto Backfill Partial",
                        f"Backfill parcial - {success_rate:.1f}% datos restaurados - Revisar manualmente"
                    )
            
            else:
                # Error en el proceso
                error_msg = result.get("message", "Unknown error")
                logger.warning(f"⚠️ Auto backfill issue: {error_msg}")
                
                await self._send_alert(
                    "Auto Backfill Warning",
                    f"Sistema de recuperación automática encontró problemas: {error_msg}"
                )
            
            job_duration = (datetime.now() - job_start).total_seconds()
            logger.info(f"✅ Auto backfill check completed in {job_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Auto backfill check job failed: {e}")
            await self._send_alert(
                "Auto Backfill Error",
                f"Sistema de recuperación automática falló: {str(e)}"
            )
    
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