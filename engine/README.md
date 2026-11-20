ViralCut Local Engine
=====================

The local engine captures livestream media on the user's computer. Heavy media processing does not run on Vercel or in the web browser.

Requirements
------------
- Python 3.10+
- FFmpeg available on PATH
- yt-dlp available on PATH

Install and run
---------------

    python -m venv .venv
    # Windows PowerShell: .venv\\Scripts\\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    python -m uvicorn app:app --host 127.0.0.1 --port 8765

Health check: http://127.0.0.1:8765/health

API
---
- GET /health — engine and dependency availability.
- POST /api/v1/jobs — validate a YouTube URL and start capture for an active livestream.
- GET /api/v1/jobs — list job metadata.
- GET /api/v1/jobs/{id} — read job state.
- POST /api/v1/jobs/{id}/stop — request capture stop.

Capture writes 30-second MP4 segments under engine/data/segments/. Job metadata is stored in SQLite. This first version supports one active capture per local engine process.

Important
---------
This is the capture foundation, not the finished AI clipping pipeline. URL validation does not grant recording or publishing rights. YouTube restrictions, login requirements, regional availability and upstream changes can prevent capture. Keep this service bound to localhost; do not expose it to the public internet.
