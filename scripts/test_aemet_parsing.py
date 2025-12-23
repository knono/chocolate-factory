
import asyncio
import sys
import os
from datetime import datetime, timezone
from loguru import logger

# Añadir el path del código fuente para poder importar los módulos
sys.path.append(os.path.join(os.getcwd(), "src/fastapi-app"))

from infrastructure.external_apis.aemet_client import AEMETAPIClient

async def test_aemet_parsing():
    """
    Script para probar el parseo de la predicción de AEMET sin necesidad de 
    reconstruir todo el entorno.
    """
    logger.info("🚀 Iniciando prueba de parseo de AEMET...")
    
    try:
        async with AEMETAPIClient() as client:
            # Probar el método de predicción horaria por municipio (Linares: 23055)
            logger.info("📡 Obteniendo predicción horaria de AEMET...")
            forecast_data = await client.get_hourly_forecast_municipality("23055")
            
            if not forecast_data:
                logger.error("❌ No se recibieron datos de predicción.")
                return

            logger.success(f"✅ Se recibieron {len(forecast_data)} registros de predicción.")
            
            # Mostrar los primeros 3 registros para verificar formato
            for i, record in enumerate(forecast_data[:3]):
                logger.info(f"📝 Registro {i+1}:")
                logger.info(f"   ⏰ Timestamp: {record['timestamp']}")
                logger.info(f"   🌡️ Temperatura: {record['temperature']}°C")
                logger.info(f"   💧 Humedad: {record['humidity']}%")
                logger.info(f"   🌬️ Viento: {record['wind_speed']} km/h ({record['wind_direction_text']})")
                logger.info(f"   📡 Fuente: {record['source']} ({record['data_type']})")

    except Exception as e:
        logger.exception(f"❌ Error durante la prueba: {e}")

if __name__ == "__main__":
    asyncio.run(test_aemet_parsing())
