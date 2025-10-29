"""
🏭 Historical Analytics Service
Análisis de datos históricos REE para optimización de fábrica
"""

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import logging
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
import statistics

logger = logging.getLogger(__name__)

class FactoryMetrics(BaseModel):
    """Métricas de consumo de fábrica"""
    total_kwh: float
    avg_daily_cost: float
    peak_consumption: float  # kW
    total_cost: float
    days_analyzed: int

class PriceAnalysis(BaseModel):
    """Análisis de precios históricos"""
    min_price_eur_kwh: float
    max_price_eur_kwh: float
    avg_price_eur_kwh: float
    volatility_coefficient: float
    price_range_eur_kwh: float

class OptimizationPotential(BaseModel):
    """Potencial de optimización"""
    total_savings_eur: float
    optimal_production_hours: int
    annual_savings_projection: float
    efficiency_improvement_pct: float

class HistoricalAnalytics(BaseModel):
    """Analytics históricos completos"""
    factory_metrics: FactoryMetrics
    price_analysis: PriceAnalysis
    optimization_potential: OptimizationPotential
    recommendations: List[str]
    analysis_period: str
    last_update: str

class HistoricalAnalyticsService:
    """Servicio de análisis histórico de datos REE"""
    
    def __init__(self):
        # Configuración InfluxDB usando las mismas variables de entorno que data_ingestion
        import os
        self.influx_client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
            token=os.getenv("INFLUXDB_TOKEN", ""),
            org=os.getenv("INFLUXDB_ORG", "chocolate-factory")
        )
        self.query_api = self.influx_client.query_api()
        self.bucket = os.getenv("INFLUXDB_BUCKET", "energy-data")
        
        # Constantes de fábrica (del TFM)
        self.FACTORY_PEAK_KW = 156  # kW pico
        self.FACTORY_DAILY_KWH = 2496  # kWh/día
        self.FACTORY_AVG_KW = 104  # kW promedio (2496/24)

    async def get_historical_analytics(self, days_back: int = 220) -> HistoricalAnalytics:
        """Obtiene analytics históricos completos"""
        try:
            # Consultar datos históricos REE
            ree_data = await self._query_ree_historical_data(days_back)
            
            if not ree_data:
                logger.warning("No historical REE data found")
                return self._create_empty_analytics()
            
            # Calcular métricas
            factory_metrics = self._calculate_factory_metrics(ree_data)
            price_analysis = self._analyze_prices(ree_data)
            optimization_potential = self._calculate_optimization_potential(ree_data, price_analysis)
            recommendations = self._generate_recommendations(price_analysis, optimization_potential)
            
            return HistoricalAnalytics(
                factory_metrics=factory_metrics,
                price_analysis=price_analysis,
                optimization_potential=optimization_potential,
                recommendations=recommendations,
                analysis_period=f"Últimos {days_back} días",
                last_update=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Historical analytics error: {e}")
            return self._create_empty_analytics()

    async def _query_ree_historical_data(self, days_back: int) -> List[dict]:
        """Consulta datos históricos de REE desde InfluxDB"""
        try:
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r["_measurement"] == "energy_prices")
                |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
                |> filter(fn: (r) => r["source"] == "REE")
                |> keep(columns: ["_time", "_value"])
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(query)
            
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time(),
                        'price_eur_kwh': record.get_value()
                    })
            
            logger.info(f"Retrieved {len(data)} historical REE records")
            return data
            
        except Exception as e:
            logger.error(f"Error querying historical REE data: {e}")
            return []

    def _calculate_factory_metrics(self, ree_data: List[dict]) -> FactoryMetrics:
        """Calcula métricas de fábrica basadas en datos históricos"""
        if not ree_data:
            return FactoryMetrics(
                total_kwh=0, avg_daily_cost=0, peak_consumption=0, total_cost=0, days_analyzed=0
            )
        
        # Calcular días únicos
        days_analyzed = len(set(record['timestamp'].date() for record in ree_data))
        
        # Calcular consumo total (basado en días analizados)
        total_kwh = days_analyzed * self.FACTORY_DAILY_KWH
        
        # Calcular costo total y promedio diario
        total_cost = sum(record['price_eur_kwh'] * self.FACTORY_DAILY_KWH/24 for record in ree_data)
        avg_daily_cost = total_cost / max(days_analyzed, 1)
        
        return FactoryMetrics(
            total_kwh=total_kwh,
            avg_daily_cost=avg_daily_cost,
            peak_consumption=self.FACTORY_PEAK_KW,
            total_cost=total_cost,
            days_analyzed=days_analyzed
        )

    def _analyze_prices(self, ree_data: List[dict]) -> PriceAnalysis:
        """Analiza precios históricos"""
        if not ree_data:
            return PriceAnalysis(
                min_price_eur_kwh=0, max_price_eur_kwh=0, avg_price_eur_kwh=0,
                volatility_coefficient=0, price_range_eur_kwh=0
            )
        
        prices = [record['price_eur_kwh'] for record in ree_data]
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = statistics.mean(prices)
        price_range = max_price - min_price
        
        # Coeficiente de volatilidad (desviación estándar / promedio)
        volatility = statistics.stdev(prices) / avg_price if avg_price > 0 else 0
        
        return PriceAnalysis(
            min_price_eur_kwh=min_price,
            max_price_eur_kwh=max_price,
            avg_price_eur_kwh=avg_price,
            volatility_coefficient=volatility,
            price_range_eur_kwh=price_range
        )

    def _calculate_optimization_potential(self, ree_data: List[dict], price_analysis: PriceAnalysis) -> OptimizationPotential:
        """Calcula el potencial de optimización"""
        if not ree_data:
            return OptimizationPotential(
                total_savings_eur=0, optimal_production_hours=0, 
                annual_savings_projection=0, efficiency_improvement_pct=0
            )
        
        # Calcular ahorros potenciales operando solo en horas de precio bajo
        # Definir umbral de precio bajo (25% percentile)
        prices = [record['price_eur_kwh'] for record in ree_data]
        prices_sorted = sorted(prices)
        low_price_threshold = prices_sorted[len(prices_sorted)//4]  # 25% percentile
        
        # Horas óptimas (precio bajo)
        optimal_hours = sum(1 for price in prices if price <= low_price_threshold)
        
        # Ahorros calculando diferencia entre precio promedio y precio bajo
        avg_hourly_consumption = self.FACTORY_DAILY_KWH / 24
        savings_per_optimal_hour = (price_analysis.avg_price_eur_kwh - low_price_threshold) * avg_hourly_consumption
        total_savings = optimal_hours * savings_per_optimal_hour
        
        # Proyección anual
        days_in_sample = len(set(record['timestamp'].date() for record in ree_data))
        annual_savings = (total_savings / max(days_in_sample, 1)) * 365
        
        # Porcentaje de mejora de eficiencia
        efficiency_improvement = (total_savings / (price_analysis.avg_price_eur_kwh * len(ree_data) * avg_hourly_consumption)) * 100
        
        return OptimizationPotential(
            total_savings_eur=total_savings,
            optimal_production_hours=optimal_hours,
            annual_savings_projection=annual_savings,
            efficiency_improvement_pct=efficiency_improvement
        )

    def _generate_recommendations(self, price_analysis: PriceAnalysis, optimization: OptimizationPotential) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = []
        
        if optimization.annual_savings_projection > 50000:
            recommendations.append("🎯 Implementar programación inteligente: ahorros anuales superiores a 50.000€")
        
        if price_analysis.volatility_coefficient > 0.3:
            recommendations.append("⚡ Alta volatilidad de precios: ideal para optimización temporal")
        
        if optimization.efficiency_improvement_pct > 20:
            recommendations.append(f"📈 Mejora de eficiencia del {optimization.efficiency_improvement_pct:.1f}% disponible")
        
        recommendations.append("🔄 Considerar storage de energía para aprovechar precios mínimos")
        recommendations.append("📊 Implementar alertas automáticas para precios óptimos")
        
        return recommendations

    def _create_empty_analytics(self) -> HistoricalAnalytics:
        """Crea analytics vacíos en caso de error"""
        return HistoricalAnalytics(
            factory_metrics=FactoryMetrics(
                total_kwh=0, avg_daily_cost=0, peak_consumption=156, total_cost=0, days_analyzed=0
            ),
            price_analysis=PriceAnalysis(
                min_price_eur_kwh=0, max_price_eur_kwh=0, avg_price_eur_kwh=0,
                volatility_coefficient=0, price_range_eur_kwh=0
            ),
            optimization_potential=OptimizationPotential(
                total_savings_eur=0, optimal_production_hours=0, 
                annual_savings_projection=0, efficiency_improvement_pct=0
            ),
            recommendations=["❌ Sin datos históricos disponibles"],
            analysis_period="Sin datos",
            last_update=datetime.now().isoformat()
        )