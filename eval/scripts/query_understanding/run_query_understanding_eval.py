"""
Run query-understanding models over the recall-query ground-truth set,
store predictions, then write aggregated metrics CSV.

Pipeline (one model at a time):
    1. Load ground-truth rows from recall_queries.jsonl
    2. Call Ollama for each query then write predictions
    3. Score predictions against GT and imet_eval embeddings for HyDE)
    4. Write eval/results/query_understanding_results.csv

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
    EVAL_DATABASE_URL and a seeded imet_eval (python eval/scripts/recall/seed_eval_db.py)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from query_understanding_engines import EMPTY_PREDICTION, OLLAMA_TAGS, run_ollama_model
from rapidfuzz import fuzz
from sqlalchemy import create_engine, select

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "recall_queries.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "query_understanding"
RESULTS_PATH = REPO_ROOT / "eval" / "results" / "query_understanding_results.csv"

# RapidFuzz ratio threshold after exact / substring matching for keyword matching
FUZZ_THRESHOLD = 85

# recall@K cutoffs for HyDE scoring
# 20 mirrors RECALL_MAX_CANDIDATES (the pool the reranker sees)
HYDE_RECALL_KS = (5, 20)


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


def normalise_token(token: str) -> str:
    """
    Lowercase and strip a keyword token for matching.
    """
    return token.strip().lower()


def tokens_match(expected: str, predicted: str) -> bool:
    """
    Check if the predicted keyword token matches the expected keyword token.
    """
    # Exact match after normalisation
    if expected == predicted:
        return True
    # Substring either way
    if expected in predicted or predicted in expected:
        return True
    # RapidFuzz fallback
    return fuzz.ratio(expected, predicted) >= FUZZ_THRESHOLD


def greedy_keyword_matches(expected: list[str], predicted: list[str]) -> int:
    """
    Counts how many ground-truth keywords got a unique predicted partner.
    """
    # Normalise tokens and drop empties
    expected_norm = [normalise_token(t) for t in expected if t.strip()]
    predicted_norm = [normalise_token(t) for t in predicted if t.strip()]
    used: set[int] = set()
    matched = 0

    # Greedy: for each expected token, take the first unused predicted match
    for exp in expected_norm:
        # Scan predicted tokens left to right, skip ones already paired
        for i, pred in enumerate(predicted_norm):
            if i in used:
                continue
            if tokens_match(exp, pred):
                # Lock this predicted token so it cannot match another GT token
                used.add(i)
                matched += 1
                break
    
    return matched


def prediction_or_empty(row: dict) -> dict:
    """
    Return the prediction dict, or the empty plan on missing/invalid prediction.
    """
    # Missing or malformed prediction row
    pred = row.get("prediction")
    if not isinstance(pred, dict):
        return dict(EMPTY_PREDICTION)

    return {
        "in_scope": bool(pred.get("in_scope", False)),
        "keywords": pred.get("keywords") if isinstance(pred.get("keywords"), list) else [],
        "hyde_rewrite": pred.get("hyde_rewrite") if isinstance(pred.get("hyde_rewrite"), str) else "",
    }


def mean(values: list[float]) -> float | None:
    """
    Return the arithmetic mean, or None if the list is empty.
    """
    # Empty list has no mean
    if not values:
        return None
    return float(sum(values) / len(values))


def dot(a: list[float], b: list[float]) -> float:
    """
    Dot product of two embeddings.
    Embeddings are L2-normalised so this is cosine similarity.
    """
    return float(sum(x * y for x, y in zip(a, b, strict=True)))


def load_contact_embeddings() -> dict[int, list[float]]:
    """
    Pulls every contact embedding out of the eval database
    so HyDE scoring can rank contacts without hitting Postgres on every query.

    Steps:
    1. Load EVAL_DATABASE_URL
    2. Query embedded contacts
    """
    # Step 1: Load env then import backend models
    load_dotenv(REPO_ROOT / ".env.local")
    # Puts repo root on Python import path to import backend models
    sys.path.insert(0, str(REPO_ROOT))
    from backend.models import Contact

    raw = os.environ.get("EVAL_DATABASE_URL", "").strip()
    if not raw:
        raise SystemExit("EVAL_DATABASE_URL is missing. Set it in .env.local")

    # Step 2: Query embedded contacts
    engine = create_engine(raw, pool_pre_ping=True)
    embeddings: dict[int, list[float]] = {}
    with engine.connect() as conn:
        rows = conn.execute(
            select(Contact.id, Contact.profile_embedding).where(
                Contact.profile_embedding.isnot(None)
            )
        ).all()
        # Build a mapping of contact id to embedding
        for contact_id, vector in rows:
            if vector is None:
                continue
            embeddings[int(contact_id)] = list(vector)
    engine.dispose()

    # Handle no contact embeddings
    if not embeddings:
        raise SystemExit(
            "imet_eval has no contact embeddings. "
            "Run: python eval/scripts/recall/seed_eval_db.py"
        )
    return embeddings


def score_in_scope(gt_rows: list[dict], pred_by_id: dict[int, dict]) -> list[dict]:
    """
    Exact bool match for in_scope

    Metrics:
        in_scope_acc for all queries
        in_scope_acc_true for GT in_scope is true
        in_scope_acc_false for GT in_scope is false
    """
    overall: list[bool] = []
    when_true: list[bool] = []
    when_false: list[bool] = []

    for gt in gt_rows:
        expected = bool(gt["expected"]["in_scope"])
        pred = prediction_or_empty(pred_by_id[gt["id"]])
        # True if predicted in_scope matches ground truth
        correct = pred["in_scope"] is expected
        overall.append(correct)
        # Split so a model that always predicts true cannot hide on the false slice
        if expected:
            when_true.append(correct)
        else:
            when_false.append(correct)

    return [
        {"metric": "in_scope_acc", "value": mean(overall), "n": len(overall)},
        {"metric": "in_scope_acc_true", "value": mean(when_true), "n": len(when_true)},
        {"metric": "in_scope_acc_false", "value": mean(when_false), "n": len(when_false)},
    ]


def score_keywords(gt_rows: list[dict], pred_by_id: dict[int, dict]) -> list[dict]:
    """
    Keyword recall and precision with greedy 1 to1 matching.

    recall = matched tokens / GT tokens
    precision = matched tokens / predicted tokens
    (skip queries with no GT or predicted keywords)
    """
    matched_expected = 0
    expected_total = 0
    matched_predicted = 0
    predicted_total = 0

    for gt in gt_rows:
        # Keep non-empty string keywords only
        raw_expected = gt["expected"].get("keywords") or []
        expected = [kw for kw in raw_expected if isinstance(kw, str) and kw.strip()]
        
        pred = prediction_or_empty(pred_by_id[gt["id"]])
        predicted = [kw for kw in pred["keywords"] if isinstance(kw, str) and kw.strip()]
        
        # Count how many ground-truth keywords got a unique predicted partner
        matched = greedy_keyword_matches(expected, predicted)

        # Recall denominator skips queries with no expected keywords
        if expected:
            matched_expected += matched
            expected_total += len(expected)
        # Precision denominator skips queries with no predicted keywords
        if predicted:
            matched_predicted += matched
            predicted_total += len(predicted)

    # Average across queries
    recall = (matched_expected / expected_total) if expected_total else None
    precision = (matched_predicted / predicted_total) if predicted_total else None
    return [
        {"metric": "keyword_recall", "value": recall, "n": expected_total},
        {"metric": "keyword_precision", "value": precision, "n": predicted_total},
    ]


def score_hyde(
    gt_rows: list[dict],
    pred_by_id: dict[int, dict],
    contact_embeddings: dict[int, list[float]],
) -> list[dict]:
    """
    Score the quality of the HyDE retrieval vs the raw query
    """
    from backend.ai.embeddings.bge import get_embedder

    # Get the same embedder as main app
    embedder = get_embedder()
    # List of all contact ids
    ranked_ids = list(contact_embeddings.keys())
    # Lists for HyDE scoring metrics
    beats: list[float] = []
    # One recall list per cutoff, keyed by K
    recalls: dict[int, list[float]] = {k: [] for k in HYDE_RECALL_KS}

    for gt in gt_rows:
        expected_ids = [int(i) for i in (gt["expected"].get("contact_ids") or [])]
        # Skip out-of-scope / no-match queries
        if not expected_ids:
            continue
        # Drop expected ids that were not seeded into imet_eval
        expected_ids = [i for i in expected_ids if i in contact_embeddings]
        if not expected_ids:
            continue

        pred = prediction_or_empty(pred_by_id[gt["id"]])
        raw_query = gt["query"].strip()
        hyde_text = (pred["hyde_rewrite"] or "").strip()
        # Skip if the LLM produced no HyDE rewrite
        if not hyde_text:
            continue

        # Embed raw query and HyDE rewrite
        raw_vec = embedder.embed_text(raw_query)
        hyde_vec = embedder.embed_text(hyde_text)

        # Build a list of beat flags for each expected contact
        beat_flags = [
            1.0
            if dot(hyde_vec, contact_embeddings[cid]) > dot(raw_vec, contact_embeddings[cid])
            else 0.0
            for cid in expected_ids
        ]
        beats.append(sum(beat_flags) / len(beat_flags))

        # Rank contacts by HyDE cosine (descending)
        scored = sorted(
            ranked_ids,
            key=lambda cid: dot(hyde_vec, contact_embeddings[cid]),
            reverse=True,
        )
        expected_id_set = set(expected_ids)

        # recall@K: expected contacts found in the top K, divided by how many could fit there.
        # Cap the denominator at K so queries with more than K expected contacts can still score 1.0
        for k in HYDE_RECALL_KS:
            top_k = scored[:k]
            recalls[k].append(
                sum(1 for cid in top_k if cid in expected_id_set)
                / min(len(expected_ids), k)
            )

    # Calculate the mean for each metric
    return [
        {"metric": "hyde_beats_raw", "value": mean(beats), "n": len(beats)},
        *[
            {
                "metric": f"hyde_recall@{k}",
                "value": mean(recalls[k]),
                "n": len(recalls[k]),
            }
            for k in HYDE_RECALL_KS
        ],
    ]


def score_model(gt_rows: list[dict], pred_rows: list[dict], contact_embeddings: dict[int, list[float]]) -> list[dict]:
    """
    Score one model's predictions and attach latency_ms_mean to every metric row.
    """
    # Index predictions by query id
    pred_by_id = {int(row["id"]): row for row in pred_rows}
    # Skip rows with no latency (empty queries)
    latencies = [
        float(row["latency_ms"])
        for row in pred_rows
        if row.get("latency_ms") is not None
    ]
    latency_ms_mean = mean(latencies)

    # Score in_scope, keywords, and HyDE
    metric_rows = []
    metric_rows.extend(score_in_scope(gt_rows, pred_by_id))
    metric_rows.extend(score_keywords(gt_rows, pred_by_id))
    metric_rows.extend(score_hyde(gt_rows, pred_by_id, contact_embeddings))

    # Copy mean LLM latency onto each metric row
    for row in metric_rows:
        row["latency_ms_mean"] = latency_ms_mean
    return metric_rows


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


def write_results_csv(rows: list[dict], replace_models: list[str]) -> None:
    """
    Write eval/results/query_understanding_results.csv.

    Keeps existing rows for other models (only adds new rows for the current model)

    Steps:
    1. Keep existing CSV rows
    2. Append the new metric rows
    3. Overwrite the CSV
    """
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["model", "metric", "value", "n", "latency_ms_mean"]
    replace = set(replace_models)
    merged: list[dict] = []

    # Step 1: Keep existing CSV rows
    if RESULTS_PATH.is_file():
        with RESULTS_PATH.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("model") not in replace:
                    merged.append(row)

    # Step 2: Append the new metric rows
    merged.extend(rows)

    # Step 3: Overwrite the CSV
    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in merged:
            writer.writerow(
                {
                    "model": row["model"],
                    "metric": row["metric"],
                    "value": row["value"],
                    "n": row["n"],
                    "latency_ms_mean": row["latency_ms_mean"],
                }
            )


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


def score_models(models: list[str], gt_rows: list[dict]) -> None:
    """
    Score existing prediction JSONL files and write the results CSV.
    """
    # Load contact embeddings from imet_eval
    contact_embeddings = load_contact_embeddings()
    print(f"Loaded {len(contact_embeddings)} contact embeddings from imet_eval")

    # Score each model
    csv_rows: list[dict] = []
    for model in models:
        pred_path = PRED_DIR / f"{model}.jsonl"
        if not pred_path.is_file():
            raise SystemExit(f"Missing predictions file: {pred_path}")
        
        pred_rows = load_jsonl(pred_path)
        print(f"Scoring {model}...")
        for metric_row in score_model(gt_rows, pred_rows, contact_embeddings):
            csv_rows.append({"model": model, **metric_row})

    # Write the results CSV
    write_results_csv(csv_rows, models)
    print(f"Wrote {len(csv_rows)} rows to: {RESULTS_PATH.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main query-understanding evaluation pipeline.

    Steps:
    1. Parse CLI arguments
    2. Load ground-truth rows
    3. Run the selected model(s)
    4. Score predictions and write CSV
    """
    # Step 1: Parse CLI argument --model
    parser = argparse.ArgumentParser(description="Run query-understanding eval")
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

    # Step 4: Score predictions and write CSV
    score_models(models, gt_rows)


if __name__ == "__main__":
    main()