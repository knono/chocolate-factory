"""
Chatbot Context Builder Service
================================

Sprint 11 - Chatbot BI Conversacional

RAG local sin vector DB, usando keyword matching inteligente.
Optimizado para tokens (500-1500 tokens/pregunta).
"""

import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)


class ChatbotContextService:
    """
    Construye contexto relevante para Claude Haiku basado en keywords.

    NO usa embeddings ni vector DB.
    Usa keyword matching simple + endpoints disponibles.
    """

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.keywords_map = {
            "optimal_windows": [
                "cuándo", "cuando", "producir", "ventana", "ventanas",
                "mejor momento", "momento óptimo", "mejores horas", "mejor hora",
                "días", "dia", "próximos", "proximos", "mañana", "manana",
                "lanzar producción", "lanzar", "próximas horas", "horario",
                "semana", "semanas", "siguiente", "próxima semana", "esta semana",
                "forecast", "predicción", "prediccion", "previsión", "prevision"
            ],
            "price_forecast": ["precio", "precios", "energía", "energia", "costo", "coste", "tarifa", "kwh"],
            "alerts": ["alerta", "alertas", "problema", "problemas", "warning", "crítico", "critico"],
            "savings": ["ahorro", "ahorros", "saving", "comparar", "comparativa", "roi", "beneficio"],
            "production_plan": ["plan", "planificar", "optimizar", "optimización", "batches", "proceso"],
            "analysis": [
                "análisis", "analisis", "histórico", "historico", "siar",
                "temperatura", "clima", "meses", "mes", "estación", "estacion",
                "estacional", "año", "anual", "patrón", "patron", "tendencia"
            ],
            "current_status": ["actual", "ahora", "estado", "status", "qué está pasando", "que esta pasando"],
            "recommendations": [
                "recomendación", "recomendacion", "recomienda", "aconsejar", "aconseja",
                "qué hacer", "que hacer", "qué hago", "que hago", "sugerencia", "consejo"
            ],
        }

    async def build_context(self, question: str) -> str:
        """
        Construye contexto relevante basado en keywords detectados.

        OPTIMIZACIÓN: Ejecuta todas las llamadas HTTP en paralelo con asyncio.gather()
        para reducir latencia de ~15s → ~3s

        Args:
            question: Pregunta del usuario

        Returns:
            Contexto formateado para Claude (< 2000 tokens)
        """
        import asyncio

        question_lower = question.lower()

        # Detectar categorías relevantes
        relevant_categories = self._detect_categories(question_lower)

        logger.info(f"Pregunta: '{question}' → Categorías: {relevant_categories}")

        # Preparar tareas paralelas
        tasks = []
        task_names = []

        # Estado actual siempre incluido (baseline)
        tasks.append(self._get_current_status())
        task_names.append("current_status")

        # Contexto de producción SIEMPRE (para que entienda el negocio)
        tasks.append(self._get_production_context())
        task_names.append("production_context")

        # Añadir contextos específicos según categorías detectadas
        if "optimal_windows" in relevant_categories:
            tasks.append(self._get_optimal_windows())
            task_names.append("optimal_windows")
            # Añadir también el forecast semanal Prophet
            tasks.append(self._get_weekly_forecast())
            task_names.append("weekly_forecast")

        if "price_forecast" in relevant_categories:
            tasks.append(self._get_price_forecast())
            task_names.append("price_forecast")

        if "alerts" in relevant_categories:
            tasks.append(self._get_alerts())
            task_names.append("alerts")

        if "savings" in relevant_categories:
            tasks.append(self._get_savings())
            task_names.append("savings")

        if "production_plan" in relevant_categories:
            tasks.append(self._get_production_plan())
            task_names.append("production_plan")

        if "analysis" in relevant_categories:
            tasks.append(self._get_analysis())
            task_names.append("analysis")
            # Añadir también analytics históricos
            tasks.append(self._get_historical_analytics())
            task_names.append("historical_analytics")

        if "recommendations" in relevant_categories:
            tasks.append(self._get_human_recommendation())
            task_names.append("human_recommendation")

        # Si no hay match específico, usar dashboard completo
        if len(relevant_categories) == 0:
            tasks.append(self._get_full_dashboard())
            task_names.append("full_dashboard")

        # 🚀 EJECUTAR TODAS LAS LLAMADAS EN PARALELO
        logger.info(f"Ejecutando {len(tasks)} llamadas HTTP en paralelo: {task_names}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Construir contexto con resultados exitosos
        context_parts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Error en {task_names[i]}: {result}")
            else:
                context_parts.append(result)

        # Unir contextos
        full_context = "\n\n".join(context_parts)

        # Log tamaño aproximado (1 token ≈ 4 caracteres)
        estimated_tokens = len(full_context) // 4
        logger.info(f"Contexto construido: ~{estimated_tokens} tokens")

        return full_context

    def _detect_categories(self, question_lower: str) -> List[str]:
        """Detecta categorías relevantes basándose en keywords."""
        detected = []

        for category, keywords in self.keywords_map.items():
            if any(keyword in question_lower for keyword in keywords):
                detected.append(category)

        return detected

    async def _get_current_status(self) -> str:
        """Estado actual básico (siempre incluido)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            # Extraer datos del dashboard completo
            current = data.get('current_info', {})
            energy = current.get('energy', {})
            weather = current.get('weather', {})

            # Log datos para debugging
            logger.info(f"Dashboard data keys: {list(data.keys())}")
            logger.info(f"Current info keys: {list(current.keys())}")
            logger.info(f"Energy data: {energy}")
            logger.info(f"Weather data: {weather}")

            # Construir contexto con valores reales
            price = energy.get('price_eur_kwh', 'N/A')
            temp = weather.get('temperature', 'N/A')
            humidity = weather.get('humidity', 'N/A')
            pressure = weather.get('pressure', 'N/A')
            comfort = weather.get('comfort_index', 'N/A')
            prod_status = current.get('production_status', 'N/A')
            efficiency = current.get('factory_efficiency', 'N/A')

            # Extraer predicciones sklearn (restauradas Oct 22, 2025)
            predictions = data.get('predictions', {})
            energy_opt = predictions.get('energy_optimization', {})
            prod_rec = predictions.get('production_recommendation', {})

            energy_score = energy_opt.get('score', 'N/A')
            energy_rec = energy_opt.get('recommendation', 'N/A')
            prod_class = prod_rec.get('class', 'N/A')
            prod_confidence = prod_rec.get('confidence', 'N/A')

            context = f"""ESTADO ACTUAL CHOCOLATE FACTORY
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Precio energía actual: {price} €/kWh
Tendencia precio: {energy.get('trend', 'N/A')}
Temperatura: {temp}°C
Humedad: {humidity}%
Presión: {pressure} hPa
Confort: {comfort}
Estado producción: {prod_status}
Eficiencia fábrica: {efficiency}%

🤖 PREDICCIONES ML (sklearn):
Optimización energética: {energy_score}/100 ({energy_rec})
Recomendación producción: {prod_class} (confianza {prod_confidence}%)"""

            logger.info(f"Context built successfully with {len(context)} chars")
            return context

    async def _get_optimal_windows(self) -> str:
        """Próximas ventanas óptimas (Sprint 09)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/insights/optimal-windows")
            data = response.json()

            windows = data.get('optimal_windows', [])[:5]  # Limitar a 5 ventanas

            windows_text = "PRÓXIMAS VENTANAS ÓPTIMAS DE PRODUCCIÓN (Sprint 09):\n\n"
            for w in windows:
                date_str = w.get('datetime', '')[:10]  # YYYY-MM-DD
                hours = w.get('hours', 'N/A')
                price = w.get('avg_price_eur_kwh', 0)
                process = w.get('recommended_process', 'N/A')
                savings = w.get('estimated_savings_eur', 0)
                quality = w.get('quality', 'N/A')

                windows_text += f"📅 {date_str} · {hours}\n"
                windows_text += f"   💰 Precio: {price:.4f} €/kWh ({quality})\n"
                windows_text += f"   🏭 Proceso: {process}\n"
                windows_text += f"   💵 Ahorro estimado: {savings:.2f} €\n\n"

            return windows_text

    async def _get_weekly_forecast(self) -> str:
        """Forecast Prophet 7 días (calendar_days del dashboard)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            weekly = data.get('weekly_forecast', {})
            days = weekly.get('calendar_days', [])
            summary = weekly.get('summary', {})

            forecast_text = f"""FORECAST PROPHET ML - PRÓXIMOS 7 DÍAS ({summary.get('period', {}).get('start_date', 'N/A')} a {summary.get('period', {}).get('end_date', 'N/A')}):

📊 RESUMEN SEMANAL:
   • Precio mínimo: {summary.get('price_summary', {}).get('min_price', 0):.4f} €/kWh
   • Precio máximo: {summary.get('price_summary', {}).get('max_price', 0):.4f} €/kWh
   • Precio promedio: {summary.get('price_summary', {}).get('avg_price', 0):.4f} €/kWh
   • Días óptimos: {summary.get('optimal_days', 0)}/{summary.get('period', {}).get('total_days', 7)}

📅 PRECIOS DIARIOS PREVISTOS:
"""
            # Mostrar solo los próximos 5 días (no todos los 7)
            for day in days[1:6]:  # Saltar hoy, mostrar 5 días siguientes
                date = day.get('date', '')
                day_name = day.get('day_name', '')
                price = day.get('avg_price_eur_kwh', 0)
                temp = day.get('avg_temperature', 0)
                icon = day.get('recommendation_icon', '⚪')

                forecast_text += f"   {icon} {date} ({day_name}): {price:.4f} €/kWh, {temp:.1f}°C\n"

            return forecast_text

    async def _get_price_forecast(self) -> str:
        """Precios REE y análisis de desviación."""
        from datetime import date, timedelta

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Obtener último precio REE
            latest_response = await client.get(f"{self.base_url}/ree/prices/latest")
            latest = latest_response.json()

            # Obtener estadísticas REE (últimos 30 días)
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            stats_response = await client.get(
                f"{self.base_url}/ree/prices/stats",
                params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
            )
            stats = stats_response.json()

            price_now = latest.get('price_eur_kwh', 0)
            timestamp = latest.get('timestamp', 'N/A')
            hour = timestamp[11:16] if len(timestamp) > 11 else 'N/A'

            # Clasificar precio actual
            if price_now < 0.10:
                icon = "🟢"
                label = "EXCELENTE"
            elif price_now < 0.15:
                icon = "🟡"
                label = "BUENO"
            else:
                icon = "🔴"
                label = "ALTO"

            forecast_text = f"""ANÁLISIS PRECIOS ENERGÍA REE (últimos 30 días):

💰 Precio actual ({hour}h): {icon} {price_now:.4f} €/kWh ({label})

📊 Estadísticas históricas (30 días):
   • Precio mínimo: {stats.get('min', 0):.4f} €/kWh
   • Precio máximo: {stats.get('max', 0):.4f} €/kWh
   • Precio promedio: {stats.get('avg', 0):.4f} €/kWh
   • Precio mediana: {stats.get('median', 0):.4f} €/kWh
   • Total registros: {stats.get('count', 0):,}

RECOMENDACIÓN: {'PRODUCIR AHORA' if price_now < 0.10 else 'ESPERAR A VALLE' if price_now > 0.15 else 'PRODUCCIÓN MODERADA'}"""

            return forecast_text

    async def _get_alerts(self) -> str:
        """Alertas predictivas (Sprint 09)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/insights/alerts")
            data = response.json()

            alerts_text = f"ALERTAS ACTIVAS ({data.get('total_alerts', 0)}):\n"
            for alert in data.get('alerts', [])[:5]:  # Limitar a 5 alertas
                alerts_text += f"- [{alert['severity']}] {alert['message']}\n"

            return alerts_text

    async def _get_savings(self) -> str:
        """Tracking de ahorros (Sprint 09)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/insights/savings-tracking")
            data = response.json()

            # Extraer correctamente los datos del JSON
            daily = data.get('daily_savings', {})
            weekly = data.get('weekly_projection', {})
            monthly = data.get('monthly_tracking', {})
            annual = data.get('annual_projection', {})

            savings_text = f"""TRACKING AHORROS ENERGÉTICOS (Sprint 09):

💰 AHORROS ACTUALES:
   • Hoy: {daily.get('savings_eur', 0):.2f} € ({daily.get('savings_pct', 0):.1f}% ahorro)
   • Semana (proyección): {weekly.get('savings_eur', 0):.2f} €
   • Mes (progreso): {monthly.get('projected_eur', 0):.2f} € de {monthly.get('target_eur', 0):.0f} € objetivo ({monthly.get('progress_pct', 0):.1f}%)
   • Año (estimado): {annual.get('estimated_savings_eur', 0):.0f} €

📊 COMPARATIVA COSTOS:
   • Optimizado hoy: {daily.get('optimized_cost_eur', 0):.2f} €
   • Baseline hoy: {daily.get('baseline_cost_eur', 0):.2f} €

🎯 ROI: {annual.get('roi_description', 'N/A')}
📈 Estado mensual: {monthly.get('status', 'N/A')}"""

            return savings_text

    async def _get_production_plan(self) -> str:
        """Plan de producción optimizado (Sprint 08)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/optimize/production/daily",
                json={"target_kg": 200}
            )
            data = response.json()

            plan_text = "PLAN PRODUCCIÓN OPTIMIZADO (Hoy):\n"
            for batch in data.get('recommended_batches', [])[:3]:  # Limitar a 3 batches
                plan_text += f"- {batch['start_hour']}:00-{batch['end_hour']}:00h: {batch['process']} (Precio: {batch['avg_price']} €/kWh)\n"

            return plan_text

    async def _get_analysis(self) -> str:
        """Análisis histórico SIAR (Sprint 07)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            siar = data.get('siar_analysis', {}).get('seasonal_patterns', {})
            thresholds = data.get('siar_analysis', {}).get('thresholds', {})

            best_month = siar.get('best_month', {})
            worst_month = siar.get('worst_month', {})
            temp_thresh = thresholds.get('temperature', {})

            analysis_text = f"""ANÁLISIS HISTÓRICO (25 años SIAR - 88,935 registros):

