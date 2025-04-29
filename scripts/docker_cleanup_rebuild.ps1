# Adjusted for PowerShell
# Step 1: Scan and diagnose Docker setup
Write-Host "🔍 Scanning Docker setup..."
docker ps -a
docker images
docker volume ls

# Step 2: Stop and remove all containers, images, and volumes
Write-Host "🛑 Stopping all running containers..."
docker ps -q | ForEach-Object { docker stop $_ }

Write-Host "🗑️ Removing all containers..."
docker ps -aq | ForEach-Object { docker rm $_ }

Write-Host "🗑️ Removing all images..."
docker images -q | ForEach-Object { docker rmi $_ -f }

Write-Host "🗑️ Removing all volumes..."
docker volume ls -q | ForEach-Object { docker volume rm $_ }

# Step 3: Rebuild Docker environment
Write-Host "🔨 Rebuilding Docker environment..."
docker-compose -f deploy/docker-compose.yml build

# Step 4: Start the system and verify health
Write-Host "🚀 Starting the system..."
docker-compose -f deploy/docker-compose.yml up -d

# Verify system health
Write-Host "🩺 Verifying system health..."
try {
    Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Out-Null
    Write-Host "🎉 Health check passed!"
} catch {
    Write-Host "❌ Health check failed. Check logs for details."
}

Write-Host "🎉 Docker system cleanup and rebuild complete!"