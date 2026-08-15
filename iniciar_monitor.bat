@echo off
title Ticket Assistant - Monitor 24/7
color 0A
echo ===================================================
echo     INICIANDO TICKET ASSISTANT MONITOR 24/7
echo ===================================================
echo.
cd /d "%~dp0"
python -m app.main monitor
if errorlevel 1 (
    echo.
    echo Probando con ruta directa de Python...
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m app.main monitor
)
pause
