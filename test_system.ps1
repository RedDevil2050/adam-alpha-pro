#!/usr/bin/env pwsh

# The script has been converted to PowerShell for compatibility with Windows systems.
Write-Host "Starting system test..."

# Optional: Add a delay to allow services to initialize fully
# Start-Sleep -Seconds 15

Write-Host "Waiting for services to be up and healthy..."
# Use check_readiness.py with --wait to check availability AND health/other endpoints
python .\deploy\check_readiness.py --wait --base-url http://localhost:8000
if ($LASTEXITCODE -ne 0) {
    Write-Error "System readiness check failed."
    exit 1
}

# Add more specific tests here...
# e.g., test specific API endpoints

Write-Host "System tests passed!"
exit 0
