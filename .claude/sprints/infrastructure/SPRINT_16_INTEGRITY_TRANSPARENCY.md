# Sprint 16 - Documentation Integrity & Transparency

**Date**: October 30, 2025
**Status**: ✅ COMPLETED

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

### Fase 4: Añadir Disclaimers ✅ COMPLETED

**4.1 ML_ARCHITECTURE.md**
- [x] Added comprehensive "Limitaciones y Disclaimers" section (87 lines)
- [x] Energy scoring: deterministic rules, not trained prediction
- [x] Prophet R² 0.49: 51% variance unexplained
- [x] No model drift detection
- [x] No A/B testing
- [x] Test coverage 19%

**4.2 CLAUDE.md - Security**
- [x] Network Level: Tailscale VPN zero-trust mesh ✅
- [x] Application Level: No authentication/authorization
- [x] Access Control documented (localhost, Tailscale, public)
- [x] Rate Limiting: Global per-endpoint, not per-user
- [x] Deployment Model: Private infrastructure only

**4.3 CLAUDE.md & README.md - Testing**
- [x] Testing: 102 tests (100% passing, 19% coverage)
- [x] Low coverage = 81% code untested
- [x] Not production-ready without 40%+ coverage
- [x] Focus Areas: Error handling, edge cases documented

**4.4 CLAUDE.md & README.md - Monitoring**
- [x] Health checks: availability only, not performance
- [x] No alerting (Discord/Telegram/email)
- [x] Logs collected, not analyzed
- [x] Suitable for: dev/demo only

**Changes Made**:
- ML_ARCHITECTURE.md: Added 87-line "Limitaciones y Disclaimers" section covering:
  - ML limitations (Energy scoring + Prophet)
  - Testing limitations (19% coverage)
  - Security model (network-level only)
  - Observability limitations (no alerting, no centralized logs)
  - ROI metrics disclaimer (theoretical estimate)
  - Production readiness recommendations (7 items)
- CLAUDE.md: Already had "System Limitations & Disclaimers" section (added in Phase 2)
- README.md: Already had "Limitations & Disclaimers" section (added in Phase 2)
- Updated Sprint 16 reference in ML_ARCHITECTURE.md
- Updated last update date to 2025-10-30

## Success Criteria ✅ ALL ACHIEVED

- [x] **Cero claims falsos verificables**:
  - ✅ ML_ARCHITECTURE.md: R² 0.9986 removed, replaced with "deterministic scoring"
  - ✅ API_REFERENCE.md: Endpoint count corrected, non-existent endpoints removed
  - ✅ TROUBLESHOOTING.md: Prophet metrics realistic (MAE 0.033, R² 0.49)
  - ✅ All docs: Prophet training "30min" → "24h"

- [x] **Valores hardcoded etiquetados**:
  - ✅ ROI 1,661€ marked as "theoretical baseline estimate, NOT measured" (Phase 2)
  - ✅ Prophet metrics tagged as "Last measured Oct 24, 2025 - initial benchmark"
  - ✅ Data volumes tagged "As of Oct 2025"

- [x] **Ejemplos código testeados**:
  - ✅ All TROUBLESHOOTING.md curl examples verified
  - ✅ Prophet endpoint paths fixed (`/predict/prices/models/price-forecast/status`)
  - ✅ API_REFERENCE.md endpoints tested

- [x] **5+ disclaimers añadidos**:
  - ✅ ML_ARCHITECTURE.md: 87-line comprehensive "Limitaciones y Disclaimers" section
  - ✅ CLAUDE.md: "System Limitations & Disclaimers" section (ML, Testing, Security, Monitoring)
  - ✅ README.md: "Limitations & Disclaimers" section
  - ✅ Total disclaimers: 20+ warnings/limitations documented

- [x] **MLflow references: 0 (in scope files)**:
  - ✅ TROUBLESHOOTING.md: MLflow section completely removed (lines 165-221)
  - ✅ ML_ARCHITECTURE.md: No MLflow references
  - ✅ API_REFERENCE.md: No MLflow references
  - ✅ CLAUDE.md: No MLflow references
  - ⚠️ Legacy docs (PREVENTION_CHECKLIST.md, MONITORING_GUIDE.md, etc.): Out of scope

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
