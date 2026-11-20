from __future__ import annotations

import json
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

# A lightweight, local-first first pass. This ranks speech-rich segments and
# transcript cues; it does not claim to understand virality or audience reaction.
CUE_WORDS = {
    "wow", "what", "no way", "insane", "crazy", "amazing", "unbelievable",
    "oh my god", " omg ", " lets go", " let's go", " clutch", " gg ",
    "भाई", "क्या", "अरे", "वाह", "जबरदस्त", "नहीं", "सच में",
}


def _audio_for_video(video: Path, target: Path) -> None:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        raise RuntimeError("Could not extract audio from " + video.name + ": " + (result.stderr or "unknown FFmpeg error")[-400:])


def analyze_segments(output_dir: Path, model_size: str = "base") -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("AI transcription is not installed. Run engine/setup-windows.bat again, or install faster-whisper from engine/requirements.txt.") from exc

    files = sorted(
        (p for p in output_dir.rglob("*.mp4") if p.is_file() and p.stat().st_size > 0),
        key=lambda p: p.stat().st_mtime,
    )
    if not files:
        raise RuntimeError("No completed recording segments are available to analyze.")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    results: list[dict[str, Any]] = []
    all_text: list[str] = []

    with tempfile.TemporaryDirectory(prefix="viralcut-audio-") as temp:
        temp_dir = Path(temp)
        for index, video in enumerate(files, start=1):
            audio = temp_dir / (str(index) + ".wav")
            _audio_for_video(video, audio)
            segments, info = model.transcribe(
                str(audio),
                beam_size=3,
                vad_filter=True,
                word_timestamps=True,
            )
            transcript_segments = []
            words = 0
            text_parts = []
            for segment in segments:
                text = segment.text.strip()
                if not text:
                    continue
                text_parts.append(text)
                words += len(text.split())
                transcript_segments.append({
                    "start": round(float(segment.start), 2),
                    "end": round(float(segment.end), 2),
                    "text": text,
                })
            transcript = " ".join(text_parts).strip()
            all_text.append(transcript)
            lower = " " + transcript.lower() + " "
            cues = [cue.strip() for cue in CUE_WORDS if cue in lower]
            # Transparent baseline score: speech density + a small cue bonus.
            # Replace with contextual multimodal ranking in a later milestone.
            score = min(100, round(min(words / 45, 1) * 75 + min(len(cues), 5) * 5))
            results.append({
                "source_segment": video.name,
                "duration_seconds": 30,
                "language": getattr(info, "language", None),
                "language_probability": round(float(getattr(info, "language_probability", 0) or 0), 3),
                "word_count": words,
                "score": score,
                "score_basis": "speech density and transcript cue words; not a virality prediction",
                "cue_words": cues,
                "transcript": transcript,
                "transcript_segments": transcript_segments,
            })

    ranked = sorted(results, key=lambda item: item["score"], reverse=True)
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return {
        "model": "faster-whisper/" + model_size,
        "device": "cpu",
        "segments_analyzed": len(results),
        "ranking_method": "transparent speech-density baseline",
        "notice": "This is an early transcript-based candidate ranking, not semantic or audience-reaction virality detection.",
        "highlights": ranked,
        "transcript": "\\n".join(all_text),
    }
