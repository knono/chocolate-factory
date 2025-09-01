"""
Dashboard principal con Reflex
"""

import reflex as rx
from .state import DashboardState
from .components import (
    metric_card, 
    production_status_card, 
    connection_status_banner,
    alerts_panel,
    simple_line_chart
)


def header() -> rx.Component:
    """Header del dashboard"""
    return rx.hstack(
        rx.hstack(
            rx.text("🍫", font_size="3em"),
            rx.vstack(
                rx.text("TFM Chocolate Factory", font_size="2xl", font_weight="bold"),
                rx.text("Dashboard de Monitoreo en Tiempo Real", font_size="md", color="gray.500"),
                spacing="1",
                align_items="flex-start"
            ),
            spacing="4"
        ),
        rx.button(
            rx.icon("refresh_cw"),
            rx.text("Actualizar"),
            on_click=DashboardState.load_dashboard_data,
            color_scheme="blue",
            size="sm"
        ),
        justify="space-between",
        align_items="center",
        width="100%",
        padding="4",
        background="white",
        border_bottom="1px solid #e2e8f0",
        position="sticky",
        top="0",
        z_index="10"
    )


def metrics_section() -> rx.Component:
    """Sección de métricas principales"""
    return rx.grid(
        metric_card(
            title="Precio Energía", 
            value=DashboardState.current_energy_price.to(str) + " €/kWh",
            icon="⚡",
            color=DashboardState.get_price_color(),
            description=DashboardState.price_trend.to(str).replace("rising", "📈 Subiendo").replace("falling", "📉 Bajando").replace("stable", "➡️ Estable")
        ),
        metric_card(
            title="Temperatura",
            value=DashboardState.current_temperature.to(str) + "°C", 
            icon="🌡️",
            color="blue",
            description=DashboardState.get_temp_status()
        ),
        metric_card(
            title="Humedad",
            value=DashboardState.current_humidity.to(str) + "%",
            icon="💧", 
            color="cyan",
            description=DashboardState.get_humidity_status()
        ),
        production_status_card(
            recommendation=DashboardState.production_recommendation,
            confidence=DashboardState.production_confidence,
            energy_score=DashboardState.energy_optimization_score
        ),
        columns=rx.breakpoints(base="1", sm="2", lg="4"),
        spacing="4",
        width="100%"
    )


def charts_section() -> rx.Component:
    """Sección de gráficas"""
    return rx.grid(
        simple_line_chart(
            data=DashboardState.price_history,
            title="📈 Precios Energía (24h)"
        ),
        simple_line_chart(
            data=DashboardState.temp_history, 
            title="🌡️ Temperatura (24h)"
        ),
        columns=rx.breakpoints(base="1", lg="2"),
        spacing="4",
        width="100%"
    )


def alerts_section() -> rx.Component:
    """Sección de alertas"""
    return alerts_panel(DashboardState.alerts)


def footer() -> rx.Component:
    """Footer del dashboard"""
    return rx.center(
        rx.text(
            f"TFM Chocolate Factory Dashboard | Última actualización: {DashboardState.last_update}",
            font_size="xs",
            color="gray.400"
        ),
        width="100%",
        padding="4",
        background="gray.50",
        border_top="1px solid #e2e8f0"
    )


@rx.page(route="/", title="Chocolate Factory Dashboard")
def index() -> rx.Component:
    """Página principal del dashboard"""
    return rx.vstack(
        header(),
        connection_status_banner(
            is_connected=DashboardState.is_connected,
            last_update=DashboardState.last_update,
            error_message=DashboardState.error_message
        ),
        rx.container(
            rx.vstack(
                metrics_section(),
                charts_section(),
                alerts_section(),
                spacing="6",
                width="100%"
            ),
            max_width="1200px",
            padding="6"
        ),
        footer(),
        spacing="0",
        width="100%",
        min_height="100vh",
        background="gray.50"
    )


# App principal
app = rx.App(
    state=DashboardState,
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    theme=rx.theme(
        appearance="light",
        accent_color="brown",
        font_family="Inter"
    )
)

# Hook para cargar datos al inicializar
app.add_page(
    index,
    on_load=DashboardState.load_dashboard_data
)