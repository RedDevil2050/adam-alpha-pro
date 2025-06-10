# Quick Market Deployment Verification Script
# Run this after deployment to verify all systems are operational

Write-Host "🔍 Zion Market Analysis Platform - Deployment Verification" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Test 1: Health Check
Write-Host "`n🏥 Testing Health Endpoints..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -TimeoutSec 10
    if ($health.status -eq "healthy" -or $health.status -eq "ok") {
        Write-Host "✅ API Health Check: PASSED" -ForegroundColor Green
    } else {
        Write-Host "⚠️ API Health Check: DEGRADED ($($health.status))" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ API Health Check: FAILED - $_" -ForegroundColor Red
}

# Test 2: Authentication
Write-Host "`n🔐 Testing Authentication..." -ForegroundColor Yellow
try {
    $authBody = @{
        username = "admin"
        password = $env:API_PASS
    } | ConvertTo-Json
    
    $authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/login" -Method Post -Body $authBody -ContentType "application/json" -TimeoutSec 10
    if ($authResponse.access_token) {
        Write-Host "✅ Authentication: PASSED" -ForegroundColor Green
        $token = $authResponse.access_token
    } else {
        throw "No access token received"
    }
} catch {
    Write-Host "❌ Authentication: FAILED - $_" -ForegroundColor Red
    exit 1
}

# Test 3: Market Analysis
Write-Host "`n📊 Testing Market Analysis..." -ForegroundColor Yellow
$testSymbols = @("RELIANCE", "TCS", "INFY")
$passedTests = 0

foreach ($symbol in $testSymbols) {
    try {
        Write-Host "Testing analysis for $symbol..." -ForegroundColor Gray
        $analysisResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/analyze/$symbol" -Method Get -Headers @{Authorization = "Bearer $token"} -TimeoutSec 30
        
        if ($analysisResponse.symbol -eq $symbol -and $analysisResponse.agents) {
            Write-Host "✅ Analysis for $symbol: PASSED ($($analysisResponse.agents.Count) agents)" -ForegroundColor Green
            $passedTests++
        } else {
            Write-Host "⚠️ Analysis for $symbol: INCOMPLETE" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Analysis for $symbol: FAILED - $_" -ForegroundColor Red
    }
}

if ($passedTests -eq $testSymbols.Count) {
    Write-Host "✅ Market Analysis: ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "⚠️ Market Analysis: $passedTests/$($testSymbols.Count) tests passed" -ForegroundColor Yellow
}

# Test 4: Database Connectivity
Write-Host "`n🗄️ Testing Database Connectivity..." -ForegroundColor Yellow
try {
    # Test through metrics endpoint which queries the database
    $metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/metrics" -Method Get -TimeoutSec 10
    Write-Host "✅ Database Connectivity: PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ Database Connectivity: FAILED - $_" -ForegroundColor Red
}

# Test 5: Redis Cache
Write-Host "`n🔄 Testing Redis Cache..." -ForegroundColor Yellow
try {
    # Test cache by running the same analysis twice and checking response times
    $startTime = Get-Date
    Invoke-RestMethod -Uri "http://localhost:8000/api/analyze/RELIANCE" -Method Get -Headers @{Authorization = "Bearer $token"} -TimeoutSec 30 | Out-Null
    $firstCallTime = (Get-Date) - $startTime
    
    $startTime = Get-Date
    Invoke-RestMethod -Uri "http://localhost:8000/api/analyze/RELIANCE" -Method Get -Headers @{Authorization = "Bearer $token"} -TimeoutSec 30 | Out-Null
    $secondCallTime = (Get-Date) - $startTime
    
    if ($secondCallTime.TotalMilliseconds -lt $firstCallTime.TotalMilliseconds * 0.5) {
        Write-Host "✅ Redis Cache: WORKING (Cache hit detected)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Redis Cache: UNKNOWN (Unable to detect cache performance)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Redis Cache: FAILED - $_" -ForegroundColor Red
}

# Test 6: Monitoring Stack
Write-Host "`n📈 Testing Monitoring Stack..." -ForegroundColor Yellow
try {
    $prometheusResponse = Invoke-WebRequest -Uri "http://localhost:9090" -Method Get -TimeoutSec 5
    if ($prometheusResponse.StatusCode -eq 200) {
        Write-Host "✅ Prometheus: RUNNING" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Prometheus: NOT ACCESSIBLE" -ForegroundColor Red
}

try {
    $grafanaResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 5
    if ($grafanaResponse.StatusCode -eq 200) {
        Write-Host "✅ Grafana: RUNNING" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Grafana: NOT ACCESSIBLE" -ForegroundColor Red
}

# Test 7: System Resources
Write-Host "`n💻 Checking System Resources..." -ForegroundColor Yellow
$cpu = Get-Counter "\Processor(_Total)\% Processor Time" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue
$memory = Get-CimInstance -ClassName Win32_OperatingSystem | ForEach-Object { [math]::Round(($_.TotalVisibleMemorySize - $_.FreePhysicalMemory) / $_.TotalVisibleMemorySize * 100, 2) }

if ($cpu -lt 80) {
    Write-Host "✅ CPU Usage: $([math]::Round($cpu, 1))% (NORMAL)" -ForegroundColor Green
} else {
    Write-Host "⚠️ CPU Usage: $([math]::Round($cpu, 1))% (HIGH)" -ForegroundColor Yellow
}

if ($memory -lt 85) {
    Write-Host "✅ Memory Usage: $memory% (NORMAL)" -ForegroundColor Green
} else {
    Write-Host "⚠️ Memory Usage: $memory% (HIGH)" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "🎯 DEPLOYMENT VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray
Write-Host "🌐 API Endpoint: http://localhost:8000/api" -ForegroundColor White
Write-Host "📊 Grafana Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "🔍 Prometheus Metrics: http://localhost:9090" -ForegroundColor White
Write-Host "`nDeployment verification completed at $(Get-Date)" -ForegroundColor Gray
