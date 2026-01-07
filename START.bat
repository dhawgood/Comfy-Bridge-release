@echo off
setlocal enabledelayedexpansion
REM Comfy Bridge - Smart Launch Script v1.2.2

cd /d "%~dp0"
echo ========================================
echo   Comfy Bridge v1.2.1
echo   Starting application...
echo ========================================
echo.

REM --- STRATEGY: Find any compatible Python (3.10 - 3.13) ---

REM 1. Try default 'python' in PATH
call :check_python "python"
if !errorlevel!==0 (
    set FOUND_CMD=python
    goto :found
)

REM 2. Try 'py' launcher (defaults to newest installed)
call :check_python "py"
if !errorlevel!==0 (
    set FOUND_CMD=py
    goto :found
)

REM 3. Try searching for specific versions via py launcher
echo [INFO] Default Python not found or too old. Searching for specific versions...

call :check_python "py -3.13"
if !errorlevel!==0 ( set FOUND_CMD=py -3.13 & goto :found )

call :check_python "py -3.12"
if !errorlevel!==0 ( set FOUND_CMD=py -3.12 & goto :found )

call :check_python "py -3.11"
if !errorlevel!==0 ( set FOUND_CMD=py -3.11 & goto :found )

call :check_python "py -3.10"
if !errorlevel!==0 ( set FOUND_CMD=py -3.10 & goto :found )

REM --- FAILURE ---
    echo.
echo [ERROR] No compatible Python version found (3.10 - 3.13).
    echo.
echo Please install Python 3.12 from python.org.
echo IMPORTANT: Check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1

REM --- SUCCESS ---
:found
echo [SUCCESS] Using compatible Python: !FOUND_CMD!
echo.
endlocal & set FINAL_CMD=%FOUND_CMD%
call scripts\run_bridge.bat "%FINAL_CMD%"
exit /b

REM --- SUBROUTINE: Check Version ---
:check_python
set "CMD=%~1"
%CMD% --version >nul 2>&1
if errorlevel 1 exit /b 1

for /f "tokens=2" %%V in ('%CMD% --version 2^>^&1') do set VER=%%V
for /f "tokens=1,2 delims=." %%a in ("!VER!") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if !MAJOR! LSS 3 exit /b 1
if !MAJOR!==3 if !MINOR! LSS 10 exit /b 1
exit /b 0
