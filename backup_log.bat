@echo off
setlocal

REM Go to project folder (this file's folder)
cd /d "%~dp0"

REM Ensure log folder exists
if not exist "backups\logs" mkdir "backups\logs"

REM Append output to log (one file per day, optional)
set "LOG=backups\logs\backup_log_%date:~6,4%%date:~3,2%%date:~0,2%.txt"

echo ==== Run started: %date% %time% ====>> "%LOG%"
call "%~dp0backup_postgres.bat" >> "%LOG%" 2>&1
echo ==== Run finished: %date% %time% (exit code %errorlevel%) ====>> "%LOG%"
echo.>> "%LOG%"

endlocal
