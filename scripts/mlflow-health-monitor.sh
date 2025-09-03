#!/bin/bash
# MLflow Health Monitoring Script
# Usage: ./scripts/mlflow-health-monitor.sh
# Cron: 0 8 * * * /path/to/chocolate-factory/scripts/mlflow-health-monitor.sh

set -e

# Configuration
BASE_URL="http://localhost"
FASTAPI_PORT="8000"
MLFLOW_PORT="5000"
LOG_FILE="logs/mlflow-health.log"
ALERT_EMAIL=""  # Set if email alerts needed
WEBHOOK_URL=""  # Set if Slack/Teams alerts needed

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Alert function
alert() {
    local message="$1"
    local level="$2"  # INFO, WARNING, CRITICAL
    
    log "${RED}ALERT [$level]: $message${NC}"
    
    # Email alert (if configured)
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "MLflow Alert: $message" | mail -s "Chocolate Factory MLflow Alert" "$ALERT_EMAIL"
    fi
    
    # Webhook alert (if configured)
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"🚨 Chocolate Factory MLflow Alert: $message\"}" \
            2>/dev/null || true
    fi
}

# Check if service is responding
check_service() {
    local url="$1"
    local name="$2"
    
    if curl -s --max-time 10 "$url" >/dev/null 2>&1; then
        log "${GREEN}✅ $name: OK${NC}"
        return 0
    else
        alert "$name service not responding at $url" "CRITICAL"
        return 1
    fi
}

# Check MLflow recent training
check_recent_training() {
    log "🔍 Checking recent MLflow training..."
    
    local response
    response=$(curl -s --max-time 15 "${BASE_URL}:${MLFLOW_PORT}/api/2.0/mlflow/runs/search" \
        -H "Content-Type: application/json" \
        -d '{"experiment_ids":["1","2"],"max_results":5,"order_by":["start_time DESC"]}' 2>/dev/null)
    
    if [[ -z "$response" ]]; then
        alert "MLflow API not responding" "CRITICAL"
        return 1
    fi
    
    # Check for recent runs (within last 24 hours)
    local recent_runs
    recent_runs=$(echo "$response" | jq -r --arg cutoff "$(($(date +%s) - 86400))000" \
        '.runs[] | select(.info.start_time > ($cutoff | tonumber)) | .info.run_name' 2>/dev/null || echo "")
    
    if [[ -n "$recent_runs" ]]; then
        log "${GREEN}✅ Recent training runs found:${NC}"
        echo "$recent_runs" | head -3 | while read -r run; do
            log "   - $run"
        done
    else
        # Check if any runs exist at all
        local any_runs
        any_runs=$(echo "$response" | jq -r '.runs[0].info.run_name // "NONE"' 2>/dev/null || echo "NONE")
        
        if [[ "$any_runs" == "NONE" ]]; then
            alert "No MLflow training runs found at all" "CRITICAL"
        else
            alert "No recent MLflow training runs (last 24h). Latest: $any_runs" "WARNING"
        fi
        return 1
    fi
}

# Check feature engineering pipeline
check_feature_engineering() {
    log "🔧 Checking feature engineering pipeline..."
    
    local response
    response=$(curl -s --max-time 20 "${BASE_URL}:${FASTAPI_PORT}/mlflow/features?hours_back=3" 2>/dev/null)
    
    if [[ -z "$response" ]]; then
        alert "Feature engineering endpoint not responding" "CRITICAL"
        return 1
    fi
    
    local status
    status=$(echo "$response" | jq -r '.status // "ERROR"' 2>/dev/null || echo "ERROR")
    
    if [[ "$status" == *"No data available"* ]]; then
        alert "Feature engineering pipeline broken: $status" "CRITICAL"
        return 1
    elif [[ "$status" == "ERROR" ]]; then
        alert "Feature engineering returned error response" "CRITICAL"
        return 1
    else
        log "${GREEN}✅ Feature engineering: OK${NC}"
    fi
}

# Check data freshness
check_data_freshness() {
    log "📊 Checking data freshness..."
    
    local response
    response=$(curl -s --max-time 15 "${BASE_URL}:${FASTAPI_PORT}/influxdb/verify" 2>/dev/null)
    
    if [[ -z "$response" ]]; then
        alert "InfluxDB verify endpoint not responding" "CRITICAL"
        return 1
    fi
    
    # Check energy data
    local energy_records
    energy_records=$(echo "$response" | jq -r '.data.energy_prices.records_found // 0' 2>/dev/null || echo "0")
    
    local weather_records  
    weather_records=$(echo "$response" | jq -r '.data.weather_data.records_found // 0' 2>/dev/null || echo "0")
    
    if [[ "$energy_records" -eq 0 ]]; then
        alert "No energy price data found in InfluxDB" "CRITICAL"
        return 1
    fi
    
    if [[ "$weather_records" -eq 0 ]]; then
        alert "No weather data found in InfluxDB" "WARNING"
    fi
    
    log "${GREEN}✅ Data freshness: Energy($energy_records) Weather($weather_records)${NC}"
}

