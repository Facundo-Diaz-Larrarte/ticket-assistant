@echo off
title Ticket Assistant - Iniciar Sesion en Eden
color 0B
echo ===================================================
echo     INICIAR SESION EN EDEN ENTRADAS
echo ===================================================
echo.
echo Se abrira una ventana de navegador. Inicia sesion con tu cuenta
echo de Eden y luego presiona Enter aqui para guardar tu sesion.
echo.
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m app.main login
) else (
    py -m app.main login 2>nul || python -m app.main login
)
pause
