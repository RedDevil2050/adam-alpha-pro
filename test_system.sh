#!/bin/bash

echo "Starting system test..."

# Wait for services to be ready
echo "Waiting for services to be up..."
sleep 10

# Test backend health
echo "Testing backend health..."
curl -f http://localhost:8000/health
if [ $? -ne 0 ]; then
    echo "Backend health check failed"
    exit 1
fi

# Test Redis connection
echo "Testing Redis connection..."
docker exec zion-redis-1 redis-cli ping
if [ $? -ne 0 ]; then
    echo "Redis connection failed"
    exit 1
fi

# Add demo mode checks
if [ "$1" == "--demo" ]; then
    echo "Running in demonstration mode..."
    
    # Check market data quality
    echo "Verifying market data quality..."
    curl -s "http://localhost:8000/health/market" || {
        echo "Market data check failed"
        exit 1
    }
    
    # Monitor system metrics
    echo "System metrics:"
    curl -s http://localhost:8000/metrics
fi

echo "All systems operational!"
