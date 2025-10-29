"""
Backfill Service - Chocolate Factory
========================================

Servicio para rellenar gaps (huecos) de datos de manera inteligente,
usando APIs históricas de REE y estrategias híbridas para datos climáticos.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd
from loguru import logger

from .gap_detector import GapDetectionService, DataGap
from .data_ingestion import DataIngestionService
from infrastructure.external_apis import REEAPIClient  # Sprint 15: consolidate API clients
from .siar_etl import SiarETL

# For backward compatibility with old imports
REEClient = REEAPIClient


@dataclass
class BackfillResult:
    """Resultado de una operación de backfill"""
    measurement: str
    gap_start: datetime
    gap_end: datetime
    records_requested: int
    records_obtained: int
    records_written: int
    success_rate: float
    duration_seconds: float
    method_used: str
    errors: List[str]


class BackfillService:
    """Servicio para backfill inteligente de datos faltantes"""
    
    def __init__(self):
        self.gap_detector = GapDetectionService()
        
    async def execute_intelligent_backfill(self, days_back: int = 10) -> Dict[str, Any]:
        """Ejecutar backfill completo e inteligente"""
        try:
            start_time = datetime.now()
            logger.info(f"🔄 Iniciando backfill inteligente - últimos {days_back} días")
            
            # 1. Detectar gaps
            analysis = await self.gap_detector.detect_all_gaps(days_back)
            
            if analysis.total_gaps_found == 0:
                return {
                    "status": "success",
                    "message": "No gaps found - data is up to date",
                    "gaps_found": 0,
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            
            # 2. Ejecutar backfill REE
            ree_results = []
            if analysis.ree_gaps:
                logger.info(f"📊 Ejecutando backfill REE para {len(analysis.ree_gaps)} gaps")
                ree_results = await self._backfill_ree_gaps(analysis.ree_gaps)
            
            # 3. Ejecutar backfill Weather
            weather_results = []
            if analysis.weather_gaps:
                logger.info(f"🌤️ Ejecutando backfill Weather para {len(analysis.weather_gaps)} gaps")
                weather_results = await self._backfill_weather_gaps(analysis.weather_gaps)
            
            # 4. Consolidar resultados
            total_duration = (datetime.now() - start_time).total_seconds()
            
            summary = self._generate_backfill_summary(
                ree_results, weather_results, total_duration
            )
            
            logger.info(f"✅ Backfill completado en {total_duration:.1f}s")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error en backfill inteligente: {e}")
            raise
    
    async def _backfill_ree_gaps(self, gaps: List[DataGap]) -> List[BackfillResult]:
        """Backfill específico para gaps de REE"""
        results = []
        
        try:
            async with REEClient() as ree_client:
                async with DataIngestionService() as ingestion_service:
                    
                    for gap in gaps:
                        gap_start = datetime.now()
                        logger.info(f"📊 Rellenando gap REE: {gap.start_time} - {gap.end_time}")
                        
                        try:
                            # Obtener datos históricos REE por días
                            current_date = gap.start_time.date()
                            end_date = gap.end_time.date()
                            
                            total_records = 0
                            total_written = 0
                            errors = []
                            
                            while current_date <= end_date:
                                try:
                                    # Obtener datos para el día actual
                                    day_start = datetime.combine(
                                        current_date, datetime.min.time()
                                    ).replace(tzinfo=timezone.utc)
                                    
                                    day_end = day_start + timedelta(days=1) - timedelta(minutes=1)
                                    
                                    # Usar get_pvpc_prices con rango de fechas
                                    daily_data = await ree_client.get_pvpc_prices(
                                        start_date=day_start, 
                                        end_date=day_end
                                    )
                                    
                                    if daily_data:
                                        # Escribir a InfluxDB usando el método correcto
                                        write_result = await ingestion_service.ingest_ree_prices_historical(daily_data)
                                        total_records += len(daily_data)
                                        total_written += write_result.successful_writes
                                        
                                        logger.info(f"📊 Día {current_date}: {len(daily_data)} registros REE escritos")
                                    
                                    # Rate limiting
                                    await asyncio.sleep(2)  # 30 req/min max
                                    
                                except Exception as day_error:
                                    error_msg = f"Error día {current_date}: {day_error}"
                                    errors.append(error_msg)
                                    logger.warning(error_msg)
                                
                                current_date += timedelta(days=1)
                            
                            # Crear resultado
                            duration = (datetime.now() - gap_start).total_seconds()
                            success_rate = (total_written / total_records * 100) if total_records > 0 else 0
                            
                            result = BackfillResult(
                                measurement="energy_prices",
                                gap_start=gap.start_time,
                                gap_end=gap.end_time,
                                records_requested=gap.expected_records,
                                records_obtained=total_records,
                                records_written=total_written,
                                success_rate=success_rate,
                                duration_seconds=duration,
                                method_used="REE_historical_daily",
                                errors=errors
                            )
                            
                            results.append(result)
                            logger.info(f"✅ Gap REE completado: {total_written}/{total_records} records")
                            
                        except Exception as gap_error:
                            logger.error(f"❌ Error en gap REE {gap.start_time}: {gap_error}")
                            
                            result = BackfillResult(
                                measurement="energy_prices",
                                gap_start=gap.start_time,
                                gap_end=gap.end_time,
                                records_requested=gap.expected_records,
                                records_obtained=0,
                                records_written=0,
                                success_rate=0,
                                duration_seconds=(datetime.now() - gap_start).total_seconds(),
                                method_used="REE_historical_daily",
                                errors=[str(gap_error)]
                            )
                            results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error general en backfill REE: {e}")
            return results
    
    async def _backfill_weather_gaps(self, gaps: List[DataGap]) -> List[BackfillResult]:
        """
        Backfill específico para gaps de Weather con estrategia inteligente

        Estrategia basada en antigüedad del gap:
        - Gaps recientes (<48h): OpenWeatherMap (datos en tiempo real)
        - Gaps históricos (≥48h): AEMET API (datos consolidados oficiales)

        Razón: AEMET necesita 24-48h para consolidar datos diarios oficiales.
        """
        results = []

        try:
            # Determinar estrategia basada en antigüedad del gap
            now = datetime.now(timezone.utc)
            RECENT_GAP_THRESHOLD_HOURS = 48  # Umbral para considerar gap "reciente"

            for gap in gaps:
                gap_start = datetime.now()
                hours_since_gap_end = (now - gap.end_time).total_seconds() / 3600

                logger.info(f"🌤️ Rellenando gap Weather: {gap.start_time} - {gap.end_time}")
                logger.info(f"   📊 Antigüedad del gap: {hours_since_gap_end:.1f}h desde el final del gap")

                try:
                    # ESTRATEGIA INTELIGENTE: Basada en antigüedad del gap
                    if hours_since_gap_end < RECENT_GAP_THRESHOLD_HOURS:
                        # Gap reciente: Usar OpenWeatherMap (datos en tiempo real)
                        logger.info(f"🔄 Gap reciente (<48h) - usando OpenWeatherMap API")
                        result = await self._backfill_weather_openweather(gap)
                    else:
                        # Gap histórico: Usar AEMET API (datos consolidados oficiales)
                        logger.info(f"📅 Gap histórico (≥48h) - usando AEMET API oficial")
                        result = await self._backfill_weather_aemet(gap)

                    # Si AEMET falla con gap grande (>30 días), notificar para descarga SIAR manual
                    if result.success_rate < 50 and gap.gap_duration_hours > 720:  # 30 días
                        logger.warning(f"⚠️ AEMET falló con gap grande ({gap.gap_duration_hours:.1f}h). "
                                     f"Considerar descarga manual SIAR para {gap_month}/{gap_year}")
                        # Aquí podrías agregar notificación por email/webhook si la configuras
                    
                    results.append(result)
                    
                except Exception as gap_error:
                    logger.error(f"❌ Error en gap Weather {gap.start_time}: {gap_error}")
                    
                    result = BackfillResult(
                        measurement="weather_data",
                        gap_start=gap.start_time,
                        gap_end=gap.end_time,
                        records_requested=gap.expected_records,
                        records_obtained=0,
                        records_written=0,
                        success_rate=0,
                        duration_seconds=(datetime.now() - gap_start).total_seconds(),
                        method_used="failed",
                        errors=[str(gap_error)]
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error general en backfill Weather: {e}")
            return results
    
    
    async def _backfill_weather_aemet(self, gap: DataGap) -> BackfillResult:
        """Backfill usando AEMET API oficial (método principal para cualquier fecha)"""
        gap_start = datetime.now()
        
        try:
            from infrastructure.external_apis import AEMETAPIClient  # Sprint 15
            async with AEMETAPIClient() as aemet_client:
                async with DataIngestionService() as ingestion_service:
                    
                    # Procesar por días para evitar timeouts
                    current_date = gap.start_time.date()
                    end_date = gap.end_time.date()
                    
                    total_records = 0
                    total_written = 0
                    errors = []
                    
                    # Para AEMET en mes actual, usar método simplificado
                    # El gap representa días faltantes, usar ingesta por rango de fechas
                    try:
                        logger.info(f"🌤️ Procesando datos AEMET gap: {gap.start_time} - {gap.end_time}")
                        
                        # Usar el método existente que maneja la lógica interna
                        write_result = await ingestion_service.ingest_aemet_weather(
                            station_ids=["5279X"],  # Linares, Jaén
                            start_date=gap.start_time,
                            end_date=gap.end_time
                        )
                        
                        total_records = write_result.total_records
                        total_written = write_result.successful_writes
                        
                        logger.info(f"✅ AEMET gap processed: {total_written}/{total_records} records")
                        
                    except Exception as gap_error:
                        error_msg = f"Error procesando gap AEMET: {gap_error}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                    
                    # Calcular resultado
                    duration = (datetime.now() - gap_start).total_seconds()
                    success_rate = (total_written / gap.expected_records * 100) if gap.expected_records > 0 else 0
                    
                    return BackfillResult(
                        measurement="weather_data",
                        gap_start=gap.start_time,
                        gap_end=gap.end_time,
                        records_requested=gap.expected_records,
                        records_obtained=total_records,
                        records_written=total_written,
                        success_rate=success_rate,
                        duration_seconds=duration,
                        method_used="aemet_current_month",
                        errors=errors
                    )
                    
        except Exception as e:
            logger.error(f"Error en backfill AEMET: {e}")
            
            return BackfillResult(
                measurement="weather_data",
                gap_start=gap.start_time,
                gap_end=gap.end_time,
                records_requested=gap.expected_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=(datetime.now() - gap_start).total_seconds(),
                method_used="aemet_current_month",
                errors=[str(e)]
            )

    async def _backfill_weather_openweather(self, gap: DataGap) -> BackfillResult:
        """
        Backfill usando OpenWeatherMap para gaps recientes (<48h)

        OpenWeatherMap proporciona datos en tiempo real y históricos recientes,
        ideal para gaps que aún no han sido consolidados por AEMET.
        """
        gap_start = datetime.now()

        try:
            from infrastructure.external_apis import OpenWeatherMapAPIClient  # Sprint 15
            async with OpenWeatherMapAPIClient() as owm_client:
                async with DataIngestionService() as ingestion_service:

                    total_records = 0
                    total_written = 0
                    errors = []

                    try:
                        logger.info(f"🌤️ Procesando datos OpenWeatherMap gap: {gap.start_time} - {gap.end_time}")

                        # OpenWeatherMap: Obtener datos actuales (solo datos recientes, no históricos)
                        # Nota: OWM free tier no proporciona datos históricos, solo actuales
                        # Este método obtiene datos del momento actual, no del gap específico
                        write_result = await ingestion_service.ingest_openweathermap_weather()

                        total_records = write_result.total_records
                        total_written = write_result.successful_writes

                        logger.info(f"✅ OpenWeatherMap current data obtained: {total_written}/{total_records} records")
                        logger.warning(f"⚠️ OpenWeatherMap Free tier no soporta datos históricos. Solo datos actuales obtenidos.")

                    except Exception as gap_error:
                        error_msg = f"Error procesando gap OpenWeatherMap: {gap_error}"
                        errors.append(error_msg)
                        logger.warning(error_msg)

                    # Calcular resultado
                    duration = (datetime.now() - gap_start).total_seconds()
                    success_rate = (total_written / gap.expected_records * 100) if gap.expected_records > 0 else 0

                    return BackfillResult(
                        measurement="weather_data",
                        gap_start=gap.start_time,
                        gap_end=gap.end_time,
                        records_requested=gap.expected_records,
                        records_obtained=total_records,
                        records_written=total_written,
                        success_rate=success_rate,
                        duration_seconds=duration,
                        method_used="openweathermap_recent",
                        errors=errors
                    )

        except Exception as e:
            logger.error(f"Error en backfill OpenWeatherMap: {e}")

            return BackfillResult(
                measurement="weather_data",
                gap_start=gap.start_time,
                gap_end=gap.end_time,
                records_requested=gap.expected_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=(datetime.now() - gap_start).total_seconds(),
                method_used="openweathermap_recent",
                errors=[str(e)]
            )

    def _generate_backfill_summary(self, ree_results: List[BackfillResult], 
                                 weather_results: List[BackfillResult],
                                 total_duration: float) -> Dict[str, Any]:
        """Generar resumen completo del backfill"""
        
        all_results = ree_results + weather_results
        
        total_requested = sum(r.records_requested for r in all_results)
        total_obtained = sum(r.records_obtained for r in all_results)
        total_written = sum(r.records_written for r in all_results)
        
        overall_success_rate = (total_written / total_requested * 100) if total_requested > 0 else 0
        
        # Contadores por tipo
        ree_written = sum(r.records_written for r in ree_results)
        weather_written = sum(r.records_written for r in weather_results)
        
        return {
            "status": "success" if overall_success_rate > 70 else "partial",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_gaps_processed": len(all_results),
                "ree_gaps": len(ree_results),
                "weather_gaps": len(weather_results),
                "total_duration_seconds": round(total_duration, 1),
                "overall_success_rate": round(overall_success_rate, 1)
            },
            "records": {
                "total_requested": total_requested,
                "total_obtained": total_obtained,
                "total_written": total_written,
                "ree_records_written": ree_written,
                "weather_records_written": weather_written
            },
            "detailed_results": [
                {
                    "measurement": r.measurement,
                    "gap_period": f"{r.gap_start.isoformat()} - {r.gap_end.isoformat()}",
                    "records_written": r.records_written,
                    "success_rate": round(r.success_rate, 1),
                    "method": r.method_used,
                    "duration_seconds": round(r.duration_seconds, 1),
                    "errors": r.errors
                }
                for r in all_results
            ],
            "recommendations": {
                "data_status": "updated" if overall_success_rate > 90 else "partially_updated",
                "next_check": "Run /gaps/summary to verify results"
            }
        }
    
    async def check_and_execute_auto_backfill(self, max_gap_hours: float = 6.0) -> Dict[str, Any]:
        """Verificar si hay gaps significativos y ejecutar backfill automático"""
        try:
            # Obtener últimos timestamps
            latest = await self.gap_detector.get_latest_timestamps()
            now = datetime.now(timezone.utc)
            
            needs_backfill = False
            ree_gap_hours = 0
            weather_gap_hours = 0
            
            # Verificar gap REE
            if latest['latest_ree']:
                ree_gap_hours = (now - latest['latest_ree']).total_seconds() / 3600
                if ree_gap_hours > max_gap_hours:
                    needs_backfill = True
            else:
                needs_backfill = True
                ree_gap_hours = 24 * 7  # Asumimos 1 semana sin datos
            
            # Verificar gap Weather
            if latest['latest_weather']:
                weather_gap_hours = (now - latest['latest_weather']).total_seconds() / 3600
                if weather_gap_hours > max_gap_hours:
                    needs_backfill = True
            else:
                needs_backfill = True
                weather_gap_hours = 24 * 7  # Asumimos 1 semana sin datos
            
            if needs_backfill:
                logger.info(f"🔄 Auto-backfill triggered: REE gap {ree_gap_hours:.1f}h, Weather gap {weather_gap_hours:.1f}h")
                
                # Calcular días hacia atrás necesarios
                max_gap = max(ree_gap_hours, weather_gap_hours)
                days_back = min(int(max_gap / 24) + 2, 30)  # Máximo 30 días
                
                # Ejecutar backfill
                result = await self.execute_intelligent_backfill(days_back)
                result["trigger"] = "automatic"
                result["detected_gaps"] = {
                    "ree_hours": round(ree_gap_hours, 1),
                    "weather_hours": round(weather_gap_hours, 1)
                }
                
                return result
            else:
                return {
                    "status": "no_action_needed",
                    "message": "Data is up to date",
                    "gaps": {
                        "ree_hours": round(ree_gap_hours, 1),
                        "weather_hours": round(weather_gap_hours, 1),
                        "threshold_hours": max_gap_hours
                    }
                }
                
        except Exception as e:
            logger.error(f"Error en auto-backfill check: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# Instancia global
backfill_service = BackfillService()