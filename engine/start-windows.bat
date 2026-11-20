@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Local environment not found. Run setup-windows.bat first.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is missing. Install FFmpeg and add its bin folder to PATH.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set VIRALCUT_ALLOWED_ORIGINS=https://viralcut-ai-ayuddys-projects.vercel.app,https://viralcut-ai-beta.vercel.app
python -m uvicorn app:app --host 127.0.0.1 --port 8765
pause
