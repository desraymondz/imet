"""
Run profile-generation models over the evaluation ground-truth set and store predictions.

Pipeline (one model at a time):
    1. Load ground-truth rows from profile_generation.jsonl
    2. Call Ollama for each capture input then write predictions
    3. Write eval/predictions/profile_generation/{model}.jsonl (overwrites if present)

Prediction row fields:
    id, model, prediction, raw_response, latency_ms, error

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Usage
    python eval/scripts/profile_generation/run_profile_eval.py --model qwen3.5_0.8b
    python eval/scripts/profile_generation/run_profile_eval.py --model qwen3.5_2b
    python eval/scripts/profile_generation/run_profile_eval.py --model qwen3.5_4b
    python eval/scripts/profile_generation/run_profile_eval.py --model all

Requires
    ollama serve
    ollama pull qwen3.5:0.8b
    ollama pull qwen3.5:2b
    ollama pull qwen3.5:4b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from profile_generation_engines import OLLAMA_TAGS, run_ollama_model

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "ground_truths" / "profile_generation.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "profile_generation"


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
    Run one profile-generation model on all ground-truth inputs and write prediction JSONL.

    Steps:
    1. Validate the CLI model name against OLLAMA_TAGS
    2. Call run_ollama_model on all dataset inputs
    3. Join GT metadata with results and write predictions/profile_generation/{model}.jsonl
    """
    # Step 1: Validate the CLI model name against OLLAMA_TAGS
    if model not in OLLAMA_TAGS:
        known = ", ".join(OLLAMA_TAGS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Ensure output directory exists for the predictions file
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    # Build the output path for the predictions file
    out_path = PRED_DIR / f"{model}.jsonl"

    # Collect capture inputs
    capture_inputs = [row["input"] for row in rows]

    # Step 2: Call the model on all capture inputs
    results = run_ollama_model(model, capture_inputs)

    # Step 3: Join GT metadata with results and write
    with out_path.open("w", encoding="utf-8") as fh:
        for row, result in zip(rows, results):
            record = {
                "id": row["id"],
                "model": model,
                "prediction": result["prediction"],
                "raw_response": result["raw_response"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    """
    Main profile-generation evaluation prediction pipeline.

    Steps:
    1. Parse CLI argument --model
    2. Load ground-truth rows
    3. Run the selected models one at a time
    """
    # Step 1: Parse CLI argument --model
    parser = argparse.ArgumentParser(description="Run profile-generation eval predictions")
    parser.add_argument(
        "--model",
        required=True,
        help="qwen3.5_4b | qwen3.5_2b | qwen3.5_0.8b | all",
    )
    args = parser.parse_args()

    # Step 2: Load ground truth rows
    rows = load_gt_rows(GT_PATH)
    if not rows:
        raise SystemExit(f"No rows in {GT_PATH}")

    # Handle which models to run (one at a time)
    model = args.model.strip().lower()
    if model == "all":
        models = list(OLLAMA_TAGS.keys())
    else:
        models = [model]

    # Step 3: Run the selected models one at a time
    print(f"Running {len(models)} model(s) on {len(rows)} capture inputs")
    for model in models:
        print(f"Running {model}...")
        run_model(model, rows)
        print(f"Finished running {model}.")


if __name__ == "__main__":
    main()