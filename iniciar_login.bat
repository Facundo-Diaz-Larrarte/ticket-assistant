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
python -m app.main login
if errorlevel 1 (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m app.main login
)
pause
