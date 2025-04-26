#!/bin/bash

set -e

echo "🚀 Starting Market Launch Sequence..."

# Source configurations
source deploy/production-config.env

# Run system test first
./deploy/test-system.sh

# Initialize market launch
echo "Initializing market data feeds..."
IFS=',' read -ra PAIRS <<< "$ALLOWED_PAIRS"

for pair in "${PAIRS[@]}"; do
    echo "🔄 Starting market feed for $pair"
    curl -X POST -H "Authorization: Bearer $API_KEY" \
         -H "Content-Type: application/json" \
         -d "{\"symbol\":\"$pair\",\"active\":true}" \
         http://localhost:8000/api/market/init

    # Verify data flow
    echo "Verifying market data for $pair..."
    if ! curl -s "http://localhost:8000/api/market/status/$pair" | grep -q "active"; then
        echo "❌ Market data initialization failed for $pair"
        exit 1
    fi
    
    echo "✅ $pair successfully initialized"
    sleep 5  # Stagger starts to prevent flooding
done

# Monitor initial market data
echo "📊 Monitoring market data quality..."
curl -N http://localhost:8000/api/market/health/stream &
MONITOR_PID=$!

# Set up emergency stop trigger
trap "kill $MONITOR_PID; curl -X POST http://localhost:8000/api/market/emergency-stop" SIGINT SIGTERM

echo "🎯 Market launch complete! Active pairs:"
for pair in "${PAIRS[@]}"; do
    echo "- $pair: LIVE"
done

echo "⚠️  Press Ctrl+C for emergency shutdown"
wait $MONITOR_PID
