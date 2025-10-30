# Optimization Rules - Business Logic

## Energy Optimization Priorities

### Priority 1: Protect Critical Processes
- Conchadora running: NEVER interrupt (batch lost = 50 kg + 24-72h)
- Templadora in progress: Complete batch (20min commitment)
- Cost: Interrupt = 80-230 kWh wasted + raw materials

### Priority 2: Schedule Long Processes in Valle
- Conchado 24h: Start in P3 (valle), avoid P1 (punta)
- Target: 80% of conchado hours in P3 tariff
- Savings: ~40€/batch vs random scheduling

### Priority 3: Batch High-Power Tasks
- Run mezcladora + roladora together: 4.3 kW (within 10 kW limit)
- Avoid mezcladora + conchadora + templadora: 7.5 kW (near limit)

### Priority 4: Weather-Dependent Scheduling
- Templado: Only schedule if forecast <24°C next 2h
- Conchado: Prefer <22°C ambient (quality improvement)
- Hot days (>28°C): Reduce production or night-shift only

## Scheduling Constraints

### Cannot Overlap
- 2x Conchadoras: 6.4 kW (acceptable but tight)
- 3x Any high-power: >7 kW (risk brownout)

### Must Sequence
- Mezcla → Rolado: 0-2h gap (paste must stay warm)
- Rolado → Conchado: 0-4h gap (can buffer in heated tank)
- Conchado → Templado: 0-8h gap (can hold liquid chocolate)

### Batch Size Optimization
- 50 kg batch: Best machine utilization (100%)
- 25 kg batch: Acceptable for small orders (50% efficiency)
- <25 kg: Avoid (poor economics, setup time = production time)

## Prophet Price Forecast Integration

### Tariff Period Classification
- P1 (Punta): 10-13h, 18-21h - Avoid high-power tasks
- P2 (Llano): 8-9h, 14-17h, 22-23h - Acceptable for non-critical
- P3 (Valle): 0-7h, rest - Ideal for conchado start

### Price Threshold Rules
- >0.25 €/kWh: Emergency only (finish in-progress batches)
- 0.15-0.25 €/kWh: Avoid new high-power tasks
- 0.10-0.15 €/kWh: Normal operations
- <0.10 €/kWh: Opportunity - batch multiple processes

### Forecast Confidence
- MAE 0.033 €/kWh: High confidence scheduling
- If forecast unavailable: Use historical P1/P2/P3 averages
- If InfluxDB down: Halt non-critical production (safety first)

## ML Model Trust Levels

### Energy Score (0-100)
- 80-100: Excellent - schedule all production
- 60-79: Good - schedule normal batches
- 40-59: Fair - prioritize critical only
- <40: Poor - consider postponing non-urgent

### Production State Classifier
- "Optimal": Trust 100% - proceed with scheduled plan
- "Moderate": Trust 80% - verify weather forecast
- "Reduced": Trust 60% - manual review recommended
- "Halt": Trust 90% - respect unless emergency

## Fallback Rules (When Systems Fail)

### Prophet Model Unavailable
- Use static tariff periods (P1/P2/P3)
- Conservative scheduling (avoid P1 punta)
- Reduce batch count by 25%

### Weather Forecast Unavailable
- Check last 24h average from InfluxDB
- If >24°C: Avoid templado until verified
- If >26°C: Halt production until data available

### InfluxDB Unavailable
- Cannot optimize (no historical data)
- Fallback: Manual scheduling with P3 valle preference
- Alert: Production planning limited

## Business Rules Summary

**Golden Rule**: Protect conchadora batches (highest value + longest time).

**Secondary Rule**: Maximize valle hours for long processes.

**Safety Rule**: Environmental thresholds override all optimization.
