param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$env:PYTHONUTF8 = "1"
python "$scriptRoot\app_server.py" --port $Port
