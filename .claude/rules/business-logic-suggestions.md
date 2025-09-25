# Lógica de Negocio para Sugerencias del Sistema - Chocolate Factory

## Principios Fundamentales

### 🏭 **NUNCA SUGERIR PARAR PRODUCCIÓN COMPLETA**
- **Realidad**: Somos una fábrica de chocolate, vivimos de producir.
- **Alternativas**: Reducir, optimizar, ajustar — nunca detener.
- **Excepción única**: Emergencia de seguridad alimentaria (no por costos).

### 💰 **Thresholds Realistas de Precios Energéticos**
Basados en el contexto real español y la estructura de costos:

- **€0.05–0.15/kWh**: Precio **EXCELENTE** (aprovechar al máximo)
- **€0.15–0.25/kWh**: Precio **NORMAL** (producción estándar)
- **€0.25–0.35/kWh**: Precio **ALTO** (reducir procesos no críticos)
- **€0.35–0.50/kWh**: Precio **MUY ALTO** (solo lotes críticos)
- **>€0.50/kWh**: Precio **EXTREMO** (evaluar pausa temporal de conchado)

### 🌡️ **Condiciones Ambientales Realistas**
Basadas en el clima de Linares, Jaén:

#### Temperatura
- **15–25°C**: ÓPTIMA — Maximizar producción  
- **25–30°C**: BUENA — Activar refrigeración, producción normal  
- **30–38°C**: ALTA — Aumentar refrigeración, monitorear calidad  
- **38–42°C**: MUY ALTA — Solo lotes prioritarios + refrigeración máxima  
- **>42°C**: CRÍTICA — Evaluar operaciones según equipos  

#### Humedad
- **45–65%**: ÓPTIMA — Condiciones ideales  
- **65–75%**: ALTA — Activar deshumidificación  
- **75–85%**: MUY ALTA — Deshumidificación + monitoreo bloom  
- **>85%**: CRÍTICA — Procesos mínimos hasta control  

---

## Matriz de Decisiones Operacionales

### 🎯 **Niveles de Recomendación**

#### 1. **MAXIMIZAR PRODUCCIÓN** (Score: 80–100)
- **Condiciones**: Precio <€0.18/kWh + Temp 15–28°C + Hum 45–70%  
- **Acciones**:
  - Incrementar al 120% capacidad si posible  
  - Priorizar calidad premium (conchado 12h)  
  - Extender turnos  
  - Generar stock para períodos caros  

#### 2. **PRODUCCIÓN ESTÁNDAR** (Score: 60–79)
- **Condiciones**: Precio <€0.28/kWh + Condiciones aceptables  
- **Acciones**:
  - Mantener plan de producción normal  
  - Mix 70% estándar / 30% premium  
  - Horarios regulares  
  - Monitoreo rutinario  

#### 3. **PRODUCCIÓN REDUCIDA** (Score: 40–59)
- **Condiciones**: Precio €0.28–0.40/kWh **o** condiciones subóptimas  
- **Acciones**:
  - Reducir al 70% capacidad  
  - Priorizar calidad estándar (conchado 6h)  
  - Solo lotes de alta rotación  
  - Aplazar procesos no urgentes  

#### 4. **PRODUCCIÓN MÍNIMA** (Score: 20–39)
- **Condiciones**: Precio >€0.40/kWh **o** condiciones difíciles  
- **Acciones**:
  - Reducir al 40% capacidad  
  - Solo pedidos comprometidos  
  - Diferir conchado a horas valle  
  - Activar protocolos de ahorro  

#### 5. **OPERACIONES CRÍTICAS** (Score: <20)
- **Condiciones**: Crisis energética **o** emergencia ambiental  
- **Acciones**:
  - Solo completar lotes en proceso  
  - Activar plan de contingencia  
  - Mantener equipos en standby  
  - **NO PARAR** — evaluar cada 2 horas  

---

## Reglas de Negocio Específicas

### ⚡ **Gestión Energética Inteligente**

#### Por Horarios (España)
- **Valle (00:00–06:00)**: Aprovechar para conchado intensivo  
- **Pico AM (10:00–14:00)**: Procesos de mezcla y rolado  
- **Pico PM (19:00–22:00)**: Templado y moldeado  
- **Llano (resto)**: Producción estándar  

#### Por Días
- **Lunes–Jueves**: Producción normal según matriz  
- **Viernes**: Priorizar volumen (demanda weekend)  
- **Sábado**: Solo turno mañana, lotes rápidos  
- **Domingo**: Mantenimiento (sin producción programada)  

### 🎯 **Optimización de Calidades**

#### Precio <€0.20/kWh
- **70% Premium** (conchado 12h) — Maximizar margen  
- **30% Estándar** (conchado 6h) — Cubrir volumen base  

#### Precio €0.20–0.30/kWh
- **30% Premium** — Solo pedidos confirmados  
- **70% Estándar** — Volumen principal  

#### Precio >€0.30/kWh
- **10% Premium** — Solo clientes premium  
- **90% Estándar** — Foco en eficiencia  

### 🌡️ **Adaptación por Condiciones Ambientales**

#### Temperatura Alta (>30°C)
1. Incrementar refrigeración (costo adicional €0.05/kg)  
2. Reducir tiempo de templado 15%  
3. Monitoreo calidad cada batch  
4. **Continuar produciendo** con ajustes  

#### Humedad Alta (>75%)
1. Activar deshumidificación  
2. Aumentar tiempo de templado 10%  
3. Control de bloom cada 30 min  
4. **Ajustar procesos, no parar**  

---

## Mensajes para Operadores

### 📱 **Formato de Sugerencia Mejorado**