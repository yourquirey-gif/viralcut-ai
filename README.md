# ViralCut AI

A local-first livestream-to-clips workspace. The only video source is a YouTube Live URL; there is no manual video upload flow.

## Current status

Web workspace foundation is being built. URL validation is a front-end check only; it does not capture or download a stream until the local processing engine is installed and connected.

## Product principles

- YouTube Live URL only.
- Real processing events only; no fake AI progress.
- Local-first capture, rendering and clip storage.
- Human review before publishing by default.
- Process only streams you are authorized to record, edit and publish.

## Planned stack

- Next.js + TypeScript web workspace
- Python + FastAPI local processing engine
- yt-dlp for stream extraction
- FFmpeg for capture, segmenting and rendering
- SQLite for local jobs; optional cloud sync later

## Roadmap

1. Web workspace and responsive dashboard
2. Local engine and health handshake
3. yt-dlp capture with FFmpeg rolling buffer and reconnects
4. Real-time event stream and per-clip jobs
5. Speech transcription and highlight detection
6. Vertical editing, captions and face-aware reframing
7. Clip review and official publishing integrations
