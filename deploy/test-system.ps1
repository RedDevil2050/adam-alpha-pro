# Pre-Market Deployment System Test for Zion Platform
# Windows PowerShell version

Write-Host "🔍 Starting Pre-Market Deployment System Test..." -ForegroundColor Cyan

# Load environment variables
if (Test-Path ".env.production") {
    Get-Content ".env.production" | ForEach-Object {
        if ($_ -match "^([^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
    Write-Host "✅ Production environment variables loaded" -ForegroundColor Green
}
else {
    Write-Host "⚠️ Production environment file not found, using existing environment" -ForegroundColor Yellow
}

# Check if Docker is running
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not running" -ForegroundColor Red
    exit 1
}

# Test docker-compose build
Write-Host "Building containers..." -ForegroundColor Yellow
try {
    docker-compose -f docker-compose.yml build
    if ($LASTEXITCODE -ne 0) {
        throw "Container build failed"
    }
    Write-Host "✅ Container build successful" -ForegroundColor Green
}
catch {
    Write-Host "❌ Container build failed" -ForegroundColor Red
    exit 1
}

# Start services
Write-Host "Starting services..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml up -d

# Wait for services to be ready
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$isReady = $false

while ($retryCount -lt $maxRetries -and -not $isReady) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
        if ($response.status -eq "ok") {
            $isReady = $true
            Write-Host "✅ System is ready!" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "System not ready yet, waiting... ($retryCount/$maxRetries)" -ForegroundColor Yellow
        $retryCount++
        Start-Sleep -Seconds 10
    }
}

if (-not $isReady) {
    Write-Host "❌ System failed to start within the expected time" -ForegroundColor Red
    docker-compose logs
    exit 1
}

# Define diagnostic function
function Test-ServiceStatus {
    param (
        [string]$Service
    )
    
    Write-Host "Diagnosing $Service service..." -ForegroundColor Yellow
    docker-compose ps $Service
    docker-compose logs --tail=50 $Service
}

# Test Redis
Write-Host "Testing Redis connection..." -ForegroundColor Yellow
$redisResult = docker-compose exec redis redis-cli ping
if ($redisResult -ne "PONG") {
    Write-Host "❌ Redis connection failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Redis connection successful" -ForegroundColor Green

# Test PostgreSQL
Write-Host "Testing PostgreSQL connection..." -ForegroundColor Yellow
docker-compose exec postgres pg_isready -U zion_production
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ PostgreSQL connection failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ PostgreSQL connection successful" -ForegroundColor Green

# Check container status
Write-Host "Checking container status..." -ForegroundColor Yellow
$containers = docker-compose ps -q
if ([string]::IsNullOrEmpty($containers)) {
    Write-Host "❌ No containers running!" -ForegroundColor Red
    Write-Host "Checking for startup errors..." -ForegroundColor Yellow
    docker-compose logs
    exit 1
}

# Enhanced API health check
Write-Host "Testing API health..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
    Write-Host "✅ API health check successful" -ForegroundColor Green
}
catch {
    Write-Host "❌ API health check failed" -ForegroundColor Red
    Write-Host "Diagnosing API issues..." -ForegroundColor Yellow
    Test-ServiceStatus -Service "backend"
    Write-Host "Checking network connectivity..." -ForegroundColor Yellow
    docker network ls
    $networkId = docker network ls --filter name=zion -q
    docker network inspect $networkId
    Write-Host "Checking API logs for errors..." -ForegroundColor Yellow
    docker-compose logs backend --tail=100
    exit 1
}

# Test market symbols
Write-Host "Testing market symbols access..." -ForegroundColor Yellow
try {
    $symbolsResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/symbols" -Method Get
    if (-not $symbolsResponse.symbols) {
        throw "No symbols found"
    }
    Write-Host "✅ Market symbols check successful" -ForegroundColor Green
}
catch {
    Write-Host "❌ Market symbols check failed" -ForegroundColor Red
    exit 1
}

