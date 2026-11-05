$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$env:PYTHONPATH = $null

uv run --isolated --python 3.12 --with-requirements .\requirements.txt python -m app.server
