# REGLA: Solución ETL para Datos Históricos SIAR

## CUÁNDO APLICAR ESTA REGLA

Esta regla se aplica cuando:
- Se necesitan datos históricos meteorológicos para entrenamiento ML
- Los archivos CSV del sistema SIAR están disponibles en `/data/históricoClimaLinares/`
- Se requiere procesar datos históricos de 25+ años (2000-2025)
- Los datos actuales de AEMET/OpenWeatherMap son insuficientes para ML training

## CONTEXTO TÉCNICO

### Fuente de Datos: Sistema SIAR
- **Sistema**: Sistema de Información Agroclimática para el Regadío
- **URL oficial**: https://servicio.mapa.gob.es/websiar/SeleccionParametrosMap.aspx?dst=1
- **Formato**: CSV con separadores semicolon (;) y decimales con coma (,)
- **Ubicación**: Linares (Jaén), España
- **Cobertura**: 26 archivos CSV (2000-2025)

### Arquitectura de Datos
```
📊 Buckets InfluxDB:
├── energy_data (datos actuales)
│   ├── REE + Weather streaming
└── siar_historical (datos históricos)
    ├── SIAR_J09_Linares (2000-2017)
    └── SIAR_J17_Linares (2018-2025)
```

## PROBLEMAS TÉCNICOS CONOCIDOS Y SOLUCIONES

### 1. UNICODE Y ESPACIOS ESPECIALES
**Problema**: CSV contienen espacios Unicode invisibles que rompen parsing
```
❌ Original: ' 2 8 / 1 2 / 2 0 0 9 ' (21 caracteres)
✅ Esperado: '28/12/2009' (10 caracteres)
```

**Solución Obligatoria**: Limpieza carácter por carácter
```python
def clean_line(line):
    clean_chars = []
    for char in line:
        if char.isprintable() and (char.isalnum() or char in ';,/:.-'):
            clean_chars.append(char)
    return ''.join(clean_chars)
```

### 2. FORMATO ESPAÑOL DE DATOS
**Desafíos**:
- Fechas: DD/MM/YYYY (formato español)
- Decimales: coma (,) en lugar de punto (.)
- Separadores CSV: semicolon (;) en lugar de coma

**Soluciones Obligatorias**:
```python
# Decimales españoles
def safe_float(value):
    return float(str(value).replace(',', '.'))

# Fechas españolas
date_obj = pd.to_datetime(fecha_str, format='%d/%m/%Y')

# Separadores CSV
parts = clean_line.split(';')
```

### 3. DETECCIÓN DE ESTACIONES
**Regla**: Detectar automáticamente tipo de estación por filename
```python
station_type = "J17" if "J17" in csv_file else "J09"
station_id = f"SIAR_{station_type}_Linares"
```

## IMPLEMENTACIÓN OBLIGATORIA

### Script de Referencia
**Ubicación**: `/scripts/test_siar_simple.py`
**Configuración Obligatoria**:
```python
INFLUX_URL = "http://chocolate_factory_storage:8086"
INFLUX_TOKEN = "<your_influxdb_token_here>"  # Ver regla security-sensitive-data.md
INFLUX_ORG = "chocolate_factory"
BUCKET_NAME = "siar_historical"  # Bucket dedicado separado
```

### Proceso ETL Obligatorio
1. **Detección de archivos**: `find /app/data -name '*.csv' -type 'f'`
2. **Detección de encoding**: Probar latin-1, iso-8859-1, cp1252, utf-8
3. **Limpieza Unicode**: Aplicar `clean_line()` obligatoriamente
4. **Parsing datos**: Usar formatos españoles
5. **Escritura por lotes**: 100 registros por batch a InfluxDB
6. **Tags obligatorios**: `data_source=siar_historical`, `station_id=SIAR_*`

### Ejecución
```bash
# Dentro del contenedor
docker exec chocolate_factory_brain python /app/scripts/test_siar_simple.py
```

## VERIFICACIÓN OBLIGATORIA

### Resultados Esperados
- **Total archivos**: 26 CSV procesados (100% éxito)
- **Total registros**: ~88,935 registros en InfluxDB
- **Estaciones**: SIAR_J09_Linares + SIAR_J17_Linares
- **Tiempo**: ~3 minutos para 25+ años de datos

