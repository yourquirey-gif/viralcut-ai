from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("VIRALCUT_DATA_DIR", APP_DIR / "data")).resolve()
SEGMENTS_DIR = DATA_DIR / "segments"
DB_PATH = DATA_DIR / "jobs.sqlite3"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ViralCut Local Engine", version="0.2.0")
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] + [
    origin.strip()
    for origin in os.environ.get("VIRALCUT_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
JOBS: dict[str, dict[str, Any]] = {}
PROCESSES: dict[str, subprocess.Popen] = {}
STOP_EVENTS: dict[str, threading.Event] = {}
LOCK = threading.RLock()
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
MAX_RETRIES = 5
RETRY_DELAYS = (2, 4, 8, 12, 15)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                output_dir TEXT NOT NULL, error TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                event_type TEXT NOT NULL, message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        stale = conn.execute(
            "SELECT id FROM jobs WHERE status IN ('checking','capturing','stopping')"
        ).fetchall()
        for row in stale:
            conn.execute(
                "UPDATE jobs SET status='failed', updated_at=?, error=? WHERE id=?",
                (utc_now(), "The local engine restarted while this capture was active. Start a new capture.", row["id"]),
            )
            conn.execute(
                "INSERT INTO events(job_id,event_type,message,created_at) VALUES(?,?,?,?)",
                (row["id"], "engine_restarted", "Capture stopped because the local engine restarted.", utc_now()),
            )


init_db()


def emit_event(job_id: str, event_type: str, message: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO events(job_id,event_type,message,created_at) VALUES(?,?,?,?)",
            (job_id, event_type, message, utc_now()),
        )


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


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in job.items() if key != "output_dir"}


def update_job(job_id: str, status: str, error: str | None = None, message: str | None = None) -> None:
    now = utc_now()
    with LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(status=status, updated_at=now, error=error)
        with db() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, updated_at=?, error=? WHERE id=?",
                (status, now, error, job_id),
            )
    emit_event(job_id, "status", message or (error if error else "Capture status: " + status))


def run_ytdlp(binary: str, args: list[str], stop_event: threading.Event, job_id: str, timeout: int = 45) -> subprocess.CompletedProcess:
    if stop_event.is_set():
        raise InterruptedError("Capture stop requested")
    command = [binary, *args]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    with LOCK:
        PROCESSES[job_id] = process
    started = time.monotonic()
    try:
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.5)
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                if stop_event.is_set():
                    process.terminate()
                    try:
                        stdout, stderr = process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        stdout, stderr = process.communicate()
                    raise InterruptedError("Capture stop requested")
                if time.monotonic() - started > timeout:
                    process.kill()
                    process.communicate()
                    raise subprocess.TimeoutExpired(command, timeout)
    finally:
        with LOCK:
            if PROCESSES.get(job_id) is process:
                PROCESSES.pop(job_id, None)


def stream_is_live(ytdlp: str, url: str, stop_event: threading.Event, job_id: str) -> tuple[bool, str | None]:
    result = run_ytdlp(
        ytdlp,
        ["--dump-single-json", "--no-warnings", "--skip-download", url],
        stop_event,
        job_id,
        timeout=45,
    )
    if result.returncode != 0:
        detail = (result.stderr or "").strip()
        return False, detail[-500:] if detail else "yt-dlp could not inspect this stream."
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, "YouTube returned stream metadata that could not be read."
    return info.get("is_live") is True or info.get("live_status") == "is_live", None


def list_segment_files(output_dir: Path, min_age_seconds: float = 0) -> list[Path]:
    if not output_dir.exists():
        return []
    now = time.time()
    return sorted(
        (
            path for path in output_dir.rglob("*.mp4")
            if path.is_file()
            and path.stat().st_size > 0
            and now - path.stat().st_mtime >= min_age_seconds
        ),
        key=lambda path: path.stat().st_mtime,
    )


