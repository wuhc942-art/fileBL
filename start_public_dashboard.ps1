param(
    [string]$TunnelName = "fahuo-dashboard",
    [string]$TunnelToken = "",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$env:PYTHONUTF8 = "1"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared is not installed or not in PATH. Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ first."
}

$dashboard = Start-Process -FilePath "python" `
    -ArgumentList @("$scriptRoot\app_server.py", "--host", "127.0.0.1", "--port", $Port, "--no-browser") `
    -PassThru `
    -WindowStyle Hidden

try {
    Start-Sleep -Seconds 2
    Write-Host "Local dashboard: http://127.0.0.1:$Port/"
    if ($TunnelToken) {
        Write-Host "Starting Cloudflare Tunnel by token..."
        cloudflared tunnel run --token $TunnelToken
    } else {
        Write-Host "Starting Cloudflare Tunnel: $TunnelName"
        cloudflared tunnel run $TunnelName
    }
}
finally {
    if ($dashboard -and -not $dashboard.HasExited) {
        Stop-Process -Id $dashboard.Id -Force
    }
}
