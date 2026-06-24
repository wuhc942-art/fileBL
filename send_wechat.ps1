param(
    [Parameter(Mandatory = $true)]
    [string[]]$Files,

    [string]$Message = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Window {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$weixinPath = "C:\Program Files\Tencent\Weixin\Weixin.exe"
$wechat = Get-Process -Name Weixin -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $wechat) {
    Start-Process -FilePath $weixinPath
    Start-Sleep -Seconds 5
    $wechat = Get-Process -Name Weixin -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
}
if (-not $wechat) {
    throw "Weixin process was not found. Please confirm desktop WeChat is installed and signed in."
}

$shell = New-Object -ComObject WScript.Shell
$activated = $false
if ($wechat.MainWindowHandle -ne 0) {
    [void][Win32Window]::ShowWindow($wechat.MainWindowHandle, 9)
    Start-Sleep -Milliseconds 300
    $activated = [Win32Window]::SetForegroundWindow($wechat.MainWindowHandle)
}
if (-not $activated -and -not $shell.AppActivate($wechat.Id)) {
    $wechatTitle = -join ([char[]](0x5fae, 0x4fe1))
    [void]$shell.AppActivate($wechatTitle)
}
Start-Sleep -Milliseconds 700

$fileTransferAssistant = -join ([char[]](0x6587, 0x4ef6, 0x4f20, 0x8f93, 0x52a9, 0x624b))
Set-Clipboard -Value $fileTransferAssistant
$shell.SendKeys("^f")
Start-Sleep -Milliseconds 500
$shell.SendKeys("^v")
Start-Sleep -Seconds 1
$shell.SendKeys("{DOWN}")
Start-Sleep -Milliseconds 200
$shell.SendKeys("{ENTER}")
Start-Sleep -Seconds 2

if ($Message.Trim().Length -gt 0) {
    Set-Clipboard -Value $Message
    $shell.SendKeys("^v")
    Start-Sleep -Milliseconds 300
    $shell.SendKeys("{ENTER}")
    Start-Sleep -Milliseconds 500
}

$dropList = New-Object System.Collections.Specialized.StringCollection
foreach ($file in $Files) {
    $resolved = (Resolve-Path -LiteralPath $file).Path
    [void]$dropList.Add($resolved)
}
[System.Windows.Forms.Clipboard]::SetFileDropList($dropList)
Start-Sleep -Milliseconds 300
$shell.SendKeys("^v")
Start-Sleep -Seconds 1
$shell.SendKeys("{ENTER}")
Start-Sleep -Seconds 1

Write-Output "Tried to send files to WeChat File Transfer Assistant: $($Files -join ', ')"
