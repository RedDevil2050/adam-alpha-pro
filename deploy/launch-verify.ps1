Write-Host ">> Final Launch Verification"

# Check environment files
if (-not (Test-Path "deploy/production-config.env")) {
    Write-Host "X Production config missing"
    exit 1
}

# Verify backup system
Write-Host "Checking backup system..."
if (-not (Test-Path "backups")) {
    New-Item -Path "backups" -ItemType Directory
}

# Verify monitoring setup
Write-Host "Verifying monitoring setup..."
$maxRetries = 3
$retryCount = 0
$success = $false

while (-not $success -and $retryCount -lt $maxRetries) {
    try {
        # Check if metrics service is running
        $metricsService = Get-Process | Where-Object { $_.ProcessName -like "*metrics*" }
        if (-not $metricsService) {
            Write-Host ">> Starting metrics service..."
            Start-Process "powershell" -ArgumentList "-File `"deploy\start-metrics.ps1`"" -WindowStyle Hidden
            Start-Sleep -Seconds 5
        }

        $response = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -Method GET -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $success = $true
            Write-Host ">> Metrics endpoint responding correctly"
        } else {
            throw "Unexpected status code: $($response.StatusCode)"
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host ">> Retry $retryCount/$maxRetries: Metrics endpoint check failed. Waiting 5 seconds..."
            Start-Sleep -Seconds 5
        } else {
            Write-Host "X Metrics endpoint not responding after $maxRetries attempts"
            Write-Host "X Error details: $_"
            Write-Host "X Please ensure the metrics service is running and configured correctly"
            exit 1
        }
    }
}

# Check market data feeds
Write-Host "Testing market data feeds..."
$envContent = Get-Content "deploy/production-config.env"
$allowedPairs = ($envContent | Select-String "ALLOWED_PAIRS=(.*)").Matches.Groups[1].Value -split ','
foreach ($pair in $allowedPairs) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/market/test/$pair" -Method GET -UseBasicParsing
        if ($response.StatusCode -ne 200) { throw }
    } catch {
        Write-Host "X Market data test failed for $pair"
        exit 1
    }
}

# Verify rollback capability
Write-Host "Checking rollback readiness..."
if (-not (Test-Path "deploy\shutdown.ps1")) {
    Write-Host "X Emergency shutdown script missing"
    exit 1
}

Write-Host "`n=== Launch verification complete ===`n"
Write-Host "FINAL CHECKLIST:"

$checklist = @(
    "Production credentials configured",
    "Rate limits set",
    "Monitoring alerts configured",
    "Team notifications setup",
    "Backup schedule confirmed",
    "Emergency contacts updated"
)

$allConfirmed = $true
foreach ($item in $checklist) {
    $confirm = Read-Host "Confirm $item (y/n)"
    if ($confirm -ne "y") {
        $allConfirmed = $false
        Write-Host "X $item not confirmed"
    } else {
        Write-Host ">> $item confirmed"
    }
}

if ($allConfirmed) {
    Write-Host "`n>> All checks passed. Ready for launch.`n"
    Write-Host "Warning: This will deploy the system to production!"
    $launchConfirm = Read-Host "Type 'LAUNCH' to proceed with system deployment"
    
    if ($launchConfirm -eq "LAUNCH") {
        Write-Host "`n>> Initiating launch sequence..."
        try {
            Write-Host ">> Starting deployment process..."
            & ".\deploy\start.ps1"
            Write-Host ">> System launched successfully"
            Write-Host ">> Verifying system status..."
            Start-Sleep -Seconds 5
            $healthCheck = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -UseBasicParsing
            if ($healthCheck.StatusCode -eq 200) {
                Write-Host ">> System health check passed"
                Write-Host "`n=== SYSTEM LAUNCHED SUCCESSFULLY ===`n"
            } else {
                throw "Health check failed"
            }
        } catch {
            Write-Host "X Launch failed. Error: $_"
            Write-Host "X Initiating emergency rollback..."
            & ".\deploy\shutdown.ps1"
            exit 1
        }
    } else {
        Write-Host "Launch aborted by user"
        exit 0
    }
} else {
    Write-Host "`nX Launch checklist incomplete. Aborting."
    exit 1
}
