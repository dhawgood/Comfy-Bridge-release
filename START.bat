@echo off
REM Comfy Bridge - Easy Launch Script
REM Double-click this file to start Comfy Bridge

cd /d "%~dp0"
echo ========================================
echo   Comfy Bridge v1.2.1
echo   Starting application...
echo ========================================
echo.

REM 1. Check if Python is installed and in PATH
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please ensure:
    echo   1. Python 3.10-3.13 is installed
    echo   2. Python was added to PATH during installation
    echo.
    echo Download Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM 2. Strict Version Check (Must be 3.10+)
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYTHON_VERSION=%%V
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo [ERROR] Python 3 is required. Found version %PYTHON_VERSION%.
    pause
    exit /b 1
)
if %MAJOR%==3 if %MINOR% LSS 10 (
    echo [ERROR] Python 3.10 or higher is required. Found version %PYTHON_VERSION%.
    echo Comfy Bridge requires features from Python 3.10+.
    echo Please upgrade your Python installation.
    pause
    exit /b 1
)

echo Python version detected: %PYTHON_VERSION% (Supported)
echo.

REM 3. Run the main launch script
call scripts\run_bridge.bat
