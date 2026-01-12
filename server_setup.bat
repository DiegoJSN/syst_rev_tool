@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  py -3 -m venv venv 2>nul || python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt

if not exist ".env" (
  echo DATABASE_URL=postgresql://review_user:TU_PASSWORD@100.104.194.28:5432/systrev_db> .env
  echo SECRET_KEY=change-me>> .env
)

echo.
echo Setup terminado. Revisa .env y luego ejecuta run.bat
pause
