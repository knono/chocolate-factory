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
                "lanzar producción", "lanzar", "próximas horas", "horario"
            ],
            "price_forecast": ["precio", "precios", "energía", "energia", "costo", "coste", "tarifa", "kwh"],
            "alerts": ["alerta", "alertas", "problema", "problemas", "warning", "crítico", "critico"],
            "savings": ["ahorro", "ahorros", "saving", "comparar", "comparativa", "roi", "beneficio"],
            "production_plan": ["plan", "planificar", "optimizar", "optimización", "batches", "proceso"],
            "analysis": ["análisis", "analisis", "histórico", "historico", "siar", "temperatura", "clima"],
            "current_status": ["actual", "ahora", "estado", "status", "qué está pasando", "que esta pasando"],
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

        # Añadir contextos específicos según categorías detectadas
        if "optimal_windows" in relevant_categories:
            tasks.append(self._get_optimal_windows())
            task_names.append("optimal_windows")

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

            context = f"""ESTADO ACTUAL CHOCOLATE FACTORY
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Precio energía actual: {price} €/kWh
Tendencia precio: {energy.get('trend', 'N/A')}
Temperatura: {temp}°C
Humedad: {humidity}%
Presión: {pressure} hPa
Confort: {comfort}
Estado producción: {prod_status}
Eficiencia fábrica: {efficiency}%"""

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
            response = await client.get(f"{self.base_url}/analysis/siar-summary")
            data = response.json()

            analysis_text = f"""ANÁLISIS HISTÓRICO (25 años SIAR):
Mejor mes: {data.get('best_month', 'N/A')} ({data.get('best_month_efficiency', 0):.1f}% eficiencia)
Peor mes: {data.get('worst_month', 'N/A')} ({data.get('worst_month_efficiency', 0):.1f}% eficiencia)
Temperatura crítica P90: {data.get('temp_p90', 'N/A')}°C
Temperatura crítica P95: {data.get('temp_p95', 'N/A')}°C"""

            return analysis_text

    async def _get_full_dashboard(self) -> str:
        """Dashboard completo (fallback)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/dashboard/complete")
            data = response.json()

            # Extraer info más relevante del dashboard
            dashboard_text = f"""DASHBOARD COMPLETO:
Estado sistema: {data.get('system', {}).get('status', 'N/A')}
Precio actual: {data.get('energy', {}).get('current_price', 'N/A')} €/kWh
Temperatura: {data.get('weather', {}).get('temperature', 'N/A')}°C
Próximas 24h: Ver forecast de precios
Recomendación ML: {data.get('ml_recommendation', {}).get('action', 'N/A')}"""

            return dashboard_text
