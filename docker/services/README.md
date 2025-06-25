# Estructura de Servicios - Docker Bind Mounts

Esta carpeta contiene los datos persistentes de cada servicio, mapeados directamente desde los contenedores para acceso en tiempo real.

## Estructura de Directorios

```
docker/services/
├── fastapi/
│   └── logs/              # Logs de la aplicación FastAPI
├── influxdb/
│   ├── data/              # Base de datos InfluxDB (series temporales)
│   └── config/            # Configuración de InfluxDB
├── postgres/
│   └── data/              # Base de datos PostgreSQL (MLflow metadata)
├── mlflow/
│   └── artifacts/         # Artefactos y modelos ML
└── nodered/
    ├── data/              # Datos persistentes de Node-RED
    ├── flows.json         # Flujos de Node-RED (configuración)
    └── settings.js        # Configuración de Node-RED
```

## Beneficios de esta Estructura

- **Acceso directo** a los datos sin entrar en contenedores
- **Backups fáciles** de carpetas específicas
- **Monitoreo en tiempo real** del estado de cada servicio
- **Debugging** más sencillo al poder inspeccionar logs y datos
- **Migración** simple entre entornos

## Notas de Seguridad

- Los directorios se crean automáticamente al levantar los contenedores
- Asegúrate de hacer backup de estas carpetas antes de operaciones críticas
- Los permisos se gestionan automáticamente por Docker