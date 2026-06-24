param(
    [string]$Date = "",
    [switch]$NoSend
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

$env:PYTHONUTF8 = "1"

$logDir = Join-Path $scriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ([string]::IsNullOrWhiteSpace($Date)) {
    $Date = (Get-Date).ToString("yyyy-MM-dd")
}

$logFile = Join-Path $logDir "shipment-$Date.log"
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] start daily shipment summary for $Date" | Out-File -FilePath $logFile -Encoding utf8 -Append

$pythonOutput = & python "$scriptRoot\summarize_shipments.py" --config "$scriptRoot\shipment_config.json" --date $Date 2>&1
$pythonOutput | Out-File -FilePath $logFile -Encoding utf8 -Append
if ($LASTEXITCODE -ne 0) {
    throw "Summary generation failed. See $logFile"
}

$manifestLine = $pythonOutput | Where-Object { $_ -like "manifest=*" } | Select-Object -Last 1
if (-not $manifestLine) {
    throw "Summary manifest was not printed. See $logFile"
}
$manifestPath = $manifestLine.Substring("manifest=".Length)
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not (Test-Path -LiteralPath $manifest.csv) -or -not (Test-Path -LiteralPath $manifest.html)) {
    throw "Generated CSV or HTML file was not found. See $logFile"
}

if (-not $NoSend) {
    $message = "Daily shipment summary $Date is ready. Rows: $($manifest.rows); customers: $($manifest.customers); amount: $([math]::Round([double]$manifest.amount, 2))."
    & "$scriptRoot\send_wechat.ps1" -Files @($manifest.html, $manifest.csv) -Message $message 2>&1 |
        Out-File -FilePath $logFile -Encoding utf8 -Append
    if ($LASTEXITCODE -ne 0) {
        throw "WeChat send failed. See $logFile"
    }
}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] done" | Out-File -FilePath $logFile -Encoding utf8 -Append
Write-Output "Done: $($manifest.html)"
Write-Output "Done: $($manifest.csv)"
Write-Output "Log: $logFile"