📅 MEJOR MES: {best_month.get('name', 'N/A')}
   • Eficiencia: {best_month.get('efficiency_score', 0):.1f}%
   • Temperatura promedio: {best_month.get('avg_temp', 0):.1f}°C
   • Días óptimos: {best_month.get('optimal_days', 0)}

📅 PEOR MES: {worst_month.get('name', 'N/A')}
   • Eficiencia: {worst_month.get('efficiency_score', 0):.1f}%
   • Temperatura promedio: {worst_month.get('avg_temp', 0):.1f}°C

🌡️ UMBRALES CRÍTICOS:
   • P90: {temp_thresh.get('p90', 'N/A')}°C
   • P95: {temp_thresh.get('p95', 'N/A')}°C
   • P99: {temp_thresh.get('p99', 'N/A')}°C"""

            return analysis_text

    async def _get_historical_analytics(self) -> str:
        """Analytics históricos con ahorro anual proyectado."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            analytics = data.get('historical_analytics', {})
            factory = analytics.get('factory_metrics', {})
            price = analytics.get('price_analysis', {})
            optimization = analytics.get('optimization_potential', {})

            analytics_text = f"""ANALYTICS HISTÓRICOS (Últimos {analytics.get('analysis_period', 'N/A')}):

💰 POTENCIAL DE AHORRO:
   • Ahorro anual proyectado: {optimization.get('annual_savings_projection', 0):.2f} €
   • Ahorro total detectado: {optimization.get('total_savings_eur', 0):.2f} €
   • Mejora eficiencia: {optimization.get('efficiency_improvement_pct', 0):.1f}%
   • Horas óptimas detectadas: {optimization.get('optimal_production_hours', 0)}

📊 MÉTRICAS FÁBRICA:
   • Consumo total: {factory.get('total_kwh', 0):,.0f} kWh
   • Costo promedio diario: {factory.get('avg_daily_cost', 0):.2f} €
   • Días analizados: {factory.get('days_analyzed', 0)}

⚡ ANÁLISIS PRECIOS:
   • Volatilidad: {price.get('volatility_coefficient', 0):.1%}
   • Rango precios: {price.get('price_range_eur_kwh', 0):.4f} €/kWh"""

            return analytics_text

    async def _get_human_recommendation(self) -> str:
        """Recomendación del sistema con lógica de negocio."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            human_rec = data.get('recommendations', {}).get('human_recommendation', {})
            main_msg = human_rec.get('main_message', {})
            next_window = human_rec.get('next_window', {})
            economic = human_rec.get('economic_impact', {})

            rec_text = f"""RECOMENDACIÓN DEL SISTEMA:

