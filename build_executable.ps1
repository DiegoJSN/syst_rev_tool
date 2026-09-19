$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv-build\Scripts\python.exe")) { python -m venv .venv-build }
& ".venv-build\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt pyinstaller==6.20.0
& ".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --noupx --console --name "SystRevTool-Demo" --add-data "templates;templates" --add-data "static;static" --add-data "example_pdfs;example_pdfs" --add-data "example_data;example_data" --exclude-module psycopg launcher.py
Write-Host ""
Write-Host "Portable folder created at: dist\SystRevTool-Demo"

