@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ======== CONFIG (EDIT THIS) ========
set "PG_BIN=C:\Program Files\PostgreSQL\18\bin"
set "DB_NAME=systrev_db"
set "OUT_DIR=G:\Mi Unidad\Backups\Postgres"
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

REM Checks
if not exist "%PG_BIN%\pg_dump.exe" (
  echo ERROR: pg_dump.exe not found in "%PG_BIN%".
  echo Fix PG_BIN to match your PostgreSQL version/path.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)
if not exist "%PG_BIN%\pg_dumpall.exe" (
  echo ERROR: pg_dumpall.exe not found in "%PG_BIN%".
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Backing up GLOBALS (roles/permissions) -> "%GLOBALS_FILE%" ===
"%PG_BIN%\pg_dumpall.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" --globals-only > "%GLOBALS_FILE%"
if errorlevel 1 (
  echo ERROR: pg_dumpall failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Backing up DB "%DB_NAME%" -> "%DB_FILE%" ===
"%PG_BIN%\pg_dump.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -F c -b -v -f "%DB_FILE%" "%DB_NAME%"
if errorlevel 1 (
  echo ERROR: pg_dump failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo.
echo Everything is correct. You can now close the terminal.
echo Files created:
echo   %GLOBALS_FILE%
echo   %DB_FILE%
pause
