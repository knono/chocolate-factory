# Production Process - Chocolate Factory

## Process Overview

The chocolate production follows a strict sequential process with defined timing and capacity constraints.

## Process Sequence

### 1. Mixing (Mezclado)
- **Duration**: 5-10 minutes per batch
- **Capacity**: 10 kg per batch
- **Inputs**: 
  - Chocolate liquor (40%)
  - Sugar (35%)
  - Milk powder (25%)
- **Output**: Homogeneous mixture ready for refining
- **Critical Parameters**:
  - Temperature: 45-50°C
  - Mixing speed: 60-120 RPM
- **Next Step**: Must proceed to rolling within 30 minutes

### 2. Rolling (Rolado)
- **Duration**: 15-20 minutes per batch
- **Capacity**: 10 kg input from mixing
- **Function**: Particle size reduction to 20-25 microns
- **Output**: Refined chocolate paste
- **Critical Parameters**:
  - Roller pressure: 120 bar optimal
  - Temperature maintenance: 40-45°C
- **Next Step**: Transfer to conching within 30 minutes

### 3. Conching (Conchado)
- **Duration**: 4-24 hours (depending on quality requirements)
  - Standard quality: 4-6 hours
  - Premium quality: 8-12 hours
  - Ultra-premium: 16-24 hours
- **Capacity**: 10 kg per conche
- **Function**: 
  - Flavor development
  - Moisture reduction
  - Texture refinement
- **Critical Parameters**:
  - Temperature: 55-60°C
  - Continuous agitation at 20-30 RPM
  - Humidity control < 50% RH
- **Next Step**: Must temper within 15 minutes of completion

### 4. Tempering (Templado)
- **Duration**: 30-45 minutes per batch
- **Capacity**: 10 kg from conching
- **Temperature Profile**:
  1. Heat to 45-50°C (melt all crystals)
  2. Cool to 27-28°C (form stable and unstable crystals)
  3. Reheat to 31-32°C (melt unstable crystals only)
- **Critical Parameters**:
  - Temperature precision: ±0.2°C
  - Agitation: 10-15 RPM constant
  - Ambient temperature: 18-22°C required
- **Next Step**: Immediate molding required (< 5 minutes)

### 5. Molding & Cooling (Moldeado y Enfriamiento)
- **Duration**: 20-30 minutes
- **Capacity**: 10 kg yields approximately 66 bars (150g each)
- **Process**:
  - Pour at 31-32°C into molds
  - Vibration table: 2-3 minutes (remove air bubbles)
  - Cooling tunnel: 15-20 minutes at 12-15°C
- **Output**: Finished chocolate bars ready for packaging

## Production Timing

### Batch Cycle Times
- **Minimum cycle time**: ~6 hours (with 4-hour conching)
- **Standard cycle time**: ~10 hours (with 8-hour conching)
- **Premium cycle time**: ~18 hours (with 16-hour conching)

### Daily Production Capacity
- **Operating hours**: 16 hours/day (2 shifts × 8 hours)
- **Theoretical maximum**: 960 cycles (1-minute resolution)
- **Practical throughput**:
  - Standard quality: 2-3 complete batches per shift
  - Premium quality: 1 complete batch per shift
  - Mixed production: Typically 1 premium + 2 standard per day

## Process Constraints

### Sequential Dependencies
- Each step MUST complete before the next begins
- No parallel processing of single batch
- Multiple batches can be at different stages

### Time Windows
- **Mixing → Rolling**: Max 30 minutes hold
- **Rolling → Conching**: Max 30 minutes hold
- **Conching → Tempering**: Max 15 minutes hold
- **Tempering → Molding**: Max 5 minutes hold

### Quality Checkpoints
1. **Post-mixing**: Homogeneity verification
2. **Post-rolling**: Particle size measurement
3. **During conching**: Hourly moisture and viscosity checks
4. **Post-tempering**: Crystal structure validation
5. **Post-molding**: Visual inspection and snap test

## Bottlenecks and Optimization Points

### Primary Bottleneck
- **Conching**: Longest process (4-24 hours)
- Strategy: Multiple conches for parallel processing
- Current setup: Single conche (limits throughput)

### Secondary Bottleneck
- **Tempering**: Precision requirement slows process
- Cannot rush without quality loss
- Temperature control critical

### Optimization Opportunities
1. **Energy optimization**: Schedule conching during off-peak electricity rates
2. **Quality mix**: Balance standard/premium based on demand
3. **Batch sequencing**: Minimize idle time between processes
4. **Predictive scheduling**: Use REE price data for operation timing