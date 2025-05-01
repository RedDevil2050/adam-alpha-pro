# Azure Key Vault Market Deployment Script for Zion Platform
# For Windows environments

Write-Host "🚀 Starting Zion Market Analysis Platform Production Deployment..." -ForegroundColor Cyan

# Step 1: Retrieve secrets from Azure Key Vault and set them as environment variables
Write-Host "🔑 Retrieving secrets from Azure Key Vault..." -ForegroundColor Yellow

# Azure Key Vault name
$KEY_VAULT_NAME = "zion-production-kv"

# Login to Azure if not already logged in
Write-Host "Authenticating with Azure..." -ForegroundColor Yellow
try {
    $azAccount = az account show | ConvertFrom-Json
    Write-Host "Already logged in as $($azAccount.user.name)" -ForegroundColor Green
} catch {
    Write-Host "Azure login required..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Azure login failed. Please check your credentials and try again." -ForegroundColor Red
        exit 1
    }
}

# Function to retrieve secret from Key Vault and set as environment variable
function Get-AzureKeyVaultSecret {
    param(
        [string]$SecretName,
        [string]$EnvVarName
    )
    
    Write-Host "Retrieving $SecretName from Key Vault..." -ForegroundColor Yellow
    try {
        $value = az keyvault secret show --name $SecretName --vault-name $KEY_VAULT_NAME --query "value" -o tsv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to retrieve secret"
        }
        
        # Set as environment variable
        [Environment]::SetEnvironmentVariable($EnvVarName, $value, "Process")
        Write-Host "✅ Secret $SecretName retrieved and set as $EnvVarName" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to retrieve $SecretName from Key Vault: $_" -ForegroundColor Red
        exit 1
    }
}

# Retrieve all required secrets
Get-AzureKeyVaultSecret -SecretName "DbPassword" -EnvVarName "DB_PASSWORD"
Get-AzureKeyVaultSecret -SecretName "GrafanaPassword" -EnvVarName "GRAFANA_PASSWORD"
Get-AzureKeyVaultSecret -SecretName "JwtSecret" -EnvVarName "JWT_SECRET"
Get-AzureKeyVaultSecret -SecretName "ApiPassHash" -EnvVarName "API_PASS_HASH"
Get-AzureKeyVaultSecret -SecretName "AlphaVantageKey" -EnvVarName "ALPHA_VANTAGE_KEY"
Get-AzureKeyVaultSecret -SecretName "YahooFinanceApiKey" -EnvVarName "YAHOO_FINANCE_API_KEY"
Get-AzureKeyVaultSecret -SecretName "FinnhubApiKey" -EnvVarName "FINNHUB_API_KEY"
Get-AzureKeyVaultSecret -SecretName "PolygonApiKey" -EnvVarName "POLYGON_API_KEY"
Get-AzureKeyVaultSecret -SecretName "SlackWebhookUrl" -EnvVarName "SLACK_WEBHOOK_URL"
Get-AzureKeyVaultSecret -SecretName "AlertEmail" -EnvVarName "ALERT_EMAIL"

Write-Host "🔒 All secrets have been retrieved from Azure Key Vault" -ForegroundColor Green

# Step 2: Validate Docker and Docker Compose installation
Write-Host "🔍 Validating Docker configuration..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose not installed"
    }
    Write-Host "✅ Docker Compose is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose not found. Please install Docker Compose and try again." -ForegroundColor Red
    exit 1
}

# Step 3: Validate Docker Compose configuration
Write-Host "🧪 Validating Docker Compose configuration..." -ForegroundColor Yellow
try {
    docker-compose config -q
    if ($LASTEXITCODE -ne 0) {
        throw "Invalid configuration"
    }
    Write-Host "✅ Docker Compose configuration is valid" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose configuration is invalid." -ForegroundColor Red
    exit 1
}

# Step 4: Generate .env file for Docker Compose with Azure Key Vault secrets
Write-Host "📝 Generating environment configuration..." -ForegroundColor Yellow
$envContent = @"
# Environment Configuration
ENV=production
PRIMARY_PROVIDER=yahoo_finance
FALLBACK_PROVIDERS='["alpha_vantage", "web_scraper"]'
MARKET_INDEX_SYMBOL=^NSEI

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=zion_production
DB_USER=zion_production
DB_PASSWORD=$env:DB_PASSWORD

# Redis Configuration
REDIS_URL=redis://redis:6379

