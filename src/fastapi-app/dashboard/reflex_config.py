"""
Configuración de Reflex para TFM Chocolate Factory Dashboard
"""

import reflex as rx

config = rx.Config(
    app_name="chocolate_factory_dashboard",
    frontend_port=3001,  # Puerto diferente para desarrollo
    backend_port=8001,   # Puerto diferente para desarrollo  
    env=rx.Env.DEV,
    tailwind={
        "theme": {
            "extend": {
                "colors": {
                    "chocolate": {
                        "50": "#fdf8f6",
                        "100": "#f2e8e5", 
                        "200": "#eaddd7",
                        "300": "#e0cec7",
                        "400": "#d2bab0",
                        "500": "#bfa094",
                        "600": "#a18072",
                        "700": "#977669",
                        "800": "#846358",
                        "900": "#43302b",
                    },
                    "energy": {
                        "low": "#22c55e",
                        "medium": "#eab308", 
                        "high": "#ef4444"
                    }
                }
            }
        }
    }
)