"""
ASR model runners for evaluation (Whisper base, Whisper large-v3-turbo, Parakeet).

Each run_* function:
    1. Load the model once
    2. Run ASR on every audio path
    3. Unload the model

Result row shape (per clip):
    {"transcript": str, "latency_ms": float | None, "error": str | None}

Used by
    eval/scripts/asr/run_asr_eval.py
"""

from __future__ import annotations

import time
from pathlib import Path


def run_asr_one(transcribe, path: Path) -> dict:
    """
    Run ASR model on a single audio file

    Returns a dict with transcript, latency_ms (milliseconds), and optional error.
    """
    # Handle missing file (skip ASR run)
    if not path.is_file():
        return {
            "transcript": "",
            "latency_ms": None,
            "error": f"missing audio: {path}",
        }

    # Start timer
    t0 = time.perf_counter()
    try:
        text = transcribe(path)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"transcript": text, "latency_ms": ms, "error": None}

    except Exception as exc:
        # ASR failed, store error
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "transcript": "",
            "latency_ms": ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_asr_all(name: str, transcribe, audio_paths: list[Path]) -> list[dict]:
    """
    Run the selected ASR model on all audio paths by calling the transcribe function
    Prints progress every 10 clips (and on the last).
    """
    results: list[dict] = []
    total = len(audio_paths)

    # Run ASR on each audio clip
    for i, path in enumerate(audio_paths, start=1):
        results.append(run_asr_one(transcribe, path))

        # Log progress every 10 clips
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def run_whisper_base(audio_paths: list[Path]) -> list[dict]:
    """
    Load Whisper base (faster-whisper) once, run on all audio paths, then unload.
    Same size/device/compute_type as the main app prototype ASR.
    """
    from faster_whisper import WhisperModel

    print("Loading Whisper base...")
    # Loaded once and reused for every clip in this batch
    # Used in the main app prototype (backend/ai/asr/faster_whisper.py)
    # Reference: https://pypi.org/project/faster-whisper/
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8",
    )
    print("Whisper base ready.")

    def transcribe(path: Path) -> str:
        # Transcribe the audio file to text in english
        segments, _ = model.transcribe(str(path), language="en")
        # Join the segments into a single string
        return " ".join(segment.text.strip() for segment in segments)

    # Run Whisper base on all clips
    return run_asr_all("whisper_base", transcribe, audio_paths)


def run_whisper_large_v3_turbo(audio_paths: list[Path]) -> list[dict]:
    """
    Load Whisper large-v3-turbo (faster-whisper) once, run on all audio paths, then unload.
    """
    from faster_whisper import WhisperModel

    print("Loading Whisper large-v3-turbo...")
    # Loaded once and reused for every clip in this batch
    model = WhisperModel(
        "large-v3-turbo",
        device="cpu",
        compute_type="int8",
    )
    print("Whisper large-v3-turbo ready.")

    def transcribe(path: Path) -> str:
        # Transcribe the audio file to text in english
        segments, _ = model.transcribe(str(path), language="en")
        # Join the segments into a single string
        return " ".join(segment.text.strip() for segment in segments)

    # Run Whisper large-v3-turbo on all clips
    return run_asr_all("whisper_large_v3_turbo", transcribe, audio_paths)


def run_parakeet(audio_paths: list[Path]) -> list[dict]:
    """
    Load Parakeet TDT 0.6B v3 once, run on all audio paths, then unload.
    """
    from parakeet_mlx import from_pretrained

    print("Loading Parakeet TDT 0.6B v3...")
    # Loaded once and reused for every clip in this batch
    # Reference: https://github.com/senstella/parakeet-mlx
    model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
    print("Parakeet TDT 0.6B v3 ready.")

    def transcribe(path: Path) -> str:
        # Transcribe the audio file; result exposes full text
        result = model.transcribe(str(path))
        return str(result.text).strip()

    # Run Parakeet on all clips
    return run_asr_all("parakeet", transcribe, audio_paths)


# Map CLI model names to load-once runners
MODELS = {
    "whisper_base": run_whisper_base,
    "whisper_large_v3_turbo": run_whisper_large_v3_turbo,
    "parakeet": run_parakeet,
}