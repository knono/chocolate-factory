# Especificaciones de Maquinaria - Fábrica de Chocolate

## Equipos de Producción

### Mezcladora
- **Capacidad**: 10 kg por ciclo
- **Consumo**: 0.5 kWh/min
- **Tiempo ciclo**: Variable (1-5 min típico)
- **Ingredientes**: Chocolate liquor, azúcar, leche en polvo
- **Sensores requeridos**:
  - Temperatura superficie: 20-60°C
  - Vibración: 0-5 g RMS
  - RPM motor: 0-1500 rpm
  - Consumo eléctrico: Trifásico hasta 30A

### Máquina de Rolado
- **Capacidad**: 10 kg por ciclo
- **Consumo**: 0.7 kWh/min
- **Función**: Reducción tamaño partículas
- **Sensores requeridos**:
  - Vibración: 0-10 g RMS (crítico para detectar desgaste rodillos)
  - Temperatura rodillos: 25-45°C
  - Presión hidráulica: 50-200 bar
  - Consumo eléctrico: Trifásico hasta 40A

### Conchadora
- **Capacidad**: 10 kg por ciclo
- **Consumo**: 0.8 kWh/min
- **Tiempo proceso**: 4-24 horas (según calidad)
- **Temperatura control**: 45-60°C
- **Sensores requeridos**:
  - Temperatura masa: 45-60°C ±0.5°C
  - Humedad relativa ambiente: <50%
  - Vibración: 0-8 g RMS
  - RPM agitador: 20-60 rpm

### Templadora
- **Capacidad**: 10 kg por ciclo
- **Consumo**: 0.6 kWh/min
- **Perfil térmico**: 
  - Calentamiento: 45-50°C
  - Enfriamiento: 27-28°C
  - Recalentamiento: 31-32°C
- **Sensores críticos**:
  - Temperatura precisión: ±0.2°C
  - Velocidad agitación: 10-30 rpm
  - Tiempo en cada fase

## Restricciones Operativas

1. **Secuencia obligatoria**: Mezcla → Rolado → Conchado → Templado
2. **Buffer máximo entre etapas**: 30 minutos
3. **Temperatura ambiente crítica**: 18-22°C para templado
4. **Humedad máxima**: 60% RH (riesgo de bloom)