param(
    [int]$Port = 8765,
    [switch]$ReadOnly,
    [string]$AdminToken = ""
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$env:PYTHONUTF8 = "1"
if ($ReadOnly) {
    $env:SHIPMENT_PUBLIC_READONLY = "1"
}
if ($AdminToken) {
    $env:SHIPMENT_ADMIN_TOKEN = $AdminToken
}
python "$scriptRoot\app_server.py" --port $Port
