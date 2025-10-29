"""
Enhanced Recommendations System - Chocolate Factory
================================================

Sistema de recomendaciones mejorado que integra:
- Datos históricos completos (SIAR + REE)
- Reglas de negocio específicas
- Análisis de costos real-time
- Predicciones temporales avanzadas
- Optimización multi-objetivo
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio

import pandas as pd
import numpy as np

from domain.ml.enhanced_ml_service import EnhancedMLService  # Sprint 15
from services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)

class EnhancedRecommendationEngine:
    """Motor de recomendaciones avanzado con integración histórica"""

    def __init__(self):
        self.ml_service = EnhancedMLService()

        # Business rules from .claude context
        self.production_constraints = {
            'max_daily_production_kg': 250,
            'min_batch_size_kg': 10,
            'max_batch_size_kg': 10,
            'energy_cost_target': 0.24,  # €/kg
            'material_cost_per_kg': 4.28,
            'labor_cost_per_kg': 8.00,
            'fixed_overhead_per_kg': 1.12,
            'target_margin_standard': 0.40,
            'target_margin_premium': 0.53,
            'machine_sequence': ['mezcladora', 'roladora', 'conchadora', 'templadora'],
            'conching_times': {
                'standard': 360,    # 6 hours in minutes
                'premium': 720,     # 12 hours in minutes
                'ultra_premium': 1440  # 24 hours in minutes
            },
            'optimal_conditions': {
                'temperature': (18, 25),
                'humidity': (45, 65),
                'ambient_temp_max': 22
            }
        }

        # Energy consumption from machinery.md
        self.machine_consumption = {
            'mezcladora': 0.5,    # kWh/min
            'roladora': 0.7,      # kWh/min
            'conchadora': 0.8,    # kWh/min
            'templadora': 0.6     # kWh/min
        }

        # Peak and valley hours for Spanish electricity market
        self.time_periods = {
            'peak_hours': [10, 11, 12, 13, 19, 20, 21],
            'valley_hours': [0, 1, 2, 3, 4, 5, 6],
            'flat_hours': [7, 8, 9, 14, 15, 16, 17, 18, 22, 23]
        }

    async def get_comprehensive_recommendations(self, current_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera recomendaciones comprehensivas basadas en datos históricos y ML
        """
        try:
            logger.info("🎯 Generating comprehensive recommendations...")

            # Extract current conditions
            price_kwh = current_conditions.get('price_eur_kwh', 0.15)
            temperature = current_conditions.get('temperature', 20)
            humidity = current_conditions.get('humidity', 50)
            now = datetime.now()

            # === 1. ANÁLISIS DE COSTOS Y RENTABILIDAD ===
            cost_analysis = await self._analyze_production_costs(price_kwh, temperature, humidity)

            # === 2. ANÁLISIS TEMPORAL ÓPTIMO ===
            temporal_analysis = await self._analyze_optimal_timing(price_kwh, now)

            # === 3. ANÁLISIS DE CONDICIONES DE PRODUCCIÓN ===
            production_analysis = self._analyze_production_conditions(temperature, humidity)

            # === 4. RECOMENDACIONES DE CALIDAD/VOLUMEN ===
            quality_recommendations = self._analyze_quality_mix(price_kwh, temperature, humidity)

            # === 5. ALERTAS Y LIMITACIONES ===
            alerts = self._generate_production_alerts(current_conditions)

            # === 6. RECOMENDACIÓN PRINCIPAL ===
            main_recommendation = self._generate_main_recommendation(
                cost_analysis, temporal_analysis, production_analysis, quality_recommendations
            )

            return {
                "🏢": "Chocolate Factory - Enhanced Recommendations",
                "🎯": "Comprehensive Production Optimization",
                "timestamp": now.isoformat(),
                "current_conditions": current_conditions,

                "main_recommendation": main_recommendation,

                "detailed_analysis": {
                    "cost_analysis": cost_analysis,
                    "temporal_analysis": temporal_analysis,
                    "production_analysis": production_analysis,
                    "quality_recommendations": quality_recommendations
                },

                "alerts": alerts,

                "next_optimal_windows": await self._get_next_optimal_windows(),

                "business_impact": {
                    "estimated_cost_per_kg": cost_analysis.get("total_cost_per_kg", 13.90),
                    "margin_impact": cost_analysis.get("margin_impact", "neutral"),
                    "production_efficiency": production_analysis.get("efficiency_score", 50),
                    "energy_optimization_score": temporal_analysis.get("energy_score", 50)
                }
            }

        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            return {"error": str(e)}

    async def _analyze_production_costs(self, price_kwh: float, temperature: float, humidity: float) -> Dict[str, Any]:
        """Análisis detallado de costos de producción"""

        # Base costs from cost_structure.yaml
        material_cost = self.production_constraints['material_cost_per_kg']
        labor_cost = self.production_constraints['labor_cost_per_kg']
        fixed_overhead = self.production_constraints['fixed_overhead_per_kg']

        # Energy cost calculation per kg
        # Total production time: ~10 minutes (mixing + rolling + tempering) + variable conching
        base_production_minutes = 5 + 18 + 38  # Average times
        standard_conching_minutes = self.production_constraints['conching_times']['standard']
        total_minutes = base_production_minutes + standard_conching_minutes

        # Energy consumption calculation
        energy_kwh_per_kg = (
            self.machine_consumption['mezcladora'] * 5 +      # Mixing 5 min
            self.machine_consumption['roladora'] * 18 +       # Rolling 18 min
            self.machine_consumption['conchadora'] * standard_conching_minutes +  # Conching variable
            self.machine_consumption['templadora'] * 38       # Tempering 38 min
        ) / 10  # Per kg (10 kg batch)

        current_energy_cost = price_kwh * energy_kwh_per_kg

        # Seasonal and condition adjustments
        seasonal_factor = 1.15 if datetime.now().month in [6, 7, 8] else 1.0  # Summer penalty
        condition_factor = 1.0

        # Temperature impact on cooling costs
        if temperature > 30:
            condition_factor += 0.1  # 10% increase for high temp
        elif temperature < 15:
            condition_factor += 0.05  # 5% increase for heating

        # Humidity impact on dehumidification
        if humidity > 75:
            condition_factor += 0.05

        adjusted_energy_cost = current_energy_cost * seasonal_factor * condition_factor

        # Total cost calculation
        total_cost_per_kg = (
            material_cost +
            labor_cost +
            fixed_overhead +
            adjusted_energy_cost
        )

        # Margin analysis
        wholesale_price_standard = 23.33  # €/kg (3.50 per 150g bar)
        margin_standard = (wholesale_price_standard - total_cost_per_kg) / wholesale_price_standard

        # Cost category classification
        target_cost = material_cost + labor_cost + fixed_overhead + self.production_constraints['energy_cost_target']
        cost_category = "optimal" if total_cost_per_kg <= target_cost else "elevated" if total_cost_per_kg <= target_cost * 1.1 else "high"

        return {
            "total_cost_per_kg": round(total_cost_per_kg, 2),
            "cost_breakdown": {
                "materials": material_cost,
                "labor": labor_cost,
                "fixed_overhead": fixed_overhead,
                "energy": round(adjusted_energy_cost, 3),
                "energy_kwh_per_kg": round(energy_kwh_per_kg, 2)
            },
            "margin_analysis": {
                "standard_margin": round(margin_standard, 3),
                "break_even": margin_standard > 0,
                "target_margin": self.production_constraints['target_margin_standard']
            },
            "cost_category": cost_category,
            "vs_target": {
                "target_cost": target_cost,
                "difference": round(total_cost_per_kg - target_cost, 2),
                "percentage": round((total_cost_per_kg / target_cost - 1) * 100, 1)
            },
            "optimization_potential": round(max(0, adjusted_energy_cost - self.production_constraints['energy_cost_target']), 3)
        }

    async def _analyze_optimal_timing(self, price_kwh: float, current_time: datetime) -> Dict[str, Any]:
        """Análisis temporal para optimización de energía"""

        hour = current_time.hour
        is_weekend = current_time.weekday() >= 5

        # Time period classification
        if hour in self.time_periods['valley_hours']:
            period = "valley"
            period_score = 100
        elif hour in self.time_periods['peak_hours']:
            period = "peak"
            period_score = 20
        else:
            period = "flat"
            period_score = 60

        # Price analysis
        if price_kwh <= 0.10:
            price_category = "very_low"
            price_score = 100
        elif price_kwh <= 0.15:
            price_category = "low"
            price_score = 80
        elif price_kwh <= 0.20:
            price_category = "medium"
            price_score = 60
        elif price_kwh <= 0.25:
            price_category = "high"
            price_score = 30
        else:
            price_category = "very_high"
            price_score = 10

        # Combined energy optimization score
        energy_score = (period_score * 0.4 + price_score * 0.6)
        if is_weekend:
            energy_score *= 1.1  # Weekend bonus (lower demand)

        energy_score = min(100, energy_score)

        # Timing recommendations
        recommendations = []
        if energy_score >= 80:
            recommendations.append("🟢 MOMENTO ÓPTIMO: Maximizar producción intensiva")
        elif energy_score >= 60:
            recommendations.append("🟡 MOMENTO FAVORABLE: Producción estándar recomendada")
        elif energy_score >= 40:
            recommendations.append("🟠 MOMENTO REGULAR: Evaluar procesos no críticos")
        else:
            recommendations.append("🔴 MOMENTO DESFAVORABLE: Reducir/aplazar producción")

        # Specific timing advice
        if period == "peak":
            recommendations.append("⏰ Considerar aplazamiento hasta horas valle (00:00-06:00)")
        elif period == "valley":
            recommendations.append("⚡ Momento ideal para conchado de larga duración")

        if price_kwh > 0.20:
            recommendations.append("💰 Precio elevado: Programar para madrugada")
        elif price_kwh < 0.12:
            recommendations.append("💚 Precio bajo: Aprovechar para stock y reservas")

        return {
            "energy_score": round(energy_score, 1),
            "period": period,
            "price_category": price_category,
            "is_optimal_time": energy_score >= 70,
            "recommendations": recommendations,
            "next_valley_period": self._get_next_valley_period(current_time),
            "savings_potential": round(max(0, (price_kwh - 0.10) * 2.4), 3)  # vs very low price
        }

    def _analyze_production_conditions(self, temperature: float, humidity: float) -> Dict[str, Any]:
        """Análisis de condiciones de producción"""

        temp_min, temp_max = self.production_constraints['optimal_conditions']['temperature']
        humid_min, humid_max = self.production_constraints['optimal_conditions']['humidity']

        # Temperature analysis
        temp_optimal = temp_min <= temperature <= temp_max
        temp_score = 100 if temp_optimal else max(0, 100 - abs(temperature - 21.5) * 5)

        # Humidity analysis
        humid_optimal = humid_min <= humidity <= humid_max
        humid_score = 100 if humid_optimal else max(0, 100 - abs(humidity - 55) * 2)

        # Combined efficiency score
        efficiency_score = (temp_score * 0.6 + humid_score * 0.4)  # Temperature more critical

        # Condition alerts
        alerts = []
        if temperature > 35:
            alerts.append("🌡️ CRÍTICO: Temperatura muy alta - Riesgo de calidad")
        elif temperature > 30:
            alerts.append("⚠️ ADVERTENCIA: Temperatura elevada - Aumentar refrigeración")
        elif temperature < 15:
            alerts.append("❄️ ADVERTENCIA: Temperatura baja - Verificar calefacción")

        if humidity > 80:
            alerts.append("💧 CRÍTICO: Humedad muy alta - Riesgo de bloom")
        elif humidity > 70:
            alerts.append("⚠️ ADVERTENCIA: Humedad elevada - Activar deshumidificación")
        elif humidity < 40:
            alerts.append("🏜️ ADVERTENCIA: Humedad baja - Posible agrietamiento")

        # Production capability assessment
        if efficiency_score >= 80:
            capability = "optimal"
            recommendation = "Condiciones ideales para maximizar producción"
        elif efficiency_score >= 60:
            capability = "good"
            recommendation = "Condiciones favorables para producción estándar"
        elif efficiency_score >= 40:
            capability = "limited"
            recommendation = "Condiciones subóptimas - Monitorear calidad"
        else:
            capability = "critical"
            recommendation = "Condiciones críticas - Considerar parar producción"

        return {
            "efficiency_score": round(efficiency_score, 1),
            "capability": capability,
            "temperature_analysis": {
                "value": temperature,
                "optimal_range": f"{temp_min}-{temp_max}°C",
                "score": round(temp_score, 1),
                "status": "optimal" if temp_optimal else "suboptimal"
            },
            "humidity_analysis": {
                "value": humidity,
                "optimal_range": f"{humid_min}-{humid_max}%",
                "score": round(humid_score, 1),
                "status": "optimal" if humid_optimal else "suboptimal"
            },
            "alerts": alerts,
            "recommendation": recommendation
        }

    def _analyze_quality_mix(self, price_kwh: float, temperature: float, humidity: float) -> Dict[str, Any]:
        """Análisis de mezcla óptima de calidades"""

        # Cost analysis for different qualities
        standard_conching_hours = 6
        premium_conching_hours = 12

        standard_energy_cost = price_kwh * 0.8 * (60 * standard_conching_hours) / 60  # kWh for conching
        premium_energy_cost = price_kwh * 0.8 * (60 * premium_conching_hours) / 60

        # Margin analysis
        standard_margin = 23.33 - (13.90 + standard_energy_cost)  # Simplified
        premium_margin = 33.33 - (15.67 + premium_energy_cost)    # Premium costs more

        # Condition suitability
        conditions_score = (100 - abs(temperature - 21.5) * 5 + 100 - abs(humidity - 55) * 2) / 2

        recommendations = []

        # Standard quality analysis
        if price_kwh <= 0.15 and conditions_score >= 60:
            recommendations.append({
                "quality": "standard",
                "recommendation": "favorable",
                "reason": "Costos energéticos favorables y condiciones adecuadas",
                "expected_margin": round(standard_margin, 2),
                "production_ratio": 0.7
            })
        elif price_kwh <= 0.20:
            recommendations.append({
                "quality": "standard",
                "recommendation": "moderate",
                "reason": "Costos moderados, mantener volumen base",
                "expected_margin": round(standard_margin, 2),
                "production_ratio": 0.6
            })
        else:
            recommendations.append({
                "quality": "standard",
                "recommendation": "limited",
                "reason": "Costos energéticos elevados",
                "expected_margin": round(standard_margin, 2),
                "production_ratio": 0.4
            })

        # Premium quality analysis
        if price_kwh <= 0.12 and conditions_score >= 80:
            recommendations.append({
                "quality": "premium",
                "recommendation": "optimal",
                "reason": "Condiciones ideales y costos mínimos",
                "expected_margin": round(premium_margin, 2),
                "production_ratio": 0.3
            })
        elif price_kwh <= 0.18 and conditions_score >= 70:
            recommendations.append({
                "quality": "premium",
                "recommendation": "favorable",
                "reason": "Buenas condiciones justifican mayor consumo energético",
                "expected_margin": round(premium_margin, 2),
                "production_ratio": 0.2
            })
        else:
            recommendations.append({
                "quality": "premium",
                "recommendation": "avoid",
                "reason": "Costos/condiciones no justifican tiempo extra de conchado",
                "expected_margin": round(premium_margin, 2),
                "production_ratio": 0.1
            })

        return {
            "quality_recommendations": recommendations,
            "optimal_mix": {
                "standard_ratio": sum([r["production_ratio"] for r in recommendations if r["quality"] == "standard"]),
                "premium_ratio": sum([r["production_ratio"] for r in recommendations if r["quality"] == "premium"])
            },
            "energy_cost_impact": {
                "standard_kwh": round(standard_energy_cost, 3),
                "premium_kwh": round(premium_energy_cost, 3),
                "premium_vs_standard": round(premium_energy_cost - standard_energy_cost, 3)
            }
        }

    def _generate_production_alerts(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera alertas de producción basadas en condiciones"""

        alerts = []
        price = conditions.get('price_eur_kwh', 0.15)
        temp = conditions.get('temperature', 20)
        humidity = conditions.get('humidity', 50)
        hour = datetime.now().hour

        # Price alerts
        if price > 0.30:
            alerts.append({
                "type": "cost",
                "level": "critical",
                "message": f"Precio energía crítico: {price:.3f} €/kWh",
                "action": "Parar producción inmediatamente",
                "impact": "high"
            })
        elif price > 0.25:
            alerts.append({
                "type": "cost",
                "level": "warning",
                "message": f"Precio energía muy alto: {price:.3f} €/kWh",
                "action": "Reducir producción y programar para valle",
                "impact": "medium"
            })
        elif price < 0.08:
            alerts.append({
                "type": "opportunity",
                "level": "info",
                "message": f"Precio energía excepcional: {price:.3f} €/kWh",
                "action": "Maximizar producción y generar stock",
                "impact": "positive"
            })

        # Environmental alerts
        if temp > 35:
            alerts.append({
                "type": "environment",
                "level": "critical",
                "message": f"Temperatura crítica: {temp}°C",
                "action": "Activar refrigeración de emergencia",
                "impact": "high"
            })
        elif temp < 15:
            alerts.append({
                "type": "environment",
                "level": "warning",
                "message": f"Temperatura muy baja: {temp}°C",
                "action": "Verificar calefacción zonas críticas",
                "impact": "medium"
            })

        if humidity > 85:
            alerts.append({
                "type": "environment",
                "level": "critical",
                "message": f"Humedad crítica: {humidity}%",
                "action": "Activar deshumidificación inmediata",
                "impact": "high"
            })

        # Timing alerts
        if hour in self.time_periods['peak_hours'] and price > 0.18:
            alerts.append({
                "type": "timing",
                "level": "warning",
                "message": "Hora pico con precio elevado",
                "action": "Aplazar procesos no críticos",
                "impact": "medium"
            })

        return alerts

    def _generate_main_recommendation(self, cost_analysis: Dict, temporal_analysis: Dict,
                                    production_analysis: Dict, quality_analysis: Dict) -> Dict[str, Any]:
        """Genera la recomendación principal del sistema"""

        # Scoring system
        cost_score = 100 if cost_analysis['cost_category'] == 'optimal' else 60 if cost_analysis['cost_category'] == 'elevated' else 20
        timing_score = temporal_analysis['energy_score']
        conditions_score = production_analysis['efficiency_score']

        # Weighted overall score
        overall_score = (cost_score * 0.4 + timing_score * 0.35 + conditions_score * 0.25)

        # Decision matrix
        if overall_score >= 80:
            action = "maximize_production"
            priority = "high"
            description = "Condiciones óptimas: Maximizar producción y aprovechar ventana favorable"
            specific_actions = [
                "Incrementar volumen de producción al máximo",
                "Priorizar calidad premium si condiciones lo permiten",
                "Generar stock adicional para períodos desfavorables",
                "Extender turnos si es posible"
            ]
        elif overall_score >= 65:
            action = "standard_production"
            priority = "medium"
            description = "Condiciones favorables: Mantener producción estándar con optimizaciones"
            specific_actions = [
                "Mantener volumen de producción planificado",
                "Optimizar mezcla de calidades según margen",
                "Monitorear evolución de condiciones",
                "Preparar ajustes para próxima ventana"
            ]
        elif overall_score >= 45:
            action = "reduced_production"
            priority = "medium"
            description = "Condiciones subóptimas: Reducir producción y optimizar costos"
            specific_actions = [
                "Reducir volumen al 60-70% de capacidad",
                "Priorizar lotes de alta rotación",
                "Postponer calidad premium",
                "Monitorear alertas de calidad"
            ]
        else:
            action = "halt_production"
            priority = "critical"
            description = "Condiciones críticas: Parar producción y esperar mejores condiciones"
            specific_actions = [
                "Detener nueva producción inmediatamente",
                "Completar lotes en proceso con precaución",
                "Activar protocolos de emergencia si necesario",
                "Planificar reinicio cuando mejoren condiciones"
            ]

        return {
            "action": action,
            "priority": priority,
            "description": description,
            "overall_score": round(overall_score, 1),
            "confidence": "high" if abs(overall_score - 50) > 25 else "medium",
            "specific_actions": specific_actions,
            "score_breakdown": {
                "cost_score": round(cost_score, 1),
                "timing_score": round(timing_score, 1),
                "conditions_score": round(conditions_score, 1)
            },
            "estimated_duration": self._estimate_action_duration(action, overall_score)
        }

    def _get_next_valley_period(self, current_time: datetime) -> Dict[str, Any]:
        """Obtiene información del próximo período valle"""

        current_hour = current_time.hour

        # Find next valley hour
        valley_hours = self.time_periods['valley_hours']

        if current_hour in valley_hours:
            # Currently in valley period
            next_valley_start = current_time.replace(minute=0, second=0, microsecond=0)
            valley_end = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
            if current_hour >= 6:
                valley_end += timedelta(days=1)
        else:
            # Find next valley start
            if current_hour < valley_hours[0]:
                # Same day
                next_valley_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Next day
                next_valley_start = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

            valley_end = next_valley_start.replace(hour=6)

        hours_until_valley = (next_valley_start - current_time).total_seconds() / 3600
        valley_duration = (valley_end - next_valley_start).total_seconds() / 3600

        return {
            "next_start": next_valley_start.isoformat(),
            "end_time": valley_end.isoformat(),
            "hours_until_start": round(max(0, hours_until_valley), 1),
            "duration_hours": round(valley_duration, 1),
            "currently_in_valley": current_hour in valley_hours
        }

    async def _get_next_optimal_windows(self) -> List[Dict[str, Any]]:
        """Obtiene las próximas ventanas óptimas de producción"""

        windows = []
        current_time = datetime.now()

        # Check next 48 hours
        for hours_ahead in range(0, 48, 6):  # Every 6 hours
            future_time = current_time + timedelta(hours=hours_ahead)
            hour = future_time.hour

            # Determine if it's a good window
            is_valley = hour in self.time_periods['valley_hours']
            is_weekend = future_time.weekday() >= 5

            score = 50  # Base score

            if is_valley:
                score += 30
            elif hour in self.time_periods['peak_hours']:
                score -= 20

            if is_weekend:
                score += 10

            # Estimated price (simplified model)
            base_price = 0.15
            if is_valley:
                estimated_price = base_price * 0.7
            elif hour in self.time_periods['peak_hours']:
                estimated_price = base_price * 1.4
            else:
                estimated_price = base_price

            if score >= 70:
                windows.append({
                    "start_time": future_time.isoformat(),
                    "end_time": (future_time + timedelta(hours=6)).isoformat(),
                    "score": score,
                    "estimated_price": round(estimated_price, 3),
                    "period_type": "valley" if is_valley else "peak" if hour in self.time_periods['peak_hours'] else "flat",
                    "recommendation": "optimal" if score >= 80 else "favorable"
                })

        return windows[:5]  # Return top 5 windows

    def _estimate_action_duration(self, action: str, score: float) -> str:
        """Estima duración recomendada para la acción"""

        if action == "maximize_production":
            return "Mantener mientras condiciones sean favorables (score > 70)"
        elif action == "standard_production":
            return "Reevaluar en 2-4 horas según evolución"
        elif action == "reduced_production":
            return "Reducir hasta mejora de condiciones"
        else:  # halt_production
            return "Detener hasta que score > 45"


# Service factory
def get_enhanced_recommendation_engine() -> EnhancedRecommendationEngine:
    """Get enhanced recommendation engine instance"""
    return EnhancedRecommendationEngine()