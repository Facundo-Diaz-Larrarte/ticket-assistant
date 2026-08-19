@echo off
title Ticket Assistant - Monitor 24/7
color 0A
echo ===================================================
echo     INICIANDO TICKET ASSISTANT MONITOR 24/7
echo ===================================================
echo.
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m app.main monitor
) else (
    py -m app.main monitor 2>nul || python -m app.main monitor
)
pause
