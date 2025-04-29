#!/bin/bash

set -e

echo "🚀 Starting Staging Environment Launch..."

# Source staging config
source deploy/staging-config.env

# Function to check if within allowed hours (IST)
check_market_hours() {
    current_hour=$(TZ=Asia/Kolkata date +%H:%M)
    if [[ "$current_hour" > "$MARKET_HOURS_START" ]] && [[ "$current_hour" < "$MARKET_HOURS_END" ]]; then
        return 0
    else
        return 1
    fi
}

# Check if we're in allowed hours
if ! check_market_hours; then
    echo "❌ Outside staging hours (${MARKET_HOURS_START}-${MARKET_HOURS_END} IST)"
    exit 1
fi

# Check system resources
echo "Checking system resources..."
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
MEM_FREE=$(free -m | awk 'NR==2{print $4}')

if [ $(echo "$CPU_USAGE > $CPU_THRESHOLD" | bc) -eq 1 ]; then
    echo "❌ CPU usage too high: $CPU_USAGE%"
    exit 1
fi

if [ $(echo "$MEM_FREE < 1024" | bc) -eq 1 ]; then
    echo "❌ Insufficient free memory: $MEM_FREE MB"
    exit 1
fi

# Initialize market data feeds
echo "Initializing market data feeds..."
IFS=',' read -ra PAIRS <<< "$ALLOWED_PAIRS"

for pair in "${PAIRS[@]}"; do
    echo "🔄 Starting market feed for $pair"
    curl -X POST -H "Content-Type: application/json" \
         -d "{\"symbol\":\"$pair\",\"active\":true}" \
         http://localhost:8000/api/market/init
    
    # Verify data flow
    if ! curl -s "http://localhost:8000/api/market/status/$pair" | grep -q "active"; then
        echo "❌ Market data initialization failed for $pair"
        exit 1
    fi
    
    echo "✅ $pair successfully initialized"
    sleep 2  # Prevent API rate limiting
done

# Start monitoring
echo "📊 Starting monitoring..."
curl -N http://localhost:8000/api/market/health/stream &
MONITOR_PID=$!

# Set up metrics endpoint
echo "Setting up metrics collection..."
curl -X POST http://localhost:8000/api/metrics/enable

# Emergency shutdown handler
trap cleanup EXIT
cleanup() {
    echo "Cleaning up..."
    kill $MONITOR_PID 2>/dev/null || true
    curl -X POST http://localhost:8000/api/market/stop
}

echo "✅ Staging environment ready!"
echo "Monitor at: http://localhost:${METRICS_PORT}"
echo "Press Ctrl+C to shutdown"

# Keep script running
wait $MONITOR_PID