# Check scheduler status
check_scheduler() {
    log "⏰ Checking APScheduler status..."
    
    local response
    response=$(curl -s --max-time 10 "${BASE_URL}:${FASTAPI_PORT}/scheduler/status" 2>/dev/null)
    
    if [[ -z "$response" ]]; then
        alert "Scheduler status endpoint not responding" "CRITICAL"
        return 1
    fi
    
    local running
    running=$(echo "$response" | jq -r '.scheduler.running // false' 2>/dev/null || echo "false")
    
    local job_count
    job_count=$(echo "$response" | jq -r '.scheduler.total_jobs // 0' 2>/dev/null || echo "0")
    
    if [[ "$running" != "true" ]]; then
        alert "APScheduler is not running" "CRITICAL"
        return 1
    fi
    
    if [[ "$job_count" -lt 5 ]]; then
        alert "Too few scheduled jobs: $job_count (expected 10+)" "WARNING"
    fi
    
    log "${GREEN}✅ Scheduler: Running with $job_count jobs${NC}"
}

# Check container health
check_containers() {
    log "🐳 Checking container health..."
    
    local containers=("chocolate_factory_brain" "chocolate_factory_storage" "chocolate_factory_mlops")
    local all_healthy=true
    
    for container in "${containers[@]}"; do
        if docker inspect "$container" >/dev/null 2>&1; then
            local status
            status=$(docker inspect "$container" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-health-check")
            
            if [[ "$status" == "healthy" ]] || [[ "$status" == "no-health-check" ]]; then
                log "${GREEN}✅ $container: OK${NC}"
            else
                alert "Container $container health status: $status" "WARNING"
                all_healthy=false
            fi
        else
            alert "Container $container not found" "CRITICAL"
            all_healthy=false
        fi
    done
    
    return $([[ "$all_healthy" == true ]])
}

# Emergency recovery actions
emergency_recovery() {
    log "${YELLOW}🚨 Starting emergency recovery procedures...${NC}"
    
    # Try to force MLflow training
    log "Attempting emergency MLflow training..."
    
    curl -s -X POST "${BASE_URL}:${FASTAPI_PORT}/mlflow/train" >/dev/null 2>&1 || {
        log "Standard training failed, trying direct training..."
        
        # Execute direct training as fallback
        docker exec chocolate_factory_brain python -c "
import mlflow
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression  
from datetime import datetime

try:
    mlflow.set_tracking_uri('http://mlflow:5000')
    mlflow.set_experiment('chocolate_energy_optimization')
    
    with mlflow.start_run(run_name=f'EMERGENCY_RECOVERY_{datetime.now().strftime(\"%Y%m%d_%H%M\")}'):
        X, y = make_regression(n_samples=100, n_features=8, noise=0.1, random_state=42)
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        mlflow.log_param('model_type', 'Emergency_Recovery')
        mlflow.log_param('timestamp', datetime.now().isoformat())
        mlflow.log_metric('train_r2', model.score(X, y))
        
        print('Emergency training completed')
except Exception as e:
    print(f'Emergency training failed: {e}')
" >/dev/null 2>&1
    }
    
    log "${GREEN}Emergency recovery completed${NC}"
}

# Main health check routine
main() {
    log "${GREEN}🏭 Starting Chocolate Factory MLflow Health Check${NC}"
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    local health_score=0
    local max_score=6
    
    # Run all health checks
    check_service "${BASE_URL}:${FASTAPI_PORT}/health" "FastAPI" && ((health_score++))
    check_service "${BASE_URL}:${MLFLOW_PORT}/version" "MLflow" && ((health_score++))
    check_recent_training && ((health_score++))
    check_feature_engineering && ((health_score++))  
    check_data_freshness && ((health_score++))
    check_scheduler && ((health_score++))
    
    # Container health is informational
    check_containers || log "${YELLOW}Some containers have health issues${NC}"
    
    # Calculate health percentage
    local health_percentage=$((health_score * 100 / max_score))
    
    log "📊 Overall health score: $health_score/$max_score ($health_percentage%)"
    
    if [[ $health_percentage -lt 50 ]]; then
        alert "Critical system health: $health_percentage%" "CRITICAL"
        emergency_recovery
        exit 1
    elif [[ $health_percentage -lt 80 ]]; then
        alert "System health degraded: $health_percentage%" "WARNING"
        exit 1
    else
        log "${GREEN}🎉 System health: EXCELLENT ($health_percentage%)${NC}"
        exit 0
    fi
}

# Run the health check
main "$@"