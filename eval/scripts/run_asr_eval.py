"""
Run ASR models over the evaluation ground-truth set and store predictions.

Pipeline (one model at a time):
    1. Load ground-truth rows from asr.jsonl
    2. Load model then ASR all audio clips then unload model
    3. Write eval/predictions/{model}.jsonl (overwrites if present)

Prediction row fields:
    id, model, condition, audio, transcript, latency_ms, error

Usage
    python eval/scripts/run_asr_eval.py --model whisper_base
    python eval/scripts/run_asr_eval.py --model whisper_large_v3_turbo
    python eval/scripts/run_asr_eval.py --model parakeet
    python eval/scripts/run_asr_eval.py --model all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from asr_engines import MODELS

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[2]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "ground_truths" / "asr.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions"


def load_gt_rows(path: Path) -> list[dict]:
    """
    Load ground-truth rows from a JSONL file then convert into a list of dictionaries
    """
    rows: list[dict] = []

    # Read file line by line
    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip empty lines
        if not line.strip():
            continue
        # Parse JSON and add to list
        rows.append(json.loads(line))

    return rows


def run_model(model: str, rows: list[dict]) -> None:
    """
    Run one ASR model on all ground-truth audio clips and write prediction JSONL.

    Steps:
    1. Find the ASR function for the current model name
    2. Call the ASR function to run ASR on all dataset clips
    3. Join GT metadata with ASR results and write predictions/{model}.jsonl
    """
    # Step 1: Find the ASR function for the current model name
    run_fn = MODELS.get(model)
    if run_fn is None:
        known = ", ".join(MODELS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Ensure output directory exists for the predictions file
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    # Build the output path for the predictions file
    out_path = PRED_DIR / f"{model}.jsonl"

    # Build absolute paths for the input audio clips
    audio_paths = [REPO_ROOT / row["audio"] for row in rows]
    print(f"[{model}] {len(audio_paths)} clips")

    # Step 2: Call the ASR function to run ASR on all dataset clips
    # Load ASR model, transcribe every clip, then unload model
    results = run_fn(audio_paths)

    # Step 3: Join GT metadata with ASR results and write
    # Write one JSON object per clip (same order as ground-truth rows)
    with out_path.open("w", encoding="utf-8") as fh:
        for row, result in zip(rows, results):
            record = {
                "id": row["id"],
                "model": model,
                "condition": row["condition"],
                "audio": row["audio"],
                "transcript": result["transcript"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main ASR evaluation prediction pipeline.

    Steps:
    1. Parse command line argument --model (whisper_base | whisper_large_v3_turbo | parakeet | all)
    2. Load ground-truth rows
    3. Run the selected models one at a time
    """
    # Step 1: Parse CLI argument --model
    parser = argparse.ArgumentParser(description="Run ASR eval predictions")
    parser.add_argument(
        "--model",
        required=True,
        help="whisper_base | whisper_large_v3_turbo | parakeet | all",
    )
    args = parser.parse_args()

    # Step 2: Load ground truth rows
    rows = load_gt_rows(GT_PATH)
    if not rows:
        raise SystemExit(f"No rows in {GT_PATH}")

    # Handle which models to run (one at a time)
    model = args.model.strip().lower()
    if model == "all":
        models = list(MODELS.keys())
    else:
        models = [model]

    # Step 3: Run the selected models one at a time
    print(f"Running {len(models)} model(s) on {len(rows)} clips")
    for model in models:
        print(f"Running {model}...")
        run_model(model, rows)
        print(f"Finished running {model}.")


if __name__ == "__main__":
    main()