🎯 {main_msg.get('title', 'N/A')}
   Situación: {main_msg.get('situation', 'N/A')}

💰 IMPACTO ECONÓMICO:
   • Costo actual por kg: {economic.get('current_cost_per_kg', 0):.2f} €
   • Eficiencia producción: {economic.get('production_efficiency', 'N/A')}
   • Categoría costo: {economic.get('cost_category', 'N/A')}

⏰ PRÓXIMA VENTANA ÓPTIMA:
   • Inicio: {next_window.get('next_optimal_start', 'N/A')[:16] if next_window.get('next_optimal_start') else 'N/A'}
   • Beneficio estimado: {next_window.get('estimated_benefit', 'N/A')}
   • Horas hasta óptima: {next_window.get('hours_until_optimal', 0):.1f}h"""

            # Añadir acciones prioritarias si existen
            actions = main_msg.get('priority_actions', [])
            if actions:
                rec_text += f"\n\n🔧 ACCIONES PRIORITARIAS:\n"
                for action in actions[:3]:  # Máximo 3 acciones
                    rec_text += f"   • {action}\n"

            return rec_text

    async def _get_production_context(self) -> str:
        """Contexto de procesos de producción de chocolate."""
        return """PROCESOS DE PRODUCCIÓN - Chocolate Factory:

