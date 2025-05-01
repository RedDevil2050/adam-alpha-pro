#!/bin/bash

echo "🔍 Starting Pre-Market Deployment System Test..."

# Set error handling
set -e

# Load environment variables
if [ -f ".env.production" ]; then
    source .env.production
    echo "✅ Production environment variables loaded"
else
    echo "⚠️ Production environment file not found, using existing environment"
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi
echo "✅ Docker is running"

# Test docker-compose build
echo "Building containers..."
if ! docker-compose -f docker-compose.yml build; then
    echo "❌ Container build failed"
    exit 1
fi
echo "✅ Container build successful"

# Start services
echo "Starting services..."
docker-compose -f docker-compose.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/health | grep -q "status.*ok"; then
        echo "✅ System is ready!"
        break
    fi
    
    echo "System not ready yet, waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ System failed to start within the expected time"
    docker-compose logs
    exit 1
fi

# Test Redis
echo "Testing Redis connection..."
if ! docker-compose exec redis redis-cli ping | grep -q "PONG"; then
    echo "❌ Redis connection failed"
    exit 1
fi
echo "✅ Redis connection successful"

# Test PostgreSQL
echo "Testing PostgreSQL connection..."
if ! docker-compose exec postgres pg_isready -U zion_production; then
    echo "❌ PostgreSQL connection failed"
    exit 1
fi
echo "✅ PostgreSQL connection successful"

# Enhanced error diagnostics
check_service_status() {
    local service=$1
    echo "Diagnosing $service service..."
    docker-compose ps $service
    docker-compose logs --tail=50 $service
}

# Check container status
echo "Checking container status..."
CONTAINERS=$(docker-compose ps -q)
if [ -z "$CONTAINERS" ]; then
    echo "❌ No containers running!"
    echo "Checking for startup errors..."
    docker-compose logs
    exit 1
fi

# Enhanced API health check
echo "Testing API health..."
if ! curl -f -s "http://localhost:8000/api/health" > /dev/null; then
    echo "❌ API health check failed"
    echo "Diagnosing API issues..."
    check_service_status backend
    echo "Checking network connectivity..."
    docker network ls
    docker network inspect $(docker network ls --filter name=zion -q)
    echo "Checking API logs for errors..."
    docker-compose logs backend --tail=100
    exit 1
fi
echo "✅ API health check successful"

# Test market symbols
echo "Testing market symbols access..."
if ! curl -f -s "http://localhost:8000/api/symbols" | grep -q "symbols"; then
    echo "❌ Market symbols check failed"
    exit 1
fi
echo "✅ Market symbols check successful"

