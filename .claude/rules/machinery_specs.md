# Chocolate Factory - Machinery Specifications

## Equipment Inventory

### Mezcladora (Mixer)
- Model: Industrial Mixer 2000
- Capacity: 50 kg/batch
- Power consumption: 2.5 kW (0.5 kWh/min)
- Processing time: 30 min/batch
- Throughput: 100 kg/h max
- Optimal temperature: 18-22°C
- Requires: Raw ingredients (cacao, sugar, lecithin)

### Roladora (Roller)
- Model: Three-Roll Refiner
- Capacity: 40 kg/batch
- Power consumption: 1.8 kW (0.7 kWh/min)
- Processing time: 45 min/batch
- Throughput: 53 kg/h max
- Optimal temperature: 20-24°C
- Requires: Mixed paste from Mezcladora

### Conchadora (Conche)
- Model: Longitudinal Conche Pro
- Capacity: 25 kg/batch
- Power consumption: 3.2 kW (0.8 kWh/min)
- Processing time: 24-72 hours (depending on quality)
- Throughput: 25 kg/24h (premium), 25 kg/12h (standard)
- Optimal temperature: 55-82°C (phase dependent)
- Requires: Refined paste from Roladora
- Critical: Long process, cannot interrupt

### Templadora (Tempering Machine)
- Model: Automatic Tempering Unit
- Capacity: 40 kg/batch
- Power consumption: 1.5 kW (0.6 kWh/min)
- Processing time: 20 min/batch
- Throughput: 120 kg/h max
- Temperature curve: 45°C → 27°C → 31°C (precise control)
- Requires: Conched chocolate
- Critical: Temperature precision ±0.5°C

## Production Sequences

### Sequence A - Premium Dark Chocolate (72h)
1. Mezcla: 50 kg → 30 min → 1.25 kWh
2. Rolado: 50 kg → 45 min → 2.1 kWh
3. Conchado: 50 kg → 72 hours → 230.4 kWh
4. Templado: 50 kg → 20 min → 0.5 kWh

Total time: 72h 1h 35min
Total energy: 234.25 kWh

### Sequence B - Standard Milk Chocolate (24h)
1. Mezcla: 50 kg → 30 min → 1.25 kWh
2. Rolado: 50 kg → 45 min → 2.1 kWh
3. Conchado: 50 kg → 24 hours → 76.8 kWh
4. Templado: 50 kg → 20 min → 0.5 kWh

Total time: 24h 1h 35min
Total energy: 80.65 kWh

## Constraints

### Production Capacity
- Daily maximum: 200 kg finished chocolate
- Minimum batch size: 25 kg
- Maximum batch size: 50 kg
- Standard batch: 50 kg (optimizes machine utilization)

### Environmental Requirements
- Ambient temperature: 18-22°C optimal, 15-25°C acceptable
- Humidity: 50-60% optimal, 40-70% acceptable
- Exceeding ranges affects:
  - Conchado: Quality degradation at >25°C
  - Templado: Fails at >24°C (bloom risk)

### Energy Constraints
- Peak power limit: 10 kW (4 machines max simultaneous)
- Typical daily consumption: 80-240 kWh (depending on sequences)
- Critical machines: Conchadora (runs 24-72h continuously)

## Maintenance Schedule

- Mezcladora: Weekly cleaning (2h downtime)
- Roladora: Weekly cleaning + monthly calibration (3h downtime)
- Conchadora: Monthly deep clean (8h downtime)
- Templadora: Daily cleaning (30min downtime)
