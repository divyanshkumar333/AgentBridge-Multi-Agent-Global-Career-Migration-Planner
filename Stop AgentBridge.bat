@echo off
title Stop AgentBridge

echo ===================================================
echo             Stop AgentBridge Server
echo ===================================================
echo.

echo Checking for processes on port 8000...
set found=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing process %%a using port 8000...
    taskkill /f /t /pid %%a
    set found=1
)

if %found%==0 (
    echo No active AgentBridge server found running on port 8000.
) else (
    echo Server stopped successfully.
)

echo.
pause
