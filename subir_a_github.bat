@echo off
title Subir proyecto a GitHub
color 0B
echo ===================================================
echo        SUBIENDO PROYECTO A GITHUB
echo ===================================================
echo.
cd /d "%~dp0"
git push -u origin main
echo.
if errorlevel 0 (
    echo [OK] Repositorio subido exitosamente a GitHub!
) else (
    echo [INFO] Si te pidio autorizacion, confirma en la ventana de tu navegador.
)
echo.
pause
