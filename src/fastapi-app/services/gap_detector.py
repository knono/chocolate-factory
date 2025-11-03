"""
Gap Detection Service - Chocolate Factory
============================================

Servicio para detectar gaps (huecos) en los datos de InfluxDB
y planificar el backfill necesario de manera inteligente.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pydantic import BaseModel
import pandas as pd
from loguru import logger

from .data_ingestion import DataIngestionService


@dataclass 
class DataGap:
    """Representa un gap (hueco) en los datos"""
    measurement: str
    start_time: datetime
    end_time: datetime
    expected_records: int
    missing_records: int
    gap_duration_hours: float
    severity: str  # "minor", "moderate", "critical"


class GapAnalysis(BaseModel):
    """Análisis completo de gaps en los datos"""
    analysis_timestamp: datetime
    total_gaps_found: int
    ree_gaps: List[DataGap]
    weather_gaps: List[DataGap] 
    recommended_backfill_strategy: Dict[str, Any]
    estimated_backfill_duration: str


class GapDetectionService:
    """Servicio para detectar gaps en datos temporales"""

    def __init__(self, telegram_service=None):
        self.expected_interval_minutes = 60  # Datos cada hora (normal operation)
        self.accelerated_interval_minutes = 5  # Modo acelerado temporal
        self.telegram_service = telegram_service
        
    async def detect_all_gaps(self, days_back: int = 30) -> GapAnalysis:
        """Detectar todos los gaps en datos de REE y clima"""
        try:
            logger.info(f"🔍 Iniciando detección de gaps - últimos {days_back} días")
            
            # Detectar gaps en precios REE
            ree_gaps = await self._detect_ree_gaps(days_back)
            
            # Detectar gaps en datos climáticos  
            weather_gaps = await self._detect_weather_gaps(days_back)
            
            # Generar estrategia de backfill
            strategy = self._generate_backfill_strategy(ree_gaps, weather_gaps)
            
            # Estimar duración total
            duration = self._estimate_backfill_duration(ree_gaps, weather_gaps)
            
            analysis = GapAnalysis(
                analysis_timestamp=datetime.now(timezone.utc),
                total_gaps_found=len(ree_gaps) + len(weather_gaps),
                ree_gaps=ree_gaps,
                weather_gaps=weather_gaps,
                recommended_backfill_strategy=strategy,
                estimated_backfill_duration=duration
            )

            logger.info(f"✅ Análisis completado: {analysis.total_gaps_found} gaps encontrados")

            # Send alert if critical gaps detected (>12h)
            await self._check_and_alert_critical_gaps(ree_gaps, weather_gaps)

            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error detectando gaps: {e}")
            raise
    
    async def _detect_ree_gaps(self, days_back: int) -> List[DataGap]:
        """Detectar gaps en datos de precios REE"""
        try:
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Obtener datos REE existentes
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=days_back)
                
                query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> sort(columns: ["_time"])
                '''
                
                tables = query_api.query(query)
                
                # Extraer timestamps existentes
                existing_times = []
                for table in tables:
                    for record in table.records:
                        existing_times.append(record.get_time())
                
                # Generar timeline esperado (cada hora)
                expected_times = []
                current = start_time.replace(minute=0, second=0, microsecond=0)
                while current <= end_time:
                    expected_times.append(current)
                    current += timedelta(hours=1)
                
                # Detectar gaps
                gaps = self._find_time_gaps(
                    expected_times, 
                    existing_times, 
                    "energy_prices",
                    timedelta(hours=1)
                )
                
                logger.info(f"📊 REE: {len(gaps)} gaps detectados en {days_back} días")
                return gaps
                
        except Exception as e:
            logger.error(f"Error detectando gaps REE: {e}")
            return []
    
    async def _detect_weather_gaps(self, days_back: int) -> List[DataGap]:
        """Detectar gaps en datos climáticos"""
        try:
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Obtener datos climáticos existentes
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=days_back)
                
                query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> sort(columns: ["_time"])
                '''
                
                tables = query_api.query(query)
                
                # Extraer timestamps existentes
                existing_times = []
                for table in tables:
                    for record in table.records:
                        existing_times.append(record.get_time())
                
                # Generar timeline esperado (cada hora)
                expected_times = []
                current = start_time.replace(minute=0, second=0, microsecond=0)
                while current <= end_time:
                    expected_times.append(current)
                    current += timedelta(hours=1)
                
                # Detectar gaps
                gaps = self._find_time_gaps(
                    expected_times,
                    existing_times,
                    "weather_data", 
                    timedelta(hours=1)
                )
                
                logger.info(f"🌤️ Weather: {len(gaps)} gaps detectados en {days_back} días")
                return gaps
                
        except Exception as e:
            logger.error(f"Error detectando gaps climáticos: {e}")
            return []
    
    def _find_time_gaps(self, expected_times: List[datetime],
                       existing_times: List[datetime],
                       measurement: str,
                       interval: timedelta) -> List[DataGap]:
        """Encontrar gaps comparando tiempos esperados vs existentes"""

        existing_set = set(existing_times)
        gaps = []

        # Agrupar tiempos faltantes en rangos continuos
        missing_times = [t for t in expected_times if t not in existing_set]

        if not missing_times:
            return gaps

        # IMPROVED: Lógica mejorada para detectar gaps grandes
        missing_times.sort()
        current_gap_start = missing_times[0]
        current_gap_end = missing_times[0]

        for i in range(1, len(missing_times)):
            time_diff = missing_times[i] - current_gap_end

            # IMPROVED: Tolerancia adaptativa basada en tamaño del gap
            current_gap_duration = current_gap_end - current_gap_start

            # Si el gap actual es pequeño (<6h), usar tolerancia estricta
            if current_gap_duration < timedelta(hours=6):
                tolerance = interval * 1.5  # 1.5 horas
            # Si el gap actual es mediano (6h-24h), usar tolerancia media
            elif current_gap_duration < timedelta(hours=24):
                tolerance = interval * 3    # 3 horas
            # Si el gap actual es grande (>24h), usar tolerancia amplia
            else:
                tolerance = interval * 6    # 6 horas

            if time_diff <= tolerance:
                # Extender gap actual
                current_gap_end = missing_times[i]
            else:
                # IMPROVED: Solo crear gap si es significativo (>30min)
                gap_duration = current_gap_end - current_gap_start
                if gap_duration >= timedelta(minutes=30):
                    gap = self._create_gap(
                        measurement, current_gap_start, current_gap_end, interval
                    )
                    gaps.append(gap)

                current_gap_start = missing_times[i]
                current_gap_end = missing_times[i]

        # Añadir último gap si es significativo
        gap_duration = current_gap_end - current_gap_start
        if gap_duration >= timedelta(minutes=30):
            gap = self._create_gap(
                measurement, current_gap_start, current_gap_end, interval
            )
            gaps.append(gap)

        return gaps
    
    def _create_gap(self, measurement: str, start: datetime, 
                   end: datetime, interval: timedelta) -> DataGap:
        """Crear objeto DataGap con metadatos calculados"""
        
        duration_hours = (end - start).total_seconds() / 3600
        expected_records = int(duration_hours / (interval.total_seconds() / 3600)) + 1
        
        # Determinar severidad
        if duration_hours <= 2:
            severity = "minor"
        elif duration_hours <= 12:
            severity = "moderate"
        else:
            severity = "critical"
        
        return DataGap(
            measurement=measurement,
            start_time=start,
            end_time=end,
            expected_records=expected_records,
            missing_records=expected_records,  # Asumimos 100% faltante en el gap
            gap_duration_hours=duration_hours,
            severity=severity
        )
    
    def _generate_backfill_strategy(self, ree_gaps: List[DataGap], 
                                  weather_gaps: List[DataGap]) -> Dict[str, Any]:
        """Generar estrategia óptima de backfill"""
        
        strategy = {
            "approach": "intelligent_progressive",
            "ree_strategy": {
                "api": "REE_historical",
                "method": "daily_chunks", 
                "gaps_count": len(ree_gaps),
                "total_missing_hours": sum(gap.gap_duration_hours for gap in ree_gaps)
            },
            "weather_strategy": {
                "primary_api": "aemet.es",
                "fallback_api": "SIAR_manual_download",
                "method": "gap_specific",
                "gaps_count": len(weather_gaps),
                "total_missing_hours": sum(gap.gap_duration_hours for gap in weather_gaps)
            },
            "execution_order": [
                "ree_backfill",  # Más fácil primero
                "weather_backfill"  # Más complejo después
            ],
            "rate_limiting": {
                "ree_requests_per_minute": 30,
                "weather_requests_per_minute": 10
            }
        }
        
        return strategy
    
    def _estimate_backfill_duration(self, ree_gaps: List[DataGap], 
                                  weather_gaps: List[DataGap]) -> str:
        """Estimar duración total del proceso de backfill"""
        
        total_ree_hours = sum(gap.gap_duration_hours for gap in ree_gaps)
        total_weather_hours = sum(gap.gap_duration_hours for gap in weather_gaps)
        
        # Estimaciones basadas en rate limits
        ree_minutes = (total_ree_hours / 24) * 2  # 2 min por día de datos REE
        weather_minutes = (total_weather_hours / 24) * 5  # 5 min por día de datos clima
        
        total_minutes = ree_minutes + weather_minutes
        
        if total_minutes < 5:
            return "< 5 minutos"
        elif total_minutes < 30:
            return f"~{int(total_minutes)} minutos"
        else:
            return f"~{int(total_minutes // 60)}h {int(total_minutes % 60)}min"
    
    async def get_latest_timestamps(self) -> Dict[str, Optional[datetime]]:
        """Obtener timestamps del último dato de cada measurement"""
        logger.info("Gap detector: Starting get_latest_timestamps query")
        try:
            async with DataIngestionService() as service:
                query_api = service.client.query_api()
                
                # Último precio REE - Fix: ordenar por timestamp desc y tomar el más reciente
                ree_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> group()
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
                '''
                
                # Último dato climático - Fix: mismo fix para weather data
                weather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> group()
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
                '''
                
                results = {}
                
                # Obtener último REE
                ree_tables = query_api.query(ree_query)
                results['latest_ree'] = None
                for table in ree_tables:
                    for record in table.records:
                        results['latest_ree'] = record.get_time()
                        logger.info(f"Gap detector: Latest REE timestamp found: {results['latest_ree']}")
                        break
                
                # Obtener último Weather
                weather_tables = query_api.query(weather_query)
                results['latest_weather'] = None
                for table in weather_tables:
                    for record in table.records:
                        results['latest_weather'] = record.get_time()
                        break
                
                return results

        except Exception as e:
            logger.error(f"Error obteniendo últimos timestamps: {e}")
            return {'latest_ree': None, 'latest_weather': None}

    async def _check_and_alert_critical_gaps(
        self,
        ree_gaps: List[DataGap],
        weather_gaps: List[DataGap]
    ):
        """
        Check for critical gaps (>12h) and send Telegram alert.

        Args:
            ree_gaps: List of detected REE gaps
            weather_gaps: List of detected weather gaps
        """
        if not self.telegram_service:
            return

        # Find gaps > 12 hours
        critical_gaps = []

        for gap in ree_gaps:
            if gap.gap_duration_hours > 12:
                critical_gaps.append(f"REE: {gap.gap_duration_hours:.1f}h gap")

        for gap in weather_gaps:
            if gap.gap_duration_hours > 12:
                critical_gaps.append(f"Weather: {gap.gap_duration_hours:.1f}h gap")

        # Send alert if critical gaps found
        if critical_gaps:
            try:
                from services.telegram_alert_service import AlertSeverity

                gaps_text = "\n".join(critical_gaps[:5])  # Max 5 gaps
                total_critical = len(critical_gaps)

                await self.telegram_service.send_alert(
                    message=f"Critical data gaps detected (>{total_critical} gaps >12h):\n\n{gaps_text}",
                    severity=AlertSeverity.WARNING,
                    topic="gap_detection"
                )

                logger.info(f"📱 Telegram alert sent for {total_critical} critical gaps")

            except Exception as e:
                logger.error(f"❌ Failed to send gap detection alert: {e}")