# ViralCut Desktop App

This folder builds a native Windows desktop shell using Electron. The app opens the ViralCut workspace in its own window, prepares the local Python environment, starts the FastAPI engine on loopback, and stops active capture jobs safely when the app exits.

## Requirements on the user's PC

- Windows 10/11, 64-bit
- Python 3.11 with the Python Launcher enabled
- FFmpeg available on PATH (first launch attempts a winget install)
- Internet connection for the dashboard, YouTube access, and initial Python package installation

## Build locally

From this folder:

```powershell
npm install
npm run dist
```

The Windows installer is created in `desktop-app/dist/`.

## First launch behavior

The app copies the engine into the user's Local AppData folder, creates a private Python virtual environment, installs the engine requirements, checks FFmpeg and starts the local API. The Whisper model is downloaded only when the user starts AI analysis for the first time.

Logs are saved under the ViralCut user data folder as `viralcut-engine.log`. Capture files and SQLite data are stored in that folder, not inside Program Files.

This app does not use paid cloud compute. Heavy processing runs on the user's PC. The dashboard UI is hosted online and requires internet access.

## Current product scope

This packages the existing capture and basic local speech-analysis foundation. Advanced semantic highlight detection, automatic 9:16 face-aware editing, final clip rendering/export and social publishing are not yet implemented.
