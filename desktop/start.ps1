$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$engine = Join-Path $root "engine"
$engineLauncher = Join-Path $engine "start-windows.bat"
$site = "https://viralcut-ai-ayuddys-projects.vercel.app"
$health = "http://127.0.0.1:8765/health"

if (-not (Test-Path $engineLauncher)) { throw "Local engine files were not found. Re-download the complete ViralCut repository." }
try { $response = Invoke-RestMethod -Uri $health -TimeoutSec 2 } catch {
  Write-Host "Starting ViralCut Local Engine on this PC..." -ForegroundColor Cyan
  Start-Process -FilePath "$env:ComSpec" -ArgumentList "/c `"$engineLauncher`"" -WorkingDirectory $engine -WindowStyle Minimized
  $response = $null
  for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    try { $response = Invoke-RestMethod -Uri $health -TimeoutSec 2; break } catch {}
  }
}
if (-not $response -or $response.status -ne "ok") { throw "Local Engine did not become ready. Open engine\\start-windows.bat to view the error, then run desktop\\INSTALL-ViralCut.bat again." }
if (-not $response.tools.ffmpeg -or -not $response.tools.yt_dlp) { throw "Local Engine started, but FFmpeg or yt-dlp is missing. Run desktop\\INSTALL-ViralCut.bat and verify the dependency setup." }

Write-Host "ViralCut Local Engine is ready." -ForegroundColor Green
$edge = "$env:ProgramFiles(x86)\\Microsoft\\Edge\\Application\\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\\Microsoft\\Edge\\Application\\msedge.exe" }
$chrome = "$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe"
if (-not (Test-Path $chrome)) { $chrome = "$env:ProgramFiles(x86)\\Google\\Chrome\\Application\\chrome.exe" }
if (Test-Path $edge) { Start-Process -FilePath $edge -ArgumentList "--app=$site" }
elseif (Test-Path $chrome) { Start-Process -FilePath $chrome -ArgumentList "--app=$site" }
else { Start-Process $site }
Write-Host "ViralCut opened. Keep the minimized Local Engine window running while capturing." -ForegroundColor Green
