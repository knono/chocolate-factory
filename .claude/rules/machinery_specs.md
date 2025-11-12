# Chocolate Factory - Machinery Specifications

**Implementation**: `domain/machinery/specs.py`

## Equipment Inventory (Implemented Values)

### Mezclado (Mixer)
- **Power**: 30 kW
- **Duration**: 60 min (1 hour)
- **Energy per cycle**: 30 kWh
- **Optimal temperature**: 20-30°C
- **Optimal humidity**: 50%
- **Category**: Light process
- **Schedule**: 14:00-24:00 (afternoon/evening)

### Templado (Tempering)
- **Power**: 36 kW
- **Duration**: 120 min (2 hours)
- **Energy per cycle**: 72 kWh
- **Optimal temperature**: 28-32°C
- **Optimal humidity**: 60%
- **Category**: Moderate process
- **Schedule**: 10:00-14:00 (midday)

### Refinado (Refining)
- **Power**: 42 kW
- **Duration**: 240 min (4 hours)
- **Energy per cycle**: 168 kWh
- **Optimal temperature**: 30-40°C
- **Optimal humidity**: 55%
- **Category**: Moderate process
- **Schedule**: 06:00-10:00 (morning)

### Conchado (Conching)
- **Power**: 48 kW
- **Duration**: 300 min (5 hours)
- **Energy per cycle**: 240 kWh
- **Optimal temperature**: 40-50°C
- **Optimal humidity**: 50%
- **Category**: Intensive process
- **Schedule**: 00:00-06:00 (night)

## ML Integration

### Machine-Specific Features (implemented)
These specifications are used in `direct_ml.py` for physics-based ML training:

1. **machine_power_kw**: Active process power consumption
2. **machine_duration_hours**: Process duration converted to hours
3. **machine_optimal_temp**: Midpoint of optimal temperature range
4. **machine_optimal_humidity**: Target humidity for process
5. **machine_thermal_efficiency**: 100 - (|temp - optimal| × 5), clipped to [0,100]
6. **machine_humidity_efficiency**: 100 - (|humidity - optimal| × 2), clipped to [0,100]
7. **estimated_energy_kwh**: power_kw × duration_hours
8. **estimated_cost_eur**: energy_kwh × price_eur_kwh
9. **tariff_multiplier**: P1=1.3, P2=1.0, P3=0.8
10. **cost_with_tariff**: estimated_cost × tariff_multiplier

### Target Calculation
**Energy Optimization Score** (0-100):
```
score = (100 - price_normalized) × 0.4 +          # 40% price
        thermal_efficiency × 0.35 +                # 35% thermal
        humidity_efficiency × 0.15 +               # 15% humidity
        ((tariff_multiplier - 1) × -50 + 50) × 0.1 # 10% tariff
```

**Production Recommendation** (Optimal/Moderate/Reduced/Halt):
```
suitability = thermal_efficiency × 0.45 +     # 45% thermal
              humidity_efficiency × 0.25 +    # 25% humidity
              (100 - price_normalized) × 0.30 # 30% price

if P3_Valle: suitability × tariff_multiplier

Classes:
- Optimal: suitability ≥ 75
- Moderate: 55 ≤ suitability < 75
- Reduced: 35 ≤ suitability < 55
- Halt: suitability < 35
```

## Model Performance (Nov 12, 2025)

After integrating machinery specifications into `direct_ml.py`:

**Energy Optimization Model** (RandomForestRegressor):
- R²: 0.978 (+240% improvement from 0.287)
- Features: 10 (5 basic + 5 machinery-specific)
- Training samples: 495
- Test samples: 124

**Production Recommendation Model** (RandomForestClassifier):
- Accuracy: 0.911 (+12% improvement from 0.814)
- Classes: 4 (Optimal, Moderate, Reduced, Halt)
- Features: 10 (same as energy model)
- Training samples: 495
- Test samples: 124

**Key Improvement**: Physics-based targets using real machinery thermal/humidity efficiency replaced synthetic noise-based targets.
