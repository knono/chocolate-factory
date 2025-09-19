"""
Historical Data Service - Chocolate Factory
===========================================

Servicio para incorporar datos históricos de 10 años de manera progresiva,
creando series temporales robustas para ML avanzado.

Estrategia:
- REE: ESIOS API para datos desde 2014
- Weather: datosclima.es ETL para años históricos
- Progresión: año por año, con verificación de integridad
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from loguru import logger

from .ree_client import REEClient
from .siar_etl import SiarETL
from .data_ingestion import DataIngestionService
from .gap_detector import GapDetectionService


class DataSource(Enum):
    """Fuentes de datos históricos"""
    REE_ESIOS = "ree_esios"
    REE_STANDARD = "ree_standard"
    WEATHER_DATOSCLIMA = "weather_datosclima"
    WEATHER_AEMET = "weather_aemet"


@dataclass
class YearlyIngestionPlan:
    """Plan de ingesta para un año específico"""
    year: int
    start_date: datetime
    end_date: datetime
    ree_source: DataSource
    weather_source: DataSource
    expected_ree_records: int
    expected_weather_records: int
    priority: int  # 1 = alta, 3 = baja


@dataclass
class HistoricalIngestionResult:
    """Resultado de ingesta histórica"""
    year: int
    data_source: DataSource
    records_requested: int
    records_obtained: int
    records_written: int
    success_rate: float
    duration_seconds: float
    data_quality_score: float  # 0-100
    errors: List[str]


class HistoricalDataService:
    """Servicio para gestión de datos históricos de 10 años"""

    def __init__(self):
        self.gap_detector = GapDetectionService()

        # Configuración de prioridades por año
        self.year_priorities = {
            2025: 1,  # Año actual - máxima prioridad
            2024: 1,  # Año anterior - alta prioridad
            2023: 2,  # 2 años - prioridad media-alta
            2022: 2,  # 3 años - prioridad media-alta
            2021: 2,  # 4 años - prioridad media
            2020: 3,  # 5 años - prioridad media-baja
            2019: 3,  # 6 años - prioridad baja
            2018: 3,  # 7 años - prioridad baja
            2017: 3,  # 8 años - prioridad baja
            2016: 3,  # 9 años - prioridad baja
            2015: 3,  # 10 años - prioridad mínima
        }

    async def analyze_historical_data_status(self) -> Dict[str, Any]:
        """Analizar estado actual de datos históricos"""
        try:
            logger.info("🔍 Analizando estado de datos históricos (10 años)")

            analysis_start = datetime.now()

            # Verificar qué años tenemos datos
            available_years = await self._get_available_data_years()

            # Generar plan de 10 años
            ten_year_plan = self._generate_10_year_plan()

            # Calcular estadísticas
            total_expected_records = sum(
                plan.expected_ree_records + plan.expected_weather_records
                for plan in ten_year_plan
            )

            current_data_years = len(available_years.get('ree_years', []))
            current_weather_years = len(available_years.get('weather_years', []))

            # Calcular progreso
            progress_percentage = (current_data_years / 10) * 100

            duration = (datetime.now() - analysis_start).total_seconds()

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "historical_data_status": {
                    "ree_data_years": available_years.get('ree_years', []),
                    "weather_data_years": available_years.get('weather_years', []),
                    "total_ree_years": current_data_years,
                    "total_weather_years": current_weather_years,
                    "target_years": 10,
                    "progress_percentage": round(progress_percentage, 1)
                },
                "10_year_plan": [
                    {
                        "year": plan.year,
                        "priority": plan.priority,
                        "expected_ree_records": plan.expected_ree_records,
                        "expected_weather_records": plan.expected_weather_records,
                        "ree_source": plan.ree_source.value,
                        "weather_source": plan.weather_source.value
                    }
                    for plan in ten_year_plan
                ],
                "ingestion_strategy": {
                    "approach": "progressive_yearly",
                    "total_expected_records": total_expected_records,
                    "estimated_duration_hours": total_expected_records / 1000,  # Rough estimate
                    "recommended_order": "priority_descending"
                },
                "next_steps": {
                    "immediate": "Execute year-by-year ingestion starting with priority 1",
                    "endpoint": "POST /historical/ingest-year/{year}"
                },
                "analysis_duration_seconds": round(duration, 2)
            }

        except Exception as e:
            logger.error(f"❌ Error analizando datos históricos: {e}")
            raise

    async def _get_available_data_years(self) -> Dict[str, List[int]]:
        """Obtener años con datos disponibles en InfluxDB"""
        try:
            async with DataIngestionService() as service:
                query_api = service.client.query_api()

                results = {'ree_years': [], 'weather_years': []}

                # Query años con datos REE
                ree_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -10y)
                |> filter(fn: (r) => r._measurement == "energy_prices")
                |> filter(fn: (r) => r._field == "price_eur_kwh")
                |> aggregateWindow(every: 1y, fn: count)
                |> group(columns: ["_time"])
                |> yield(name: "ree_years")
                '''

                # Query años con datos Weather
                weather_query = f'''
                from(bucket: "{service.config.bucket}")
                |> range(start: -10y)
                |> filter(fn: (r) => r._measurement == "weather_data")
                |> filter(fn: (r) => r._field == "temperature")
                |> aggregateWindow(every: 1y, fn: count)
                |> group(columns: ["_time"])
                |> yield(name: "weather_years")
                '''

                # Procesar REE
                try:
                    ree_tables = query_api.query(ree_query)
                    for table in ree_tables:
                        for record in table.records:
                            year = record.get_time().year
                            if record.get_value() > 0:  # Tiene datos
                                results['ree_years'].append(year)
                except Exception as e:
                    logger.warning(f"Error query REE years: {e}")

                # Procesar Weather
                try:
                    weather_tables = query_api.query(weather_query)
                    for table in weather_tables:
                        for record in table.records:
                            year = record.get_time().year
                            if record.get_value() > 0:  # Tiene datos
                                results['weather_years'].append(year)
                except Exception as e:
                    logger.warning(f"Error query Weather years: {e}")

                # Ordenar y deduplicar
                results['ree_years'] = sorted(list(set(results['ree_years'])))
                results['weather_years'] = sorted(list(set(results['weather_years'])))

                logger.info(f"📊 Datos disponibles: REE {len(results['ree_years'])} años, Weather {len(results['weather_years'])} años")

                return results

        except Exception as e:
            logger.error(f"Error obteniendo años disponibles: {e}")
            return {'ree_years': [], 'weather_years': []}

    def _generate_10_year_plan(self) -> List[YearlyIngestionPlan]:
        """Generar plan de ingesta para 10 años"""
        plans = []
        current_year = datetime.now().year

        for i in range(10):
            year = current_year - i

            # Fechas del año
            start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

            # Determinar fuentes de datos
            if year >= 2020:
                ree_source = DataSource.REE_ESIOS  # ESIOS para años recientes
            else:
                ree_source = DataSource.REE_ESIOS  # ESIOS histórico (mejor calidad)

            weather_source = DataSource.WEATHER_DATOSCLIMA  # datosclima.es para todo

            # Calcular registros esperados
            days_in_year = (end_date - start_date).days + 1
            expected_ree = days_in_year * 24  # Horario
            expected_weather = days_in_year * 24  # Horario también

            # Prioridad
            priority = self.year_priorities.get(year, 3)

            plan = YearlyIngestionPlan(
                year=year,
                start_date=start_date,
                end_date=end_date,
                ree_source=ree_source,
                weather_source=weather_source,
                expected_ree_records=expected_ree,
                expected_weather_records=expected_weather,
                priority=priority
            )

            plans.append(plan)

        # Ordenar por prioridad
        return sorted(plans, key=lambda x: (x.priority, -x.year))

    async def ingest_year_data(self, year: int,
                              include_ree: bool = True,
                              include_weather: bool = True) -> Dict[str, Any]:
        """Ingestar datos de un año específico"""
        try:
            ingestion_start = datetime.now()
            logger.info(f"🔄 Iniciando ingesta año {year} - REE: {include_ree}, Weather: {include_weather}")

            # Obtener plan para el año
            plan = None
            for p in self._generate_10_year_plan():
                if p.year == year:
                    plan = p
                    break

            if not plan:
                raise ValueError(f"No hay plan definido para el año {year}")

            results = []

            # Ingesta REE
            if include_ree:
                logger.info(f"📊 Procesando datos REE {year} con {plan.ree_source.value}")
                ree_result = await self._ingest_ree_year(plan)
                results.append(ree_result)

            # Ingesta Weather
            if include_weather:
                logger.info(f"🌤️ Procesando datos Weather {year} con {plan.weather_source.value}")
                weather_result = await self._ingest_weather_year(plan)
                results.append(weather_result)

            # Consolidar resultados
            total_duration = (datetime.now() - ingestion_start).total_seconds()

            total_records_written = sum(r.records_written for r in results)
            total_records_requested = sum(r.records_requested for r in results)

            overall_success_rate = (total_records_written / total_records_requested * 100) if total_records_requested > 0 else 0

            summary = {
                "year": year,
                "status": "success" if overall_success_rate > 80 else "partial",
                "timestamp": datetime.now().isoformat(),
                "ingestion_summary": {
                    "total_duration_seconds": round(total_duration, 1),
                    "total_records_requested": total_records_requested,
                    "total_records_written": total_records_written,
                    "overall_success_rate": round(overall_success_rate, 1),
                    "data_sources_processed": len(results)
                },
                "detailed_results": [
                    {
                        "data_source": r.data_source.value,
                        "records_written": r.records_written,
                        "success_rate": round(r.success_rate, 1),
                        "duration_seconds": round(r.duration_seconds, 1),
                        "data_quality_score": round(r.data_quality_score, 1),
                        "errors": r.errors
                    }
                    for r in results
                ],
                "next_steps": {
                    "verification": f"GET /gaps/detect?days_back={365}",
                    "next_year": year - 1 if year > 2015 else None
                }
            }

            logger.info(f"✅ Año {year} completado: {total_records_written} registros ({overall_success_rate:.1f}% éxito)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error ingesta año {year}: {e}")
            raise

    async def _ingest_ree_year(self, plan: YearlyIngestionPlan) -> HistoricalIngestionResult:
        """Ingestar datos REE para un año específico"""
        start_time = datetime.now()

        try:
            if plan.ree_source == DataSource.REE_ESIOS:
                # Usar ESIOS API para datos históricos robustos
                return await self._ingest_ree_esios_year(plan)
            else:
                # Fallback a REE estándar
                return await self._ingest_ree_standard_year(plan)

        except Exception as e:
            logger.error(f"Error ingesta REE año {plan.year}: {e}")

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=plan.ree_source,
                records_requested=plan.expected_ree_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                data_quality_score=0,
                errors=[str(e)]
            )

    async def _ingest_ree_esios_year(self, plan: YearlyIngestionPlan) -> HistoricalIngestionResult:
        """Ingesta REE usando ESIOS API para máxima calidad histórica"""
        start_time = datetime.now()
        errors = []

        try:
            # ESIOS tiene mejores datos históricos que REE API standard
            import httpx

            total_records = 0
            total_written = 0

            async with DataIngestionService() as ingestion_service:
                # Procesar por meses para evitar timeouts
                current_date = plan.start_date

                while current_date <= plan.end_date:
                    month_end = min(
                        current_date.replace(day=28) + timedelta(days=4) - timedelta(days=current_date.day),
                        plan.end_date
                    )

                    try:
                        logger.info(f"📊 ESIOS {plan.year}: {current_date.strftime('%Y-%m')} -> {month_end.strftime('%Y-%m')}")

                        # Usar ESIOS API con indicador PVPC
                        params = {
                            'start_date': current_date.strftime('%Y-%m-%dT00:00'),
                            'end_date': month_end.strftime('%Y-%m-%dT23:59'),
                            'geo_ids[]': 8741,  # Peninsula
                            'time_trunc': 'hour'
                        }

                        # ESIOS indicador 1001 = PVPC 2.0TD
                        url = "https://api.esios.ree.es/indicators/1001"

                        headers = {
                            'Accept': 'application/json',
                            'User-Agent': 'ChocolateFactory-Historical/1.0'
                        }

                        async with httpx.AsyncClient(timeout=60) as client:
                            response = await client.get(url, params=params, headers=headers)

                            if response.status_code == 200:
                                data = response.json()

                                monthly_prices = []

                                if 'indicator' in data and 'values' in data['indicator']:
                                    for value in data['indicator']['values']:
                                        if 'datetime' in value and 'value' in value and value['value'] is not None:
                                            timestamp = datetime.fromisoformat(
                                                value['datetime'].replace('Z', '+00:00')
                                            )

                                            # Convert MWh to kWh for consistency
                                            price_eur_kwh = float(value['value']) / 1000

                                            price_data = {
                                                'timestamp': timestamp,
                                                'price_eur_kwh': price_eur_kwh,
                                                'market_type': 'historical_esios',
                                                'provider': 'ree_esios'
                                            }

                                            monthly_prices.append(price_data)

                                if monthly_prices:
                                    # Escribir usando método histórico
                                    write_result = await ingestion_service.ingest_ree_prices_historical(monthly_prices)

                                    total_records += len(monthly_prices)
                                    total_written += write_result.successful_writes

                                    logger.info(f"✅ ESIOS {current_date.strftime('%Y-%m')}: {len(monthly_prices)} registros")
                                else:
                                    logger.warning(f"⚠️ ESIOS {current_date.strftime('%Y-%m')}: sin datos")

                            else:
                                error_msg = f"ESIOS API error {response.status_code} para {current_date.strftime('%Y-%m')}"
                                errors.append(error_msg)
                                logger.warning(error_msg)

                        # Rate limiting para ESIOS
                        await asyncio.sleep(2)

                    except Exception as month_error:
                        error_msg = f"Error mes {current_date.strftime('%Y-%m')}: {month_error}"
                        errors.append(error_msg)
                        logger.warning(error_msg)

                    # Siguiente mes
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1, day=1)

            duration = (datetime.now() - start_time).total_seconds()
            success_rate = (total_written / total_records * 100) if total_records > 0 else 0

            # Calcular calidad de datos basada en completitud
            expected_records = plan.expected_ree_records
            completeness = (total_written / expected_records * 100) if expected_records > 0 else 0
            data_quality = min(completeness, 100)

            logger.info(f"📊 ESIOS año {plan.year}: {total_written}/{expected_records} registros ({success_rate:.1f}%)")

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=DataSource.REE_ESIOS,
                records_requested=expected_records,
                records_obtained=total_records,
                records_written=total_written,
                success_rate=success_rate,
                duration_seconds=duration,
                data_quality_score=data_quality,
                errors=errors
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error ESIOS año {plan.year}: {e}")

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=DataSource.REE_ESIOS,
                records_requested=plan.expected_ree_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=duration,
                data_quality_score=0,
                errors=[str(e)]
            )

    async def _ingest_ree_standard_year(self, plan: YearlyIngestionPlan) -> HistoricalIngestionResult:
        """Fallback: ingesta REE usando API estándar"""
        start_time = datetime.now()

        try:
            logger.info(f"📊 REE estándar año {plan.year} (fallback)")

            total_records = 0
            total_written = 0
            errors = []

            async with REEClient() as ree_client:
                async with DataIngestionService() as ingestion_service:

                    # Procesar por meses
                    current_date = plan.start_date

                    while current_date <= plan.end_date:
                        month_end = min(
                            current_date.replace(day=28) + timedelta(days=4) - timedelta(days=current_date.day),
                            plan.end_date
                        )

                        try:
                            monthly_data = await ree_client.get_price_range(current_date, month_end)

                            if monthly_data:
                                # Convertir formato
                                formatted_data = [
                                    {
                                        'timestamp': price.timestamp,
                                        'price_eur_kwh': price.price_eur_mwh / 1000,  # MWh -> kWh
                                        'market_type': 'historical_standard',
                                        'provider': 'ree'
                                    }
                                    for price in monthly_data
                                ]

                                write_result = await ingestion_service.ingest_ree_prices_historical(formatted_data)

                                total_records += len(formatted_data)
                                total_written += write_result.successful_writes

                            await asyncio.sleep(1)  # Rate limiting

                        except Exception as month_error:
                            errors.append(f"Mes {current_date.strftime('%Y-%m')}: {month_error}")

                        # Siguiente mes
                        if current_date.month == 12:
                            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                        else:
                            current_date = current_date.replace(month=current_date.month + 1, day=1)

            duration = (datetime.now() - start_time).total_seconds()
            success_rate = (total_written / total_records * 100) if total_records > 0 else 0
            data_quality = (total_written / plan.expected_ree_records * 100) if plan.expected_ree_records > 0 else 0

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=DataSource.REE_STANDARD,
                records_requested=plan.expected_ree_records,
                records_obtained=total_records,
                records_written=total_written,
                success_rate=success_rate,
                duration_seconds=duration,
                data_quality_score=min(data_quality, 100),
                errors=errors
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=DataSource.REE_STANDARD,
                records_requested=plan.expected_ree_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=duration,
                data_quality_score=0,
                errors=[str(e)]
            )

    async def _ingest_weather_year(self, plan: YearlyIngestionPlan) -> HistoricalIngestionResult:
        """Ingestar datos climáticos para un año específico"""
        start_time = datetime.now()

        try:
            logger.info(f"🌤️ Procesando datos climáticos año {plan.year}")

            # Usar datosclima.es ETL para datos históricos
            etl_service = SiarETL()

            # Ejecutar ETL para el año específico
            etl_result = await etl_service.process_station_data(
                station_id="5279X",  # Linares, Jaén
                years=1,
                target_year=plan.year
            )

            duration = (datetime.now() - start_time).total_seconds()

            if etl_result.get("status") == "success":
                records_processed = etl_result.get("records_processed", 0)
                success_rate = 100 if records_processed > 0 else 0

                # Calcular calidad basada en completitud esperada
                completeness = (records_processed / plan.expected_weather_records * 100) if plan.expected_weather_records > 0 else 0
                data_quality = min(completeness, 100)

                logger.info(f"✅ Weather año {plan.year}: {records_processed} registros procesados")

                return HistoricalIngestionResult(
                    year=plan.year,
                    data_source=DataSource.WEATHER_DATOSCLIMA,
                    records_requested=plan.expected_weather_records,
                    records_obtained=records_processed,
                    records_written=records_processed,
                    success_rate=success_rate,
                    duration_seconds=duration,
                    data_quality_score=data_quality,
                    errors=etl_result.get("errors", [])
                )
            else:
                error_msg = etl_result.get("error", "ETL failed")
                logger.error(f"❌ Weather año {plan.year}: {error_msg}")

                return HistoricalIngestionResult(
                    year=plan.year,
                    data_source=DataSource.WEATHER_DATOSCLIMA,
                    records_requested=plan.expected_weather_records,
                    records_obtained=0,
                    records_written=0,
                    success_rate=0,
                    duration_seconds=duration,
                    data_quality_score=0,
                    errors=[error_msg]
                )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error weather año {plan.year}: {e}")

            return HistoricalIngestionResult(
                year=plan.year,
                data_source=DataSource.WEATHER_DATOSCLIMA,
                records_requested=plan.expected_weather_records,
                records_obtained=0,
                records_written=0,
                success_rate=0,
                duration_seconds=duration,
                data_quality_score=0,
                errors=[str(e)]
            )

    async def execute_progressive_10_year_ingestion(self,
                                                   max_years_per_session: int = 3) -> Dict[str, Any]:
        """Ejecutar ingesta progresiva de 10 años con límite por sesión"""
        try:
            session_start = datetime.now()
            logger.info(f"🚀 Iniciando ingesta progresiva 10 años (máx {max_years_per_session} años por sesión)")

            # Obtener plan ordenado por prioridad
            plans = self._generate_10_year_plan()

            # Verificar años ya disponibles
            available_years = await self._get_available_data_years()

            # Filtrar años que necesitan procesamiento
            years_to_process = []
            for plan in plans:
                needs_ree = plan.year not in available_years.get('ree_years', [])
                needs_weather = plan.year not in available_years.get('weather_years', [])

                if needs_ree or needs_weather:
                    years_to_process.append((plan.year, needs_ree, needs_weather))

            # Limitar por sesión
            session_years = years_to_process[:max_years_per_session]

            logger.info(f"📋 Procesando {len(session_years)} años en esta sesión: {[y[0] for y in session_years]}")

            session_results = []

            for year, needs_ree, needs_weather in session_years:
                logger.info(f"🔄 Procesando año {year}...")

                year_result = await self.ingest_year_data(
                    year=year,
                    include_ree=needs_ree,
                    include_weather=needs_weather
                )

                session_results.append(year_result)

                # Pausa entre años para no sobrecargar sistemas
                await asyncio.sleep(5)

            # Consolidar resultados de sesión
            total_duration = (datetime.now() - session_start).total_seconds()

            total_records = sum(
                r["ingestion_summary"]["total_records_written"]
                for r in session_results
            )

            successful_years = sum(
                1 for r in session_results
                if r["status"] == "success"
            )

            # Calcular progreso total hacia 10 años
            updated_available = await self._get_available_data_years()
            current_progress = (len(updated_available.get('ree_years', [])) / 10) * 100

            return {
                "session_timestamp": datetime.now().isoformat(),
                "session_summary": {
                    "years_processed": len(session_results),
                    "successful_years": successful_years,
                    "total_records_written": total_records,
                    "session_duration_hours": round(total_duration / 3600, 2),
                    "progress_towards_10_years": round(current_progress, 1)
                },
                "yearly_results": session_results,
                "remaining_work": {
                    "years_pending": len(years_to_process) - len(session_years),
                    "next_session_years": [y[0] for y in years_to_process[max_years_per_session:max_years_per_session*2]],
                    "estimated_sessions_remaining": max(1, (len(years_to_process) - len(session_years)) // max_years_per_session)
                },
                "recommendations": {
                    "next_action": "POST /historical/progressive-ingestion" if len(years_to_process) > len(session_years) else "Data ingestion complete",
                    "optimal_schedule": "Run 1 session per day to avoid API rate limits"
                }
            }

        except Exception as e:
            logger.error(f"❌ Error ingesta progresiva: {e}")
            raise


# Instancia global
historical_data_service = HistoricalDataService()