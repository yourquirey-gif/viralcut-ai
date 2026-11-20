from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("VIRALCUT_DATA_DIR", APP_DIR / "data")).resolve()
SEGMENTS_DIR = DATA_DIR / "segments"
DB_PATH = DATA_DIR / "jobs.sqlite3"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ViralCut Local Engine", version="0.1.0")
ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"] + [origin.strip() for origin in os.environ.get("VIRALCUT_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
JOBS: dict[str, dict[str, Any]] = {}
PROCESSES: dict[str, subprocess.Popen] = {}
LOCK = threading.RLock()
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, url TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, output_dir TEXT NOT NULL, error TEXT)")


init_db()


def validate_youtube_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname not in YOUTUBE_HOSTS:
        raise HTTPException(status_code=422, detail="Only HTTPS YouTube URLs are accepted.")
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith(("/live/", "/embed/")):
        parts = parsed.path.split("/")
        video_id = parts[2] if len(parts) > 2 else ""
    else:
        video_id = ""
    if not VIDEO_ID.fullmatch(video_id):
        raise HTTPException(status_code=422, detail="The URL does not contain a valid YouTube video ID.")
    return "https://www.youtube.com/watch?v=" + video_id


def tool_version(name: str) -> str | None:
    binary = shutil.which(name)
    if not binary:
        return None
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=8, check=False)
        return (result.stdout or result.stderr).strip().splitlines()[0][:100]
    except Exception:
        return "Installed (version check unavailable)"


def update_job(job_id: str, status: str, error: str | None = None) -> None:
    now = utc_now()
    with LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(status=status, updated_at=now, error=error)
        with db() as conn:
            conn.execute("UPDATE jobs SET status=?, updated_at=?, error=? WHERE id=?", (status, now, error, job_id))


def capture_worker(job_id: str, url: str, output_dir: Path) -> None:
    ytdlp, ffmpeg = shutil.which("yt-dlp"), shutil.which("ffmpeg")
    if not ytdlp or not ffmpeg:
        update_job(job_id, "failed", "Install yt-dlp and FFmpeg, then restart the local engine.")
        return
    try:
        meta = subprocess.run([ytdlp, "--dump-single-json", "--no-warnings", "--skip-download", url], capture_output=True, text=True, timeout=45, check=False)
        if meta.returncode != 0:
            update_job(job_id, "failed", "Could not inspect this stream. It may be offline, restricted, or unavailable to yt-dlp.")
            return
        try:
            info = json.loads(meta.stdout)
        except json.JSONDecodeError:
            update_job(job_id, "failed", "YouTube returned stream metadata that could not be read.")
            return
        if info.get("is_live") is not True and info.get("live_status") != "is_live":
            update_job(job_id, "failed", "This URL is not an active livestream. Start capture when the stream is live.")
            return
        stream = subprocess.run([ytdlp, "-g", "-f", "best", "--no-warnings", url], capture_output=True, text=True, timeout=45, check=False)
        if stream.returncode != 0 or not stream.stdout.strip():
            update_job(job_id, "failed", "Could not resolve the live media stream. Check availability and permissions.")
            return
        media_url = stream.stdout.strip().splitlines()[0]
        pattern = str(output_dir / "segment-%Y%m%d-%H%M%S.mp4")
        command = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-i", media_url, "-map", "0:v:0", "-map", "0:a?", "-c", "copy", "-f", "segment", "-segment_time", "30", "-reset_timestamps", "1", "-strftime", "1", pattern]
        update_job(job_id, "capturing")
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        with LOCK:
            PROCESSES[job_id] = process
        process.communicate()
        with LOCK:
            PROCESSES.pop(job_id, None)
            stopping = JOBS.get(job_id, {}).get("status") == "stopping"
        if stopping:
            update_job(job_id, "stopped")
        elif process.returncode == 0:
            update_job(job_id, "completed")
        else:
            update_job(job_id, "failed", "FFmpeg ended unexpectedly. Check stream availability and local dependencies.")
    except subprocess.TimeoutExpired:
        update_job(job_id, "failed", "The stream check timed out.")
    except Exception:
        update_job(job_id, "failed", "Unexpected capture error. Restart the local engine and try again.")


class StartJob(BaseModel):
    url: str = Field(min_length=12, max_length=500)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "viralcut-local-engine", "version": "0.1.0", "tools": {"yt_dlp": tool_version("yt-dlp"), "ffmpeg": tool_version("ffmpeg")}, "active_jobs": sum(1 for j in JOBS.values() if j["status"] in {"checking", "capturing", "stopping"})}


@app.get("/api/v1/jobs")
def list_jobs() -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute("SELECT id,status,created_at,updated_at,error FROM jobs ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"jobs": [dict(row) for row in rows]}


@app.post("/api/v1/jobs")
def start_job(body: StartJob) -> dict[str, Any]:
    url = validate_youtube_url(body.url)
    if not shutil.which("yt-dlp") or not shutil.which("ffmpeg"):
        raise HTTPException(status_code=503, detail="Local dependencies missing. Install yt-dlp and FFmpeg first.")
    with LOCK:
        if any(j["status"] in {"checking", "capturing", "stopping"} for j in JOBS.values()):
            raise HTTPException(status_code=409, detail="A capture is already running in this local engine.")
    job_id = str(uuid.uuid4())
    output_dir = (SEGMENTS_DIR / job_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    job = {"id": job_id, "status": "checking", "created_at": now, "updated_at": now, "output_dir": str(output_dir), "error": None}
    with LOCK:
        JOBS[job_id] = job
        with db() as conn:
            conn.execute("INSERT INTO jobs(id,url,status,created_at,updated_at,output_dir,error) VALUES(?,?,?,?,?,?,?)", (job_id, url, "checking", now, now, str(output_dir), None))
    threading.Thread(target=capture_worker, args=(job_id, url, output_dir), daemon=True).start()
    return {"job": {k: v for k, v in job.items() if k != "output_dir"}}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with LOCK:
        job = JOBS.get(job_id)
    if job:
        return {"job": {k: v for k, v in job.items() if k != "output_dir"}}
    with db() as conn:
        row = conn.execute("SELECT id,status,created_at,updated_at,error FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job": dict(row)}


@app.post("/api/v1/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, str]:
    with LOCK:
        process = PROCESSES.get(job_id)
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found in this engine session.")
        if not process:
            raise HTTPException(status_code=409, detail="This job is not currently capturing.")
        job["status"] = "stopping"
        process.terminate()
    return {"status": "stop_requested"}
