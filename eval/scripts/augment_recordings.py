"""
Augment voice-memo recordings for ASR model evaluation dataset

Applied transformations:
- babble noise at 10 dB SNR (babble_snr10)
- babble noise at 20 dB SNR (babble_snr20)

Always augment from the original clip. Never chain from an already-augmented file.

Blocks IDs in asr.jsonl:
    1-20    raw
    21-40   babble_snr10
    41-60   babble_snr20

Usage
    python eval/scripts/augment_recordings.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "eval" / "datasets" / "audio" / "raw"
OUT_DIR = REPO_ROOT / "eval" / "datasets" / "audio" / "augmented"
GT_PATH = REPO_ROOT / "eval" / "datasets" / "ground_truths" / "asr.jsonl"
BABBLE_PATH = OUT_DIR / "babble_sfx.mp3"

# Locate each block's first ID in asr.jsonl
BLOCKS = {"raw": 1, "babble_snr10": 21, "babble_snr20": 41}

# Augmentation conditions
CONDITIONS = ("babble_snr10", "babble_snr20")

# Sample rate for decode / process / encode
SAMPLE_RATE = 16000

# Target SNRs (dB) for babble mixes
SNR_DB = {"babble_snr10": 10.0, "babble_snr20": 20.0}

# Define random seed for reproducibility
RANDOM_SEED = 42


def require_ffmpeg() -> None:
    """
    Check if ffmpeg is installed and available
    """
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found on PATH")


def get_clip_id(path: Path) -> int:
    """
    Extract clip id from filename (e.g. 'asr_007.webm' becomes 7)
    """
    # Extract all digit characters from filename (without extension)
    digits = "".join(c for c in path.stem if c.isdigit())
    
    # Ensure at least one digit was found
    if not digits:
        raise ValueError(f"no digits in {path.name}")
    
    # Remove leading zeros and convert to int
    return int(digits)


def load_raw_rows(path: Path) -> list[dict]:
    """
    Load a JSONL file and return only rows with condition='raw'.
    """
    rows = []
    
    # Read file line by line
    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip empty lines
        if not line.strip():
            continue

        # Parse JSON and keep raw condition only
        row = json.loads(line)
        if row.get("condition") == "raw":
            rows.append(row)
    
    return rows


def decode_audio(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Decode any audio file to mono float32 PCM via ffmpeg.
    """
    # Build ffmpeg command: input file into mono float32 PCM at sample_rate on stdout
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(path),
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "pipe:1",
    ]
    try:
        # capture_output keeps raw PCM bytes
        proc = subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise SystemExit(f"ffmpeg decode failed for {path}: {err or exc}") from exc

    # Interpret stdout bytes as float32 samples
    audio = np.frombuffer(proc.stdout, dtype=np.float32)
    
    # Ensure at least one sample was decoded
    if audio.size == 0:
        raise SystemExit(f"decoded empty audio from {path}")
    
    return audio


def encode_webm(audio: np.ndarray, dest: Path, sample_rate: int = SAMPLE_RATE) -> None:
    """
    Encode mono float32 PCM to Opus WebM via ffmpeg.
    """
    # Create parent directory if it does not exist
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Peak-normalise to avoid clipping, leave small headroom at 0.95
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-9:
        audio = (audio / peak) * 0.95
    
    # Pack samples as contiguous float32 bytes for the ffmpeg pipe
    pcm = np.ascontiguousarray(audio, dtype=np.float32).tobytes()

    # Build ffmpeg command: stdin PCM to Opus webm at dest
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "f32le",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-i", "pipe:0",
        "-c:a", "libopus",
        "-b:a", "64k",
        str(dest),
    ]
    try:
        # Feed PCM on stdin
        subprocess.run(cmd, check=True, input=pcm, capture_output=True)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise SystemExit(f"ffmpeg encode failed for {dest}: {err or exc}") from exc


def rms(x: np.ndarray) -> float:
    """
    Root-mean-square amplitude of an audio buffer.
    Measure the average loudness of the audio.
    """
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def match_length(noise: np.ndarray, target_length: int, rng: np.random.Generator) -> np.ndarray:
    """
    Match the length of noise to the length of speech.
    Crop (if longer) or repeat (if shorter).
    """
    # Ensure noise has length
    if noise.size == 0:
        raise SystemExit("Noise is empty")
    
    # When noise and speech have the same length
    if noise.size == target_length:
        # Return a copy
        return noise.copy()
    
    # When noise is longer than speech
    if noise.size > target_length:
        # Pick a random contiguous segment of length target_length
        start = int(rng.integers(0, noise.size - target_length + 1))
        return noise[start:start + target_length].copy()
    
    # When noise is shorter than speech
    # Tile (repeat) the noise to match the length of speech
    reps = int(np.ceil(target_length / noise.size))
    tiled = np.tile(noise, reps)
    # Trim to the length of speech
    return tiled[:target_length].copy()


