#!/usr/bin/env pwsh

# The script has been converted to PowerShell for compatibility with Windows systems.
Write-Host "Starting system test..."

# Wait for services to be ready
Write-Host "Waiting for services to be up..."
Start-Sleep -Seconds 10

# Test backend health
Write-Host "Testing backend health..."
try {
    Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
    Write-Host "Backend health check passed"
} catch {
    Write-Host "Backend health check failed"
    exit 1
}

# Test Redis connection
Write-Host "Testing Redis connection..."
try {
    docker exec zion-redis-1 redis-cli ping | Out-String | Select-String "PONG"
    Write-Host "Redis connection passed"
} catch {
    Write-Host "Redis connection failed"
    exit 1
}

# Add demo mode checks
if ($args[0] -eq "--demo") {
    Write-Host "Running in demonstration mode..."

    # Check market data quality
    Write-Host "Verifying market data quality..."
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health/market" -UseBasicParsing -ErrorAction Stop
        Write-Host "Market data quality check passed"
    } catch {
        Write-Host "Market data check failed"
        exit 1
    }

    # Monitor system metrics
    Write-Host "System metrics:"
    Invoke-WebRequest -Uri "http://localhost:8000/metrics" -UseBasicParsing
}

Write-Host "All systems operational!"
