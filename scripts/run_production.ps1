$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:DJANGO_SETTINGS_MODULE = "fintrack.production"
& .\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:8000 fintrack.wsgi:application
exit $LASTEXITCODE
