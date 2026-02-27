@echo off
REM Production startup script for OEM Incident Intelligence System

echo ==========================================
echo OEM Incident Intelligence System
echo ==========================================
echo.

REM Set Python path
set PYTHONPATH=.

REM Check Python version
echo [*] Checking Python version...
python --version

REM Kill existing processes
echo [*] Checking for existing processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo [OK] Killed existing Python processes
    timeout /t 2 >nul
)

REM Start server
echo.
echo [*] Starting uvicorn server...
echo [*] Command: python -m uvicorn app:app --host 0.0.0.0 --port 8000
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8000

REM If we get here, server stopped
echo.
echo [!] Server stopped
pause
