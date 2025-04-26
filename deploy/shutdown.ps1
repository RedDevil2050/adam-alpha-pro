Write-Host "Initiating emergency shutdown..."

# Stop application processes
Get-Process | Where-Object { $_.ProcessName -like "*metrics*" } | Stop-Process -Force
Get-Process | Where-Object { $_.ProcessName -like "*node*" } | Stop-Process -Force

Write-Host "System shutdown complete"
