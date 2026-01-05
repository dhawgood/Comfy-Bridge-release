@echo off
cd /d "%~dp0.."
echo Working Directory: %CD%
echo.

REM 1. Check if venv exists and is valid
if exist "venv\Scripts\python.exe" (
    echo Using existing virtual environment...
    call venv\Scripts\activate
    if errorlevel 1 (
        echo [WARNING] Failed to activate existing venv, recreating...
        rmdir /s /q venv 2>nul
        if exist "venv" (
            ren venv venv_old 2>nul
        )
        goto :create_venv
    )
    goto :install_deps
)

:create_venv
REM 2. Create new venv only if it doesn't exist or is broken
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv!
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Failed to activate venv!
    pause
    exit /b 1
)

:install_deps
REM 3. Ensure pip is present (Fixes some broken Python installs)
python -m ensurepip >nul 2>&1

REM 4. Install/update dependencies (With Speed Optimization)
if exist ".deps_installed" (
    echo Dependencies already installed. Skipping check...
) else (
    echo Installing dependencies...
    python -m pip install --upgrade pip --quiet --disable-pip-version-check 2>nul
    python -m pip install -r requirements.txt --quiet
    
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    REM Create marker file so we don't check again next time
    echo done > .deps_installed
)

REM 5. Run app
echo Launching Comfy Bridge...
python run_bridge.py
