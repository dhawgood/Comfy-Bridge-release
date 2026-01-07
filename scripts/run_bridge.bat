@echo off
cd /d "%~dp0.."
echo Working Directory: %CD%
echo.

REM --- NEW: Capture the python command passed from START.bat ---
REM If run manually without arguments, default to 'python'
set SYS_PYTHON=%~1
if "%SYS_PYTHON%"=="" set SYS_PYTHON=python

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
        REM --- FIX 1: Invalidate cache if venv is broken ---
        del .deps_installed 2>nul
        goto :create_venv
    )
    goto :install_deps
)

:create_venv
REM 2. Create new venv using the SMART detected python
echo Creating virtual environment using: %SYS_PYTHON%

REM --- FIX 2: Invalidate cache before creating new venv ---
del .deps_installed 2>nul

REM --- CRITICAL FIX: Use the passed command, not hardcoded 'python' ---
%SYS_PYTHON% -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create venv!
    echo Command used: %SYS_PYTHON% -m venv venv
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
