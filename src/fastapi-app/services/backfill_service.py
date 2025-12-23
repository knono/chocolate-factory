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

    def __init__(self, telegram_service=None):
        self.gap_detector = GapDetectionService(telegram_service=telegram_service)
        self.telegram_service = telegram_service
        
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

            # Send success alert
            if self.telegram_service:
                try:
                    from services.telegram_alert_service import AlertSeverity

                    total_records = summary.get("total_records_written", 0)
                    gap_hours = summary.get("total_gap_hours", 0)

                    await self.telegram_service.send_alert(
                        message=f"Backfill completed successfully\n"
                                f"Records written: {total_records}\n"
                                f"Gap filled: {gap_hours:.1f}h\n"
                                f"Duration: {total_duration:.1f}s",
                        severity=AlertSeverity.INFO,
                        topic="backfill_completion"
                    )
                except Exception as alert_error:
                    logger.warning(f"Failed to send success alert: {alert_error}")

            return summary

        except Exception as e:
            logger.error(f"❌ Error en backfill inteligente: {e}")

            # Send failure alert
            if self.telegram_service:
                try:
                    from services.telegram_alert_service import AlertSeverity

                    await self.telegram_service.send_alert(
                        message=f"Backfill failed: {str(e)[:200]}",
                        severity=AlertSeverity.CRITICAL,
                        topic="backfill_failure"
                    )
                except Exception as alert_error:
                    logger.warning(f"Failed to send failure alert: {alert_error}")

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

                                    # Usar get_pvpc_prices con target_date (API solo acepta fecha única)
                                    daily_data = await ree_client.get_pvpc_prices(
                                        target_date=current_date
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
        Backfill específico para gaps de Weather usando AEMET API

        IMPORTANTE: OpenWeatherMap Free tier NO soporta datos históricos, solo actuales.
        Por lo tanto, SIEMPRE usamos AEMET API para backfill de gaps históricos.

        Estrategia optimizada para reducir tiempo de equipo encendido:
        - Gaps futuros o recientes (<48h desde ahora): AEMET predicción horaria por municipio (48h forecast)
        - Gaps pasados recientes (48-72h): AEMET observaciones horarias de estación
        - Gaps antiguos (≥72h): AEMET valores climatológicos diarios
        - OpenWeatherMap solo se usa para ingesta en tiempo real (no backfill)

        La predicción por municipio permite pre-cargar 48h de datos meteorológicos,
        reduciendo la necesidad de tener el equipo encendido para backfill.
        """
        results = []

        try:
            now = datetime.now(timezone.utc)

            for gap in gaps:
                gap_start = datetime.now()

                # Calcular antigüedad del gap (desde INICIO, no desde fin)
                gap_age_hours = (now - gap.start_time).total_seconds() / 3600
                # Calcular si el gap termina en el futuro cercano (dentro de 48h)
                hours_until_gap_end = (gap.end_time - now).total_seconds() / 3600

                logger.info(f"🌤️ Rellenando gap Weather: {gap.start_time} - {gap.end_time}")
                logger.info(f"   ⏰ Antigüedad gap: {gap_age_hours:.1f}h (duración: {gap.gap_duration_hours:.1f}h)")
                logger.info(f"   ⏰ Horas hasta fin del gap: {hours_until_gap_end:.1f}h")

                try:
                    # Seleccionar estrategia según posición temporal del gap
                    if hours_until_gap_end > 0 and hours_until_gap_end <= 48:
                        # Gap que incluye el futuro cercano: usar predicción horaria AEMET (48h forecast)
                        logger.info(f"   🔮 Usando AEMET predicción horaria por municipio (gap incluye futuro <48h)")
                        result = await self._backfill_weather_aemet_forecast(gap)
                    elif gap_age_hours < 48 and gap.gap_duration_hours <= 48:
                        # Gap muy reciente y corto: también podemos usar predicción
                        logger.info(f"   🔮 Usando AEMET predicción horaria por municipio (gap reciente <48h)")
                        result = await self._backfill_weather_aemet_forecast(gap)
                    elif gap_age_hours >= 72 or gap.gap_duration_hours >= 72:
                        # Gap antiguo o muy largo: usar valores climatológicos diarios
                        logger.info(f"   📅 Usando AEMET valores climatológicos diarios (gap antiguo o largo)")
                        result = await self._backfill_weather_aemet(gap)
                    else:
                        # Gap intermedio (48-72h): usar observaciones horarias de estación
                        logger.info(f"   📊 Usando AEMET observaciones horarias (gap 48-72h)")
                        result = await self._backfill_weather_aemet_hourly(gap)

                    # Si AEMET falla con gap grande (>30 días), notificar para descarga SIAR manual
                    if result.success_rate < 50 and gap.gap_duration_hours > 720:  # 30 días
                        logger.warning(f"⚠️ AEMET falló con gap grande ({gap.gap_duration_hours:.1f}h). "
                                     f"Considerar descarga manual SIAR si necesario")

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

    async def _backfill_weather_aemet_hourly(self, gap: DataGap) -> BackfillResult:
        """
        Backfill usando observaciones horarias de AEMET (para gaps recientes <72h)

        AEMET tiene un delay de ~3 días para valores climatológicos diarios,
        pero las observaciones horarias están disponibles inmediatamente.

        Endpoint: /api/observacion/convencional/datos/estacion/{idema}
        Retorna: últimas 24h de observaciones de la estación
        """
        gap_start = datetime.now()

        try:
            from infrastructure.external_apis import AEMETAPIClient
            async with AEMETAPIClient() as aemet_client:
                async with DataIngestionService() as ingestion_service:

                    logger.info(f"🌤️ Procesando observaciones AEMET hourly gap: {gap.start_time} - {gap.end_time}")

                    total_records = 0
                    total_written = 0
                    errors = []

                    # AEMET observaciones horarias solo devuelve últimas 24h
                    # Para gaps más grandes, necesitamos llamar múltiples veces o usar diarios
                    try:
                        # Usar el método de ingesta existente para observaciones actuales
                        write_result = await ingestion_service.ingest_aemet_weather(
                            station_ids=["5279X"],  # Linares, Jaén
                            start_date=None,  # Sin fechas = modo current weather
                            end_date=None
                        )

                        total_records = write_result.total_records
                        total_written = write_result.successful_writes

                        logger.info(f"✅ AEMET hourly gap processed: {total_written}/{total_records} records")

                    except Exception as gap_error:
                        error_msg = f"Error procesando gap AEMET hourly: {gap_error}"
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
                        method_used="aemet_hourly_observations",
                        errors=errors
                    )

        except Exception as e:
            logger.error(f"Error en backfill AEMET hourly: {e}")

            return BackfillResult(
                measurement="weather_data",
                gap_start=gap.start_time,
                gap_end=gap.end_time,
                records_requested=gap.expected_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=(datetime.now() - gap_start).total_seconds(),
                method_used="aemet_hourly_observations",
                errors=[str(e)]
            )

    async def _backfill_weather_aemet_forecast(self, gap: DataGap) -> BackfillResult:
        """
        Backfill usando predicción horaria AEMET por municipio (para gaps <48h).

        Este método usa el endpoint de predicción horaria por municipio que proporciona
        datos hora a hora para las próximas 48 horas. Ideal para:
        - Llenar gaps cuando el equipo está apagado
        - Pre-cargar datos meteorológicos futuros
        - Reducir dependencia de tener el equipo encendido 24/7

        Endpoint: /api/prediccion/especifica/municipio/horaria/{municipio}
        Municipio Linares (Jaén): 23055

        NOTA: Estos son datos de PREDICCIÓN, no observaciones reales.
        Se marcan con data_type='forecast' para diferenciarnos.
        """
        gap_start_time = datetime.now()

        try:
            from infrastructure.external_apis import AEMETAPIClient
            async with AEMETAPIClient() as aemet_client:
                async with DataIngestionService() as ingestion_service:

                    logger.info(f"🔮 Obteniendo predicción horaria AEMET para gap: {gap.start_time} - {gap.end_time}")

                    total_records = 0
                    total_written = 0
                    errors = []

                    try:
                        # Obtener predicción horaria (hasta 48h)
                        forecast_data = await aemet_client.get_hourly_forecast_municipality()

                        if not forecast_data:
                            errors.append("No se obtuvieron datos de predicción AEMET")
                            logger.warning("⚠️ AEMET predicción horaria no devolvió datos")
                        else:
                            # Filtrar solo los registros dentro del rango del gap
                            relevant_records = []
                            for record in forecast_data:
                                record_time = record.get("timestamp")
                                if record_time and gap.start_time <= record_time <= gap.end_time:
                                    relevant_records.append(record)

                            total_records = len(relevant_records)

                            if relevant_records:
                                # Escribir a InfluxDB usando ingestion service
                                write_result = await ingestion_service.ingest_weather_forecast(relevant_records)
                                total_written = write_result.successful_writes

                                logger.info(f"✅ AEMET predicción horaria: {total_written}/{total_records} records escritos")
                            else:
                                logger.warning(f"⚠️ No hay registros de predicción dentro del gap {gap.start_time} - {gap.end_time}")

                    except Exception as forecast_error:
                        error_msg = f"Error obteniendo predicción AEMET: {forecast_error}"
                        errors.append(error_msg)
                        logger.warning(error_msg)

                    # Calcular resultado
                    duration = (datetime.now() - gap_start_time).total_seconds()
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
                        method_used="aemet_hourly_forecast_municipality",
                        errors=errors
                    )

        except Exception as e:
            logger.error(f"Error en backfill AEMET forecast: {e}")

            return BackfillResult(
                measurement="weather_data",
                gap_start=gap.start_time,
                gap_end=gap.end_time,
                records_requested=gap.expected_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=(datetime.now() - gap_start_time).total_seconds(),
                method_used="aemet_hourly_forecast_municipality",
                errors=[str(e)]
            )

    async def _backfill_weather_openweather(self, gap: DataGap) -> BackfillResult:
        """
        Backfill usando OpenWeatherMap para gaps recientes (<48h)

        LIMITATION: OpenWeatherMap Free tier solo proporciona datos ACTUALES,
        no datos históricos. No puede llenar gaps pasados, solo obtener el dato del momento presente.

        Este método está limitado a:
        - Obtener datos meteorológicos del momento actual
        - NO puede recuperar datos de horas/días pasados
        - NO puede llenar el gap solicitado con datos históricos

        Para backfill real de gaps históricos, usar AEMET API.
        """
        gap_start = datetime.now()
        errors = ["OpenWeatherMap Free tier no soporta datos históricos. No se puede llenar este gap. Use AEMET para gaps históricos."]

        logger.warning(f"⚠️ OpenWeatherMap no puede llenar gap {gap.start_time} - {gap.end_time}")
        logger.warning(f"⚠️ OpenWeatherMap Free tier solo proporciona datos actuales, no históricos")
        logger.info(f"💡 Sugerencia: Use AEMET API para backfill de gaps históricos")

        # No intentar backfill - OpenWeatherMap Free tier no lo soporta
        return BackfillResult(
            measurement="weather_data",
            gap_start=gap.start_time,
            gap_end=gap.end_time,
            records_requested=gap.expected_records,
            records_obtained=0,
            records_written=0,
            success_rate=0,
            duration_seconds=(datetime.now() - gap_start).total_seconds(),
            method_used="openweathermap_not_supported",
            errors=errors
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