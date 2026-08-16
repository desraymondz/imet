"""
Run query-understanding models over the recall-query ground-truth set and store predictions.

Pipeline (one model at a time):
    1. Load ground-truth rows from recall_queries.jsonl
    2. Call Ollama for each query then write predictions
    3. Write eval/predictions/query_understanding/{model}.jsonl

Prediction row fields:
    id, model, prediction, latency_ms, error

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Usage
    python eval/scripts/query_understanding/run_query_understanding_eval.py --model qwen3.5_0.8b
    python eval/scripts/query_understanding/run_query_understanding_eval.py --model qwen3.5_2b
    python eval/scripts/query_understanding/run_query_understanding_eval.py --model qwen3.5_4b
    python eval/scripts/query_understanding/run_query_understanding_eval.py --model all

Requires
    ollama serve
    ollama pull qwen3.5:0.8b / 2b / 4b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from query_understanding_engines import OLLAMA_TAGS, run_ollama_model

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "recall_queries.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "query_understanding"


def load_jsonl(path: Path) -> list[dict]:
    """
    Load rows from a JSONL file then convert into a list of dictionaries
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


def write_predictions(model: str, gt_rows: list[dict], results: list[dict]) -> Path:
    """
    Write eval/predictions/query_understanding/{model}.jsonl (overwrites if present).
    """
    # Ensure output directory exists for the predictions file
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PRED_DIR / f"{model}.jsonl"

    # Write one JSON object per query (same order as ground-truth rows)
    with out_path.open("w", encoding="utf-8") as fh:
        for row, result in zip(gt_rows, results):
            record = {
                "id": row["id"],
                "model": model,
                "prediction": result["prediction"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path


def run_model(model: str, gt_rows: list[dict]) -> None:
    """
    Run one query-understanding model on all ground-truth queries and write prediction JSONL.
    """
    # Validate the CLI model name against OLLAMA_TAGS
    if model not in OLLAMA_TAGS:
        known = ", ".join(OLLAMA_TAGS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Build a list of query strings
    queries = [row["query"] for row in gt_rows]

    # Call the model on all queries
    results = run_ollama_model(model, queries)

    # Join GT metadata with results and write
    out_path = write_predictions(model, gt_rows, results)
    print(f"Wrote {len(gt_rows)} rows to: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main query-understanding evaluation pipeline.

    Steps:
    1. Parse CLI arguments
    2. Load ground-truth rows
    3. Run the selected model(s)
    """
    # Step 1: Parse CLI argument --model
    parser = argparse.ArgumentParser(description="Run query-understanding eval predictions")
    parser.add_argument(
        "--model",
        required=True,
        help="qwen3.5_4b | qwen3.5_2b | qwen3.5_0.8b | all",
    )
    args = parser.parse_args()

    # Step 2: Load ground truth rows
    gt_rows = load_jsonl(GT_PATH)
    if not gt_rows:
        raise SystemExit(f"No rows in {GT_PATH}")

    # Handle which models to run (one at a time)
    model = args.model.strip().lower()
    if model == "all":
        models = list(OLLAMA_TAGS.keys())
    else:
        models = [model]
        if model not in OLLAMA_TAGS:
            known = ", ".join(OLLAMA_TAGS)
            raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Step 3: Run the selected models one at a time
    print(f"Running {len(models)} model(s) on {len(gt_rows)} queries")
    for name in models:
        print(f"Running {name}...")
        run_model(name, gt_rows)
        print(f"Finished running {name}.")


if __name__ == "__main__":
    main()
