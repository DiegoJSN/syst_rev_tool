$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
& ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
& ".venv\Scripts\python.exe" app.py