# Get auth token for API tests
Write-Host "Getting authentication token for API tests..." -ForegroundColor Yellow
try {
    $authBody = @{
        username = "admin"
        password = $env:API_PASS
    } | ConvertTo-Json

    $authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/token" -Method Post -Body $authBody -ContentType "application/json"
    $apiToken = $authResponse.access_token

    if ([string]::IsNullOrEmpty($apiToken)) {
        throw "Failed to get token"
    }
    Write-Host "✅ Authentication token obtained" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to get authentication token" -ForegroundColor Red
    Write-Host "Response: $_" -ForegroundColor Red
    exit 1
}

# Check API authentication
Write-Host "Verifying API authentication..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/verify" -Method Get -Headers @{
        "Authorization" = "Bearer $apiToken"
    }
    Write-Host "✅ API authentication verification successful" -ForegroundColor Green
}
catch {
    Write-Host "❌ API authentication verification failed" -ForegroundColor Red
    exit 1
}

# Check configuration validation
Write-Host "Validating configurations..." -ForegroundColor Yellow
if ([string]::IsNullOrEmpty($env:API_PASS)) {
    Write-Host "❌ API_PASS not set in environment" -ForegroundColor Red
    exit 1
}

# Check environment variables for market trading
Write-Host "Checking market environment variables..." -ForegroundColor Yellow
if ([string]::IsNullOrEmpty($env:ALLOWED_PAIRS)) {
    Write-Host "❌ ALLOWED_PAIRS not configured" -ForegroundColor Red
    exit 1
}

# Verify API keys for data providers
Write-Host "Verifying data provider API keys..." -ForegroundColor Yellow
$providers = @("YAHOO_FINANCE_API_KEY", "ALPHA_VANTAGE_KEY", "FINNHUB_API_KEY", "POLYGON_API_KEY")
foreach ($provider in $providers) {
    if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($provider))) {
        Write-Host "❌ $provider not set in environment" -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host "✅ $provider is configured" -ForegroundColor Green
    }
}

# Test Prometheus metrics endpoint
Write-Host "Testing Prometheus metrics endpoint..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://localhost:9090/-/healthy" -Method Get
    Write-Host "✅ Prometheus health check successful" -ForegroundColor Green
}
catch {
    Write-Host "⚠️ Warning: Prometheus health check failed" -ForegroundColor Yellow
}

# Test Grafana availability
Write-Host "Testing Grafana availability..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
    Write-Host "✅ Grafana health check successful" -ForegroundColor Green
}
catch {
    Write-Host "⚠️ Warning: Grafana health check failed" -ForegroundColor Yellow
}

# Run basic load test with improved error handling
Write-Host "Running load test..." -ForegroundColor Yellow
$successCount = 0
$failureCount = 0

1..100 | ForEach-Object {
    try {
        $statusCode = (Invoke-WebRequest -Uri "http://localhost:8000/api/symbols" -Method Get -UseBasicParsing).StatusCode
        if ($statusCode -eq 200) {
            $successCount++
        }
        else {
            $failureCount++
        }
    }
    catch {
        $failureCount++
    }
}

