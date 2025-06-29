#!/bin/bash

# Monitor InfluxDB Data Ingestion - TFM Chocolate Factory
# =======================================================

echo "🏭 TFM Chocolate Factory - InfluxDB Monitoring System"
echo "======================================================"

while true; do
    clear
    echo "🏭 TFM Chocolate Factory - InfluxDB Real-Time Monitoring"
    echo "========================================================="
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Data size monitoring
    echo "📊 STORAGE METRICS:"
    echo "  Data Engine: $(du -sh docker/services/influxdb/data/engine/ | cut -f1)"
    echo "  Bolt DB: $(du -sh docker/services/influxdb/data/influxd.bolt | cut -f1)" 
    echo "  SQLite: $(du -sh docker/services/influxdb/data/influxd.sqlite | cut -f1)"
    echo ""
    
    # Container status
    echo "🐳 CONTAINER STATUS:"
    docker ps --filter "name=chocolate_factory" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -v "PORTS"
    echo ""
    
    # Recent logs
    echo "📝 RECENT ACTIVITY (Last 3 lines):"
    docker logs chocolate_factory_brain --tail 3 2>/dev/null | sed 's/^/  /'
    echo ""
    
    # API health check
    echo "🌐 API ENDPOINTS STATUS:"
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "  ✅ FastAPI: Healthy"
        
        # Quick data check via API
        RECORDS=$(curl -s "http://localhost:8000/influxdb/verify?hours=8760" | grep -o '"total_records":[0-9]*' | cut -d':' -f2)
        if [ ! -z "$RECORDS" ]; then
            echo "  📊 Records in DB: $RECORDS"
        fi
    else
        echo "  ❌ FastAPI: Not responding"
    fi
    
    if curl -s http://localhost:8086/health > /dev/null; then
        echo "  ✅ InfluxDB: Healthy"
    else
        echo "  ❌ InfluxDB: Not responding"
    fi
    echo ""
    
    echo "🔄 Refreshing in 10 seconds... (Ctrl+C to stop)"
    sleep 10
done