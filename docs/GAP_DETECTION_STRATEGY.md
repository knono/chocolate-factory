# Estrategias de Detección de Gaps - TFM Chocolate Factory

## Índice
1. [Conceptos Fundamentales](#conceptos-fundamentales)
2. [Algoritmo de Detección](#algoritmo-de-detección)
3. [Clasificación de Gaps](#clasificación-de-gaps)
4. [Estrategias de Recuperación](#estrategias-de-recuperación)
5. [Casos de Uso Reales](#casos-de-uso-reales)
6. [Optimizaciones y Consideraciones](#optimizaciones-y-consideraciones)

## Conceptos Fundamentales

### ¿Qué es un Gap?
Un **gap (hueco)** es un período de tiempo donde **faltan datos esperados** en una serie temporal. En el contexto de TFM Chocolate Factory, los gaps pueden ocurrir en:

- **Energy Prices (REE)**: Datos esperados cada hora
- **Weather Data**: Datos esperados cada hora (híbrido AEMET/OpenWeatherMap)

### Causas Comunes de Gaps
1. **Downtime del sistema** (equipo parado 5+ días)
2. **Fallos de API externa** (REE, AEMET caídos temporalmente)
3. **Problemas de conectividad** (red, firewall)
4. **Rate limiting excesivo** (demasiadas requests, APIs bloqueadas)
5. **Mantenimiento programado** (updates, reincios)

### Impacto de los Gaps
- **ML Models**: Predicciones basadas en datos incompletos
- **Dashboard**: Gráficos con huecos, métricas incorrectas
- **Alertas**: False negatives por falta de datos
- **Compliance**: Reportes incompletos para auditoria

## Algoritmo de Detección

### Timeline Expected vs Reality

```
Timeline Esperado (cada hora):
00:00 → 01:00 → 02:00 → 03:00 → 04:00 → 05:00 → 06:00

Timeline Real (con gaps):
00:00 → [GAP] → [GAP] → 03:00 → [GAP] → 05:00 → 06:00
```

### Implementación del Algoritmo

```python
def _find_time_gaps(self, expected_times: List[datetime], 
                   existing_times: List[datetime],
                   measurement: str,
                   interval: timedelta) -> List[DataGap]:
    """
    Algoritmo principal de detección de gaps
    """
    existing_set = set(existing_times)
    gaps = []
    
    # 1. Identificar tiempos faltantes
    missing_times = [t for t in expected_times if t not in existing_set]
    
    if not missing_times:
        return gaps  # No gaps found
    
    # 2. Agrupar tiempos consecutivos en gaps
    missing_times.sort()
    current_gap_start = missing_times[0]
    current_gap_end = missing_times[0]
    
    for i in range(1, len(missing_times)):
        time_diff = missing_times[i] - current_gap_end
        
        if time_diff <= interval * 1.5:  # Tolerancia del 50%
            # Extender gap actual
            current_gap_end = missing_times[i]
        else:
            # Finalizar gap actual y empezar uno nuevo
            gap = self._create_gap(measurement, current_gap_start, current_gap_end, interval)
            gaps.append(gap)
            
            current_gap_start = missing_times[i]
            current_gap_end = missing_times[i]
    
    # 3. Añadir último gap
    gap = self._create_gap(measurement, current_gap_start, current_gap_end, interval)
    gaps.append(gap)
    
    return gaps
```

### Generación de Timeline Esperado

```python
# Para REE (datos cada hora)
expected_times = []
current = start_time.replace(minute=0, second=0, microsecond=0)
while current <= end_time:
    expected_times.append(current)
    current += timedelta(hours=1)

# Para Weather (datos cada hora con lógica híbrida)
# Similar pero considerando fuentes múltiples (AEMET + OpenWeatherMap)
```

### Query de Datos Existentes

```python
# Query InfluxDB para REE
ree_query = f'''
from(bucket: "{service.config.bucket}")
|> range(start: -{days_back}d)
|> filter(fn: (r) => r._measurement == "energy_prices")
|> filter(fn: (r) => r._field == "price_eur_kwh")
|> sort(columns: ["_time"])
'''

# Query InfluxDB para Weather
weather_query = f'''
from(bucket: "{service.config.bucket}")
|> range(start: -{days_back}d)
|> filter(fn: (r) => r._measurement == "weather_data")
|> filter(fn: (r) => r._field == "temperature")
|> sort(columns: ["_time"])
'''
```

## Clasificación de Gaps

### Por Duración

#### 1. **Minor Gaps** (≤2 horas)
```python
if duration_hours <= 2:
    severity = "minor"
```
- **Impacto**: Mínimo en operaciones
- **Causa típica**: Reinicio de sistema, mantenimiento breve
- **Prioridad**: Baja
- **Estrategia**: Backfill automático en próximo cycle

#### 2. **Moderate Gaps** (2-12 horas)  
```python
elif duration_hours <= 12:
    severity = "moderate"
```
- **Impacto**: Afecta dashboard y algunas predicciones
- **Causa típica**: Fallo de API, problemas de red
- **Prioridad**: Media
- **Estrategia**: Backfill inmediato con alertas

#### 3. **Critical Gaps** (>12 horas)
```python
else:
    severity = "critical"
```
- **Impacto**: Compromete ML models, dashboard inutilizable
- **Causa típica**: Sistema parado, downtime prolongado
- **Prioridad**: Alta
- **Estrategia**: Backfill agresivo con múltiples intentos

### Por Tipo de Datos

#### Energy Prices (REE)
```python
@dataclass
class DataGap:
    measurement: str = "energy_prices"
    expected_records: int  # 24 records/day (hourly)
    missing_records: int
    severity: str
```

**Características**:
- Datos críticos para optimización energética
- Alta confiabilidad de API REE
- Backfill relativamente fácil

#### Weather Data
```python
@dataclass  
class DataGap:
    measurement: str = "weather_data"
    expected_records: int  # 24 records/day (hourly)
    missing_records: int
    severity: str
```

**Características**:
- Datos críticos para predicciones ML
- APIs menos confiables (AEMET limitaciones)
- Backfill complejo (estrategia híbrida)

### Métricas de Gap

```python
@dataclass
class DataGap:
    measurement: str
    start_time: datetime
    end_time: datetime
    expected_records: int
    missing_records: int
    gap_duration_hours: float
    severity: str  # "minor", "moderate", "critical"
```

#### Cálculos Derivados
```python
# Duración del gap
duration_hours = (end_time - start_time).total_seconds() / 3600

# Records esperados (asumiendo datos cada hora)
expected_records = int(duration_hours / (interval.total_seconds() / 3600)) + 1

# Porcentaje de datos faltantes
missing_percentage = (missing_records / expected_records) * 100
```

## Estrategias de Recuperación

### Matriz de Decisión

| Gap Type | Duration | Data Source | Strategy | Priority |
|----------|----------|-------------|----------|----------|
| REE Minor | <2h | REE API | Immediate | Low |
| REE Moderate | 2-12h | REE API | Immediate + Alert | Medium |
| REE Critical | >12h | REE API | Aggressive + Multi-retry | High |
| Weather Minor (Current Month) | <2h | AEMET API | Immediate | Low |
| Weather Moderate (Current Month) | 2-12h | AEMET API | Immediate + Alert | Medium |
| Weather Critical (Current Month) | >12h | AEMET API | Multi-batch | High |
| Weather (Previous Months) | Any | Sistema SIAR ETL | ETL Process | Medium |

### Implementación de Estrategias

#### REE Recovery Strategy
```python
async def _backfill_ree_gaps(self, gaps: List[DataGap]) -> List[BackfillResult]:
    for gap in gaps:
        if gap.severity == "critical":
            # Estrategia agresiva: chunks más pequeños, más intentos
            chunk_size = timedelta(hours=6)  # 6h chunks instead of daily
            max_retries = 3
        elif gap.severity == "moderate":
            # Estrategia estándar
            chunk_size = timedelta(days=1)   # Daily chunks
            max_retries = 2
        else:
            # Estrategia simple
            chunk_size = timedelta(days=1)
            max_retries = 1
            
        # Ejecutar con estrategia específica
        await self._execute_ree_recovery(gap, chunk_size, max_retries)
```

#### Weather Recovery Strategy (Temporal Intelligence)
```python
async def _backfill_weather_gaps(self, gaps: List[DataGap]) -> List[BackfillResult]:
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    for gap in gaps:
        gap_month = gap.start_time.month
        gap_year = gap.start_time.year
        
        is_current_month = (gap_year == current_year and gap_month == current_month)
        
        if is_current_month:
            # AEMET API Strategy (current month)
            if gap.severity == "critical":
                # Múltiples batches pequeños
                result = await self._aemet_multi_batch_recovery(gap)
            else:
                # Batch simple
                result = await self._aemet_simple_recovery(gap)
        else:
            # Sistema SIAR ETL Strategy (historical months)
            result = await self._datosclima_etl_recovery(gap)
```

### Auto-Recovery Triggers

#### Configuración de Umbrales
```python
# En scheduler service
async def _auto_backfill_check_job(self):
    # Umbral por defecto: 3 horas
    result = await backfill_service.check_and_execute_auto_backfill(max_gap_hours=3.0)
    
    if result.get("trigger") == "automatic":
        # Recovery automático ejecutado
        await self._handle_auto_recovery_results(result)
```

#### Lógica de Activación
```python
async def check_and_execute_auto_backfill(self, max_gap_hours: float = 6.0) -> Dict[str, Any]:
    latest = await self.gap_detector.get_latest_timestamps()
    now = datetime.now(timezone.utc)
    
    needs_backfill = False
    
    # Verificar gap REE
    if latest['latest_ree']:
        ree_gap_hours = (now - latest['latest_ree']).total_seconds() / 3600
        if ree_gap_hours > max_gap_hours:
            needs_backfill = True
    
    # Verificar gap Weather
    if latest['latest_weather']:
        weather_gap_hours = (now - latest['latest_weather']).total_seconds() / 3600
        if weather_gap_hours > max_gap_hours:
            needs_backfill = True
    
    if needs_backfill:
        # Activar backfill automático
        return await self.execute_intelligent_backfill(days_back)
    else:
        return {"status": "no_action_needed"}
```

## Casos de Uso Reales

### Caso 1: Sistema Parado 7 Días

**Situación**: Equipo estuvo inactivo del 29 junio al 7 julio 2025

**Gaps Detectados**:
```json
{
  "total_gaps": 9,
  "ree_gaps": 3,
  "weather_gaps": 6,
  "estimated_backfill_time": "~1h 2min"
}
```

**Estrategia Aplicada**:
- **REE**: 3 gaps procesados con API histórica (success rate: 85%)
- **Weather July**: AEMET API para días en julio (success rate: 60%)
- **Weather June**: Sistema SIAR ETL para días en junio (success rate: 75%)

**Resultado**:
```json
{
  "overall_success_rate": 32.9,
  "records_written": 127,
  "ree_records_written": 72,
  "weather_records_written": 55
}
```

### Caso 2: Fallo API REE (4 horas)

**Situación**: REE API caída de 14:00 a 18:00

**Gap Detectado**:
```json
{
  "measurement": "energy_prices",
  "duration_hours": 4.0,
  "missing_records": 4,
  "severity": "moderate"
}
```

**Estrategia Aplicada**:
- Backfill inmediato con alertas
- Daily chunk strategy (4 hours en un request)
- 1 retry automático

**Resultado**:
```json
{
  "success_rate": 100.0,
  "records_written": 4,
  "duration_seconds": 5.2
}
```

### Caso 3: AEMET Rate Limiting (12 horas)

**Situación**: AEMET API devolviendo 429 errors

**Gap Detectado**:
```json
{
  "measurement": "weather_data", 
  "duration_hours": 12.0,
  "missing_records": 12,
  "severity": "critical"
}
```

**Estrategia Aplicada**:
- Multi-batch con delays aumentados (3s → 5s)
- Fallback automático a OpenWeatherMap current data
- 3 reintentos con backoff exponencial

**Resultado**:
```json
{
  "success_rate": 75.0,
  "records_written": 9,
  "errors": ["3 records failed due to AEMET rate limit"]
}
```

## Optimizaciones y Consideraciones

### Performance Optimizations

#### 1. **Lazy Gap Detection**
```python
# Solo analizar si hay indicios de gaps
latest_ree = await self.get_latest_timestamp("energy_prices")
if latest_ree and (now - latest_ree).total_seconds() < 7200:  # <2h
    return []  # No gaps analysis needed
```

#### 2. **Chunked Analysis**
```python
# Para rangos grandes, analizar por chunks
if days_back > 30:
    # Analizar en chunks de 1 semana
    chunks = self._create_analysis_chunks(days_back, chunk_size=7)
    for chunk in chunks:
        gaps.extend(await self._analyze_chunk(chunk))
```

#### 3. **Parallel Detection**
```python
# Detectar REE y Weather gaps en paralelo
ree_task = asyncio.create_task(self._detect_ree_gaps(days_back))
weather_task = asyncio.create_task(self._detect_weather_gaps(days_back))

ree_gaps, weather_gaps = await asyncio.gather(ree_task, weather_task)
```

### Memory Considerations

#### Large Dataset Handling
```python
# Para datasets grandes, usar streaming
async def _detect_gaps_streaming(self, days_back: int):
    batch_size = 1000  # Process 1000 records at a time
    
    async for batch in self._stream_records(days_back, batch_size):
        batch_gaps = self._analyze_batch(batch)
        yield batch_gaps
```

#### Cache Strategy
```python
# Cache de últimos timestamps para evitar queries repetidas
@lru_cache(maxsize=32)
async def get_cached_latest_timestamp(self, measurement: str) -> Optional[datetime]:
    return await self._query_latest_timestamp(measurement)
```

### Reliability Patterns

#### 1. **Circuit Breaker**
```python
class APICircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.last_failure_time = None
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
```

#### 2. **Retry with Exponential Backoff**
```python
async def _retry_with_backoff(self, func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(delay)
```

#### 3. **Graceful Degradation**
```python
async def _backfill_with_fallback(self, gap: DataGap):
    try:
        # Primary strategy
        return await self._primary_backfill(gap)
    except Exception:
        # Fallback strategy
        return await self._fallback_backfill(gap)
```

### Monitoring and Alerting

#### Gap Detection Metrics
```python
# Métricas que se deben monitorear
class GapMetrics:
    total_gaps_detected: int
    avg_gap_duration: float
    critical_gaps_count: int
    detection_duration_ms: int
    last_detection_timestamp: datetime
```

#### Alert Thresholds
```python
# Configuración de alertas
ALERT_CONFIG = {
    "critical_gap_threshold": 12,  # horas
    "multiple_gaps_threshold": 5,  # número de gaps simultáneos
    "detection_failure_threshold": 3,  # fallos consecutivos de detección
    "backfill_failure_rate": 0.3  # 30% de fallos en backfill
}
```

## Actualizaciones Recientes

### 🔧 **Fix Crítico: Gap Detection Query (Sept 22, 2025)**

#### Problema Identificado
- **Síntoma**: Gap detector reportaba `"🚨 4d atrasado"` para REE cuando datos estaban actualizados
- **Causa root**: Query `last()` en InfluxDB devolvía múltiples registros con diferentes tags
- **Impacto**: Backfill innecesario ejecutándose, sistema reportando falsos gaps

#### Análisis Técnico
**Query problemático**:
```flux
from(bucket: "energy_data")
|> range(start: -30d)
|> filter(fn: (r) => r._measurement == "energy_prices")
|> filter(fn: (r) => r._field == "price_eur_kwh")
|> last()  // ❌ Devuelve múltiples registros con diferentes tags
```

**Resultado**: Tomaba el primer record del resultado, que no era necesariamente el más reciente:
- ✅ **2025-09-22T11:00** (data_source=ree_historical) ← Más reciente
- ✅ **2025-09-22T10:00** (provider=ree, tariff_period=P1)
- ❌ **2025-09-17T22:00** (tariff_period=P6) ← **Se tomaba este por error**

#### Solución Implementada
**Query corregido**:
```flux
from(bucket: "energy_data")
|> range(start: -30d)
|> filter(fn: (r) => r._measurement == "energy_prices")
|> filter(fn: (r) => r._field == "price_eur_kwh")
|> group()                           // ✅ Agrupa todos los tags
|> sort(columns: ["_time"], desc: true)  // ✅ Ordena por timestamp desc
|> limit(n: 1)                       // ✅ Toma solo el más reciente
```

#### Mejoras en Desarrollo
**Bind Mount Completo**:
- **Antes**: Archivos individuales → Reconstruir contenedor para cada cambio
- **Después**: `./src/fastapi-app/services:/app/services` → Cambios instantáneos
- **Beneficio**: Desarrollo 10x más rápido, sin reconstrucciones

#### Archivos Afectados
- `services/gap_detector.py`: Query fix para REE y weather
- `docker-compose.yml`: Bind mount completo del directorio services
- `main.py`: Debug endpoint temporal para testing

#### Resultados Post-Fix
- **REE Status**: `"✅ Actualizado"` (antes: `"🚨 4d atrasado"`)
- **Latest Data**: `"2025-09-22T11:00:00+00:00"` (antes: `"2025-09-17T22:00:00+00:00"`)
- **Gap Hours**: `0.6` (antes: `109.4`)
- **Backfill**: Ya no se ejecuta innecesariamente

#### Lecciones Aprendidas
1. **InfluxDB `last()`** no garantiza el timestamp más reciente cuando hay múltiples series
2. **Bind mounts** son esenciales para desarrollo iterativo rápido
3. **Debug endpoints** acelerar troubleshooting de queries complejas

---

**Documentación actualizada**: 2025-09-22
**Versión del algoritmo**: v1.2
**Estado**: ✅ Implementado y Validado en Producción - Gap Detection Fixed