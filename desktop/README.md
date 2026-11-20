# ViralCut Desktop for Windows 10/11

ViralCut has two Windows desktop paths:

- **Native desktop app (recommended):** built from `desktop-app/`. It opens the dashboard in its own application window and manages the local engine.
- **Launcher fallback:** `INSTALL-ViralCut.bat` and `START-ViralCut.bat` create a desktop shortcut that opens the hosted dashboard in Edge/Chrome app mode.

## Native app installer

The GitHub Actions workflow builds a Windows x64 NSIS installer when desktop or engine code changes. Open the repository's **Actions → Build Windows Desktop Installer** run and download the `ViralCut-Windows-Installer` artifact. Artifacts are retained for 14 days.

To build locally, open PowerShell in `desktop-app/` and run:

```powershell
npm install
npm run dist
```

The installer is written to `desktop-app/dist/`.

## PC requirements

- Windows 10/11, 64-bit
- Python 3.11 with the Python Launcher enabled
- FFmpeg available on PATH (the native app attempts a winget installation on first launch)
- Internet for the hosted dashboard, YouTube access and initial package installation

On first launch, the native app copies the engine into the user's Local AppData folder, creates a private Python environment, installs yt-dlp and AI packages, and starts the local API on `127.0.0.1:8765`. The Whisper model downloads only when AI analysis is started for the first time.

Capture data, logs and SQLite history are stored in the user's ViralCut application-data folder, not inside Program Files. Closing the app requests active captures to stop before shutting down the engine.

## Launcher fallback

If you are using the source repository instead of the native installer:

1. Run `INSTALL-ViralCut.bat` once.
2. Double-click the **ViralCut Desktop** shortcut.
3. Keep the minimized Local Engine console running during capture.
4. Close that console to stop the launcher-based engine.

## Important product limitations

No paid cloud compute is used. Livestream capture and current AI analysis run on the user's PC. The PC must remain powered on and connected to the internet while capturing.

The current engine milestone supports one active capture per PC, 30-second source segments, reconnect attempts, local speech transcription and basic candidate ranking. Advanced semantic highlight selection, automatic 9:16 face-aware editing, polished captions, final clip rendering/export and social publishing are still under development.

Keep the engine bound to localhost. Never expose port 8765 to the public internet. Only record and publish streams for which you have the necessary rights and permissions.