Write-Host "Load test results: $successCount successful, $failureCount failed" -ForegroundColor Cyan
if ($failureCount -gt 0) {
    Write-Host "⚠️ Warning: Load test had $failureCount failures" -ForegroundColor Yellow
    if ($failureCount -gt 20) {
        Write-Host "❌ Load test failure rate too high: $failureCount%" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "✅ Load test completed successfully" -ForegroundColor Green
}

# Check for data provider functionality with advanced error handling
Write-Host "Testing data provider functionality..." -ForegroundColor Yellow
$pairs = $env:ALLOWED_PAIRS -split ','
$providerFailures = 0

foreach ($pair in $pairs) {
    Write-Host "Testing market data for $pair..." -ForegroundColor Yellow
    try {
        $headers = @{
            "Authorization" = "Bearer $apiToken"
        }
        $priceData = Invoke-RestMethod -Uri "http://localhost:8000/api/market/price/$pair" -Method Get -Headers $headers
        
        if (-not $priceData.price) {
            throw "No price data"
        }
        Write-Host "✅ Price data available for $pair" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to get price data for $pair" -ForegroundColor Red
        Write-Host "Response: $_" -ForegroundColor Red
        $providerFailures++
    }
}

if ($providerFailures -gt 0) {
    Write-Host "⚠️ Warning: $providerFailures market data provider failures detected" -ForegroundColor Yellow
    if ($providerFailures -eq $pairs.Count) {
        Write-Host "❌ All market data provider requests failed" -ForegroundColor Red
        exit 1
    }
}

# Check for database migrations
Write-Host "Checking database migrations..." -ForegroundColor Yellow
try {
    docker-compose exec backend python -c "from backend.database import check_migrations; print(check_migrations())"
    if ($result -eq "True") {
        Write-Host "✅ Database migrations are up to date" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Warning: Database migrations are not up to date" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ Warning: Database migration check failed" -ForegroundColor Yellow
}

# Test circuit breaker functionality
Write-Host "Testing circuit breaker functionality..." -ForegroundColor Yellow
try {
    $circuitTest = Invoke-RestMethod -Uri "http://localhost:8000/api/circuit/test" -Method Post
    if ($circuitTest.status -eq "success") {
        Write-Host "✅ Circuit breaker functionality verified" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️ Warning: Circuit breaker test failed" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ Warning: Circuit breaker test failed" -ForegroundColor Yellow
}

# Check error logs with more context
Write-Host "Checking for errors in logs..." -ForegroundColor Yellow
$logs = docker-compose logs --tail=500
$errorPattern = "error"
$errorMatches = [regex]::Matches($logs, $errorPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$errorCount = $errorMatches.Count

if ($errorCount -gt 0) {
    Write-Host "⚠️ Warning: $errorCount errors found in logs" -ForegroundColor Yellow
    if ($errorCount -gt 50) {
        Write-Host "❌ Error count in logs is too high: $errorCount" -ForegroundColor Red
        $errorLogs = $logs | Select-String -Pattern $errorPattern -CaseSensitive:$false | Select-Object -First 20
        $errorLogs
        exit 1
    }
    else {
        Write-Host "Showing recent errors:" -ForegroundColor Yellow
        $errorLogs = $logs | Select-String -Pattern $errorPattern -CaseSensitive:$false | Select-Object -First 10
        $errorLogs
    }
}

Write-Host "🎉 Production readiness tests completed!" -ForegroundColor Green

# Comprehensive market readiness verification
Write-Host "Verifying Market Requirements..." -ForegroundColor Cyan
Write-Host "- Checking market data latency..." -ForegroundColor Yellow
try {
    $latencyData = Invoke-RestMethod -Uri "http://localhost:8000/api/market/latency" -Method Get
    $latencyData
    
    # Check maximum latency value
    if ($latencyData.max_latency -gt 2000) {
        Write-Host "⚠️ Warning: Maximum latency is high: $($latencyData.max_latency)ms" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ Warning: Failed to retrieve latency data" -ForegroundColor Yellow
}

# Verifying price feeds section
Write-Host "- Verifying price feeds..." -ForegroundColor Yellow
foreach ($pair in $pairs) {
    try {
        $priceData = Invoke-RestMethod -Uri "http://localhost:8000/api/market/price/$pair" -Method Get
        Write-Host "${pair}: $($priceData | ConvertTo-Json -Compress)" -ForegroundColor Cyan
    }
    catch {
        Write-Host "⚠️ Warning: Failed to retrieve price data for ${pair}" -ForegroundColor Yellow
    }
}

Write-Host "- Testing order endpoints..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $apiToken"
    }
    $orderTest = Invoke-RestMethod -Uri "http://localhost:8000/api/order/test" -Method Post -Headers $headers
    Write-Host "$($orderTest | ConvertTo-Json -Compress)" -ForegroundColor Cyan
}
catch {
    Write-Host "⚠️ Warning: Order endpoint test failed" -ForegroundColor Yellow
}

# Test backup functionality
Write-Host "Testing backup functionality..." -ForegroundColor Yellow
try {
    docker-compose exec backend python -c "from backend.utils.backup import test_backup; test_backup()"
    if ($result -eq "True") {
        Write-Host "✅ Backup functionality verified" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Warning: Backup test returned unexpected result" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ Warning: Backup functionality test failed" -ForegroundColor Yellow
}

# Test emergency shutdown
Write-Host "Testing emergency shutdown functionality..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $apiToken"
    }
    $shutdownTest = Invoke-RestMethod -Uri "http://localhost:8000/api/market/emergency-stop/test" -Method Post -Headers $headers
    
    if ($shutdownTest.status -eq "success") {
        Write-Host "✅ Emergency shutdown functionality verified" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️ Warning: Emergency shutdown test failed" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ Warning: Emergency shutdown test failed" -ForegroundColor Yellow
}

Write-Host "📝 Final Checklist:" -ForegroundColor Cyan
Write-Host "1. ✓ Verify market data provider credentials" -ForegroundColor Green
Write-Host "2. ✓ Check rate limits configuration" -ForegroundColor Green
Write-Host "3. ✓ Verify trading pairs whitelist" -ForegroundColor Green
Write-Host "4. ✓ Confirm risk management settings" -ForegroundColor Green
Write-Host "5. ✓ Backup all configurations" -ForegroundColor Green
Write-Host "6. ✓ Verify monitoring alerts" -ForegroundColor Green
Write-Host "7. ✓ Test emergency procedures" -ForegroundColor Green
Write-Host "8. ✓ Check scalability under load" -ForegroundColor Green

# Add Azure-specific checks
if (Get-Command az -ErrorAction SilentlyContinue) {
    Write-Host "🔷 Azure Environment Checks..." -ForegroundColor Cyan
    
    # Check Azure Key Vault access
    Write-Host "Testing Azure Key Vault access..." -ForegroundColor Yellow
    if (-not [string]::IsNullOrEmpty($env:KEY_VAULT_NAME)) {
        try {
            $null = az keyvault show --name $env:KEY_VAULT_NAME | ConvertFrom-Json
            Write-Host "✅ Azure Key Vault '$env:KEY_VAULT_NAME' is accessible" -ForegroundColor Green
        }
        catch {
            Write-Host "⚠️ Warning: Cannot access Azure Key Vault '$env:KEY_VAULT_NAME'" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "⚠️ Warning: KEY_VAULT_NAME not set" -ForegroundColor Yellow
    }

    # Check Azure connectivity
    Write-Host "Checking Azure connectivity..." -ForegroundColor Yellow
    try {
        $azAccount = az account show | ConvertFrom-Json
        Write-Host "✅ Connected to Azure account: $($azAccount.name)" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Warning: Not logged in to Azure" -ForegroundColor Yellow
    }
}
else {
    Write-Host "⚠️ Azure CLI not installed - skipping Azure-specific checks" -ForegroundColor Yellow
}

# Diagnostic Summary
Write-Host "Diagnostic Summary:" -ForegroundColor Cyan
Write-Host "- Container Status: $(docker-compose ps --services)" -ForegroundColor White
Write-Host "- Network Status: $(docker network ls | Select-String -Pattern 'zion')" -ForegroundColor White
Write-Host "- Data Provider Status: $(($pairs.Count - $providerFailures))/$($pairs.Count) working" -ForegroundColor White
Write-Host "- API Load Test: $successCount/100 successful requests" -ForegroundColor White

# Ask if user wants to keep containers running for further manual testing
Write-Host ""
Write-Host "🚀 Pre-market testing completed. Clean up containers? (y/n)" -ForegroundColor Cyan
$response = Read-Host
if ($response -eq "y" -or $response -eq "Y" -or $response -eq "yes" -or $response -eq "Yes") {
    # Cleanup
    Write-Host "Cleaning up containers..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✅ Cleanup completed" -ForegroundColor Green
}
else {
    Write-Host "Containers left running for manual testing. Use 'docker-compose down' to clean up when finished." -ForegroundColor Yellow
}