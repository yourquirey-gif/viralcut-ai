# ViralCut AI

A local-first YouTube livestream-to-short-form clipping workspace. The only video source is a YouTube Live URL; manual MP4/video uploads are intentionally not part of the product.

## Product principles
- Real processing state only. No fake AI activity, fabricated progress or invented analytics.
- Capture and heavy media processing run on the user's computer, not in a serverless web function.
- Clips are reviewed and approved before publishing by default.
- Only process streams you are authorized to record, edit and publish.

## Stack
- Next.js + TypeScript — web workspace
- Python + FastAPI — local processing agent in `engine/`
- yt-dlp — inspect and resolve active YouTube livestreams
- FFmpeg — record rolling 30-second MP4 segments
- SQLite — local capture-job metadata

## Run the web workspace

    npm install
    npm run dev

Open http://localhost:3000.

## Run the local engine
See `engine/README.md`. The engine runs on 127.0.0.1:8765 and exposes a health endpoint, capture-job creation, status polling and stop requests. Install Python, yt-dlp and FFmpeg first.

For a deployed website, configure the exact website origin using VIRALCUT_ALLOWED_ORIGINS as described in engine/README.md. Do not expose the local engine to the public internet.

## Current implementation
- Responsive creator dashboard and navigation.
- YouTube URL format validation in the web UI.
- Browser-to-local-engine health check.
- Local API to inspect an active livestream, resolve media through yt-dlp and record 30-second FFmpeg segments.
- Capture status polling and stop request from the dashboard.

The capture milestone is an early foundation. It supports one active capture per local engine process. It does not yet perform AI highlight detection, transcription, face tracking, automatic vertical editing, clip review/export or social publishing.

## Roadmap
1. Improve capture resilience: reconnects, segment integrity and long-stream recovery.
2. Build real-time engine events and multi-clip job tracking.
3. Add speech transcription and context-aware highlight detection.
4. Add vertical editing, captions and face-aware reframing.
5. Add clip review, export and official publishing integrations.

A public YouTube URL does not grant copyright or platform permission. You are responsible for obtaining the necessary rights and following platform terms.
