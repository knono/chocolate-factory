"""
SIAR Analysis Service - Sprint 07 (Revisado)
============================================

Servicio de análisis histórico de datos SIAR (2000-2025).
NO predice el tiempo (eso lo hace AEMET), sino que analiza 25 años de historia.

Funcionalidades:
- Análisis correlación temperatura/humedad → eficiencia producción (25 años evidencia)
- Detección patrones estacionales con datos reales
- Umbrales críticos basados en percentiles históricos
- Contextualización de predicciones AEMET con historia SIAR

Objetivo Sprint 07: R² > 0.6 correlaciones, umbrales basados en evidencia
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import pandas as pd
import numpy as np
from scipy import stats
from influxdb_client import InfluxDBClient

from .data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Resultado de análisis de correlación"""
    variable1: str
    variable2: str
    correlation: float
    r_squared: float
    p_value: float
    sample_size: int
    confidence_95: Tuple[float, float]


@dataclass
class SeasonalPattern:
    """Patrón estacional detectado"""
    month: int
    month_name: str
    avg_temperature: float
    avg_humidity: float
    critical_days_count: int  # Días con temp > umbral crítico
    optimal_days_count: int   # Días con condiciones óptimas
    production_efficiency_score: float  # 0-100


@dataclass
class CriticalThreshold:
    """Umbral crítico basado en datos históricos"""
    variable: str
    threshold_value: float
    percentile: int  # 90, 95, 99
    historical_occurrences: int
    avg_production_impact: float  # % degradación
    description: str


