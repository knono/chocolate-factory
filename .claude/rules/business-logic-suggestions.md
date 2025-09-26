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

Los mensajes deben ser:
- **Claros y accionables**: Qué hacer específicamente
- **Contextorizados**: Por qué se recomienda esa acción
- **Humanos**: Lenguaje natural, no técnico
- **Urgentes cuando procede**: Indicar prioridad real

### 🎯 **Plantillas de Mensajes por Nivel**

#### MAXIMIZAR PRODUCCIÓN (Score: 80-100)
```
🟢 **MOMENTO ÓPTIMO PARA PRODUCCIÓN**

✨ **Situación**: [Descripción condiciones favorables]
🎯 **Recomendación**: Aprovechar esta ventana para maximizar producción
📈 **Acciones prioritarias**:
   • Incrementar volumen al máximo seguro
   • Priorizar lotes premium si calidad lo permite
   • Extender turnos para generar stock
   • Monitorear que se mantengan condiciones

⏱️ **Duración estimada**: [X horas] mientras condiciones favorables
💡 **Beneficio**: Ahorro estimado de €[X]/kg vs período normal
```

#### PRODUCCIÓN ESTÁNDAR (Score: 60-79)
```
🟡 **CONDICIONES NORMALES - PRODUCCIÓN ESTÁNDAR**

✅ **Situación**: [Descripción condiciones aceptables]
🎯 **Recomendación**: Mantener ritmo normal según planificación
📋 **Acciones sugeridas**:
   • Continuar con mix de productos planificado
   • Mantener horarios regulares
   • Estar atentos a cambios en condiciones
   • Optimizar procesos sin prisa

⏱️ **Revisión**: Reevaluar en 2-3 horas
💼 **Enfoque**: Equilibrio entre eficiencia y calidad
```

#### PRODUCCIÓN REDUCIDA (Score: 40-59)
```
🟠 **ATENCIÓN: CONDICIONES SUBÓPTIMAS**

⚠️ **Situación**: [Descripción de las limitaciones]
🎯 **Recomendación**: Reducir ritmo y priorizar lotes críticos
🔧 **Acciones recomendadas**:
   • Bajar a 70% capacidad normal
   • Solo lotes de alta prioridad/rotación
   • Diferir calidad premium para mejor momento
   • Monitorear calidad más frecuentemente

⏱️ **Estrategia**: Esperar mejores condiciones para intensificar
💡 **Beneficio**: Evitar costos extras y mantener calidad
```

#### PRODUCCIÓN MÍNIMA (Score: 20-39)
```
🔴 **CONDICIONES DIFÍCILES - PRODUCCIÓN MÍNIMA**

⚡ **Situación**: [Descripción condiciones adversas]
🎯 **Recomendación**: Solo completar compromisos urgentes
🚨 **Acciones necesarias**:
   • Reducir al 40% capacidad o menos
   • Solo pedidos ya comprometidos
   • Activar protocolos de ahorro energético
   • Programar procesos largos para horas valle

⏰ **Próxima ventana favorable**: [Fecha/hora estimada]
📊 **Seguimiento**: Revisar cada 2 horas para oportunidades
```

#### OPERACIONES CRÍTICAS (Score: <20)
```
🚨 **EMERGENCIA: PARAR NUEVA PRODUCCIÓN**

💥 **Situación crítica**: [Descripción emergencia]
🛑 **ACCIÓN INMEDIATA**: Detener nuevos lotes ahora
⚙️ **Acciones de emergencia**:
   • Solo completar lotes ya en proceso
   • Activar plan de contingencia
   • Mantener equipos en standby seguro
   • Evaluar cada 2 horas para reinicio

🔄 **Reinicio cuando**: Score > 45 y condiciones estables
📞 **Escalación**: Notificar supervisión si persiste >6h
```

### 💬 **Mensajes Específicos por Situación**

#### Por Precio Energético
- **€0.05-0.10/kWh**: "💰 ¡Precio excepcional! Momento ideal para generar stock y lotes premium"
- **€0.10-0.15/kWh**: "✅ Precio favorable para operación normal"
- **€0.15-0.20/kWh**: "⚖️ Precio normal, mantener eficiencia estándar"
- **€0.20-0.25/kWh**: "⚠️ Precio elevado, optimizar procesos no críticos"
- **€0.25-0.30/kWh**: "🔸 Precio alto, reducir a lotes prioritarios"
- **€0.30-0.40/kWh**: "🔶 Precio muy alto, evaluar pausa procesos largos"
- **>€0.40/kWh**: "🚨 Precio crítico, parar producción hasta bajada"