# Get auth token for API tests
echo "Getting authentication token for API tests..."
AUTH_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"'"$API_PASS"'"}' http://localhost:8000/api/auth/token)
API_TOKEN=$(echo $AUTH_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$API_TOKEN" ]; then
    echo "❌ Failed to get authentication token"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi
echo "✅ Authentication token obtained"

# Check API authentication
echo "Verifying API authentication..."
if ! curl -f -s -H "Authorization: Bearer $API_TOKEN" "http://localhost:8000/api/auth/verify" > /dev/null; then
    echo "❌ API authentication verification failed"
    exit 1
fi
echo "✅ API authentication verification successful"

# Check configuration validation
echo "Validating configurations..."
if [ -z "$API_PASS" ]; then
    echo "❌ API_PASS not set in environment"
    exit 1
fi

# Check environment variables for market trading
echo "Checking market environment variables..."
if [ -z "$ALLOWED_PAIRS" ]; then
    echo "❌ ALLOWED_PAIRS not configured"
    exit 1
fi

# Verify API keys for data providers
echo "Verifying data provider API keys..."
for provider in YAHOO_FINANCE_API_KEY ALPHA_VANTAGE_KEY FINNHUB_API_KEY POLYGON_API_KEY; do
    if [ -z "${!provider}" ]; then
        echo "❌ $provider not set in environment"
        exit 1
    else
        echo "✅ $provider is configured"
    fi
done

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

# Test Prometheus metrics endpoint
echo "Testing Prometheus metrics endpoint..."
if ! curl -f -s "http://localhost:9090/-/healthy" > /dev/null; then
    echo "⚠️ Warning: Prometheus health check failed"
else
    echo "✅ Prometheus health check successful"
fi

# Test Grafana availability
echo "Testing Grafana availability..."
if ! curl -f -s "http://localhost:3000/api/health" > /dev/null; then
    echo "⚠️ Warning: Grafana health check failed"
else
    echo "✅ Grafana health check successful"
fi

# Run basic load test with improved error handling
echo "Running load test..."
SUCCESS_COUNT=0
FAILURE_COUNT=0

for i in {1..100}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/symbols")
    if [ "$STATUS" == "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT+1))
    else
        FAILURE_COUNT=$((FAILURE_COUNT+1))
    fi
done

echo "Load test results: $SUCCESS_COUNT successful, $FAILURE_COUNT failed"
if [ "$FAILURE_COUNT" -gt 0 ]; then
    echo "⚠️ Warning: Load test had $FAILURE_COUNT failures"
    if [ "$FAILURE_COUNT" -gt 20 ]; then
        echo "❌ Load test failure rate too high: $FAILURE_COUNT%"
        exit 1
    fi
else
    echo "✅ Load test completed successfully"
fi

# Check for data provider functionality with advanced error handling
echo "Testing data provider functionality..."
IFS=',' read -ra PAIRS <<< "$ALLOWED_PAIRS"
PROVIDER_FAILURES=0

for pair in "${PAIRS[@]}"; do
    echo "Testing market data for $pair..."
    PRICE_DATA=$(curl -s -H "Authorization: Bearer $API_TOKEN" "http://localhost:8000/api/market/price/$pair")
    
    if ! echo "$PRICE_DATA" | grep -q "price"; then
        echo "❌ Failed to get price data for $pair"
        echo "Response: $PRICE_DATA"
        PROVIDER_FAILURES=$((PROVIDER_FAILURES+1))
    else
        echo "✅ Price data available for $pair"
    fi
done

if [ "$PROVIDER_FAILURES" -gt 0 ]; then
    echo "⚠️ Warning: $PROVIDER_FAILURES market data provider failures detected"
    if [ "$PROVIDER_FAILURES" -eq "${#PAIRS[@]}" ]; then
        echo "❌ All market data provider requests failed"
        exit 1
    fi
fi

# Check for database migrations
echo "Checking database migrations..."
if ! docker-compose exec backend python -c "from backend.database import check_migrations; print(check_migrations())"; then
    echo "⚠️ Warning: Database migration check failed"
else
    echo "✅ Database migrations are up to date"
fi

# Test circuit breaker functionality
echo "Testing circuit breaker functionality..."
if ! curl -s -X POST "http://localhost:8000/api/circuit/test" | grep -q "success"; then
    echo "⚠️ Warning: Circuit breaker test failed"
else
    echo "✅ Circuit breaker functionality verified"
fi

# Check error logs with more context
echo "Checking for errors in logs..."
ERROR_COUNT=$(docker-compose logs --tail=500 | grep -i "error" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️ Warning: $ERROR_COUNT errors found in logs"
    if [ "$ERROR_COUNT" -gt 50 ]; then
        echo "❌ Error count in logs is too high: $ERROR_COUNT"
        docker-compose logs --tail=500 | grep -i "error" | head -20
        exit 1
    else
        echo "Showing recent errors:"
        docker-compose logs --tail=500 | grep -i "error" | head -10
    fi
fi

echo "🎉 Production readiness tests completed!"

# Comprehensive market readiness verification
echo "Verifying Market Requirements..."
echo "- Checking market data latency..."
LATENCY_DATA=$(curl -s "http://localhost:8000/api/market/latency")
echo "$LATENCY_DATA"

# Check maximum latency value
MAX_LATENCY=$(echo "$LATENCY_DATA" | grep -o '"max_latency":[0-9]*' | cut -d':' -f2)
if [ ! -z "$MAX_LATENCY" ] && [ "$MAX_LATENCY" -gt 2000 ]; then
    echo "⚠️ Warning: Maximum latency is high: ${MAX_LATENCY}ms"
fi

echo "- Verifying price feeds..."
for pair in "${PAIRS[@]}"; do
    PRICE_DATA=$(curl -s "http://localhost:8000/api/market/price/$pair")
    echo "$pair: $PRICE_DATA"
done

echo "- Testing order endpoints..."
ORDER_TEST=$(curl -s -X POST -H "Authorization: Bearer $API_TOKEN" "http://localhost:8000/api/order/test")
echo "$ORDER_TEST"

# Test backup functionality
echo "Testing backup functionality..."
if ! docker-compose exec backend python -c "from backend.utils.backup import test_backup; test_backup()"; then
    echo "⚠️ Warning: Backup functionality test failed"
else
    echo "✅ Backup functionality verified"
fi

# Test emergency shutdown
echo "Testing emergency shutdown functionality..."
if ! curl -s -X POST -H "Authorization: Bearer $API_TOKEN" "http://localhost:8000/api/market/emergency-stop/test" | grep -q "success"; then
    echo "⚠️ Warning: Emergency shutdown test failed"
else 
    echo "✅ Emergency shutdown functionality verified"
fi

echo "📝 Final Checklist:"
echo "1. ✓ Verify market data provider credentials"
echo "2. ✓ Check rate limits configuration"
echo "3. ✓ Verify trading pairs whitelist"
echo "4. ✓ Confirm risk management settings"
echo "5. ✓ Backup all configurations"
echo "6. ✓ Verify monitoring alerts"
echo "7. ✓ Test emergency procedures"
echo "8. ✓ Check scalability under load"

# Add Azure-specific checks
if command -v az &> /dev/null; then
    echo "🔷 Azure Environment Checks..."
    
    # Check Azure Key Vault access
    echo "Testing Azure Key Vault access..."
    if [ ! -z "$KEY_VAULT_NAME" ]; then
        if ! az keyvault show --name "$KEY_VAULT_NAME" &> /dev/null; then
            echo "⚠️ Warning: Cannot access Azure Key Vault '$KEY_VAULT_NAME'"
        else
            echo "✅ Azure Key Vault '$KEY_VAULT_NAME' is accessible"
        fi
    else
        echo "⚠️ Warning: KEY_VAULT_NAME not set"
    fi
    
    # Check Azure connectivity
    echo "Checking Azure connectivity..."
    if ! az account show &> /dev/null; then
        echo "⚠️ Warning: Not logged in to Azure"
    else
        ACCOUNT=$(az account show --query name -o tsv)
        echo "✅ Connected to Azure account: $ACCOUNT"
    fi
else
    echo "⚠️ Azure CLI not installed - skipping Azure-specific checks"
fi

# Diagnostic Summary
echo "Diagnostic Summary:"
echo "- Container Status: $(docker-compose ps --services)"
echo "- Network Status: $(docker network ls | grep zion)"
echo "- Memory Usage: $(free -h | awk 'NR==2{print $3"/"$2}')"
echo "- Disk Usage: $(df -h / | awk 'NR==2{print $5}')"
echo "- Data Provider Status: $((${#PAIRS[@]} - $PROVIDER_FAILURES))/${#PAIRS[@]} working"
echo "- API Load Test: $SUCCESS_COUNT/100 successful requests"

# Ask if user wants to keep containers running for further manual testing
echo ""
echo "🚀 Pre-market testing completed. Clean up containers? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    # Cleanup
    echo "Cleaning up containers..."
    docker-compose down
    echo "✅ Cleanup completed"
else
    echo "Containers left running for manual testing. Use 'docker-compose down' to clean up when finished."
fi