# API Keys and Secrets
YAHOO_FINANCE_API_KEY=$env:YAHOO_FINANCE_API_KEY
ALPHA_VANTAGE_KEY=$env:ALPHA_VANTAGE_KEY
FINNHUB_API_KEY=$env:FINNHUB_API_KEY
POLYGON_API_KEY=$env:POLYGON_API_KEY
API_PASS_HASH=$env:API_PASS_HASH
JWT_SECRET=$env:JWT_SECRET
GRAFANA_PASSWORD=$env:GRAFANA_PASSWORD

# Alert Configuration
SLACK_WEBHOOK_URL=$env:SLACK_WEBHOOK_URL
ALERT_EMAIL=$env:ALERT_EMAIL
"@

$envContent | Out-File -FilePath ".env.production" -Encoding utf8
Write-Host "✅ Environment configuration file created" -ForegroundColor Green

# Step 5: Start the system with production configuration
Write-Host "🚀 Starting production system..." -ForegroundColor Yellow
docker-compose -f docker-compose.yml --env-file .env.production up -d

# Wait for system to be ready
Write-Host "⏳ Waiting for system to be ready..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$isReady = $false

while ($retryCount -lt $maxRetries -and -not $isReady) {
    try {
        $healthResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
        if ($healthResponse.status -eq "ok") {
            $isReady = $true
            Write-Host "✅ System is ready!" -ForegroundColor Green
        } else {
            throw "System not ready"
        }
    } catch {
        Write-Host "System not ready yet, waiting..." -ForegroundColor Yellow
        $retryCount++
        Start-Sleep -Seconds 10
    }
}

if (-not $isReady) {
    Write-Host "❌ System failed to start within the expected time" -ForegroundColor Red
    docker-compose logs
    exit 1
}

# Step 6: Run system tests to verify deployment
Write-Host "🧪 Running system verification tests..." -ForegroundColor Yellow
& .\deploy\test-system.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ System verification tests failed. Rolling back deployment." -ForegroundColor Red
    docker-compose down
    exit 1
}
Write-Host "✅ System verification tests passed" -ForegroundColor Green

# Step 7: Initialize market data feeds
Write-Host "📊 Initializing market data feeds..." -ForegroundColor Yellow

# Parse deploy/production-config.env to get ALLOWED_PAIRS
$prodConfigContent = Get-Content .\deploy\production-config.env
# Find the line containing ALLOWED_PAIRS and extract the value
$prodConfigContent | Where-Object { $_ -match "ALLOWED_PAIRS=(.*)" } | Out-Null # Pipe to Out-Null to suppress output, -match populates $Matches
if ($Matches.Count -gt 0) {
    $allowedPairs = $Matches[1] -split ","
} else {
    Write-Host "❌ ALLOWED_PAIRS not found in .\deploy\production-config.env" -ForegroundColor Red
    exit 1
}


# Get auth token
$authBody = @{
    username = "admin"
    password = $env:API_PASS
} | ConvertTo-Json

$authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/token" -Method Post -Body $authBody -ContentType "application/json"
$token = $authResponse.access_token

foreach ($pair in $allowedPairs) {
    Write-Host "🔄 Starting market feed for $pair" -ForegroundColor Yellow
    
    $initBody = @{
        symbol = $pair
        active = $true
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/api/market/init" -Method Post -Headers @{Authorization = "Bearer $token"} -Body $initBody -ContentType "application/json"
        
        # Verify data flow
        Write-Host "Verifying market data for $pair..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5  # Stagger starts to prevent flooding
    } catch {
        Write-Host "❌ Market data initialization failed for $pair: ${_}" -ForegroundColor Red
        exit 1
    }
}
        Write-Host "✅ $pair successfully initialized" -ForegroundColor Green
        Start-Sleep -Seconds 5  # Stagger starts to prevent flooding
    } catch {
        Write-Host "❌ Market data initialization failed for $pair: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 8: Start monitoring
Write-Host "📈 Starting monitoring and alerting system..." -ForegroundColor Yellow
& .\deploy\start-metrics.ps1

Write-Host "✅ Zion Market Analysis Platform has been successfully deployed to production!" -ForegroundColor Green
Write-Host "🌐 API is available at: http://localhost:8000/api" -ForegroundColor Cyan
Write-Host "📊 Grafana dashboards are available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "⚠️ Press Ctrl+C to trigger emergency shutdown" -ForegroundColor Yellow

# Set up emergency stop
try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} finally {
    Write-Host "Emergency shutdown triggered" -ForegroundColor Red
    docker-compose exec backend python -c "from backend.market import emergency_stop; emergency_stop()"
}