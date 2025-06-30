#!/bin/bash
# =============================================================================
# Node-RED Dashboard Setup Script
# TFM Chocolate Factory - Automated Dashboard Configuration
# =============================================================================

echo "🍫 Setting up Chocolate Factory Dashboard in Node-RED..."

# Container name
CONTAINER_NAME="chocolate_factory_monitor"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "❌ Error: Node-RED container '$CONTAINER_NAME' is not running"
    echo "Please start the container first: docker compose up -d nodered"
    exit 1
fi

echo "✅ Node-RED container is running"

# Install required packages
echo "📦 Installing Node-RED Dashboard packages..."

# Install node-red-dashboard
echo "Installing node-red-dashboard..."
docker exec $CONTAINER_NAME npm install node-red-dashboard

# Install node-red-contrib-influxdb
echo "Installing node-red-contrib-influxdb..."
docker exec $CONTAINER_NAME npm install node-red-contrib-influxdb

# Optional: Install additional useful nodes
echo "Installing additional helpful nodes..."
docker exec $CONTAINER_NAME npm install node-red-node-email
docker exec $CONTAINER_NAME npm install node-red-contrib-moment

echo "✅ Package installation completed"

# Restart Node-RED to load new nodes
echo "🔄 Restarting Node-RED container to load new nodes..."
docker restart $CONTAINER_NAME

# Wait for restart
echo "⏳ Waiting for Node-RED to restart..."
sleep 10

# Check if Node-RED is accessible
echo "🔍 Checking Node-RED accessibility..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:1880)

if [ "$RESPONSE" = "200" ]; then
    echo "✅ Node-RED is accessible at http://localhost:1880"
    echo "✅ Dashboard will be available at http://localhost:1880/ui"
else
    echo "⚠️  Node-RED may still be starting up. Please wait a moment and try again."
fi

echo ""
echo "🍫 Chocolate Factory Dashboard Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Open Node-RED editor: http://localhost:1880"
echo "2. Import the dashboard flow from: docker/services/nodered/flows/chocolate_factory_dashboard.json"
echo "3. Configure InfluxDB connection with your credentials"
echo "4. Deploy the flow"
echo "5. Access dashboard: http://localhost:1880/ui"
echo ""
echo "📚 Documentation: docs/NODE_RED_DASHBOARD_SETUP.md"