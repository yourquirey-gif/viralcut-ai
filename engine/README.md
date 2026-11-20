ViralCut Local Engine
=====================

The local engine captures livestream media on the user's computer. Heavy media processing does not run on Vercel or in the web browser.

Requirements
------------
- Python 3.10+ (Windows 10/11 is the primary target for this first engine build)
- FFmpeg available on PATH
- yt-dlp available on PATH

Install and run
---------------

On Windows 10/11, first install Python 3.10+ and FFmpeg, then double-click setup-windows.bat once. After setup, use start-windows.bat whenever you want to run the local engine. The Windows launcher allows the stable ViralCut Vercel domain to connect to localhost.

Manual setup:

    python -m venv .venv
    # Windows PowerShell: .venv\\Scripts\\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m uvicorn app:app --host 127.0.0.1 --port 8765

FFmpeg must also be installed separately and its bin folder added to PATH. Confirm it is available with `ffmpeg -version`.

Health check: http://127.0.0.1:8765/health

For a different deployed preview domain, add its exact origin to the local engine allowlist before opening the site. The launcher already allows https://viralcut-ai-ayuddys-projects.vercel.app. PowerShell example:

    $env:VIRALCUT_ALLOWED_ORIGINS = "https://your-site.example"
    python -m uvicorn app:app --host 127.0.0.1 --port 8765

Keep the service bound to 127.0.0.1. Do not use a wildcard CORS origin or expose the engine publicly.

API
---
- GET /health — engine and dependency availability.
- POST /api/v1/jobs — validate a YouTube URL and start capture for an active livestream.
- GET /api/v1/jobs — list job metadata.
- GET /api/v1/jobs/{id} — read job state.
- POST /api/v1/jobs/{id}/stop — request capture stop.
- GET /api/v1/jobs/{id}/events — read real engine activity events.
- GET /api/v1/jobs/{id}/segments — list safely closed MP4 segments.
- GET /api/v1/jobs/{id}/segments/{path} — download a captured segment.

Capture writes 30-second MP4 segments under engine/data/segments/. Job metadata and activity events are stored in SQLite. The engine attempts to reconnect up to five times after a dropped stream, re-resolving the live media URL for each retry. It reports completed segments as they are closed. This first version supports one active capture per local engine process.

Windows 7/8.1 compatibility is not included in this first engine build. It needs a separately pinned legacy runtime and will have reduced support; these operating systems are also out of security support. Do not assume this current Python 3.10+ setup will run on Windows 7.

Important
---------
This is the capture foundation, not the finished AI clipping pipeline. It does not yet perform transcription, highlight scoring, face tracking, caption generation, vertical rendering, final clip export or social publishing. URL validation does not grant recording or publishing rights. YouTube restrictions, login requirements, regional availability and upstream changes can prevent capture. Keep this service bound to localhost; do not expose it to the public internet.
