"""
Componentes reutilizables del Dashboard Reflex
"""

import reflex as rx
from typing import List, Dict, Any


def metric_card(
    title: str,
    value: str,
    icon: str,
    color: str = "blue",
    description: str = "",
) -> rx.Component:
    """Tarjeta de métrica con valor, icono y descripción"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(icon, font_size="2em"),
                rx.vstack(
                    rx.text(title, font_size="sm", color="gray.500"),
                    rx.text(value, font_size="2xl", font_weight="bold", color=f"{color}.500"),
                    spacing="1",
                    align_items="flex-start"
                ),
                justify="space-between",
                width="100%"
            ),
            rx.cond(
                description != "",
                rx.text(description, font_size="xs", color="gray.400"),
                rx.box()
            ),
            spacing="3",
            align_items="flex-start"
        ),
        width="100%",
        height="120px",
        padding="4",
    )


def alert_badge(alert: Dict[str, Any]) -> rx.Component:
    """Badge de alerta con nivel de criticidad"""
    level_colors = {
        "info": "blue",
        "warning": "yellow", 
        "high": "orange",
        "critical": "red"
    }
    
    color = level_colors.get(alert.get("level", "info"), "blue")
    
    return rx.badge(
        rx.hstack(
            rx.text("⚠️" if alert.get("level") == "warning" else 
                   "🚨" if alert.get("level") == "critical" else 
                   "🔴" if alert.get("level") == "high" else "ℹ️",
                   font_size="sm"),
            rx.text(alert.get("message", ""), font_size="sm"),
            spacing="2"
        ),
        color_scheme=color,
        variant="subtle",
        padding="2",
        border_radius="md",
        width="100%"
    )


def production_status_card(
    recommendation: str,
    confidence: float,
    energy_score: float
) -> rx.Component:
    """Tarjeta de estado de producción con recomendaciones ML"""
    
    # Iconos según recomendación
    icons = {
        "Optimal": "🚀",
        "Moderate": "⚖️",
        "Reduced": "📉", 
        "Halt": "⛔"
    }
    
    # Colores según recomendación
    colors = {
        "Optimal": "green",
        "Moderate": "blue",
        "Reduced": "yellow",
        "Halt": "red"
    }
    
    icon = icons.get(recommendation, "❓")
    color = colors.get(recommendation, "gray")
    
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(icon, font_size="3em"),
                rx.vstack(
                    rx.text("Estado de Producción", font_size="sm", color="gray.500"),
                    rx.text(recommendation, font_size="xl", font_weight="bold", color=f"{color}.500"),
                    rx.text(f"Confianza: {confidence:.1f}%", font_size="sm", color="gray.400"),
                    spacing="1",
                    align_items="flex-start"
                ),
                justify="space-between",
                width="100%"
            ),
            rx.divider(),
            rx.hstack(
                rx.text("🔋 Energía:", font_size="sm", color="gray.500"),
                rx.progress(
                    value=energy_score,
                    color_scheme="green" if energy_score > 70 else "yellow" if energy_score > 40 else "red",
                    width="60%"
                ),
                rx.text(f"{energy_score:.0f}%", font_size="sm", font_weight="bold"),
                justify="space-between",
                width="100%"
            ),
            spacing="4",
            align_items="flex-start"
        ),
        width="100%",
        height="160px", 
        padding="4",
    )


def connection_status_banner(
    is_connected: bool,
    last_update: str,
    error_message: str = ""
) -> rx.Component:
    """Banner de estado de conexión en la parte superior"""
    if is_connected:
        return rx.alert(
            rx.alert_icon(),
            rx.alert_title("✅ Sistema Operativo"),
            rx.alert_description(f"Última actualización: {last_update}"),
            status="success",
            variant="subtle",
            width="100%"
        )
    else:
        return rx.alert(
            rx.alert_icon(),
            rx.alert_title("❌ Sin Conexión"),
            rx.alert_description(f"Error: {error_message}"),
            status="error",
            variant="subtle",
            width="100%"
        )


def alerts_panel(alerts: List[Dict[str, Any]]) -> rx.Component:
    """Panel de alertas del sistema"""
    if not alerts:
        return rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text("🔕", font_size="2em"),
                    rx.vstack(
                        rx.text("Alertas del Sistema", font_size="lg", font_weight="bold"),
                        rx.text("No hay alertas activas", font_size="sm", color="gray.500"),
                        spacing="1",
                        align_items="flex-start"
                    ),
                    spacing="4"
                ),
                spacing="2",
                align_items="flex-start"
            ),
            width="100%",
            padding="4"
        )
    
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text("🔔", font_size="2em"),
                rx.vstack(
                    rx.text("Alertas del Sistema", font_size="lg", font_weight="bold"),
                    rx.text(f"{len(alerts)} alerta(s) activa(s)", font_size="sm", color="red.500"),
                    spacing="1",
                    align_items="flex-start"
                ),
                spacing="4"
            ),
            rx.divider(),
            rx.vstack(
                *[alert_badge(alert) for alert in alerts[:5]],  # Máximo 5 alertas
                spacing="2",
                width="100%"
            ),
            spacing="3",
            align_items="flex-start"
        ),
        width="100%",
        padding="4"
    )


def simple_line_chart(data: List[Dict[str, Any]], title: str) -> rx.Component:
    """Gráfica de líneas simple para tendencias"""
    if not data:
        return rx.card(
            rx.center(
                rx.vstack(
                    rx.text(title, font_size="lg", font_weight="bold"),
                    rx.text("📊 Cargando datos...", color="gray.500"),
                    spacing="2"
                )
            ),
            width="100%",
            height="200px"
        )
    
    # Por simplicidad, mostrar últimos 6 puntos como texto
    recent_points = data[-6:] if len(data) >= 6 else data
    
    return rx.card(
        rx.vstack(
            rx.text(title, font_size="lg", font_weight="bold"),
            rx.divider(),
            rx.vstack(
                *[
                    rx.hstack(
                        rx.text(point.get("time", "")[-8:-3], font_size="xs", color="gray.400"),  # HH:MM
                        rx.text(f"{point.get('price', point.get('temperature', 0)):.3f}", 
                               font_size="sm", font_weight="bold"),
                        justify="space-between",
                        width="100%"
                    )
                    for point in recent_points
                ],
                spacing="1",
                width="100%"
            ),
            spacing="2",
            align_items="flex-start"
        ),
        width="100%",
        height="200px",
        padding="4"
    )