#### Por Condiciones Ambientales
- **Temperatura 15-25°C**: "🌡️ Temperatura óptima para todos los procesos"
- **Temperatura 25-30°C**: "🌡️ Activar refrigeración, producción normal"
- **Temperatura 30-35°C**: "🌡️ Aumentar refrigeración, monitorear templado"
- **Temperatura 35-40°C**: "🌡️ Refrigeración máxima, solo lotes críticos"
- **Temperatura >40°C**: "🌡️ Temperatura crítica, evaluar parada temporal"

- **Humedad 45-65%**: "💧 Humedad ideal para calidad óptima"
- **Humedad 65-75%**: "💧 Activar deshumidificación preventiva"
- **Humedad 75-85%**: "💧 Deshumidificación urgente, vigilar bloom"
- **Humedad >85%**: "💧 Humedad crítica, riesgo alto de bloom"

#### Por Horarios (España)
- **00:00-06:00 (Valle)**: "⚡ Hora valle: Ideal para conchado intensivo de 12h"
- **06:00-10:00 (Llano)**: "⚡ Horario normal: Procesos estándar"
- **10:00-14:00 (Pico)**: "⚡ Hora pico: Evitar arranques de conchado"
- **14:00-18:00 (Llano)**: "⚡ Horario normal: Mezcla y templado"
- **18:00-22:00 (Pico)**: "⚡ Hora pico: Solo completar procesos en curso"
- **22:00-00:00 (Llano)**: "⚡ Preparación para valle: Alistar lotes largos"

### 🔄 **Mensajes de Transición**

#### Mejorando Condiciones
```
📈 **MEJORA EN CONDICIONES**
Las condiciones están mejorando. En [X minutos] podremos:
• [Acción específica recomendada]
• Preparar [tipo de lotes] para aprovechar ventana
• Estimar ahorro de €[X] vs mantener estado actual
```

#### Empeorando Condiciones
```
📉 **DETERIORO DE CONDICIONES**
Las condiciones se están deteriorando. Recomendamos:
• Completar lotes actuales rápidamente
• No iniciar nuevos [proceso específico]
• Prepararse para [acción preventiva]
• Próxima ventana favorable estimada: [tiempo]
```

### 🎨 **Personalización por Contexto**

#### Lunes (Inicio Semana)
- "🏁 Inicio de semana: Planificar producción según pronóstico semanal"
- Énfasis en preparación y organización

#### Viernes (Pre-Weekend)
- "🎯 Viernes: Priorizar volumen para demanda de weekend"
- Énfasis en completar objetivos semanales

#### Fines de Semana
- "🔧 Weekend: Solo turno mañana, preparación para lunes"
- Énfasis en mantenimiento y optimización

#### Temporadas
- **Verano**: "☀️ Período estival: Extra atención a refrigeración"
- **Invierno**: "❄️ Período invernal: Vigilar calefacción y humedad"
- **Navidad/Pascua**: "🎄 Temporada alta: Maximizar calidad premium"

---

## Implementación Técnica

### 🔧 **Integración con Sistema ML**

El sistema debe:

1. **Recibir score ML** (0-100) y condiciones actuales
2. **Mapear a categoría** según thresholds definidos
3. **Seleccionar plantilla** apropiada para la situación
4. **Personalizar mensaje** con datos específicos (precio, temperatura, etc.)
5. **Agregar contexto temporal** (hora, día, temporada)
6. **Incluir próxima ventana** óptima si aplicable

### 📝 **Estructura del Servicio**

```python
class BusinessLogicService:
    def generate_human_message(self, ml_score, conditions, context):
        # 1. Determinar categoría por score
        # 2. Analizar condiciones específicas
        # 3. Seleccionar plantilla base
        # 4. Personalizar con datos reales
        # 5. Agregar contexto temporal
        # 6. Incluir acciones específicas
        # 7. Calcular próxima revisión
        return formatted_message
```

### 🎯 **Criterios de Calidad**

Los mensajes deben:
- ✅ Ser específicos y accionables
- ✅ Usar lenguaje de operadores (no técnico)
- ✅ Indicar urgencia real sin alarmismo
- ✅ Incluir beneficio/impacto económico cuando relevante
- ✅ Dar contexto temporal (cuándo revisar)
- ✅ Ser consistentes con la realidad operacional española