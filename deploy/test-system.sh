#!/bin/bash

echo "🔍 Starting System Test..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi
echo "✅ Docker is running"

# Test docker-compose build
echo "Building containers..."
if ! docker-compose -f deploy/docker-compose.yml build; then
    echo "❌ Container build failed"
    exit 1
fi
echo "✅ Container build successful"

# Start services
echo "Starting services..."
docker-compose -f deploy/docker-compose.yml up -d

# Wait for services to be ready
sleep 10

# Test Redis
echo "Testing Redis connection..."
if ! docker-compose -f deploy/docker-compose.yml exec redis redis-cli ping | grep -q "PONG"; then
    echo "❌ Redis connection failed"
    exit 1
fi
echo "✅ Redis connection successful"

# Enhanced error diagnostics
check_service_status() {
    local service=$1
    echo "Diagnosing $service service..."
    docker-compose -f deploy/docker-compose.yml ps $service
    docker-compose -f deploy/docker-compose.yml logs --tail=50 $service
}

# Add before API health check
echo "Checking container status..."
CONTAINERS=$(docker-compose -f deploy/docker-compose.yml ps -q)
if [ -z "$CONTAINERS" ]; then
    echo "❌ No containers running!"
    echo "Checking for startup errors..."
    docker-compose -f deploy/docker-compose.yml logs
    exit 1
fi

# Replace existing API health check with enhanced version
echo "Testing API health..."
if ! curl -f -v http://localhost:8000/health 2>&1; then
    echo "❌ API health check failed"
    echo "Diagnosing API issues..."
    check_service_status api
    echo "Checking network connectivity..."
    docker network ls
    docker network inspect deploy_app-network
    echo "Checking API logs for errors..."
    docker-compose -f deploy/docker-compose.yml logs api --tail=100
    exit 1
fi
echo "✅ API health check successful"

# Test market symbols
echo "Testing market symbols access..."
if ! curl -f "http://localhost:8000/api/symbols" | grep -q "symbols"; then
    echo "❌ Market symbols check failed"
    exit 1
fi
echo "✅ Market symbols check successful"

# Check API key configuration
echo "Verifying API credentials..."
if ! curl -f -H "Authorization: Bearer $API_KEY" "http://localhost:8000/api/auth/verify"; then
    echo "❌ API key verification failed"
    exit 1
fi
echo "✅ API key verification successful"

# Add before system resources check
echo "Validating configurations..."
if [ -z "$API_KEY" ]; then
    echo "❌ API_KEY not set in environment"
    exit 1
fi

if [ -z "$ALLOWED_PAIRS" ]; then
    echo "❌ ALLOWED_PAIRS not configured"
    exit 1
fi

# Enhanced resource monitoring
echo "Checking system resources..."
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
if [ $(echo "$CPU_USAGE > 80" | bc) -eq 1 ]; then
    echo "⚠️ Warning: High CPU usage detected: $CPU_USAGE%"
fi

MEM_FREE=$(free -m | awk 'NR==2{print $4}')
DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
echo "CPU Usage: $CPU_USAGE%"
echo "Free Memory: $MEM_FREE MB"
echo "Free Disk Space: $DISK_FREE"

if [ $(echo "$MEM_FREE < 1024" | bc) -eq 1 ]; then
    echo "⚠️ Critical: Low memory available: $MEM_FREE MB"
fi

# Run basic load test
echo "Running load test..."
for i in {1..100}; do
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/symbols" &
done
wait
echo "✅ Load test completed"

# Check error logs
echo "Checking for errors in logs..."
if docker-compose -f deploy/docker-compose.yml logs --tail=100 | grep -i "error"; then
    echo "⚠️ Warning: Errors found in logs"
fi

echo "🎉 Production readiness tests completed!"
# Add before Final Checklist
echo "Verifying Market Requirements..."
echo "- Checking market data latency..."
curl -s "http://localhost:8000/api/market/latency"

echo "- Verifying price feeds..."
for pair in $(echo $ALLOWED_PAIRS | tr ',' ' '); do
    curl -s "http://localhost:8000/api/market/price/$pair"
done

echo "- Testing order endpoints..."
curl -s -X POST "http://localhost:8000/api/order/test"

echo "📝 Final Checklist:"
echo "1. Verify market data provider credentials"
echo "2. Check rate limits configuration"
echo "3. Verify trading pairs whitelist"
echo "4. Confirm risk management settings"
echo "5. Backup all configurations"

# Add at the end before cleanup
echo "Diagnostic Summary:"
echo "- Container Status: $(docker-compose -f deploy/docker-compose.yml ps --services)"
echo "- Network Status: $(docker network ls | grep deploy)"
echo "- Memory Usage: $(free -h | awk 'NR==2{print $3"/"$2}')"
echo "- Disk Usage: $(df -h / | awk 'NR==2{print $5}')"

# Cleanup
docker-compose -f deploy/docker-compose.yml down
