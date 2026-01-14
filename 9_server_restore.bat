@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ======== CONFIG (EDIT THIS) ========
set "PG_BIN=C:\Program Files\PostgreSQL\18\bin"
set "IN_DIR=G:\Mi Unidad\Backups\Postgres\"
set "DB_NAME=systrev_db"
set "DB_OWNER=review_user"
set "PGHOST=localhost"
set "PGPORT=5432"
set "PGUSER=postgres"
REM =====================================

REM Find newest timestamp folder under IN_DIR (by folder name, e.g., 20260114_201530)
set "LATEST_TS="
for /f "delims=" %%D in ('dir /b /ad /o:-n "%IN_DIR%" 2^>nul') do (
  set "LATEST_TS=%%D"
  goto :got_ts
)
:got_ts

if not defined LATEST_TS (
  echo ERROR: No timestamp folders found in "%IN_DIR%".
  echo Expected folders like: YYYYMMDD_HHMMSS
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

set "RUN_DIR=%IN_DIR%\%LATEST_TS%"
set "GLOBALS_FILE=%RUN_DIR%\%LATEST_TS%_globals.sql"
set "DB_FILE=%RUN_DIR%\%LATEST_TS%_%DB_NAME%.backup"

if not exist "%GLOBALS_FILE%" (
  echo ERROR: Globals file not found:
  echo   "%GLOBALS_FILE%"
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)
if not exist "%DB_FILE%" (
  echo ERROR: DB backup file not found:
  echo   "%DB_FILE%"
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

REM Checks
if not exist "%PG_BIN%\psql.exe" (
  echo ERROR: psql.exe not found in "%PG_BIN%".
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)
if not exist "%PG_BIN%\createdb.exe" (
  echo ERROR: createdb.exe not found in "%PG_BIN%".
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)
if not exist "%PG_BIN%\pg_restore.exe" (
  echo ERROR: pg_restore.exe not found in "%PG_BIN%".
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Using folder ===
echo   %RUN_DIR%
echo === Using backup files ===
echo   Globals: "%GLOBALS_FILE%"
echo   DB dump: "%DB_FILE%"
echo.

echo === Restoring GLOBALS (roles/permissions) ===
"%PG_BIN%\psql.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -d postgres -f "%GLOBALS_FILE%"
if errorlevel 1 (
  echo ERROR: Globals restore failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Dropping/recreating DB "%DB_NAME%" with owner "%DB_OWNER%" ===
"%PG_BIN%\psql.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='%DB_NAME%' AND pid <> pg_backend_pid();" >nul 2>&1

"%PG_BIN%\psql.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -d postgres -c "DROP DATABASE IF EXISTS %DB_NAME%;"
if errorlevel 1 (
  echo ERROR: Failed to drop existing DB.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

"%PG_BIN%\createdb.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -O "%DB_OWNER%" "%DB_NAME%"
if errorlevel 1 (
  echo ERROR: createdb failed. Does DB_OWNER "%DB_OWNER%" exist?
  echo Tip: it should be created by the globals restore, or create it manually.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo === Restoring DB data ===
"%PG_BIN%\pg_restore.exe" -h "%PGHOST%" -p "%PGPORT%" -U "%PGUSER%" -d "%DB_NAME%" -v "%DB_FILE%"
if errorlevel 1 (
  echo ERROR: pg_restore failed.
  echo.
  echo Press any key to close this terminal...
  pause >nul
  exit /b 1
)

echo.
echo Everything is correct. You can now close the terminal.
pause
