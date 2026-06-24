param(
    [string]$AppName = "fa-huo-dashboard"
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$env:PYTHONUTF8 = "1"

python -m pip show pywebview pyinstaller | Out-Null

$distDir = Join-Path $scriptRoot "dist"
$buildDir = Join-Path $scriptRoot "build"
$releaseRoot = Join-Path $scriptRoot "release"
$releaseDir = Join-Path $releaseRoot $AppName

if (Test-Path $distDir) { Remove-Item -LiteralPath $distDir -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item -LiteralPath $buildDir -Recurse -Force }
if (Test-Path $releaseDir) { Remove-Item -LiteralPath $releaseDir -Recurse -Force }

python -m PyInstaller `
    --noconfirm `
    --windowed `
    --onedir `
    --name $AppName `
    --icon (Join-Path $scriptRoot "assets\app_icon.ico") `
    --hidden-import webview.platforms.winforms `
    desktop_app.py

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $distDir $AppName) -Destination $releaseDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $scriptRoot "web") -Destination (Join-Path $releaseDir "web") -Recurse -Force
Copy-Item -LiteralPath (Join-Path $scriptRoot "shipment_config.json") -Destination (Join-Path $releaseDir "shipment_config.json") -Force
Copy-Item -LiteralPath (Join-Path $scriptRoot "assets\app_icon.ico") -Destination (Join-Path $releaseDir "app_icon.ico") -Force

New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir "uploads") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir "reports") | Out-Null

$readme = @(
    "# Shipment Dashboard Desktop",
    "",
    "Double-click:",
    "",
    "fa-huo-dashboard.exe or the generated dashboard exe",
    "",
    "Data folders:",
    "",
    "- data\history.sqlite: history database",
    "- uploads\: upload cache",
    "- reports\: report packages",
    "- shipment_config.json: business rules",
    "",
    "Copy the whole folder to another computer."
) -join [Environment]::NewLine

Set-Content -LiteralPath (Join-Path $releaseDir "README.txt") -Value $readme -Encoding UTF8

Write-Host "Desktop package created:"
Write-Host $releaseDir