### Comandos de Verificación
```bash
# Verificar carga por estación
docker exec chocolate_factory_storage influx query '
from(bucket: "siar_historical")
|> range(start: 2000-01-01T00:00:00Z, stop: 2025-12-31T23:59:59Z)
|> group(columns: ["station_id"])
|> count()'

# Verificar rango temporal
docker exec chocolate_factory_storage influx query '
from(bucket: "siar_historical")
|> range(start: 2000-01-01T00:00:00Z, stop: 2025-12-31T23:59:59Z)
|> first() |> yield(name: "first_record")
from(bucket: "siar_historical")
|> range(start: 2000-01-01T00:00:00Z, stop: 2025-12-31T23:59:59Z)
|> last() |> yield(name: "last_record")'
```

### Resultado Correcto Esperado
```
SIAR_J09_Linares: 62,842 records (2000-2017)
SIAR_J17_Linares: 26,093 records (2018-2025)
Total: 88,935 registros históricos
```

## ERRORES COMUNES Y SOLUCIONES

### Error: "unauthorized access"
**Causa**: Token InfluxDB incorrecto
**Solución**: Verificar token con `docker exec chocolate_factory_storage influx auth list`

### Error: "Failed to establish connection"
**Causa**: URL InfluxDB incorrecta desde contenedor
**Solución**: Usar `http://chocolate_factory_storage:8086` (NO localhost)

### Error: Parsing de fechas falla
**Causa**: Espacios Unicode no limpiados
**Solución**: Aplicar obligatoriamente función `clean_line()`

### Error: Archivo no encontrado
**Causa**: Bind mount no configurado
**Solución**: Verificar `./data:/app/data` en docker-compose.yml

## BENEFICIOS GARANTIZADOS

### Para ML Training
- **25+ años** de datos históricos meteorológicos
- **Datos oficiales** del gobierno español (SIAR)
- **Separación clara** entre histórico y tiempo real
- **Trazabilidad completa** con tags descriptivos

### Para Sistema
- **Bucket dedicado**: No contamina datos actuales
- **Rendimiento**: 3 minutos para 25 años
- **Robustez**: Maneja errores y continúa procesando
- **Persistencia**: Datos sobreviven reinicios del sistema

## INTEGRACIÓN CON ML

### Uso en Modelos
```python
# Para training con datos históricos
bucket = "siar_historical"
filter = 'r.data_source == "siar_historical"'

# Para predicción en tiempo real
bucket = "energy_data"
filter = 'r.data_source =~ /aemet|openweather/'
```

### Features Disponibles (10 campos)
1. `temperature` - Temperatura media
2. `temperature_max` - Temperatura máxima
3. `temperature_min` - Temperatura mínima
4. `humidity` - Humedad media
5. `humidity_max` - Humedad máxima
6. `humidity_min` - Humedad mínima
7. `wind_speed` - Velocidad del viento
8. `wind_direction` - Dirección del viento
9. `wind_gust` - Ráfaga máxima
10. `precipitation` - Precipitación

## REGLAS DE MANTENIMIENTO

### NO Hacer
- ❌ No usar el bucket `energy_data` para datos SIAR
- ❌ No usar localhost como URL InfluxDB desde contenedor
- ❌ No procesar archivos sin limpieza Unicode
- ❌ No usar formatos de fecha no españoles
- ❌ No copiar archivos al contenedor (usar bind mount)

### SÍ Hacer
- ✅ Usar bucket dedicado `siar_historical`
- ✅ Aplicar limpieza Unicode obligatoriamente
- ✅ Usar formatos españoles (DD/MM/YYYY, coma decimal)
- ✅ Verificar resultados con queries InfluxDB
- ✅ Separar claramente histórico de tiempo real

## CUANDO APLICAR ESTA REGLA

**Aplica cuando**:
- Usuario solicita datos históricos meteorológicos
- Se necesita entrenar modelos ML con más datos
- Los datos actuales son insuficientes (< 1000 registros)
- Se quiere añadir robustez al sistema ML

**No aplica cuando**:
- Solo se necesitan datos actuales
- El bucket `siar_historical` ya contiene 88,935 registros
- Se trabaja con datos de otras ubicaciones geográficas
- Se requieren datos meteorológicos en tiempo real

---

**ÚLTIMA ACTUALIZACIÓN**: Septiembre 2025 - Solución verificada y funcional
**ESTADO**: ✅ PROBADO Y FUNCIONANDO - 88,935 registros cargados exitosamente