def mix_babble(
    speech: np.ndarray,
    babble: np.ndarray,
    snr_db: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Mix babble noise into speech at the target SNR (dB).
    
    SNR = 10 * log10(P_speech / P_noise)
    Noise is scaled to meet the target SNR.

    Reference: https://essentia.upf.edu/tutorial_audioproblems_snr.html
    """
    # Align babble length to the speech clip
    noise = match_length(babble, speech.size, rng)
    
    # Measure RMS of speech and noise
    speech_rms = rms(speech)
    noise_rms = rms(noise)
    if noise_rms < 1e-12:
        raise SystemExit("Noise has near-zero RMS")
    
    # Scale noise so RMS_noise = RMS_speech / 10^(snr/20)
    if speech_rms > 1e-12:
        target_noise_rms = speech_rms / (10.0 ** (snr_db / 20.0))
    else:
        # Silent speech: leave noise level unchanged
        target_noise_rms = noise_rms
    scale = target_noise_rms / noise_rms
    
    # Add scaled babble to speech
    mixed = speech.astype(np.float64) + noise.astype(np.float64) * scale
    return mixed.astype(np.float32)


def main() -> None:
    """
    Main augmentation pipeline
    
    Steps:
    1. Find all raw recordings in the raw directory
    2. Load raw ground truth rows
    3. Load babble noise
    4. Create babble_snr10 and babble_snr20 clips
    5. Rebuild asr.jsonl from raw rows and generated rows
    """
    # Ensure ffmpeg is available
    require_ffmpeg()

    # Step 1: Find all webm files in the raw directory
    raw_clips = sorted(
        p for p in RAW_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".webm"
    )
    if not raw_clips:
        raise SystemExit(f"no .webm files in {RAW_DIR}")

    # Step 2: Load raw ground truth rows
    raw_rows = load_raw_rows(GT_PATH)
    if not raw_rows:
        raise SystemExit(f"no raw rows in {GT_PATH}")

    # Step 3: Load babble noise
    if not BABBLE_PATH.is_file():
        raise SystemExit(f"babble noise not found: {BABBLE_PATH}")
    babble = decode_audio(BABBLE_PATH)

    # Step 4: Create augmented audio and row metadata
    for cond in CONDITIONS:
        (OUT_DIR / cond).mkdir(parents=True, exist_ok=True)

    generated: list[dict] = []

    # Process each raw clip and generate augmented versions
    for path in raw_clips:
        clip_id = get_clip_id(path)
        
        # Look up the ground-truth row for this clip (id 1 is at index 0)
        row_index = clip_id - 1
        if row_index < 0 or row_index >= len(raw_rows):
            raise SystemExit(f"No ground truth row for clip id {clip_id}")
        src = raw_rows[row_index]
        
        # Decode speech from the original recording
        speech = decode_audio(path)
        
        # Create RNG for reproducible babble cropping that is unique for each clip id
        rng = np.random.default_rng(RANDOM_SEED + clip_id)
        
        # Generate both babble-SNR versions
        outputs = {
            cond: mix_babble(speech, babble, SNR_DB[cond], rng)
            for cond in CONDITIONS
        }

        # Write each augmented clip and record its ground-truth row
        for cond, out_audio in outputs.items():
            new_id = BLOCKS[cond] + clip_id - 1
            rel = f"eval/datasets/audio/augmented/{cond}/asr_{new_id:03d}.webm"
            dest = REPO_ROOT / rel
            encode_webm(out_audio, dest)

            # Add metadata for this augmented clip to the list
            generated.append({
                "id": new_id,
                "condition": cond,
                "speaker": src["speaker"],
                "audio": rel,
                "transcript": src["transcript"],
                "keywords": src["keywords"],
            })

    # Step 5: Combine raw and generated rows, sort by id, write asr.jsonl
    rows = sorted(raw_rows + generated, key=lambda r: r["id"])
    GT_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print("Successfully augmented recordings.")


if __name__ == "__main__":
    main()