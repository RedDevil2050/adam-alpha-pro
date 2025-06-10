@echo off
REM 🚀 Zion Market Analysis Platform - Production Deployment Script (Windows)
REM This script handles the complete deployment process for production on Windows

setlocal enabledelayedexpansion

set PROJECT_NAME=zion-market-analysis
set DOCKER_IMAGE=%PROJECT_NAME%:latest
set BACKUP_DIR=.\backups\%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%

echo ========================================
echo 🚀 Zion Market Analysis Platform
echo Production Deployment Script (Windows)
echo ========================================

if "%1"=="" (
    set DEPLOYMENT_TYPE=staging
) else (
    set DEPLOYMENT_TYPE=%1
)

echo [INFO] Starting %DEPLOYMENT_TYPE% deployment...

REM Pre-deployment checks
echo [INFO] Running pre-deployment checks...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if required environment files exist
if not exist "api_keys.env" (
    echo [ERROR] api_keys.env file not found. Please create it with required API keys.
    exit /b 1
)

if not exist "deploy\staging-config.env" (
    echo [ERROR] deploy\staging-config.env file not found.
    exit /b 1
)

echo [SUCCESS] Pre-deployment checks passed!

REM Create backup
echo [INFO] Creating backup of current state...
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup logs if they exist
if exist "logs" (
    xcopy logs "%BACKUP_DIR%\logs" /E /I /Q
)

REM Backup configuration
xcopy deploy "%BACKUP_DIR%\deploy" /E /I /Q

echo [SUCCESS] Backup created at %BACKUP_DIR%

REM Build Docker image
echo [INFO] Building Docker image...
docker build -t %DOCKER_IMAGE% .
if errorlevel 1 (
    echo [ERROR] Docker build failed!
    exit /b 1
)

echo [SUCCESS] Docker image built successfully!

REM Deploy based on type
if "%DEPLOYMENT_TYPE%"=="staging" (
    goto deploy_staging
) else if "%DEPLOYMENT_TYPE%"=="production" (
    goto deploy_production
) else if "%DEPLOYMENT_TYPE%"=="rollback" (
    goto rollback
) else (
    goto usage
)

:deploy_staging
echo [INFO] Deploying to staging environment...

REM Stop existing staging containers
docker-compose -f docker-compose.staging.yml down

REM Start staging environment
docker-compose -f docker-compose.staging.yml up -d

REM Wait for services to be ready
echo [INFO] Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Health check
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -Method Get -TimeoutSec 10 | Out-Null; Write-Host '[SUCCESS] Staging deployment successful! Health check passed.' } catch { Write-Host '[ERROR] Staging deployment failed! Health check failed.'; exit 1 }"

goto post_deployment

:deploy_production
echo [INFO] Deploying to production environment...
echo [WARNING] This will deploy to PRODUCTION environment!
set /p CONFIRM=Are you sure you want to continue? (y/N): 

if /i not "%CONFIRM%"=="y" (
    echo [INFO] Deployment cancelled.
    exit /b 0
)

REM Stop existing production containers gracefully
docker-compose down

REM Deploy with production configuration
docker-compose up -d

REM Wait for services to be ready
echo [INFO] Waiting for production services to be ready...
timeout /t 60 /nobreak >nul

REM Health check
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -Method Get -TimeoutSec 10 | Out-Null; Write-Host '[SUCCESS] Production deployment successful! Health check passed.' } catch { Write-Host '[ERROR] Production deployment failed! Health check failed.'; goto rollback }"

goto post_deployment

:rollback
echo [WARNING] Rolling back deployment...
docker-compose down
echo [WARNING] Rollback completed. Please investigate the issue.
exit /b 1

:post_deployment
echo [INFO] Running post-deployment tasks...

REM Run database migrations if needed
echo [INFO] Running database migrations...
docker-compose exec backend alembic upgrade head

REM Clear cache
echo [INFO] Clearing cache...
docker-compose exec redis redis-cli FLUSHALL

echo [SUCCESS] Post-deployment tasks completed!
echo [SUCCESS] Deployment completed successfully! 🎉
echo [INFO] Monitor the application at: http://localhost:8000
echo [INFO] Check metrics at: http://localhost:9090
goto end

:usage
echo Usage: %0 {staging^|production^|rollback}
echo.
echo Examples:
echo   %0 staging     - Deploy to staging environment
echo   %0 production  - Deploy to production environment  
echo   %0 rollback    - Rollback to previous version
exit /b 1

:end
pause
