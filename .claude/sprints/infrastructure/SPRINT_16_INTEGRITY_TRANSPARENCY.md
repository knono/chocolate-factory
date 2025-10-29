# Sprint 16 - Documentation Integrity & Transparency

**Date**: October 30 - November 1, 2025
**Status**: IN PROGRESS

## Objetivo

Corregir documentación que no refleja la realidad del código:
- Métricas ML presentadas como predictivas cuando son determinísticas
- Valores hardcodeados presentados como mediciones reales
- Secciones obsoletas (MLflow)
- Endpoints documentados que no existen

## Problemas Identificados

1. **ML_ARCHITECTURE.md**: R² 0.9986 es circular (predice su propia fórmula)
2. **API_REFERENCE.md**: Documenta 19 endpoints, hay 45 reales
3. **TROUBLESHOOTING.md**: Sección MLflow completa obsoleta (165-221 líneas)
4. **insights.py**: ROI 1,661€ hardcodeado, presentado como tracking real
5. **Múltiples docs**: Prophet entrenamiento "cada 30min", real: 24h

## Tareas

### Fase 1: Eliminar Claims Falsos

**1.1 ML_ARCHITECTURE.md**
- [ ] Eliminar: "Regression: Energy score (0-100), R²: 0.9986 (test set)"
- [ ] Reemplazar: "Deterministic scoring function (business rules)"
- [ ] Mantener Prophet metrics (MAE 0.033, R² 0.49) - real ML
- [ ] Añadir sección "Limitations" al final

**1.2 API_REFERENCE.md**
- [ ] Eliminar endpoints inexistentes: `/insights/energy`, `/insights/production`, `/insights/weather`
- [ ] Corregir count: 19 → 45 endpoints
- [ ] Verificar cada endpoint documentado existe en código

**1.3 ml_predictions.py router**
- [ ] Añadir docstring: "Deterministic scoring, not ML prediction"
- [ ] Aclarar: Prophet = ML real, Scoring = reglas negocio

### Fase 2: Etiquetar Hardcoded

**2.1 ROI hardcoded (insights.py:301)**
```python
# Cambiar de:
"estimated_savings_eur": 1661

# A:
"baseline_theoretical_savings_eur": 1661,
"actual_measured_savings_eur": None,
"note": "Theoretical estimate, not real measurement"
```

**2.2 Prophet metrics**
- [ ] Añadir: `"last_measured": "2025-10-24"` a métricas Prophet
- [ ] Etiquetar como "Initial Benchmark" si no se actualizan

**2.3 Data volumes**
- [ ] Etiquetar 42,578 REE, 88,935 SIAR como "As of Oct 2025"
- [ ] O crear script verificación desde InfluxDB

### Fase 3: Limpiar Obsoleto ✅ COMPLETED

**3.1 TROUBLESHOOTING.md**
- [x] Eliminar líneas 165-221 (sección MLflow completa)
- [x] Reemplazar con "Direct ML Troubleshooting"
- [x] Verificar todos los curl examples funcionan

**3.2 Training frequencies**
- [x] Corregir en todos los docs: Prophet 24h (no 30min)
- [x] Verificar contra `scheduler_config.py` líneas 61, 73
- [x] Actualizar job count: documentar 7 jobs reales

**3.3 Code examples**
- [x] Testar todos los curl en TROUBLESHOOTING.md
- [x] Testar todos los curl en API_REFERENCE.md
- [x] Actualizar o eliminar los que fallen

**Changes Made**:
- TROUBLESHOOTING.md: Replaced MLflow section (lines 165-221) with "Direct ML Troubleshooting"
- TROUBLESHOOTING.md: Fixed Prophet endpoint paths (`/predict/prices/models/price-forecast/status`)
- TROUBLESHOOTING.md: Updated Quick Reference table and ML Models checklist
- CLAUDE.md: Corrected Prophet training from "Every hour at :30" to "Every 24 hours"
- CLAUDE.md: Updated job count from "13+ automated" to "7 automated"
- CLAUDE.md: Removed duplicate "ML predictions" and "Auto backfill" jobs from list
- ML_ARCHITECTURE.md: Corrected Prophet frequency from "Cada 1 hora (a los :30)" to "Cada 24 horas"
- Verified scheduler_config.py: 7 jobs total (REE, Weather, Prophet-24h, sklearn-30min, 3x health monitoring)

### Fase 4: Añadir Disclaimers

**4.1 ML_ARCHITECTURE.md**
```markdown
## Limitations

- Energy scoring: deterministic rules, not trained prediction
- Prophet R² 0.49: 51% variance unexplained
- No model drift detection
- No A/B testing
- Test coverage 19%
```

**4.2 README.md - Security**
```markdown
## Security

- No authentication/authorization
- No per-user rate limiting
- Not suitable for public internet
- Use: private networks, Tailscale VPN
```

**4.3 README.md - Testing**
```markdown
- Testing: 102 tests (100% passing, 19% coverage)
- Low coverage = 81% code untested
- Not production-ready without 40%+ coverage
```

**4.4 Monitoring**
```markdown
- Health checks: availability only, not performance
- No alerting (Discord/Telegram/email)
- Logs collected, not analyzed
- Suitable for: dev/demo only
```

## Success Criteria

- [ ] Cero claims falsos verificables
- [ ] Valores hardcoded etiquetados
- [ ] Ejemplos código testeados
- [ ] 5+ disclaimers añadidos
- [ ] MLflow references: 0

## Métricas

| Doc | Before | Target |
|-----|--------|--------|
| ML_ARCHITECTURE.md | 58% | 90% |
| API_REFERENCE.md | 72% | 90% |
| TROUBLESHOOTING.md | 52% | 90% |

## Timeline

- **Day 1**: Fase 1+2 (claims falsos, hardcoded)
- **Day 2**: Fase 3 (obsoleto)
- **Day 3**: Fase 4 (disclaimers)

**Effort**: ~8 horas

## Archivos Afectados

```
docs/
├── ML_ARCHITECTURE.md
├── API_REFERENCE.md
├── TROUBLESHOOTING.md
└── MONITORING_GUIDE.md

src/fastapi-app/
├── api/routers/ml_predictions.py
└── api/routers/insights.py

README.md
CLAUDE.md
```

## Verificación Final

```bash
# Verificar endpoints
grep -r "@router\." src/fastapi-app/api/routers/ | wc -l

# Verificar jobs scheduler
grep "add_job" src/fastapi-app/tasks/scheduler_config.py | wc -l

# Encontrar hardcoded metrics
grep -r "0.033\|0.49\|1661\|42578\|88935" src/fastapi-app --include="*.py"

# Testar ejemplos
curl -s http://localhost:8000/health | jq
```

---

**Last Updated**: October 30, 2025
