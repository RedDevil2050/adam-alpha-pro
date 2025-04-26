Write-Host "Starting system deployment..."
Set-Location $PSScriptRoot\..

# Load environment variables
$envContent = Get-Content "deploy\production-config.env"
foreach ($line in $envContent) {
    if ($line -match '^([^=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Start services
Start-Process "powershell" -ArgumentList "-File `"deploy\start-metrics.ps1`"" -WindowStyle Hidden
npm start
