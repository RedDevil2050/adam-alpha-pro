@echo off
title Zion Market Analysis - One-Click Frontend Connector

echo.
echo =====================================================
echo   Zion Market Analysis Platform
echo   One-Click Frontend Connector
echo =====================================================
echo.
echo Starting backend with frontend connectivity...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install fastapi uvicorn python-multipart
)

REM Start the connector
echo.
echo 🚀 Starting Zion Market Analysis Platform...
echo.
echo 📱 Frontend Integration Ready!
echo 🌐 Dashboard: http://localhost:8000
echo 📚 API Docs: http://localhost:8000/docs
echo 🔧 Test API: http://localhost:8000/api/connect/test
echo.
echo Press Ctrl+C to stop the server
echo.

python quick_connect.py

pause
