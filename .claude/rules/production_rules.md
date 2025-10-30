# Reglas de Producción para Claude

## Datos Autoritativos
1. **SIEMPRE usa los consumos reales** especificados en machinery_specs.md:
   - Mezcladora: 0.5 kWh/min (2.5 kW)
   - Roladora: 0.7 kWh/min (1.8 kW)
   - Conchadora: 0.8 kWh/min (3.2 kW)
   - Templadora: 0.6 kWh/min (1.5 kW)

2. **NUNCA modifiques la secuencia** de producción:
   - Orden obligatorio: Mezcla → Rolado → Conchado → Templado

3. **RESPETA las capacidades**:
   - Máximo 50 kg por batch
   - Mínimo 25 kg por batch
   - Producción diaria máxima: 200 kg

## Quality Control Thresholds

### Reject Batch If:
- Mezcla: Temperature >28°C during mixing (oxidation risk)
- Rolado: Particle size >25 microns (grittiness)
- Conchado: Temperature variance >±3°C (inconsistent quality)
- Templado: Failed temper test (bloom on sample)

### Environmental Abort Conditions
- Ambient temperature >26°C: Pause templado
- Ambient temperature >28°C: Abort conchado
- Humidity >75%: Pause all production (moisture risk)
- Power outage: Emergency conchado temperature maintenance (4h backup)

## Failure Recovery Procedures

### Conchado Interruption (Critical)
- If <12h process: Can resume within 2h (reheat to 65°C)
- If 12-48h process: Can resume within 4h (check viscosity)
- If >48h process: Cannot resume (batch lost if >4h interruption)

### Power Outage
- Priority 1: Maintain conchadora temperature (battery backup)
- Priority 2: Complete templado batch in progress (30min grace)
- Priority 3: Pause mezcladora/roladora (safe to restart)

### Equipment Failure
- Mezcladora down: Switch to manual mixing (50% capacity)
- Roladora down: No workaround (production halt)
- Conchadora down: Critical (finish batches, schedule maintenance)
- Templadora down: Manual tempering possible (slow, 25% capacity)