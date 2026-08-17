"""
Run recall-filter models over in-scope recall queries and store predictions.

Pipeline (one model at a time):
    1. Load ground-truth rows from recall_queries.jsonl
    2. Keep in_scope rows only
    3. Build merged FTS + vector candidate pools on imet_eval (once, reused across models)
    4. Call Ollama to filter each pool against the original user query
    5. Write eval/predictions/recall_filter/{model}.jsonl

Prediction row fields:
    id, model, candidate_ids, contact_ids, latency_ms, error

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Usage
    python eval/scripts/recall_filter/run_recall_filter_eval.py --model qwen3.5_0.8b
    python eval/scripts/recall_filter/run_recall_filter_eval.py --model qwen3.5_2b
    python eval/scripts/recall_filter/run_recall_filter_eval.py --model qwen3.5_4b
    python eval/scripts/recall_filter/run_recall_filter_eval.py --model all

Requires
    ollama serve
    ollama pull qwen3.5:0.8b / 2b / 4b
    EVAL_DATABASE_URL in .env.local
    python eval/scripts/recall/seed_eval_db.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from recall_filter_engines import (
    OLLAMA_TAGS,
    retrieve_merged_candidates,
    run_ollama_model,
)

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "recall_queries.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "recall_filter"


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


def in_scope_rows(gt_rows: list[dict]) -> list[dict]:
    """
    Keep queries that are in scope
    """
    kept: list[dict] = []
    for row in gt_rows:
        expected = row.get("expected") or {}
        # Only keep rows that are in scope
        if expected.get("in_scope") is True:
            kept.append(row)
    return kept


def write_predictions(
    model: str,
    gt_rows: list[dict],
    candidate_pools: list[dict],
    results: list[dict],
) -> Path:
    """
    Write eval/predictions/recall_filter/{model}.jsonl
    """
    # Ensure output directory exists for the predictions file
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PRED_DIR / f"{model}.jsonl"

    # Write one JSON object per query
    with out_path.open("w", encoding="utf-8") as fh:
        for row, pool, result in zip(gt_rows, candidate_pools, results):
            record = {
                "id": row["id"],
                "model": model,
                "candidate_ids": pool.get("candidate_ids") or [],
                "contact_ids": result["contact_ids"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path


def run_model(
    model: str,
    gt_rows: list[dict],
    candidate_pools: list[dict],
) -> None:
    """
    Run one recall-filter model on all in-scope queries and write prediction JSONL.
    """
    # Validate the CLI model name against OLLAMA_TAGS
    if model not in OLLAMA_TAGS:
        known = ", ".join(OLLAMA_TAGS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Build a list of query strings
    queries = [row["query"] for row in gt_rows]

    # Call the model on all queries
    results = run_ollama_model(model, queries, candidate_pools)

    # Join GT metadata with results and write
    out_path = write_predictions(model, gt_rows, candidate_pools, results)
    print(f"Wrote {len(gt_rows)} rows to: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main recall-filter evaluation pipeline.

    Steps:
    1. Parse CLI arguments
    2. Load ground-truth rows
    3. Build merged FTS and vector candidate pools
    4. Run the selected models one at a time
    """
    # Step 1: Parse CLI argument
    parser = argparse.ArgumentParser(description="Run recall-filter eval predictions")
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

    # Keep only the in-scope queries
    kept = in_scope_rows(gt_rows)
    if not kept:
        raise SystemExit(f"No in-scope rows in {GT_PATH}")

    print(f"Keeping {len(kept)} in-scope queries")

    # Handle which models to run (one at a time)
    model = args.model.strip().lower()
    if model == "all":
        models = list(OLLAMA_TAGS.keys())
    else:
        models = [model]
        if model not in OLLAMA_TAGS:
            known = ", ".join(OLLAMA_TAGS)
            raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Step 3: Build merged FTS and vector candidate pools
    print("Building merged FTS and vector candidate pools...")
    candidate_pools = retrieve_merged_candidates(kept)

    # Step 4: Run the selected models one at a time
    print(f"Running {len(models)} models on {len(kept)} queries")
    for name in models:
        print(f"Running {name}...")
        run_model(name, kept, candidate_pools)
        print(f"Finished running {name}.")


if __name__ == "__main__":
    main()