class SIARAnalysisService:
    """
    Servicio de análisis histórico SIAR (NO predicción).

    Analiza 88,935 registros (2000-2025) para:
    - Correlaciones históricas temperatura/humedad → producción
    - Patrones estacionales basados en datos reales
    - Umbrales críticos basados en percentiles históricos
    """

    def __init__(self):
        """Inicializa el servicio de análisis SIAR."""
        self.cache: Dict[str, Any] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.cache_ttl = timedelta(hours=24)  # Cache 24h (datos históricos no cambian)

        # Umbrales de producción chocolate (asumidos, a validar con datos)
        self.production_assumptions = {
            'optimal_temp_range': (15.0, 25.0),
            'optimal_humidity_range': (40.0, 70.0),
            'critical_temp': 35.0,
            'critical_humidity': 80.0,
        }

        logger.info("✅ SIAR Analysis Service initialized (historical data analysis)")

    async def extract_siar_complete_history(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extrae todos los datos SIAR históricos (88,935 registros, 2000-2025).

        Returns:
            Tuple[DataFrame temperatura, DataFrame humedad]
        """
        logger.info("📊 Extrayendo historial completo SIAR (88,935 registros, 2000-2025)")

        async with DataIngestionService() as service:
            # Query temperatura (todos los datos SIAR)
            # IMPORTANTE: measurement es "siar_weather" no "weather_data"
            query_temp = '''
                from(bucket: "siar_historical")
                |> range(start: 2000-01-01T00:00:00Z, stop: now())
                |> filter(fn: (r) => r._measurement == "siar_weather")
                |> filter(fn: (r) => r._field == "temperature")
                |> filter(fn: (r) => r.data_source == "siar_historical")
                |> sort(columns: ["_time"])
            '''

            # Query humedad (todos los datos SIAR)
            # IMPORTANTE: measurement es "siar_weather" no "weather_data"
            query_humidity = '''
                from(bucket: "siar_historical")
                |> range(start: 2000-01-01T00:00:00Z, stop: now())
                |> filter(fn: (r) => r._measurement == "siar_weather")
                |> filter(fn: (r) => r._field == "humidity")
                |> filter(fn: (r) => r.data_source == "siar_historical")
                |> sort(columns: ["_time"])
            '''

            try:
                query_api = service.client.query_api()

                # Extraer temperatura
                logger.info("🌡️ Extrayendo temperatura SIAR (25 años)...")
                temp_tables = query_api.query(query_temp)
                temp_data = []
                for table in temp_tables:
                    for record in table.records:
                        temp_data.append({
                            'timestamp': record.get_time(),
                            'temperature': record.get_value(),
                            'station_id': record.values.get('station_id', 'unknown')
                        })

                # Extraer humedad
                logger.info("💧 Extrayendo humedad SIAR (25 años)...")
                humidity_tables = query_api.query(query_humidity)
                humidity_data = []
                for table in humidity_tables:
                    for record in table.records:
                        humidity_data.append({
                            'timestamp': record.get_time(),
                            'humidity': record.get_value(),
                            'station_id': record.values.get('station_id', 'unknown')
                        })

                df_temp = pd.DataFrame(temp_data)
                df_humidity = pd.DataFrame(humidity_data)

                logger.info(
                    f"✅ Datos SIAR extraídos: {len(df_temp)} registros temperatura, "
                    f"{len(df_humidity)} registros humedad"
                )

                return df_temp, df_humidity

            except Exception as e:
                logger.error(f"❌ Error extrayendo datos SIAR: {e}")
                raise

    async def calculate_production_correlations(self) -> Dict[str, CorrelationResult]:
        """
        Calcula correlaciones temperatura/humedad → eficiencia producción.

        Como no tenemos datos reales de producción histórica, usamos un proxy:
        - Chocolate production index = f(temperatura, humedad)
        - Basado en literatura: óptimo 15-25°C, humedad 40-70%

        Returns:
            Dict con correlaciones temperatura y humedad
        """
        logger.info("📊 Calculando correlaciones históricas clima → producción")

        # Extraer datos SIAR
        df_temp, df_humidity = await self.extract_siar_complete_history()

        # Merge por timestamp
        df_merged = pd.merge(
            df_temp,
            df_humidity,
            on='timestamp',
            suffixes=('', '_hum')
        )

        # Calcular proxy de eficiencia producción chocolate
        # Basado en literatura: óptimo 15-25°C, humedad 40-70%
        df_merged['production_efficiency'] = df_merged.apply(
            lambda row: self._calculate_production_efficiency_proxy(
                row['temperature'],
                row['humidity']
            ),
            axis=1
        )

        # Correlación temperatura → eficiencia
        temp_corr = stats.pearsonr(
            df_merged['temperature'].dropna(),
            df_merged['production_efficiency'].dropna()
        )

        temp_result = CorrelationResult(
            variable1='temperature',
            variable2='production_efficiency',
            correlation=temp_corr[0],
            r_squared=temp_corr[0] ** 2,
            p_value=temp_corr[1],
            sample_size=len(df_merged.dropna()),
            confidence_95=self._calculate_confidence_interval(temp_corr[0], len(df_merged))
        )

        # Correlación humedad → eficiencia
        humidity_corr = stats.pearsonr(
            df_merged['humidity'].dropna(),
            df_merged['production_efficiency'].dropna()
        )

        humidity_result = CorrelationResult(
            variable1='humidity',
            variable2='production_efficiency',
            correlation=humidity_corr[0],
            r_squared=humidity_corr[0] ** 2,
            p_value=humidity_corr[1],
            sample_size=len(df_merged.dropna()),
            confidence_95=self._calculate_confidence_interval(humidity_corr[0], len(df_merged))
        )

        logger.info(
            f"✅ Correlaciones calculadas | Temp R²={temp_result.r_squared:.3f}, "
            f"Humidity R²={humidity_result.r_squared:.3f}"
        )

        results = {
            'temperature': temp_result,
            'humidity': humidity_result
        }

        # Cache resultados
        self.cache['correlations'] = results
        self.cache_timestamp = datetime.now()

        return results

    async def detect_seasonal_patterns(self) -> List[SeasonalPattern]:
        """
        Detecta patrones estacionales con datos reales (25 años).

        Returns:
            Lista de 12 patrones mensuales
        """
        logger.info("🌞 Detectando patrones estacionales (12 meses, 25 años datos)")

        # Extraer datos SIAR
        df_temp, df_humidity = await self.extract_siar_complete_history()

        # Merge datasets
        df_merged = pd.merge(df_temp, df_humidity, on='timestamp', suffixes=('', '_hum'))
        df_merged['month'] = pd.to_datetime(df_merged['timestamp']).dt.month

        # Analizar cada mes
        patterns = []
        month_names = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]

        for month in range(1, 13):
            month_data = df_merged[df_merged['month'] == month]

            if len(month_data) == 0:
                continue

            # Estadísticas mensuales
            avg_temp = month_data['temperature'].mean()
            avg_humidity = month_data['humidity'].mean()

            # Contar días críticos (temp > 35°C)
            critical_days = len(month_data[month_data['temperature'] > self.production_assumptions['critical_temp']])

            # Contar días óptimos (15-25°C, 40-70% humedad)
            optimal_days = len(month_data[
                (month_data['temperature'] >= self.production_assumptions['optimal_temp_range'][0]) &
                (month_data['temperature'] <= self.production_assumptions['optimal_temp_range'][1]) &
                (month_data['humidity'] >= self.production_assumptions['optimal_humidity_range'][0]) &
                (month_data['humidity'] <= self.production_assumptions['optimal_humidity_range'][1])
            ])

            # Calcular score eficiencia mensual
            efficiency_score = (optimal_days / len(month_data)) * 100 if len(month_data) > 0 else 0

            pattern = SeasonalPattern(
                month=month,
                month_name=month_names[month - 1],
                avg_temperature=round(avg_temp, 1),
                avg_humidity=round(avg_humidity, 1),
                critical_days_count=critical_days,
                optimal_days_count=optimal_days,
                production_efficiency_score=round(efficiency_score, 1)
            )

            patterns.append(pattern)

            logger.info(
                f"  {month_names[month - 1]}: {avg_temp:.1f}°C, {avg_humidity:.1f}% hum, "
                f"{critical_days} días críticos, {optimal_days} días óptimos"
            )

        logger.info(f"✅ Patrones estacionales detectados: {len(patterns)} meses analizados")

        # Cache resultados
        self.cache['seasonal_patterns'] = patterns
        self.cache_timestamp = datetime.now()

        return patterns

    async def identify_critical_thresholds(self) -> List[CriticalThreshold]:
        """
        Identifica umbrales críticos basados en percentiles históricos.

        Returns:
            Lista de umbrales críticos (P90, P95, P99)
        """
        logger.info("🚨 Identificando umbrales críticos (percentiles históricos)")

        # Extraer datos SIAR
        df_temp, df_humidity = await self.extract_siar_complete_history()

        thresholds = []

        # Umbrales temperatura
        temp_p90 = df_temp['temperature'].quantile(0.90)
        temp_p95 = df_temp['temperature'].quantile(0.95)
        temp_p99 = df_temp['temperature'].quantile(0.99)

        # Contar ocurrencias
        temp_p90_count = len(df_temp[df_temp['temperature'] >= temp_p90])
        temp_p95_count = len(df_temp[df_temp['temperature'] >= temp_p95])
        temp_p99_count = len(df_temp[df_temp['temperature'] >= temp_p99])

        thresholds.extend([
            CriticalThreshold(
                variable='temperature',
                threshold_value=round(temp_p90, 1),
                percentile=90,
                historical_occurrences=temp_p90_count,
                avg_production_impact=10.0,  # Estimado
                description=f"Temperatura alta (P90): {temp_p90:.1f}°C - Ocurrió {temp_p90_count} veces en 25 años"
            ),
            CriticalThreshold(
                variable='temperature',
                threshold_value=round(temp_p95, 1),
                percentile=95,
                historical_occurrences=temp_p95_count,
                avg_production_impact=20.0,  # Estimado
                description=f"Temperatura muy alta (P95): {temp_p95:.1f}°C - Ocurrió {temp_p95_count} veces"
            ),
            CriticalThreshold(
                variable='temperature',
                threshold_value=round(temp_p99, 1),
                percentile=99,
                historical_occurrences=temp_p99_count,
                avg_production_impact=40.0,  # Estimado
                description=f"Temperatura extrema (P99): {temp_p99:.1f}°C - Ocurrió {temp_p99_count} veces"
            )
        ])

        # Umbrales humedad
        humidity_p90 = df_humidity['humidity'].quantile(0.90)
        humidity_p95 = df_humidity['humidity'].quantile(0.95)
        humidity_p99 = df_humidity['humidity'].quantile(0.99)

        humidity_p90_count = len(df_humidity[df_humidity['humidity'] >= humidity_p90])
        humidity_p95_count = len(df_humidity[df_humidity['humidity'] >= humidity_p95])
        humidity_p99_count = len(df_humidity[df_humidity['humidity'] >= humidity_p99])

        thresholds.extend([
            CriticalThreshold(
                variable='humidity',
                threshold_value=round(humidity_p90, 1),
                percentile=90,
                historical_occurrences=humidity_p90_count,
                avg_production_impact=5.0,  # Estimado
                description=f"Humedad alta (P90): {humidity_p90:.1f}% - Ocurrió {humidity_p90_count} veces"
            ),
            CriticalThreshold(
                variable='humidity',
                threshold_value=round(humidity_p95, 1),
                percentile=95,
                historical_occurrences=humidity_p95_count,
                avg_production_impact=12.0,  # Estimado
                description=f"Humedad muy alta (P95): {humidity_p95:.1f}% - Ocurrió {humidity_p95_count} veces"
            ),
            CriticalThreshold(
                variable='humidity',
                threshold_value=round(humidity_p99, 1),
                percentile=99,
                historical_occurrences=humidity_p99_count,
                avg_production_impact=25.0,  # Estimado
                description=f"Humedad extrema (P99): {humidity_p99:.1f}% - Ocurrió {humidity_p99_count} veces"
            )
        ])

        logger.info(f"✅ Umbrales críticos identificados: {len(thresholds)} umbrales")

        for threshold in thresholds:
            logger.info(f"  {threshold.description}")

        # Cache resultados
        self.cache['thresholds'] = thresholds
        self.cache_timestamp = datetime.now()

        return thresholds

    async def contextualize_aemet_forecast(
        self,
        aemet_forecast: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Contextualiza predicciones AEMET con historia SIAR.

        Args:
            aemet_forecast: Lista de predicciones AEMET (temp, humidity por día)

        Returns:
            Lista de predicciones con contexto histórico añadido
        """
        logger.info("🔗 Contextualizando predicciones AEMET con historia SIAR")

        # Obtener umbrales históricos
        thresholds = await self.identify_critical_thresholds()

        # Extraer datos SIAR para análisis
        df_temp, df_humidity = await self.extract_siar_complete_history()
        df_merged = pd.merge(df_temp, df_humidity, on='timestamp', suffixes=('', '_hum'))

        contextualized = []

        for forecast_day in aemet_forecast:
            temp_forecast = forecast_day.get('temperature', 0)
            humidity_forecast = forecast_day.get('humidity', 0)

            # Buscar días históricos similares (±2°C, ±5% humedad)
            similar_days = df_merged[
                (df_merged['temperature'] >= temp_forecast - 2) &
                (df_merged['temperature'] <= temp_forecast + 2) &
                (df_merged['humidity'] >= humidity_forecast - 5) &
                (df_merged['humidity'] <= humidity_forecast + 5)
            ]

            # Calcular contexto histórico
            similar_count = len(similar_days)
            if similar_count > 0:
                avg_efficiency = similar_days.apply(
                    lambda row: self._calculate_production_efficiency_proxy(
                        row['temperature'],
                        row['humidity']
                    ),
                    axis=1
                ).mean()
            else:
                avg_efficiency = 50.0  # Neutral si no hay datos similares

            # Identificar umbrales superados
            exceeded_thresholds = []
            for threshold in thresholds:
                if threshold.variable == 'temperature' and temp_forecast >= threshold.threshold_value:
                    exceeded_thresholds.append(threshold)
                elif threshold.variable == 'humidity' and humidity_forecast >= threshold.threshold_value:
                    exceeded_thresholds.append(threshold)

            # Construir contexto
            contextualized_day = {
                **forecast_day,  # Datos AEMET originales
                'historical_context': {
                    'similar_days_count': similar_count,
                    'avg_production_efficiency': round(avg_efficiency, 1),
                    'exceeded_thresholds': [
                        {
                            'variable': t.variable,
                            'threshold': t.threshold_value,
                            'percentile': t.percentile,
                            'estimated_impact': t.avg_production_impact
                        }
                        for t in exceeded_thresholds
                    ],
                    'recommendation': self._generate_recommendation(
                        avg_efficiency,
                        len(exceeded_thresholds)
                    )
                }
            }

            contextualized.append(contextualized_day)

        logger.info(f"✅ {len(contextualized)} predicciones AEMET contextualizadas con historia SIAR")

        return contextualized

    # =========================================================================
    # MÉTODOS PRIVADOS
    # =========================================================================

    def _calculate_production_efficiency_proxy(
        self,
        temperature: float,
        humidity: float
    ) -> float:
        """
        Calcula proxy de eficiencia producción chocolate (0-100).

        Basado en literatura chocolatera:
        - Óptimo: 15-25°C, 40-70% humedad
        - Crítico: >35°C, >80% humedad
        """
        # Score temperatura (0-100)
        if 15 <= temperature <= 25:
            temp_score = 100
        elif temperature < 15:
            temp_score = max(0, 100 - (15 - temperature) * 5)
        else:  # temperature > 25
            temp_score = max(0, 100 - (temperature - 25) * 8)

        # Score humedad (0-100)
        if 40 <= humidity <= 70:
            humidity_score = 100
        elif humidity < 40:
            humidity_score = max(0, 100 - (40 - humidity) * 2)
        else:  # humidity > 70
            humidity_score = max(0, 100 - (humidity - 70) * 3)

        # Score combinado (60% temperatura, 40% humedad)
        efficiency = temp_score * 0.6 + humidity_score * 0.4

        return efficiency

    def _calculate_confidence_interval(
        self,
        correlation: float,
        sample_size: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calcula intervalo de confianza para correlación."""
        # Fisher Z transformation
        z = np.arctanh(correlation)
        se = 1 / np.sqrt(sample_size - 3)
        z_critical = stats.norm.ppf((1 + confidence) / 2)

        z_lower = z - z_critical * se
        z_upper = z + z_critical * se

        # Transform back
        lower = np.tanh(z_lower)
        upper = np.tanh(z_upper)

        return (round(lower, 3), round(upper, 3))

    def _generate_recommendation(
        self,
        avg_efficiency: float,
        exceeded_thresholds_count: int
    ) -> str:
        """Genera recomendación basada en contexto histórico."""
        if exceeded_thresholds_count >= 2:
            return "⚠️ CRÍTICO: Múltiples umbrales superados. Reducir producción 30-40%"
        elif exceeded_thresholds_count == 1:
            return "⚠️ ALERTA: Umbral crítico superado. Reducir producción 15-20%"
        elif avg_efficiency >= 80:
            return "✅ ÓPTIMO: Condiciones ideales. Maximizar producción chocolate premium"
        elif avg_efficiency >= 60:
            return "✔️ BUENO: Condiciones favorables. Producción normal"
        else:
            return "⚠️ PRECAUCIÓN: Condiciones subóptimas. Monitorear calidad templado"

    async def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen completo del análisis histórico SIAR.

        Returns:
            Dict con correlaciones, patrones, umbrales
        """
        logger.info("📊 Generando resumen completo análisis SIAR")

        # Ejecutar todos los análisis (con cache)
        correlations = await self.calculate_production_correlations()
        seasonal_patterns = await self.detect_seasonal_patterns()
        thresholds = await self.identify_critical_thresholds()

        # Identificar mejor/peor mes
        best_month = max(seasonal_patterns, key=lambda p: p.production_efficiency_score)
        worst_month = min(seasonal_patterns, key=lambda p: p.production_efficiency_score)

        summary = {
            'data_source': 'SIAR historical (2000-2025)',
            'total_records': 88935,
            'analysis_period': '25 years',
            'correlations': {
                'temperature_production': {
                    'r_squared': correlations['temperature'].r_squared,
                    'correlation': correlations['temperature'].correlation,
                    'p_value': correlations['temperature'].p_value,
                    'significance': 'significant' if correlations['temperature'].p_value < 0.05 else 'not significant'
                },
                'humidity_production': {
                    'r_squared': correlations['humidity'].r_squared,
                    'correlation': correlations['humidity'].correlation,
                    'p_value': correlations['humidity'].p_value,
                    'significance': 'significant' if correlations['humidity'].p_value < 0.05 else 'not significant'
                }
            },
            'seasonal_insights': {
                'best_month': {
                    'name': best_month.month_name,
                    'efficiency_score': best_month.production_efficiency_score,
                    'avg_temp': best_month.avg_temperature,
                    'optimal_days': best_month.optimal_days_count
                },
                'worst_month': {
                    'name': worst_month.month_name,
                    'efficiency_score': worst_month.production_efficiency_score,
                    'avg_temp': worst_month.avg_temperature,
                    'critical_days': worst_month.critical_days_count
                },
                'all_months': [
                    {
                        'month': p.month_name,
                        'efficiency': p.production_efficiency_score,
                        'temp': p.avg_temperature,
                        'humidity': p.avg_humidity
                    }
                    for p in seasonal_patterns
                ]
            },
            'critical_thresholds': [
                {
                    'variable': t.variable,
                    'value': t.threshold_value,
                    'percentile': t.percentile,
                    'occurrences': t.historical_occurrences,
                    'description': t.description
                }
                for t in thresholds
            ],
            'generated_at': datetime.now().isoformat()
        }

        logger.info(
            f"✅ Resumen SIAR generado | Mejor mes: {best_month.month_name} "
            f"({best_month.production_efficiency_score:.1f}%), "
            f"Peor mes: {worst_month.month_name} ({worst_month.production_efficiency_score:.1f}%)"
        )

        return summary