def capture_worker(job_id: str, url: str, output_dir: Path) -> None:
    ytdlp, ffmpeg = shutil.which("yt-dlp"), shutil.which("ffmpeg")
    stop_event = STOP_EVENTS[job_id]
    if not ytdlp or not ffmpeg:
        update_job(job_id, "failed", "Install yt-dlp and FFmpeg, then restart the local engine.")
        return

    successful_segments = 0
    last_error = "The live stream disconnected."
    for attempt in range(MAX_RETRIES + 1):
        if stop_event.is_set():
            update_job(job_id, "stopped", message="Capture stopped by the user.")
            return
        try:
            update_job(
                job_id,
                "checking",
                message="Checking YouTube livestream availability (attempt " + str(attempt + 1) + ").",
            )
            live, detail = stream_is_live(ytdlp, url, stop_event, job_id)
            if stop_event.is_set():
                update_job(job_id, "stopped", message="Capture stopped by the user.")
                return
            if detail:
                raise RuntimeError(detail)
            if not live:
                if successful_segments:
                    update_job(job_id, "completed", message="Livestream ended. Captured segments are ready for processing.")
                else:
                    update_job(job_id, "failed", "This URL is not an active livestream. Start capture when the stream is live.")
                return

            resolved = run_ytdlp(
                ytdlp,
                ["-g", "-f", "best", "--no-warnings", url],
                stop_event,
                job_id,
                timeout=45,
            )
            if resolved.returncode != 0 or not resolved.stdout.strip():
                last_error = (resolved.stderr or "").strip()[-500:] or "Could not resolve the live media stream."
                raise RuntimeError(last_error)
            if stop_event.is_set():
                update_job(job_id, "stopped", message="Capture stopped by the user.")
                return
            media_url = resolved.stdout.strip().splitlines()[0]

            attempt_dir = output_dir / ("attempt-" + str(attempt + 1).zfill(2))
            attempt_dir.mkdir(parents=True, exist_ok=True)
            pattern = str(attempt_dir / "segment-%Y%m%d-%H%M%S.mp4")
            command = [
                ffmpeg,
                "-hide_banner",
                "-loglevel", "warning",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_delay_max", "10",
                "-rw_timeout", "20000000",
                "-i", media_url,
                "-map", "0:v:0",
                "-map", "0:a?",
                "-c", "copy",
                "-f", "segment",
                "-segment_time", "30",
                "-reset_timestamps", "1",
                "-strftime", "1",
                "-segment_format", "mp4",
                pattern,
            ]
            emit_event(job_id, "capture_started", "Stream resolved. FFmpeg is recording 30-second segments.")
            update_job(job_id, "capturing", message="Recording livestream into 30-second segments.")
            log_path = attempt_dir / "ffmpeg.log"
            with LOCK:
                if stop_event.is_set():
                    update_job(job_id, "stopped", message="Capture stopped by the user.")
                    return
                with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
                    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=log_file, text=True)
                    PROCESSES[job_id] = process
            last_reported_count = len(list_segment_files(output_dir, min_age_seconds=2))
            while process.poll() is None:
                if stop_event.is_set() and process.poll() is None:
                    try:
                        process.terminate()
                    except OSError:
                        pass
                current_count = len(list_segment_files(output_dir, min_age_seconds=2))
                if current_count > last_reported_count:
                    last_reported_count = current_count
                    emit_event(job_id, "segments_saved", str(current_count) + " recording segments have been safely closed and saved.")
                time.sleep(1)
            process.wait()
            with LOCK:
                PROCESSES.pop(job_id, None)
            stderr = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            current_segments = list_segment_files(output_dir)
            successful_segments = len(current_segments)
            if stop_event.is_set():
                update_job(job_id, "stopped", message="Capture stopped. Saved segments are kept on this computer.")
                return

            if process.returncode == 0:
                still_live, inspect_error = stream_is_live(ytdlp, url, stop_event, job_id)
                if stop_event.is_set():
                    update_job(job_id, "stopped", message="Capture stopped by the user.")
                    return
                if inspect_error:
                    raise RuntimeError(inspect_error)
                if not still_live:
                    update_job(job_id, "completed", message="Livestream ended. Captured segments are ready for processing.")
                    return
                last_error = "The capture process ended while the livestream was still live."
            else:
                last_error = (stderr or "").strip()[-700:] or "FFmpeg lost its connection to the live stream."

        except InterruptedError:
            update_job(job_id, "stopped", message="Capture stopped by the user.")
            return
        except subprocess.TimeoutExpired:
            last_error = "The YouTube stream inspection timed out."
        except Exception as exc:
            last_error = str(exc)[:700] or "Unexpected capture error."

        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            emit_event(
                job_id,
                "reconnecting",
                "Stream connection interrupted. Retrying in " + str(delay) + " seconds (" + str(attempt + 1) + "/" + str(MAX_RETRIES) + ").",
            )
            if stop_event.wait(delay):
                update_job(job_id, "stopped", message="Capture stopped by the user.")
                return

    update_job(
        job_id,
        "failed",
        "Could not restore the live stream after " + str(MAX_RETRIES) + " retries. Last error: " + last_error,
    )


