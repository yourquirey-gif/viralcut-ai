from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="ViralCut Local Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class InspectRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


def validate_youtube_url(value: str) -> str:
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    allowed = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
    if parsed.scheme not in {"http", "https"} or host not in allowed:
        raise HTTPException(status_code=400, detail="Only YouTube video and live URLs are supported.")
    if host.endswith("youtu.be") and len(parsed.path.strip("/")) < 6:
        raise HTTPException(status_code=400, detail="The YouTube video URL is incomplete.")
    if host.endswith("youtube.com") and not (
        parsed.path == "/watch" or parsed.path.startswith("/live/") or parsed.path.startswith("/embed/")
    ):
        raise HTTPException(status_code=400, detail="Use a YouTube watch or live URL.")
    return value.strip()


def binary_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "viralcut-local-engine",
        "version": app.version,
        "tools": {"yt_dlp": binary_status("yt-dlp"), "ffmpeg": binary_status("ffmpeg")},
    }


@app.get("/api/capabilities")
async def capabilities() -> dict[str, Any]:
    return {
        "source": "youtube_live_url_only",
        "capture": {"available": False, "status": "not_implemented"},
        "inspection": {"available": shutil.which("yt-dlp") is not None},
        "processing": {"available": False, "status": "not_implemented"},
    }


@app.post("/api/streams/inspect")
async def inspect_stream(payload: InspectRequest) -> dict[str, Any]:
    url = validate_youtube_url(payload.url)
    executable = shutil.which("yt-dlp")
    if not executable:
        raise HTTPException(status_code=503, detail="yt-dlp is not installed on this computer.")

    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--no-playlist",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=35)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise HTTPException(status_code=504, detail="YouTube stream inspection timed out.")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not run yt-dlp: {exc}") from exc

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()[-1200:]
        raise HTTPException(status_code=422, detail=detail or "yt-dlp could not inspect this YouTube URL.")

    try:
        info = json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="yt-dlp returned an unreadable response.") from exc

    is_live = bool(info.get("is_live") or info.get("live_status") == "is_live")
    return {
        "status": "inspected",
        "is_live": is_live,
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "live_status": info.get("live_status"),
        "note": "Inspection only. No video has been recorded or downloaded.",
    }
