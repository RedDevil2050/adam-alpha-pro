Set-Location "d:\Zion\frontend"
Write-Host "Starting Zion Frontend..." -ForegroundColor Green
Start-Process -FilePath "npm" -ArgumentList "start" -Wait
