$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$engine = Join-Path $root "engine"
$setup = Join-Path $engine "setup-windows.bat"

Write-Host "ViralCut Desktop setup" -ForegroundColor Cyan
Write-Host "This installs the local Python engine and its Python packages on this PC."
Write-Host "No paid cloud server is used."

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python Launcher was not found. Install Python 3.10 or newer from https://www.python.org/downloads/windows/ and enable the Python Launcher."
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "FFmpeg is missing. Trying the Windows Package Manager..." -ForegroundColor Yellow
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install --id Gyan.FFmpeg.Shared --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
      Write-Host "Automatic FFmpeg install was unsuccessful. Install FFmpeg manually and add its bin folder to PATH." -ForegroundColor Yellow
    }
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
  } else {
    Write-Host "winget is unavailable. Install FFmpeg and add its bin folder to PATH: https://ffmpeg.org/download.html" -ForegroundColor Yellow
  }
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  throw "FFmpeg is still unavailable in PATH. Finish FFmpeg installation, reopen this installer, and try again."
}

Write-Host "Installing Python dependencies. The first install can take several minutes..." -ForegroundColor Cyan
$process = Start-Process -FilePath "$env:ComSpec" -ArgumentList "/c `"$setup`"" -WorkingDirectory $engine -Wait -PassThru
if ($process.ExitCode -ne 0) {
  throw "Python engine setup failed with exit code $($process.ExitCode)."
}

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "ViralCut Desktop.lnk"
$launcher = Join-Path $PSScriptRoot "START-ViralCut.bat"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Start ViralCut with local PC processing"
$shortcut.Save()

Write-Host "Setup complete. Desktop shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host "Double-click ViralCut Desktop to start the engine and open the dashboard."
