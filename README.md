# ViralCut AI

A local-first YouTube livestream clipping workspace. The source is a YouTube Live URL; manual video uploads are not part of this workflow.

## Product principles
- Real processing state only; no fabricated progress or analytics.
- Capture and heavy media processing run on the user's computer, not in a serverless web function.
- Clips are reviewed before publishing by default.
- Only process streams you are authorized to record, edit and publish.

## Stack
- Next.js + TypeScript — web workspace
- Python + FastAPI — local processing agent in `engine/`
- yt-dlp — inspect and resolve active YouTube livestreams
- FFmpeg — record rolling 30-second MP4 segments
- SQLite — local capture-job metadata and events
- faster-whisper — optional local CPU transcription and candidate ranking

## Windows Desktop
See [desktop/README.md](desktop/README.md). Run `desktop/INSTALL-ViralCut.bat` once, then use the **ViralCut Desktop** shortcut. The launcher starts the local engine and opens the hosted dashboard in an app-style browser window. This first desktop release is a launcher, not yet a self-contained signed EXE.

## Run the web workspace
```bash
npm install
npm run dev
```
Open http://localhost:3000.

## Run the local engine manually
See `engine/README.md`. The engine listens only on `127.0.0.1:8765`. Install Python 3.10+, FFmpeg, then run `engine/setup-windows.bat` and `engine/start-windows.bat`.

For the deployed dashboard, the Windows launcher configures the exact allowed Vercel origins. Do not expose the local engine to the public internet.

## Current implementation
- Responsive creator dashboard and navigation.
- YouTube URL format validation and browser-to-local-engine health check.
- Local API to inspect an active livestream, resolve media through yt-dlp and record 30-second FFmpeg segments.
- Capture status polling, stop requests, persistent activity timeline and local project history.
- Download links for safely closed source segments.
- Automatic reconnect attempts (up to five), with fresh media URL resolution.
- Local engine restart recovery.
- Optional local speech transcription and basic candidate ranking using faster-whisper.

The current milestone is the capture and basic analysis foundation. It supports one active capture per local engine process. It does not yet provide advanced semantic highlight selection, automatic face-aware 9:16 editing, polished captions, final clip rendering/export or social publishing.

## Roadmap
1. Harden local desktop pairing and capture reliability.
2. Build context-aware highlight detection.
3. Add vertical editing, captions and face-aware reframing.
4. Add clip review, final export and official publishing integrations.

A public YouTube URL does not grant copyright or platform permission. You are responsible for obtaining necessary rights and following platform terms.
