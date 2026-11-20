@echo off
setlocal
cd /d "%~dp0"
echo Setting up ViralCut Local Engine...
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.10 or newer and enable PATH.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
where ffmpeg >nul 2>nul
if errorlevel 1 echo WARNING: FFmpeg was not found on PATH. Install FFmpeg before starting capture.
echo.
echo Setup finished. Run start-windows.bat to launch the local engine.
pause
exit /b 0
:failed
echo Setup failed. Check the error above and try again.
pause
exit /b 1