🏭 PROCESOS PRINCIPALES (4 etapas):
   1. 🌰 Molienda de cacao: Trituración granos, 2-3h, 150 kWh
   2. 🔥 Conchado Premium: Refinado pasta, 6-8h, 350 kWh (MÁS INTENSIVO)
   3. 🌡️ Temperado fino: Control cristalización, 1-2h, 80 kWh
   4. 📦 Moldeado de barras: Formado final, 1h, 50 kWh

💡 OPTIMIZACIÓN CLAVE:
   • Conchado Premium = 60% del consumo energético total
   • Programar conchado en horas valle (P3 madrugada) = ahorro 40-50%
   • Temperatura óptima chocolate: 18-22°C
   • Batch típico: 200 kg, ~630 kWh total

⚡ CONSUMO POR PERIODO:
   • P1 (Punta 10-13h, 18-21h): EVITAR conchado
   • P2 (Llano): Operación moderada
   • P3 (Valle 00-07h): PRIORIZAR conchado intensivo"""

    async def _get_full_dashboard(self) -> str:
        """Dashboard completo (fallback) - TODOS los datos disponibles."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            # Extraer SIAR analysis
            siar = data.get('siar_analysis', {}).get('seasonal_patterns', {})
            best_month = siar.get('best_month', {}).get('name', 'N/A')
            worst_month = siar.get('worst_month', {}).get('name', 'N/A')

            # Current info
            current = data.get('current_info', {})

            dashboard_text = f"""RESUMEN COMPLETO SISTEMA:

📊 ESTADO ACTUAL:
• Precio: {current.get('energy', {}).get('price_eur_kwh', 'N/A')} €/kWh
• Temperatura: {current.get('weather', {}).get('temperature', 'N/A')}°C
• Eficiencia: {current.get('factory_efficiency', 'N/A')}%

📅 ANÁLISIS HISTÓRICO (25 años SIAR):
• Mejor mes producción: {best_month}
• Peor mes producción: {worst_month}
• Total registros: 88,935

💡 PRÓXIMAS ACCIONES:
Consulta endpoints específicos para:
- Ventanas óptimas: /insights/optimal-windows
- Forecast Prophet: /predict/prices/*
- Plan producción: /optimize/production/daily"""

            return dashboard_text
