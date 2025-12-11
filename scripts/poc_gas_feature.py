#!/usr/bin/env python3
"""
POC: Test ESIOS Combined Cycle (Gas) Generation as Prophet Feature
===================================================================

RESULTADO DE INVESTIGACIÓN:
- Endpoint funcional: apidatos.ree.es/es/datos/generacion/estructura-generacion
- Parámetro clave: time_trunc=day (NO hour)
- No requiere autenticación
- Datos disponibles desde 2022

Objetivo:
1. Verificar acceso a datos de "Ciclo combinado"  
2. Descargar 36 meses de histórico
3. Analizar correlación con precios

Uso:
    python3 scripts/poc_gas_feature.py

Author: Gemini
Date: December 2025
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, date
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURACIÓN - ENDPOINT VERIFICADO
# ==============================================================================
REE_BASE_URL = "https://apidatos.ree.es/es/datos"
GENERATION_ENDPOINT = "generacion/estructura-generacion"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ChocolateFactory/0.41.0"
}

# ==============================================================================
# FUNCIONES
# ==============================================================================
def fetch_generation_data(start_date: date, end_date: date) -> list:
    """
    Fetch generation data from REE API.
    
    Returns list of daily Ciclo Combinado values.
    """
    url = (
        f"{REE_BASE_URL}/{GENERATION_ENDPOINT}"
        f"?start_date={start_date}T00:00"
        f"&end_date={end_date}T23:59"
        f"&time_trunc=day"  # IMPORTANTE: day funciona, hour NO
    )
    
    req = urllib.request.Request(url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.getcode() == 200:
                data = json.loads(response.read())
                included = data.get("included", [])
                
                # Find Ciclo Combinado
                for item in included:
                    if "combinado" in item.get("type", "").lower():
                        values = item.get("attributes", {}).get("values", [])
                        return [{
                            "datetime": v["datetime"],
                            "value_mwh": v["value"],
                            "percentage": v.get("percentage", 0)
                        } for v in values]
                        
                return []
    except Exception as e:
        logger.error(f"Error fetching {start_date} to {end_date}: {e}")
        return []

def main():
    logger.info("=" * 60)
    logger.info("POC: Ciclo Combinado (Gas) como Feature para Prophet")
    logger.info("=" * 60)
    
    # ------------------------------------------------------------------
    # PASO 1: Verificar acceso a datos recientes
    # ------------------------------------------------------------------
    logger.info("\n📊 PASO 1: Verificar acceso a datos recientes")
    
    today = date.today()
    recent_data = fetch_generation_data(today - timedelta(days=7), today)
    
    if not recent_data:
        logger.error("❌ No se pudo obtener datos recientes")
        return 1
    
    logger.info(f"✅ Datos últimos 7 días: {len(recent_data)} registros")
    for r in recent_data[:3]:
        logger.info(f"   {r['datetime'][:10]}: {r['value_mwh']:,.0f} MWh ({r['percentage']*100:.1f}%)")
    
    # ------------------------------------------------------------------
    # PASO 2: Verificar acceso a histórico (36 meses)
    # ------------------------------------------------------------------
    logger.info("\n📊 PASO 2: Verificar acceso a histórico (muestra)")
    
    # Test: Diciembre 2022 (hace ~3 años)
    old_start = date(2022, 12, 1)
    old_end = date(2022, 12, 31)
    historic_data = fetch_generation_data(old_start, old_end)
    
    if not historic_data:
        logger.warning("⚠️ No hay datos de Dic 2022")
    else:
        logger.info(f"✅ Datos Dic 2022: {len(historic_data)} registros")
        avg_mwh = sum(d["value_mwh"] for d in historic_data) / len(historic_data)
        logger.info(f"   Promedio diario: {avg_mwh:,.0f} MWh")
    
    # ------------------------------------------------------------------
    # PASO 3: Estadísticas resumen
    # ------------------------------------------------------------------
    logger.info("\n📊 PASO 3: Estadísticas")
    
    if recent_data:
        values = [d["value_mwh"] for d in recent_data]
        logger.info(f"   Última semana:")
        logger.info(f"   - Promedio: {sum(values)/len(values):,.0f} MWh/día")
        logger.info(f"   - Mínimo:   {min(values):,.0f} MWh/día")
        logger.info(f"   - Máximo:   {max(values):,.0f} MWh/día")
    
    # ------------------------------------------------------------------
    # CONCLUSIÓN
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("✅ POC COMPLETADO: DATOS DISPONIBLES")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Próximos pasos para integrar en Prophet:")
    logger.info("1. Descargar 36 meses de datos diarios")
    logger.info("2. Resamplear a valores horarios (interpolar o repetir)")
    logger.info("3. Calcular correlación con precios PVPC")
    logger.info("4. Si r > 0.3, añadir como regressor:")
    logger.info("   model.add_regressor('gas_gen_mwh')")
    logger.info("")
    
    return 0

if __name__ == "__main__":
    exit(main())
