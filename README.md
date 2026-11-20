# ViralCut AI

A professional YouTube livestream-to-short-form clipping workspace.

## Product rules
- YouTube Live URL is the only video source. No manual MP4/video upload workflow.
- Local-first media capture and rendering.
- Real processing events only; never simulate AI progress or fabricated activity.
- Review and approve clips before publishing by default.

## Stack
- Next.js + TypeScript — web workspace
- Python + FastAPI — local processing agent (next milestone)
- yt-dlp — YouTube livestream source extraction
- FFmpeg — capture, rolling segments and rendering
- SQLite — local job state; optional cloud metadata sync later

## Run locally
```bash
npm install
npm run dev
```
Open http://localhost:3000.

## Current status
The web foundation includes responsive navigation, dashboard, YouTube URL validation and an honest setup dialog. URL validation does not start recording. The local engine is not connected yet.

## Roadmap
1. Local engine bootstrap and health handshake.
2. yt-dlp capture with FFmpeg rolling segments and reconnect handling.
3. Real-time event transport to dashboard.
4. Transcription and highlight detection.
5. Vertical clip rendering, captions and face-aware reframing.
6. Clip review, export and official publishing integrations.

Only process livestreams you are authorized to record, edit and publish. Public URL access does not grant copyright or platform permission.
