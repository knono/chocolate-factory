# Energy Consumption - Chocolate Factory

## Machine Consumption Specifications

### Primary Production Equipment

#### Mezcladora (Mixer)
- **Power consumption**: 0.5 kWh/min
- **Operating time per batch**: 5-10 minutes
- **Energy per batch**: 2.5-5.0 kWh
- **Daily average consumption**: 50-100 kWh
- **Peak power draw**: 35 kW
- **Power factor**: 0.85

#### Máquina de Rolado (Rolling Machine)
- **Power consumption**: 0.7 kWh/min
- **Operating time per batch**: 15-20 minutes
- **Energy per batch**: 10.5-14.0 kWh
- **Daily average consumption**: 210-280 kWh
- **Peak power draw**: 45 kW
- **Power factor**: 0.87

#### Conchadora (Conche)
- **Power consumption**: 0.8 kWh/min
- **Operating time per batch**:
  - Standard quality: 240-360 minutes (4-6 hours)
  - Premium quality: 480-720 minutes (8-12 hours)
  - Ultra-premium: 960-1440 minutes (16-24 hours)
- **Energy per batch**:
  - Standard: 192-288 kWh
  - Premium: 384-576 kWh
  - Ultra-premium: 768-1152 kWh
- **Daily average consumption**: 400-600 kWh
- **Peak power draw**: 50 kW
- **Power factor**: 0.88

#### Templadora (Tempering Machine)
- **Power consumption**: 0.6 kWh/min
- **Operating time per batch**: 30-45 minutes
- **Energy per batch**: 18-27 kWh
- **Daily average consumption**: 180-270 kWh
- **Peak power draw**: 40 kW
- **Power factor**: 0.86

### Auxiliary Equipment

#### Cooling System
- **Continuous consumption**: 5 kW
- **Operating hours**: 24 hours/day
- **Daily consumption**: 120 kWh
- **Critical for**: Tempering and storage

#### HVAC System
- **Average consumption**: 8 kW
- **Operating hours**: 24 hours/day
- **Daily consumption**: 192 kWh
- **Seasonal variation**: +30% summer, -20% winter

#### Lighting
- **LED installation**: 2 kW
- **Operating hours**: 16 hours/day
- **Daily consumption**: 32 kWh

#### Compressed Air
- **Compressor power**: 3 kW
- **Operating hours**: 8 hours/day
- **Daily consumption**: 24 kWh

## Total Energy Profile

### Daily Consumption Breakdown

| Equipment | Min (kWh) | Max (kWh) | Average (kWh) |
|-----------|-----------|-----------|---------------|
| Mezcladora | 50 | 100 | 75 |
| Roladora | 210 | 280 | 245 |
| Conchadora | 400 | 600 | 500 |
| Templadora | 180 | 270 | 225 |
| Cooling | 120 | 120 | 120 |
| HVAC | 192 | 192 | 192 |
| Lighting | 32 | 32 | 32 |
| Compressed Air | 24 | 24 | 24 |
| **TOTAL** | **1,208** | **1,618** | **1,413** |

### Energy Consumption per Production Unit

#### Per Kilogram of Chocolate
- **Current average**: 2.4 kWh/kg
- **Target**: 2.0 kWh/kg
- **Best achieved**: 2.1 kWh/kg (valley hours, standard quality)
- **Worst case**: 3.2 kWh/kg (peak hours, ultra-premium)

#### Per Batch (10 kg)
- **Standard quality total**: 24 kWh
- **Premium quality total**: 32 kWh
- **Energy distribution**:
  - Mixing: 3%
  - Rolling: 8%
  - Conching: 75%
  - Tempering: 10%
  - Auxiliary: 4%

## Optimization Strategies

### Time-of-Use Optimization
- **Peak hours (10:00-14:00, 19:00-22:00)**: Avoid high-consumption processes
- **Valley hours (00:00-06:00)**: Schedule conching operations
- **Flat hours**: Normal production operations

### Load Management
- **Maximum demand**: 150 kW (contracted)
- **Average demand**: 88 kW
- **Peak shaving target**: Keep below 120 kW
- **Load factor**: 0.59 (target: 0.70)

### Process-Specific Optimizations

#### Conching Optimization
- Run multiple small batches vs single large batch
- Utilize waste heat for pre-heating
- Optimize agitation speed based on quality requirements
- Potential savings: 15-20% energy reduction

#### Tempering Optimization
- Precise temperature control reduces cycling
- Batch sequencing to maintain temperature
- Potential savings: 10% energy reduction

#### Cooling Optimization
- Free cooling when ambient < 15°C
- Variable speed drives on fans
- Potential savings: 25% in winter months

## REE Integration Points

### Real-time Price Response
- **Price threshold for process delay**: > 0.15 €/kWh
- **Automatic scheduling adjustment**: Via APScheduler
- **Conching start decision**: Based on 6-hour price forecast
- **Energy buffer management**: Pre-cooling during low prices

### Demand Response Capabilities
- **Sheddable load**: Up to 40 kW (non-critical processes)
- **Shift-able load**: 500 kWh/day (conching)
- **Response time**: < 15 minutes
- **Participation programs**: PVPC optimization only (currently)

## Monitoring and Metering

### Measurement Points
1. **Main incomer**: Total factory consumption
2. **Production line**: Combined machinery consumption
3. **HVAC system**: Separate metering
4. **Each major machine**: Individual monitoring planned

### Key Metrics
- **Real-time power (kW)**: Updated every second
- **Energy consumption (kWh)**: 15-minute intervals
- **Power factor**: Continuous monitoring
- **Harmonic distortion (THD)**: < 5% target

### Data Integration
- **InfluxDB storage**: 1-minute resolution
- **Dashboard display**: Real-time updates
- **ML features**: 15-minute aggregations
- **REE correlation**: 15-minute matching

## Cost Impact

### Current State
- **Average energy cost**: 0.30 €/kg chocolate
- **Daily energy cost**: ~170 € (at 0.12 €/kWh average)
- **Monthly energy cost**: ~3,570 €
- **Energy as % of total cost**: 2.2%

### Optimization Potential
- **Valley hour utilization**: -30% cost
- **Peak avoidance**: -20% cost
- **Process optimization**: -15% consumption
- **Combined potential savings**: 35-40% on energy costs
- **Annual savings potential**: ~15,000 €

## Future Improvements

### Short-term (Already Planned)
- Individual machine metering
- Automated load scheduling based on REE prices
- Power factor correction to 0.95

### Medium-term (Under Evaluation)
- Variable speed drives on all motors
- Heat recovery from conching
- Battery storage for peak shaving

### Long-term (Conceptual)
- Solar PV installation (100 kWp)
- Combined heat and power (CHP)
- Full demand response participation