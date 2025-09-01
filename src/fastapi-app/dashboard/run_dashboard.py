#!/usr/bin/env python3
"""
Script para ejecutar el Dashboard Reflex independientemente
"""

import sys
import os

# Agregar el directorio parent al path para importar servicios
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar y ejecutar la app Reflex
from dashboard.main import app

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=3001,  # Puerto diferente para no conflictuar con FastAPI
        reload=True
    )