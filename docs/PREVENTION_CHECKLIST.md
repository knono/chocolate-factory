# MLflow Issues Prevention Checklist

**Prevent MLflow training failures before they occur**

## 🛡️ Daily Monitoring

### Automated Health Check
```bash
# Run daily at 8 AM
0 8 * * * /path/to/chocolate-factory/scripts/mlflow-health-monitor.sh
```

### Manual Quick Check (30 seconds)
```bash
# 1. Check recent MLflow runs
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search" -H "Content-Type: application/json" -d '{"experiment_ids":["1","2"],"max_results":1,"order_by":["start_time DESC"]}' | jq '.runs[0].info.run_name'

# 2. Test feature engineering
curl -s "http://localhost:8000/mlflow/features?hours_back=1" | jq '.status'

# 3. Check data freshness  
curl -s "http://localhost:8000/influxdb/verify" | jq '.data.energy_prices.records_found'
```

## 🎯 Warning Signs to Watch

### 🚨 Critical Issues (Act Immediately)
- [ ] MLflow UI shows no runs from last 48 hours
- [ ] Feature engineering returns "No raw data available" consistently  
- [ ] InfluxDB verify shows 0 energy_prices records
- [ ] Scheduler status shows stopped or 0 jobs

### ⚠️ Warning Signs (Investigate Soon)
- [ ] MLflow accuracy metrics declining over time
- [ ] Feature engineering slow response times (>30s)
- [ ] Weather data records much lower than energy records
- [ ] Container restarts in Docker logs

## 🔧 Preventive Maintenance

### Weekly Tasks
- [ ] **Review MLflow experiments** - Check model performance trends
- [ ] **Validate data quality** - Ensure consistent ingestion rates
- [ ] **Check disk space** - MLflow artifacts and InfluxDB data growth
- [ ] **Update dependencies** - Security patches for ML libraries

### Monthly Tasks  
- [ ] **Review training data coverage** - Ensure diverse seasonal patterns
- [ ] **Model performance audit** - Compare against baseline metrics
- [ ] **Backup verification** - Test restore procedures
- [ ] **Documentation updates** - Keep troubleshooting guides current

## 📊 Key Metrics to Track

### MLflow Health Metrics
- **Training frequency**: Should have runs every 30 minutes (automatic)
- **Model accuracy**: Energy R² > 0.85, Classification accuracy > 85%
- **Training duration**: <5 minutes per model
- **Artifact storage**: <1GB growth per month

### Data Pipeline Metrics  
- **Energy data**: 24 records per day minimum
- **Weather data**: 24-48 records per day  
- **Feature engineering**: <10 seconds response time
- **Data gaps**: <6 hours maximum

## 🔄 Backup Strategies

### MLflow Model Backup
```bash
# Export current models
curl -s "http://localhost:5000/api/2.0/mlflow/model-versions/search" | \
  jq '.model_versions[] | select(.current_stage=="Production")'

# Backup MLflow artifacts directory
tar -czf "mlflow-backup-$(date +%Y%m%d).tar.gz" docker/services/mlflow/artifacts/
```

### Training Data Backup
```bash  
# Export InfluxDB data
docker exec chocolate_factory_storage influx backup /backup/influxdb-$(date +%Y%m%d)

# Backup PostgreSQL MLflow metadata
docker exec chocolate_factory_postgres pg_dump -U mlflow mlflow > mlflow-db-backup-$(date +%Y%m%d).sql
```

## 🚀 Emergency Response Plan

### Level 1: Training Stopped (< 24h)
1. Check feature engineering: `curl http://localhost:8000/mlflow/features?hours_back=1`
2. Restart FastAPI container: `docker restart chocolate_factory_brain`  
3. Force manual training: `curl -X POST http://localhost:8000/mlflow/train`

### Level 2: Data Pipeline Broken (> 24h)
1. Run diagnostic commands from troubleshooting guide
2. Check InfluxDB data directly with container queries
3. Apply timezone/schema fixes if needed
4. Execute emergency direct training

### Level 3: Complete System Failure (> 48h)
1. Execute emergency recovery script: `./scripts/mlflow-health-monitor.sh`
2. Restore from backups if necessary
3. Rebuild containers with latest fixes
4. Validate end-to-end pipeline

## 🎓 Knowledge Transfer

### Team Training Points
- **InfluxDB query patterns**: Always use explicit UTC timestamps
- **Schema awareness**: Check tag structure before writing queries  
- **Error handling**: Log errors with full context
- **Testing approach**: Validate queries in InfluxDB before implementing

### Debugging Skills Required
- InfluxDB query syntax and tag filtering
- MLflow API usage and experiment management
- Docker container logs analysis
- FastAPI async background task debugging

## 📋 Pre-Deployment Checklist

### Before Any MLflow Changes
- [ ] Test feature engineering with sample data
- [ ] Validate InfluxDB connectivity and schema
- [ ] Check MLflow experiment creation and logging
- [ ] Verify background task execution
- [ ] Test error handling and recovery

### After Deployment
- [ ] Monitor logs for first 30 minutes
- [ ] Verify training runs appear in MLflow UI
- [ ] Check model accuracy metrics are reasonable  
- [ ] Test prediction endpoints with new models
- [ ] Validate scheduler continues automatic training

## 🔗 Quick Reference Links

- **MLflow UI**: http://localhost:5000
- **FastAPI Docs**: http://localhost:8000/docs
- **InfluxDB UI**: http://localhost:8086
- **Health Monitor**: `./scripts/mlflow-health-monitor.sh`

## 📝 Incident Documentation Template

When issues occur, document:

```markdown
## Incident Report: [Date] - [Brief Description]

**Timeline**: 
- [Time] - Issue first observed
- [Time] - Investigation started  
- [Time] - Root cause identified
- [Time] - Fix applied
- [Time] - System verified healthy

**Root Cause**: 
[Detailed explanation]

**Immediate Fix**: 
[What was done to restore service]

**Permanent Prevention**:
[Code changes, monitoring improvements, etc.]

**Lessons Learned**:
[What to do differently next time]
```

---
**Created**: September 3, 2025  
**Last Updated**: September 3, 2025  
**Next Review**: October 3, 2025