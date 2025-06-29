#!/bin/bash

# Real Data Verification Script - TFM Chocolate Factory
# No bullshit, only facts

clear
echo "🔍 VERIFICACIÓN REAL DE DATOS - TFM CHOCOLATE FACTORY"
echo "===================================================="
echo "📅 $(date)"
echo ""

# 1. Container verification
echo "1️⃣ CONTAINERS:"
if docker ps | grep -q chocolate_factory_storage; then
    echo "  ✅ InfluxDB: Running"
else
    echo "  ❌ InfluxDB: Down"
    exit 1
fi

if docker ps | grep -q chocolate_factory_brain; then
    echo "  ✅ FastAPI: Running"
else
    echo "  ❌ FastAPI: Down"
    exit 1
fi

# 2. Data size verification
echo ""
echo "2️⃣ DATA SIZE:"
CURRENT_SIZE=$(du -sh docker/services/influxdb/data/engine/ | cut -f1)
echo "  📊 Current size: $CURRENT_SIZE"

if [[ "$CURRENT_SIZE" == "29M" ]]; then
    echo "  ⚠️  SIZE UNCHANGED - No new data ingested"
else
    echo "  📈 SIZE CHANGED - Data ingestion working"
fi

# 3. API verification
echo ""
echo "3️⃣ API ENDPOINTS:"

# REE current
if curl -s http://localhost:8000/ree/prices > /dev/null; then
    echo "  ✅ REE API: Working"
else
    echo "  ❌ REE API: Failed"
fi

# AEMET current  
if curl -s http://localhost:8000/aemet/weather > /dev/null; then
    echo "  ✅ AEMET Current: Working"
else
    echo "  ❌ AEMET Current: Failed"
fi

# InfluxDB direct
if curl -s http://localhost:8086/health > /dev/null; then
    echo "  ✅ InfluxDB Direct: Working"
else
    echo "  ❌ InfluxDB Direct: Failed"
fi

# 4. Record count verification
echo ""
echo "4️⃣ RECORD COUNTS:"

# Get real record counts
REE_COUNT=$(curl -s "http://localhost:8000/init/status" | jq '.status.historical_ree_records' 2>/dev/null || echo "ERROR")
WEATHER_COUNT=$(curl -s "http://localhost:8000/init/status" | jq '.status.historical_weather_records' 2>/dev/null || echo "ERROR")

echo "  📊 REE Records: $REE_COUNT"
echo "  🌤️ Weather Records: $WEATHER_COUNT"

# 5. Expected vs actual
echo ""
echo "5️⃣ REALITY CHECK:"
if [[ "$REE_COUNT" -gt 10000 ]]; then
    echo "  ✅ REE Data: Substantial ($REE_COUNT records)"
else
    echo "  ❌ REE Data: Insufficient ($REE_COUNT records)"
fi

if [[ "$WEATHER_COUNT" -gt 1000 ]]; then
    echo "  ✅ Weather Data: Substantial ($WEATHER_COUNT records)"
else
    echo "  ❌ Weather Data: Insufficient ($WEATHER_COUNT records)"
fi

# 6. Storage efficiency check
echo ""
echo "6️⃣ STORAGE EFFICIENCY:"
TOTAL_RECORDS=$((REE_COUNT + WEATHER_COUNT))
if [[ $TOTAL_RECORDS -gt 0 ]]; then
    # Rough calculation: 29MB / total records
    BYTES_PER_RECORD=$((29 * 1024 * 1024 / TOTAL_RECORDS))
    echo "  📈 Total Records: $TOTAL_RECORDS"
    echo "  💾 Bytes per record: ~$BYTES_PER_RECORD"
    
    if [[ $BYTES_PER_RECORD -lt 10000 ]]; then
        echo "  ✅ Storage efficiency: Good"
    else
        echo "  ⚠️  Storage efficiency: High overhead"
    fi
else
    echo "  ❌ No records to analyze"
fi

echo ""
echo "🎯 CONCLUSION:"
if [[ "$REE_COUNT" -gt 10000 && "$CURRENT_SIZE" != "29M" ]]; then
    echo "  ✅ Data ingestion working - Ready for MLflow"
elif [[ "$REE_COUNT" -gt 10000 ]]; then
    echo "  ⚠️  REE working, Weather failed - Partial ready"
else
    echo "  ❌ Data ingestion failed - NOT ready for MLflow"
fi

echo ""
echo "📝 NEXT ACTIONS:"
if [[ "$WEATHER_COUNT" -lt 1000 ]]; then
    echo "  🔧 Weather data insufficient - Use synthetic or OpenWeatherMap"
fi

if [[ "$REE_COUNT" -gt 10000 ]]; then
    echo "  🚀 REE data sufficient - Can proceed with energy models"
fi

echo ""
echo "⏰ Verification completed at $(date)"