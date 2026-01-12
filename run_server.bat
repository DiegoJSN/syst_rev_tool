@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo Falta el venv. Ejecuta setup_server.bat primero.
  pause
  exit /b 1
)

REM (Opcional) comprobar que tailscale existe en PATH
where tailscale >nul 2>&1
if errorlevel 1 (
  echo No se encuentra "tailscale" en el PATH. Instala Tailscale o abre una terminal donde funcione.
  pause
  exit /b 1
)

REM Configura Serve en background (accesible en tu tailnet)
tailscale serve --bg --yes 5000

call venv\Scripts\activate
python app.py

pause
