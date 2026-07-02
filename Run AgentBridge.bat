@echo off
setlocal enabledelayedexpansion
title AgentBridge Launcher

echo ========================================================================
echo      ___                  __   ___       _     __             
echo     /   ^| ____ ____  ____/ /_ /   ^|____ (_)___/ /___ ____     
echo    / /^| ^|/ __ `/ _ \/ __  /  / __  / __/ / __  / __ `/ _ \    
echo   / ___ / /_/ /  __/ /_/ /  / /_/ / / / / /_/ / /_/ /  __/    
echo  /_/  ^|_\__, /\___/\__,_/  /_____/_/ /_/\__,_/\__, /\___/     
echo        /____/                                /____/           
echo    Global Career ^& Migration Planner
echo ========================================================================
echo.

:: 1. Verify backend/.env exists
if not exist "backend\.env" (
    echo [ERROR] Environment configuration check failed!
    echo The file "backend\.env" is missing.
    echo Please create "backend\.env" and add your NVIDIA_API_KEY.
    echo.
    pause
    exit /b 1
)
powershell -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host '  ✓ Checking environment...'"

:: 2. Verify NVIDIA_API_KEY is present
findstr /i "^NVIDIA_API_KEY=" "backend\.env" >nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] NVIDIA API key check failed!
    echo NVIDIA_API_KEY is missing from "backend\.env".
    echo Please define NVIDIA_API_KEY in "backend\.env".
    echo.
    pause
    exit /b 1
)
powershell -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host '  ✓ Loading NVIDIA API key...'"

:: 3. Kill any process already using port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /t /pid %%a >nul 2>&1
)

:: 4. Create the virtual environment if it doesn't exist
if not exist "backend\.venv" (
    py -m venv backend\.venv >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        python -m venv backend\.venv >nul 2>&1
        if !ERRORLEVEL! neq 0 (
            echo [ERROR] Failed to create virtual environment!
            echo Please verify that Python is installed.
            echo.
            pause
            exit /b 1
        )
    )
)

:: 5. Activate the virtual environment
call backend\.venv\Scripts\activate >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    echo.
    pause
    exit /b 1
)

:: 6. Verify and install dependencies
backend\.venv\Scripts\python -c "import importlib.metadata; reqs = [line.split('==')[0].split('>=')[0].split('<')[0].split('>')[0].strip() for line in open('backend/requirements.txt') if line.strip() and not line.startswith('#')]; [importlib.metadata.distribution(r) for r in reqs]" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    backend\.venv\Scripts\pip install -r backend\requirements.txt >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to install dependencies!
        echo Please check your internet connection and try again.
        echo.
        pause
        exit /b 1
    )
)

powershell -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host '  ✓ Starting backend...'"

:: 7. Start browser checker asynchronously and run FastAPI server
start /b powershell -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; while ($true) { try { $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 8000); $tcp.Close(); break; } catch { Start-Sleep -Seconds 1 } }; Write-Host '  ✓ Opening browser...'; Start-Process 'http://127.0.0.1:8000'; Write-Host '  ✓ AgentBridge is ready!'"

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] The backend server stopped unexpectedly!
    echo.
    pause

