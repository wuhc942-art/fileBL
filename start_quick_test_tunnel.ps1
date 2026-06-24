param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$env:PYTHONUTF8 = "1"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared is not installed or not in PATH. Install it first, then rerun this script."
}

$dashboard = Start-Process -FilePath "python" `
    -ArgumentList @("$scriptRoot\app_server.py", "--host", "127.0.0.1", "--port", $Port, "--no-browser") `
    -PassThru `
    -WindowStyle Hidden

try {
    Start-Sleep -Seconds 2
    Write-Host "Local dashboard: http://127.0.0.1:$Port/"
    Write-Host "Starting a temporary Cloudflare quick tunnel. Use only for short tests."
    cloudflared tunnel --url "http://127.0.0.1:$Port"
}
finally {
    if ($dashboard -and -not $dashboard.HasExited) {
        Stop-Process -Id $dashboard.Id -Force
    }
}
