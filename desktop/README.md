# ViralCut Desktop (Windows 10/11)

ViralCut Desktop is a local-PC launcher for the ViralCut workspace. It starts the Python Local Engine on **127.0.0.1:8765** and opens the hosted dashboard in an Edge/Chrome app window when available.

## Install

1. Install Python 3.10+ (Python 3.11 is recommended) and enable the Python Launcher.
2. Download or clone the complete ViralCut repository to a folder that you will keep on this PC.
3. Double-click `desktop/INSTALL-ViralCut.bat`.
4. The installer checks FFmpeg, tries to install it with winget if missing, installs the Python requirements, and creates a desktop shortcut.
5. Double-click **ViralCut Desktop** on your Windows desktop.

## Daily use

- Start from the **ViralCut Desktop** shortcut.
- Keep the minimized Local Engine window running while recording or analyzing.
- The dashboard uses the engine on this PC. The livestream capture and local AI analysis do not run on Vercel.
- To stop the engine, close the minimized ViralCut Local Engine console window.

## Important limitations

- This is the first Windows desktop launcher, not yet a self-contained signed `.exe` installer. Python and FFmpeg are installed separately.
- Internet is needed to open the hosted dashboard and to resolve YouTube livestreams.
- The PC must remain powered on and connected to the internet during capture.
- Current engine milestone supports one active capture per PC, 30-second source segments, reconnect attempts, and local speech transcription/candidate ranking.
- Full semantic highlight selection, automatic 9:16 reframing, polished captions, final clip rendering/export, and social publishing are still under development.
- Keep the engine bound to localhost. Never expose port 8765 to the public internet.
- Only record and publish streams for which you have the necessary rights and permissions.