class StartJob(BaseModel):
    url: str = Field(min_length=12, max_length=500)


@app.middleware("http")
async def enforce_local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        return JSONResponse(status_code=403, content={"detail": "This website origin is not allowed to access the local engine."})
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "viralcut-local-engine",
        "version": "0.2.0",
        "tools": {"yt_dlp": tool_version("yt-dlp"), "ffmpeg": tool_version("ffmpeg")},
        "active_jobs": sum(1 for job in JOBS.values() if job["status"] in {"checking", "capturing", "stopping"}),
    }


@app.get("/api/v1/jobs")
def list_jobs() -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id,status,created_at,updated_at,error FROM jobs ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return {"jobs": [dict(row) for row in rows]}


@app.post("/api/v1/jobs")
def start_job(body: StartJob) -> dict[str, Any]:
    url = validate_youtube_url(body.url)
    if not shutil.which("yt-dlp") or not shutil.which("ffmpeg"):
        raise HTTPException(status_code=503, detail="Local dependencies missing. Install yt-dlp and FFmpeg first.")
    with LOCK:
        if any(job["status"] in {"checking", "capturing", "stopping"} for job in JOBS.values()):
            raise HTTPException(status_code=409, detail="A capture is already running in this local engine.")
    job_id = str(uuid.uuid4())
    output_dir = (SEGMENTS_DIR / job_id).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    job = {
        "id": job_id,
        "status": "checking",
        "created_at": now,
        "updated_at": now,
        "output_dir": str(output_dir),
        "error": None,
    }
    with LOCK:
        JOBS[job_id] = job
        STOP_EVENTS[job_id] = threading.Event()
        with db() as conn:
            conn.execute(
                "INSERT INTO jobs(id,url,status,created_at,updated_at,output_dir,error) VALUES(?,?,?,?,?,?,?)",
                (job_id, url, "checking", now, now, str(output_dir), None),
            )
    emit_event(job_id, "created", "Capture job created. Waiting for the livestream check.")
    threading.Thread(
        target=capture_worker,
        args=(job_id, url, output_dir),
        daemon=True,
        name="capture-" + job_id,
    ).start()
    return {"job": public_job(job)}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with LOCK:
        job = JOBS.get(job_id)
    if job:
        return {"job": public_job(job)}
    with db() as conn:
        row = conn.execute(
            "SELECT id,status,created_at,updated_at,error FROM jobs WHERE id=?",
            (job_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job": dict(row)}


@app.get("/api/v1/jobs/{job_id}/events")
def get_events(job_id: str, after_id: int = 0) -> dict[str, Any]:
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found.")
        rows = conn.execute(
            "SELECT id,event_type,message,created_at FROM events WHERE job_id=? AND id>? ORDER BY id ASC LIMIT 200",
            (job_id, after_id),
        ).fetchall()
    return {"events": [dict(row) for row in rows]}


@app.get("/api/v1/jobs/{job_id}/segments")
def get_segments(job_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT output_dir FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    output_dir = Path(row["output_dir"]).resolve()
    files = list_segment_files(output_dir, min_age_seconds=2)
    return {
        "segments": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "download_url": "/api/v1/jobs/" + job_id + "/segments/" + path.relative_to(output_dir).as_posix(),
            }
            for path in files
        ],
        "count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
    }


@app.get("/api/v1/jobs/{job_id}/segments/{segment_path:path}")
def download_segment(job_id: str, segment_path: str):
    with db() as conn:
        row = conn.execute("SELECT output_dir FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    base = Path(row["output_dir"]).resolve()
    target = (base / segment_path).resolve()
    if base not in target.parents or target.suffix.lower() != ".mp4" or not target.is_file():
        raise HTTPException(status_code=404, detail="Segment not found.")
    return FileResponse(target, media_type="video/mp4", filename=target.name)


@app.post("/api/v1/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, str]:
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found in this engine session.")
        if job["status"] not in {"checking", "capturing", "stopping"}:
            raise HTTPException(status_code=409, detail="This capture is not active.")
        stop_event = STOP_EVENTS.get(job_id)
        if not stop_event:
            raise HTTPException(status_code=409, detail="Stop control is unavailable for this job.")
        stop_event.set()
        process = PROCESSES.get(job_id)
        if process and process.poll() is None:
            process.terminate()
        job["status"] = "stopping"
        job["updated_at"] = utc_now()
    emit_event(job_id, "stop_requested", "Stop requested. Waiting for the capture process to close safely.")
    return {"status": "stop_requested"}


# Optional local AI analysis. Heavy model work runs in a background thread.
try:
    from .ai_pipeline import analyze_segments
except ImportError:
    from ai_pipeline import analyze_segments

ANALYSIS_STATE: dict[str, dict[str, Any]] = {}
ANALYSIS_LOCK = threading.RLock()


def _analysis_worker(job_id: str, output_dir: Path) -> None:
    with ANALYSIS_LOCK:
        ANALYSIS_STATE[job_id] = {"status": "processing", "result": None, "error": None}
    emit_event(job_id, "ai_analysis_started", "Local speech transcription and candidate ranking started.")
    try:
        result = analyze_segments(output_dir, model_size=os.environ.get("VIRALCUT_WHISPER_MODEL", "base"))
        result_path = output_dir / "ai-analysis.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        with ANALYSIS_LOCK:
            ANALYSIS_STATE[job_id] = {"status": "completed", "result": result, "error": None}
        emit_event(job_id, "ai_analysis_completed", "Speech transcription finished. Candidate ranking is ready for review.")
    except Exception as exc:
        message = str(exc)[:700] or "AI analysis failed."
        with ANALYSIS_LOCK:
            ANALYSIS_STATE[job_id] = {"status": "failed", "result": None, "error": message}
        emit_event(job_id, "ai_analysis_failed", message)


@app.post("/api/v1/jobs/{job_id}/analyze")
def start_ai_analysis(job_id: str) -> dict[str, str]:
    with db() as conn:
        row = conn.execute("SELECT output_dir,status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=503, detail="FFmpeg is required for AI audio extraction.")
    output_dir = Path(row["output_dir"]).resolve()
    if not output_dir.is_dir() or not list_segment_files(output_dir, min_age_seconds=2):
        raise HTTPException(status_code=409, detail="No completed recording segments are ready to analyze.")
    with ANALYSIS_LOCK:
        current = ANALYSIS_STATE.get(job_id)
        if current and current.get("status") == "processing":
            raise HTTPException(status_code=409, detail="AI analysis is already running for this project.")
        ANALYSIS_STATE[job_id] = {"status": "queued", "result": None, "error": None}
    threading.Thread(target=_analysis_worker, args=(job_id, output_dir), daemon=True, name="ai-analysis-" + job_id).start()
    return {"status": "queued", "message": "Local AI analysis queued."}


@app.get("/api/v1/jobs/{job_id}/analysis")
def get_ai_analysis(job_id: str) -> dict[str, Any]:
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Job not found.")
    with ANALYSIS_LOCK:
        state = ANALYSIS_STATE.get(job_id)
    if state:
        return state
    with db() as conn:
        row = conn.execute("SELECT output_dir FROM jobs WHERE id=?", (job_id,)).fetchone()
    result_path = Path(row["output_dir"]) / "ai-analysis.json"
    if result_path.is_file():
        return {"status": "completed", "result": json.loads(result_path.read_text(encoding="utf-8")), "error": None}
    return {"status": "not_started", "result": None, "error": None}
