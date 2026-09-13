$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv-build\Scripts\python.exe")) { python -m venv .venv-build }
& ".venv-build\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt pyinstaller==6.16.0
& ".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --console --name "SystRevTool-Demo" --add-data "templates;templates" --add-data "static;static" --exclude-module psycopg launcher.py
Write-Host ""
Write-Host "Executable created at: dist\SystRevTool-Demo.exe"

