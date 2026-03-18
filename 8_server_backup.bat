@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ======== CONFIG (EDIT THIS) ========
set "PG_BIN=C:\Program Files\PostgreSQL\18\bin"
set "DB_NAME=systrev_db"
set "OUT_DIR=H:\Mi Unidad\Backups\server_soslivestock"
set "PGHOST=localhost"
set "PGPORT=5432"
set "PGUSER=postgres"
REM =====================================

REM Timestamp YYYYMMDD_HHMMSS
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

REM Create timestamped folder
set "RUN_DIR=%OUT_DIR%\%TS%"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"

REM Filenames inside the timestamped folder
set "GLOBALS_FILE=%RUN_DIR%\%TS%_globals.sql"
set "DB_FILE=%RUN_DIR%\%TS%_%DB_NAME%.backup"

REM Log file inside the same RUN_DIR
set "LOG_FILE=%RUN_DIR%\%TS%_backup.log"

echo ==== Backup started: %date% %time% ====>> "%LOG_FILE%"
echo RUN_DIR: %RUN_DIR%>> "%LOG_FILE%"
echo GLOBALS_FILE: %GLOBALS_FILE%>> "%LOG_FILE%"
echo DB_FILE: %DB_FILE%>> "%LOG_FILE%"
echo.>> "%LOG_FILE%"

REM Checks
if not exist "%PG_BIN%\pg_dump.exe" (
  echo ERROR: pg_dump.exe not found in "%PG_BIN%".
  echo ERROR: pg_dump.exe not found in "%PG_BIN%".>> "%LOG_FILE%"
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)
if not exist "%PG_BIN%\pg_dumpall.exe" (
  echo ERROR: pg_dumpall.exe not found in "%PG_BIN%".
  echo ERROR: pg_dumpall.exe not found in "%PG_BIN%".>> "%LOG_FILE%"
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Backing up GLOBALS (roles/permissions) ===
echo === Backing up GLOBALS (roles/permissions) ===>> "%LOG_FILE%"

REM pg_dumpall writes output to the globals file; capture errors/notes in the log
"%PG_BIN%\pg_dumpall.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" --globals-only > "%GLOBALS_FILE%" 2>> "%LOG_FILE%"
if errorlevel 1 (
  echo ERROR: pg_dumpall failed.>> "%LOG_FILE%"
  echo ERROR: pg_dumpall failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Backing up DB "%DB_NAME%" ===
echo === Backing up DB "%DB_NAME%" ===>> "%LOG_FILE%"

REM pg_dump verbose output usually goes to stderr; log everything just in case
"%PG_BIN%\pg_dump.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -F c -b -v -f "%DB_FILE%" "%DB_NAME%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo ERROR: pg_dump failed.>> "%LOG_FILE%"
  echo ERROR: pg_dump failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo.>> "%LOG_FILE%"
echo ==== Backup finished: %date% %time% (exit code 0) ====>> "%LOG_FILE%"

echo.
echo Everything is correct. You can now close the terminal.
echo Files created:
echo   %GLOBALS_FILE%
echo   %DB_FILE%
echo Log saved at:
echo   %LOG_FILE%

if /i "%1"=="--no-pause" exit /b 0
pause
