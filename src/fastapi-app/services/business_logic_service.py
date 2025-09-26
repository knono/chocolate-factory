"""
Business Logic Service - Chocolate Factory
==========================================

Servicio híbrido que integra:
- Resultados de modelos ML (scores numéricos)
- Reglas de negocio desde .claude/rules/business-logic-suggestions.md
- Mensajes humanizados para operadores
- Contexto temporal y estacional español

Genera recomendaciones humanas basadas en datos técnicos.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class BusinessLogicService:
    """Servicio de lógica de negocio que consulta reglas de .claude y humaniza recomendaciones"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.rules_file = self.project_root / ".claude" / "rules" / "business-logic-suggestions.md"

        # Cache para reglas leídas
        self._rules_cache = None
        self._cache_timestamp = None

        # Thresholds desde las reglas (sincronizado con business-logic-suggestions.md)
        self.score_thresholds = {
            'maximize': 80,      # Score 80-100
            'standard': 60,      # Score 60-79
            'reduced': 40,       # Score 40-59
            'minimal': 20,       # Score 20-39
            'critical': 0        # Score <20
        }

        # Thresholds de precio energético (€/kWh)
        self.price_thresholds = {
            'exceptional': (0.05, 0.10),
            'favorable': (0.10, 0.15),
            'normal': (0.15, 0.20),
            'elevated': (0.20, 0.25),
            'high': (0.25, 0.30),
            'very_high': (0.30, 0.40),
            'critical': (0.40, float('inf'))
        }

        # Horarios españoles
        self.time_periods = {
            'valley': list(range(0, 7)),      # 00:00-06:59
            'flat_morning': list(range(7, 10)),  # 07:00-09:59
            'peak_morning': list(range(10, 14)), # 10:00-13:59
            'flat_afternoon': list(range(14, 18)), # 14:00-17:59
            'peak_evening': list(range(18, 22)),   # 18:00-21:59
            'flat_late': list(range(22, 24))      # 22:00-23:59
        }

    def _load_rules(self) -> Dict[str, Any]:
        """Carga y parsea las reglas desde .claude/rules/business-logic-suggestions.md"""

        try:
            # Check if cache is still valid (5 minutes)
            if (self._rules_cache and self._cache_timestamp and
                (datetime.now() - self._cache_timestamp).total_seconds() < 300):
                return self._rules_cache

            if not self.rules_file.exists():
                logger.warning(f"Rules file not found: {self.rules_file}")
                return {}

            with open(self.rules_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse rules (simplified - could be more sophisticated)
            rules = {
                'content': content,
                'loaded_at': datetime.now(),
                'templates': self._extract_templates(content),
                'price_messages': self._extract_price_messages(content),
                'condition_messages': self._extract_condition_messages(content),
                'time_messages': self._extract_time_messages(content)
            }

            self._rules_cache = rules
            self._cache_timestamp = datetime.now()

            logger.info(f"✅ Business rules loaded from {self.rules_file}")
            return rules

        except Exception as e:
            logger.error(f"❌ Error loading business rules: {e}")
            return {}

    def _extract_templates(self, content: str) -> Dict[str, str]:
        """Extrae plantillas de mensajes del contenido markdown"""

        templates = {}

        # Extract message templates using regex
        patterns = {
            'maximize': r'#### MAXIMIZAR PRODUCCIÓN.*?\n```(.*?)```',
            'standard': r'#### PRODUCCIÓN ESTÁNDAR.*?\n```(.*?)```',
            'reduced': r'#### PRODUCCIÓN REDUCIDA.*?\n```(.*?)```',
            'minimal': r'#### PRODUCCIÓN MÍNIMA.*?\n```(.*?)```',
            'critical': r'#### OPERACIONES CRÍTICAS.*?\n```(.*?)```'
        }

        for level, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
            if match:
                templates[level] = match.group(1).strip()

        return templates

    def _extract_price_messages(self, content: str) -> Dict[str, str]:
        """Extrae mensajes por precio energético"""

        messages = {}

        # Find price messages section
        price_section = re.search(r'#### Por Precio Energético(.*?)####', content, re.DOTALL)
        if price_section:
            lines = price_section.group(1).strip().split('\n')
            for line in lines:
                if '€' in line and ':' in line:
                    # Parse lines like: - **€0.05-0.10/kWh**: "💰 ¡Precio excepcional!..."
                    match = re.search(r'\*\*(€[\d.-]+.*?/kWh)\*\*:\s*"(.*?)"', line)
                    if match:
                        price_range = match.group(1)
                        message = match.group(2)
                        messages[price_range] = message

        return messages

    def _extract_condition_messages(self, content: str) -> Dict[str, str]:
        """Extrae mensajes por condiciones ambientales"""

        messages = {}

        # Find environmental conditions section
        env_section = re.search(r'#### Por Condiciones Ambientales(.*?)####', content, re.DOTALL)
        if env_section:
            lines = env_section.group(1).strip().split('\n')
            for line in lines:
                if ('Temperatura' in line or 'Humedad' in line) and ':' in line:
                    # Parse condition messages
                    match = re.search(r'\*\*(.*?)\*\*:\s*"(.*?)"', line)
                    if match:
                        condition = match.group(1)
                        message = match.group(2)
                        messages[condition] = message

        return messages

    def _extract_time_messages(self, content: str) -> Dict[str, str]:
        """Extrae mensajes por horarios españoles"""

        messages = {}

        # Find time-based messages section
        time_section = re.search(r'#### Por Horarios \(España\)(.*?)###', content, re.DOTALL)
        if time_section:
            lines = time_section.group(1).strip().split('\n')
            for line in lines:
                if ':' in line and '(' in line:
                    # Parse time messages
                    match = re.search(r'\*\*(.*?)\*\*:\s*"(.*?)"', line)
                    if match:
                        time_period = match.group(1)
                        message = match.group(2)
                        messages[time_period] = message

        return messages

    def generate_human_recommendation(self, ml_score: float, conditions: Dict[str, Any],
                                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera recomendación humanizada basada en score ML y reglas de negocio

        Args:
            ml_score: Score del modelo ML (0-100)
            conditions: Condiciones actuales (price_eur_kwh, temperature, humidity, etc.)
            context: Contexto adicional (opcional)

        Returns:
            Diccionario con recomendación humanizada
        """

        try:
            logger.info(f"🎯 Generating human recommendation for score: {ml_score}")

            # Load business rules
            rules = self._load_rules()
            if not rules:
                return self._fallback_recommendation(ml_score, conditions)

            # Extract current conditions
            price_kwh = conditions.get('price_eur_kwh', 0.15)
            temperature = conditions.get('temperature', 20)
            humidity = conditions.get('humidity', 50)
            now = context.get('timestamp', datetime.now()) if context else datetime.now()

            # Determine recommendation level
            level = self._determine_recommendation_level(ml_score)

            # Get base template
            template = rules['templates'].get(level, '')

            # Generate contextualized message
            message = self._build_contextualized_message(
                template, level, ml_score, price_kwh, temperature, humidity, now, rules
            )

            # Add specific situation messages
            situation_messages = self._get_situation_specific_messages(
                price_kwh, temperature, humidity, now, rules
            )

            # Calculate next optimal window
            next_window = self._calculate_next_optimal_window(now, price_kwh)

            # Estimate economic impact
            economic_impact = self._estimate_economic_impact(ml_score, price_kwh, level)

            return {
                "🏢": "Chocolate Factory - Recomendación del Sistema",
                "timestamp": now.isoformat(),
                "ml_score": ml_score,
                "recommendation_level": level,

                "main_message": message,
                "situation_context": situation_messages,

                "economic_impact": economic_impact,
                "next_window": next_window,

                "current_conditions": {
                    "price_eur_kwh": price_kwh,
                    "temperature": temperature,
                    "humidity": humidity,
                    "hour": now.hour,
                    "weekday": now.weekday(),
                    "period": self._get_time_period(now.hour)
                },

                "metadata": {
                    "rules_loaded_at": rules.get('loaded_at', '').isoformat() if rules.get('loaded_at') else '',
                    "confidence": "high" if abs(ml_score - 50) > 25 else "medium",
                    "urgency": self._determine_urgency(level, ml_score),
                    "review_in_minutes": self._get_review_interval(level)
                }
            }

        except Exception as e:
            logger.error(f"❌ Error generating human recommendation: {e}")
            return self._fallback_recommendation(ml_score, conditions)

    def _determine_recommendation_level(self, ml_score: float) -> str:
        """Determina el nivel de recomendación basado en el score ML"""

        if ml_score >= self.score_thresholds['maximize']:
            return 'maximize'
        elif ml_score >= self.score_thresholds['standard']:
            return 'standard'
        elif ml_score >= self.score_thresholds['reduced']:
            return 'reduced'
        elif ml_score >= self.score_thresholds['minimal']:
            return 'minimal'
        else:
            return 'critical'

    def _build_contextualized_message(self, template: str, level: str, ml_score: float,
                                    price_kwh: float, temperature: float, humidity: float,
                                    timestamp: datetime, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Construye mensaje contextualizado desde la plantilla"""

        # Replace template variables
        situation_desc = self._describe_current_situation(price_kwh, temperature, humidity, timestamp)

        # Extract sections from template
        title = self._extract_title_from_template(template)
        actions = self._extract_actions_from_template(template, level, ml_score, price_kwh)
        duration = self._extract_duration_from_template(template, level)
        benefit = self._calculate_benefit_message(price_kwh, level)

        return {
            "title": title,
            "situation": situation_desc,
            "priority_actions": actions,
            "estimated_duration": duration,
            "economic_benefit": benefit,
            "confidence_level": "alta" if abs(ml_score - 50) > 25 else "media"
        }

    def _describe_current_situation(self, price_kwh: float, temperature: float,
                                  humidity: float, timestamp: datetime) -> str:
        """Describe la situación actual en lenguaje natural"""

        # Price description
        price_desc = self._get_price_description(price_kwh)

        # Temperature description
        if temperature <= 20:
            temp_desc = "temperatura fresca"
        elif temperature <= 25:
            temp_desc = "temperatura ideal"
        elif temperature <= 30:
            temp_desc = "temperatura moderada"
        elif temperature <= 35:
            temp_desc = "temperatura elevada"
        else:
            temp_desc = "temperatura alta"

        # Humidity description
        if humidity <= 50:
            humid_desc = "humedad baja"
        elif humidity <= 65:
            humid_desc = "humedad óptima"
        elif humidity <= 75:
            humid_desc = "humedad moderada"
        else:
            humid_desc = "humedad alta"

        # Time context
        period = self._get_time_period(timestamp.hour)
        time_desc = self._get_period_description(period)

        return f"{price_desc}, {temp_desc} ({temperature}°C), {humid_desc} ({humidity}%), {time_desc}"

    def _get_price_description(self, price_kwh: float) -> str:
        """Obtiene descripción humanizada del precio"""

        if price_kwh <= 0.10:
            return "precio energético excepcional"
        elif price_kwh <= 0.15:
            return "precio energético favorable"
        elif price_kwh <= 0.20:
            return "precio energético normal"
        elif price_kwh <= 0.25:
            return "precio energético elevado"
        elif price_kwh <= 0.30:
            return "precio energético alto"
        elif price_kwh <= 0.40:
            return "precio energético muy alto"
        else:
            return "precio energético crítico"

    def _get_time_period(self, hour: int) -> str:
        """Determina el período del día"""

        for period, hours in self.time_periods.items():
            if hour in hours:
                return period
        return 'unknown'

    def _get_period_description(self, period: str) -> str:
        """Obtiene descripción del período"""

        descriptions = {
            'valley': 'período valle (ideal para procesos largos)',
            'flat_morning': 'horario llano matutino',
            'peak_morning': 'hora pico matutina',
            'flat_afternoon': 'horario llano vespertino',
            'peak_evening': 'hora pico nocturna',
            'flat_late': 'horario llano nocturno'
        }
        return descriptions.get(period, 'horario normal')

    def _extract_title_from_template(self, template: str) -> str:
        """Extrae título de la plantilla"""

        lines = template.split('\n')
        for line in lines:
            if line.startswith('🟢') or line.startswith('🟡') or line.startswith('🟠') or line.startswith('🔴') or line.startswith('🚨'):
                return line.replace('**', '').strip()
        return "RECOMENDACIÓN DEL SISTEMA"

    def _extract_actions_from_template(self, template: str, level: str, ml_score: float, price_kwh: float) -> List[str]:
        """Extrae acciones prioritarias de la plantilla"""

        actions = []

        # Default actions by level
        if level == 'maximize':
            actions = [
                "Incrementar volumen al máximo seguro",
                "Priorizar lotes premium si condiciones lo permiten",
                "Extender turnos para generar stock",
                "Monitorear que se mantengan condiciones favorables"
            ]
        elif level == 'standard':
            actions = [
                "Continuar con mix de productos planificado",
                "Mantener horarios regulares",
                "Estar atentos a cambios en condiciones",
                "Optimizar procesos sin prisa"
            ]
        elif level == 'reduced':
            actions = [
                "Bajar a 70% capacidad normal",
                "Solo lotes de alta prioridad/rotación",
                "Diferir calidad premium para mejor momento",
                "Monitorear calidad más frecuentemente"
            ]
        elif level == 'minimal':
            actions = [
                "Reducir al 40% capacidad o menos",
                "Solo pedidos ya comprometidos",
                "Activar protocolos de ahorro energético",
                "Programar procesos largos para horas valle"
            ]
        else:  # critical
            actions = [
                "Solo completar lotes ya en proceso",
                "Activar plan de contingencia",
                "Mantener equipos en standby seguro",
                "Evaluar cada 2 horas para reinicio"
            ]

        return actions

    def _extract_duration_from_template(self, template: str, level: str) -> str:
        """Extrae duración estimada de la plantilla"""

        durations = {
            'maximize': "Mientras condiciones sean favorables (score > 70)",
            'standard': "Reevaluar en 2-3 horas según evolución",
            'reduced': "Esperar mejores condiciones para intensificar",
            'minimal': "Revisar cada 2 horas para oportunidades",
            'critical': "Evaluar cada 2 horas para reinicio seguro"
        }

        return durations.get(level, "Reevaluar según evolución")

    def _calculate_benefit_message(self, price_kwh: float, level: str) -> str:
        """Calcula mensaje de beneficio económico"""

        base_price = 0.15  # Precio de referencia

        if level == 'maximize' and price_kwh < base_price:
            savings = (base_price - price_kwh) * 2.4  # ~2.4 kWh/kg aprox
            return f"Ahorro estimado de €{savings:.3f}/kg vs período normal"
        elif level == 'reduced' or level == 'minimal':
            extra_cost = max(0, price_kwh - base_price) * 2.4
            return f"Evitar sobrecosto de €{extra_cost:.3f}/kg vs período normal"
        else:
            return "Mantener equilibrio costo-beneficio"

    def _get_situation_specific_messages(self, price_kwh: float, temperature: float,
                                       humidity: float, timestamp: datetime,
                                       rules: Dict[str, Any]) -> List[str]:
        """Obtiene mensajes específicos para la situación actual"""

        messages = []

        # Price-based messages
        price_message = self._get_price_specific_message(price_kwh, rules)
        if price_message:
            messages.append(price_message)

        # Temperature-based messages
        temp_message = self._get_temperature_specific_message(temperature, rules)
        if temp_message:
            messages.append(temp_message)

        # Humidity-based messages
        humid_message = self._get_humidity_specific_message(humidity, rules)
        if humid_message:
            messages.append(humid_message)

        # Time-based messages
        time_message = self._get_time_specific_message(timestamp, rules)
        if time_message:
            messages.append(time_message)

        return messages

    def _get_price_specific_message(self, price_kwh: float, rules: Dict[str, Any]) -> Optional[str]:
        """Obtiene mensaje específico por precio"""

        price_messages = rules.get('price_messages', {})

        # Find matching price range
        for price_range, message in price_messages.items():
            # Simple range matching (could be more sophisticated)
            if '0.05-0.10' in price_range and 0.05 <= price_kwh <= 0.10:
                return message
            elif '0.10-0.15' in price_range and 0.10 <= price_kwh <= 0.15:
                return message
            elif '0.15-0.20' in price_range and 0.15 <= price_kwh <= 0.20:
                return message
            elif '0.20-0.25' in price_range and 0.20 <= price_kwh <= 0.25:
                return message
            elif '0.25-0.30' in price_range and 0.25 <= price_kwh <= 0.30:
                return message
            elif '0.30-0.40' in price_range and 0.30 <= price_kwh <= 0.40:
                return message
            elif '>€0.40' in price_range and price_kwh > 0.40:
                return message

        return None

    def _get_temperature_specific_message(self, temperature: float, rules: Dict[str, Any]) -> Optional[str]:
        """Obtiene mensaje específico por temperatura"""

        condition_messages = rules.get('condition_messages', {})

        # Find matching temperature range
        for condition, message in condition_messages.items():
            if 'Temperatura' in condition:
                if '15-25°C' in condition and 15 <= temperature <= 25:
                    return message
                elif '25-30°C' in condition and 25 <= temperature <= 30:
                    return message
                elif '30-35°C' in condition and 30 <= temperature <= 35:
                    return message
                elif '35-40°C' in condition and 35 <= temperature <= 40:
                    return message
                elif '>40°C' in condition and temperature > 40:
                    return message

        return None

    def _get_humidity_specific_message(self, humidity: float, rules: Dict[str, Any]) -> Optional[str]:
        """Obtiene mensaje específico por humedad"""

        condition_messages = rules.get('condition_messages', {})

        # Find matching humidity range
        for condition, message in condition_messages.items():
            if 'Humedad' in condition:
                if '45-65%' in condition and 45 <= humidity <= 65:
                    return message
                elif '65-75%' in condition and 65 <= humidity <= 75:
                    return message
                elif '75-85%' in condition and 75 <= humidity <= 85:
                    return message
                elif '>85%' in condition and humidity > 85:
                    return message

        return None

    def _get_time_specific_message(self, timestamp: datetime, rules: Dict[str, Any]) -> Optional[str]:
        """Obtiene mensaje específico por horario"""

        time_messages = rules.get('time_messages', {})
        hour = timestamp.hour

        # Find matching time period
        for time_period, message in time_messages.items():
            if '00:00-06:00' in time_period and 0 <= hour <= 6:
                return message
            elif '06:00-10:00' in time_period and 6 <= hour <= 10:
                return message
            elif '10:00-14:00' in time_period and 10 <= hour <= 14:
                return message
            elif '14:00-18:00' in time_period and 14 <= hour <= 18:
                return message
            elif '18:00-22:00' in time_period and 18 <= hour <= 22:
                return message
            elif '22:00-00:00' in time_period and 22 <= hour <= 23:
                return message

        return None

    def _calculate_next_optimal_window(self, current_time: datetime, current_price: float) -> Dict[str, Any]:
        """Calcula la próxima ventana óptima"""

        # Simple algorithm - next valley period
        current_hour = current_time.hour

        if current_hour < 6:  # Currently in valley
            next_valley = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:  # Find today's valley or next day
            next_valley = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        valley_end = next_valley.replace(hour=6)
        hours_until = (next_valley - current_time).total_seconds() / 3600

        return {
            "next_optimal_start": next_valley.isoformat(),
            "next_optimal_end": valley_end.isoformat(),
            "hours_until_optimal": round(max(0, hours_until), 1),
            "estimated_benefit": "Período valle - ahorro ~30% en costos energéticos",
            "recommendation": "Programar conchado largo para aprovechar tarifa valle"
        }

    def _estimate_economic_impact(self, ml_score: float, price_kwh: float, level: str) -> Dict[str, Any]:
        """Estima impacto económico de la recomendación"""

        base_cost_per_kg = 13.90  # From business rules
        base_price = 0.15
        energy_kwh_per_kg = 2.4  # Approximate

        current_energy_cost = price_kwh * energy_kwh_per_kg
        base_energy_cost = base_price * energy_kwh_per_kg

        cost_difference = current_energy_cost - base_energy_cost

        # Estimate production efficiency by level
        efficiency_multipliers = {
            'maximize': 1.2,
            'standard': 1.0,
            'reduced': 0.7,
            'minimal': 0.4,
            'critical': 0.1
        }

        efficiency = efficiency_multipliers.get(level, 1.0)

        return {
            "current_cost_per_kg": round(base_cost_per_kg + cost_difference, 2),
            "vs_base_cost": round(cost_difference, 3),
            "production_efficiency": f"{efficiency*100:.0f}%",
            "cost_category": "optimal" if cost_difference <= 0 else "elevated" if cost_difference <= 0.05 else "high",
            "daily_impact_estimate": round(cost_difference * efficiency * 200, 2)  # 200kg avg daily production
        }

    def _determine_urgency(self, level: str, ml_score: float) -> str:
        """Determina urgencia de la recomendación"""

        if level == 'critical':
            return 'immediate'
        elif level == 'maximize' and ml_score > 90:
            return 'high'
        elif level in ['minimal', 'reduced']:
            return 'medium'
        else:
            return 'low'

    def _get_review_interval(self, level: str) -> int:
        """Obtiene intervalo de revisión en minutos"""

        intervals = {
            'critical': 120,    # 2 hours
            'minimal': 120,     # 2 hours
            'reduced': 180,     # 3 hours
            'standard': 180,    # 3 hours
            'maximize': 240     # 4 hours
        }

        return intervals.get(level, 180)

    def _fallback_recommendation(self, ml_score: float, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Recomendación de respaldo cuando fallan las reglas"""

        logger.warning("🔄 Using fallback recommendation - business rules not available")

        level = self._determine_recommendation_level(ml_score)
        price_kwh = conditions.get('price_eur_kwh', 0.15)

        return {
            "🏢": "Chocolate Factory - Recomendación Básica",
            "timestamp": datetime.now().isoformat(),
            "ml_score": ml_score,
            "recommendation_level": level,
            "main_message": {
                "title": f"RECOMENDACIÓN {level.upper()}",
                "situation": f"Score ML: {ml_score:.1f}, Precio: €{price_kwh:.3f}/kWh",
                "priority_actions": ["Consultar con supervisor", "Revisar condiciones manualmente"],
                "estimated_duration": "Pendiente evaluación manual",
                "economic_benefit": "A determinar"
            },
            "situation_context": ["Sistema de reglas no disponible - usar criterio operacional"],
            "error_note": "Reglas de negocio no pudieron cargarse. Consultar .claude/rules/"
        }


# Service factory
def get_business_logic_service() -> BusinessLogicService:
    """Get business logic service instance"""
    return BusinessLogicService()