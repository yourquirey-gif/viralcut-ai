# ViralCut Local Engine

Python service that runs on the creator's computer. It is intentionally separate from the hosted web UI so long-running video capture and rendering do not run inside serverless web functions.

## Setup

Python 3.10+ is recommended for the first release.

```bash
cd services/local-engine
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Install FFmpeg and yt-dlp separately and make sure both are available on PATH.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

- Health: http://127.0.0.1:8765/health
- API docs: http://127.0.0.1:8765/docs

## Current endpoints

- `GET /health` — reports engine and binary availability.
- `GET /api/capabilities` — reports implemented engine capabilities.
- `POST /api/streams/inspect` — uses yt-dlp metadata inspection to verify a YouTube URL and report whether it is currently live. This does not record or download media.

## Security

The service binds to loopback only by default. Do not expose it directly to the public internet. Only inspect or capture streams you are authorized to record and publish.

## Next engine milestone

Implement a managed capture process using yt-dlp and FFmpeg rolling segments, with job IDs, stop/reconnect controls, bounded disk usage and real event reporting.
