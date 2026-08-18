"""
Run end-to-end recall (cached QU then retrieve then filter) and store predictions

Pipeline (one model at a time):
    1. Load ground-truth rows from recall_queries.jsonl
    2. Load cached query-understanding predictions for that model
    3. Retrieve with predicted plan (keywords and HyDE)
    4. LLM-filter against the original user query
    4. Write eval/predictions/recall_e2e/{model}.jsonl

Prediction row fields:
    id, model, status, plan, candidate_ids, fts_ids, vector_ids,
    contact_ids, latency_ms, error

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Usage
    python eval/scripts/recall_e2e/run_recall_e2e_eval.py --model qwen3.5_0.8b
    python eval/scripts/recall_e2e/run_recall_e2e_eval.py --model qwen3.5_2b
    python eval/scripts/recall_e2e/run_recall_e2e_eval.py --model qwen3.5_4b
    python eval/scripts/recall_e2e/run_recall_e2e_eval.py --model all

Requires
    ollama serve
    ollama pull qwen3.5:0.8b / 2b / 4b
    EVAL_DATABASE_URL in .env.local
    python eval/scripts/recall/seed_eval_db.py
    python eval/scripts/query_understanding/run_query_understanding_eval.py --model <model>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from recall_e2e_engines import (
    OLLAMA_TAGS,
    load_jsonl,
    load_query_understanding_pred,
    run_ollama_model,
)

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "recall_queries.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "recall_e2e"


def write_predictions(
    model: str,
    gt_rows: list[dict],
    results: list[dict],
) -> Path:
    """
    Write eval/predictions/recall_e2e/{model}.jsonl
    """
    # Ensure output directory exists for the predictions file
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PRED_DIR / f"{model}.jsonl"

    # Write one JSON object per query
    with out_path.open("w", encoding="utf-8") as fh:
        for row, result in zip(gt_rows, results):
            record = {
                "id": row["id"],
                "model": model,
                "status": result["status"],
                "plan": result["plan"],
                "candidate_ids": result["candidate_ids"],
                "fts_ids": result["fts_ids"],
                "vector_ids": result["vector_ids"],
                "contact_ids": result["contact_ids"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path


def run_model(model: str, gt_rows: list[dict]) -> None:
    """
    Run one end-to-end recall model on all ground-truth queries and write JSONL
    """
    # Validate the CLI model name against OLLAMA_TAGS
    if model not in OLLAMA_TAGS:
        known = ", ".join(OLLAMA_TAGS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Load cached QU predictions and require every ground-truth id
    qu_by_id = load_query_understanding_pred(model)
    missing = [row["id"] for row in gt_rows if int(row["id"]) not in qu_by_id]
    if missing:
        raise SystemExit(
            f"QU predictions for {model} are missing ids: {missing}. "
            "Re-run query-understanding eval for this model."
        )

    # Call retrieve and filter on all queries
    results = run_ollama_model(model, gt_rows, qu_by_id)

    # Join GT metadata with results and write
    out_path = write_predictions(model, gt_rows, results)
    print(f"Wrote {len(gt_rows)} rows to: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main recall end-to-end evaluation pipeline

    Steps:
    1. Parse CLI arguments
    2. Load ground-truth rows
    3. Run the selected models one at a time
    """
    # Step 1: Parse CLI argument
    parser = argparse.ArgumentParser(description="Run recall end-to-end eval predictions")
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

    # Handle which models to run
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