"""
Run semantic retrieval over in-scope recall queries and store ranked predictions.

Pipeline:
    1. Load ground-truth rows from recall_queries.jsonl
    2. Keep in_scope rows only (skip out-of-scope with no embed or SQL)
    3. Embed the raw user query with BGE then rank eval contacts
    4. Write eval/predictions/semantic_retrieval/bge_base_en_v1.5.jsonl

Prediction row fields:
    id, query_source, ranked, latency_ms, error

query_source:
    raw_query  original user query (selected based on QU evaluation criteria)

Usage
    python eval/scripts/semantic_retrieval/run_semantic_retrieval_eval.py

Requires
    EVAL_DATABASE_URL and EMBEDDING_MODEL in .env.local
    python eval/scripts/recall/seed_eval_db.py
"""

from __future__ import annotations

import json
from pathlib import Path

from semantic_retrieval_engines import run_bge_engine

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "recall_queries.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "semantic_retrieval"
PRED_PATH = PRED_DIR / "bge_base_en_v1.5.jsonl"


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


def write_predictions(records: list[dict]) -> Path:
    """
    Write eval/predictions/semantic_retrieval/bge_base_en_v1.5.jsonl
    """
    # Ensure output directory exists
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    # Write one JSON object per query and query_source
    with PRED_PATH.open("w", encoding="utf-8") as pred_file:
        for record in records:
            pred_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return PRED_PATH


def main() -> None:
    """
    Main semantic-retrieval evaluation pipeline.

    Steps:
    1. Load ground-truth rows
    2. Keep only the in-scope queries
    3. Run BGE ranking then write predictions
    """
    # Step 1: Load ground truth rows
    gt_rows = load_jsonl(GT_PATH)
    if not gt_rows:
        raise SystemExit(f"No rows in {GT_PATH}")

    # Step 2: Keep only the in-scope queries
    kept = in_scope_rows(gt_rows)
    if not kept:
        raise SystemExit(f"No in-scope rows in {GT_PATH}")

    print(f"Keeping {len(kept)} in-scope queries")

    # Embed the raw user query
    raw_texts = [(row.get("query") or "") for row in kept]

    # Step 3: Rank then write predictions
    raw_results = run_bge_engine(raw_texts)

    records: list[dict] = []
    for row, result in zip(kept, raw_results):
        records.append(
            {
                "id": row["id"],
                "query_source": "raw_query",
                "ranked": result["ranked"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
            }
        )

    out_path = write_predictions(records)
    print(f"Wrote {len(records)} rows to: {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
