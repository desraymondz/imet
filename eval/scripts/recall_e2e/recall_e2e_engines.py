"""
Recall end-to-end model runners for evaluation.

Each run:
    1. Load cached query-understanding predictions (not re-run)
    2. Apply production empty-field fallback on in-scope plans
    3. FTS (predicted keywords) merge with vector (predicted HyDE) candidates
    4. Filter merged candidates with LLM against the original user query
    5. Apply production filter LLM failure fallback

Used by
    eval/scripts/recall_e2e/run_recall_e2e_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

# Reuse retrieve and filter runners from the recall-filter eval
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall_filter"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall"))
from recall_filter_engines import (
    OLLAMA_TAGS,
    make_ollama_generate,
    retrieve_one,
    run_filter_one,
)
from seed_eval_db import eval_database_url, load_env

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
QU_PRED_DIR = REPO_ROOT / "eval" / "predictions" / "query_understanding"

# Fallback: empty plan used when the cached QU row has no prediction object
EMPTY_PLAN: dict[str, Any] = {
    "in_scope": False,
    "keywords": [],
    "hyde_rewrite": "",
}


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


def load_query_understanding_pred(model: str) -> dict[int, dict]:
    """
    Read cached query-understanding predictions and index them by query id.

    Does not re-run query understanding.
    """
    # Build the path to the cached QU predictions for this model
    path = QU_PRED_DIR / f"{model}.jsonl"

    # Fail early if QU eval has not been run yet
    if not path.is_file():
        raise SystemExit(
            f"Missing QU predictions at {path}. "
            "Run eval/scripts/query_understanding/run_query_understanding_eval.py "
            f"--model {model} first."
        )

    # Index rows by query id so e2e can join against ground truth
    by_id: dict[int, dict] = {}
    for row in load_jsonl(path):
        by_id[int(row["id"])] = row
    return by_id


def apply_plan_fallback(plan: dict, raw_query: str) -> dict:
    """
    If in_scope but keywords or HyDE are blank, fill them from the raw query
    """
    # Strip whitespace from the original user query
    cleaned_query = (raw_query or "").strip()
    # Split the query into tokens as fallback keywords
    fallback_keywords = [token for token in cleaned_query.split() if token]

    # Get in_scope from the cached prediction
    in_scope = bool(plan.get("in_scope", False))

    # Get keywords from the cached prediction
    keywords = plan.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    # Keep non-empty strings only and strip whitespace
    keywords = [
        item.strip()
        for item in keywords
        if isinstance(item, str) and item.strip()
    ]

    # Get HyDE rewrite from the cached prediction
    hyde_rewrite = plan.get("hyde_rewrite") or ""
    if not isinstance(hyde_rewrite, str):
        hyde_rewrite = ""
    # Strip whitespace from the HyDE rewrite
    hyde_rewrite = hyde_rewrite.strip()

    # Keep retrieval usable even if the model leaves fields blank (not a failure)
    if in_scope:
        # If the keywords are empty, set the fallback keywords
        if not keywords:
            keywords = fallback_keywords or ([cleaned_query] if cleaned_query else [])
        # If the HyDE rewrite is empty, use the raw query
        if not hyde_rewrite:
            hyde_rewrite = cleaned_query

    return {
        "in_scope": in_scope,
        "keywords": keywords,
        "hyde_rewrite": hyde_rewrite,
    }


def stage_latency(
    query_understanding_ms: float | None,
    retrieve_ms: float | None,
    filter_ms: float | None,
) -> dict[str, float | None]:
    """
    Build the per-stage latency dict
    """
    # Sum the stages latency
    total = 0.0
    for part in (query_understanding_ms, retrieve_ms, filter_ms):
        if isinstance(part, (int, float)):
            total += float(part)

    # Keep skipped stages as None
    return {
        "query_understanding": query_understanding_ms if isinstance(query_understanding_ms, (int, float)) else None,
        "retrieve": retrieve_ms if isinstance(retrieve_ms, (int, float)) else None,
        "filter": filter_ms if isinstance(filter_ms, (int, float)) else None,
        "total": round(total, 2),
    }


def _empty_ids() -> dict[str, list]:
    """
    Empty retrieve/filter id lists used when a stage is skipped
    """
    return {
        "candidate_ids": [],
        "fts_ids": [],
        "vector_ids": [],
        "contact_ids": [],
    }


def run_e2e_one(
    generate,
    raw_query: str,
    qu_row: dict,
    db: Session,
    max_candidates: int,
    min_score: float,
) -> dict:
    """
    Run retrieve and filter for one query using a cached QU prediction
    """
    # Reuse cached QU latency instead of calling the LLM again
    qu_ms = qu_row.get("latency_ms")
    if not isinstance(qu_ms, (int, float)):
        qu_ms = None

    # Get the cached plan
    raw_plan = qu_row.get("prediction")
    # Fallback to empty plan if the row has no prediction object
    if not isinstance(raw_plan, dict):
        raw_plan = dict(EMPTY_PLAN)

    # QU parse / LLM failure
    qu_error = qu_row.get("error")
    if qu_error:
        ids = _empty_ids()
        return {
            "status": "error",
            "plan": dict(raw_plan),
            **ids,
            "latency_ms": stage_latency(qu_ms, None, None),
            "error": qu_error,
        }

    # Apply production empty-field fallback then check scope
    plan = apply_plan_fallback(raw_plan, raw_query)
    # Out-of-scope: skip retrieve and filter
    if not plan["in_scope"]:
        ids = _empty_ids()
        return {
            "status": "out_of_scope",
            "plan": plan,
            **ids,
            "latency_ms": stage_latency(qu_ms, None, None),
            "error": None,
        }

    # Hybrid retrieve with predicted keywords and HyDE
    pool = retrieve_one(
        db=db,
        keywords=plan["keywords"],
        hyde_rewrite=plan["hyde_rewrite"],
        max_candidates=max_candidates,
        min_score=min_score,
    )

    # Get retrieve latency
    retrieve_ms = pool.get("latency_ms")
    if not isinstance(retrieve_ms, (int, float)):
        retrieve_ms = None

    # Get the contact id lists from retrieve
    candidate_ids = pool.get("candidate_ids") or []
    fts_ids = pool.get("fts_ids") or []
    vector_ids = pool.get("vector_ids") or []
    candidates = pool.get("candidates") or []

    # Retrieve failed: skip filter and return empty contact_ids
    if pool.get("error"):
        return {
            "status": "error",
            "plan": plan,
            "candidate_ids": candidate_ids,
            "fts_ids": fts_ids,
            "vector_ids": vector_ids,
            "contact_ids": [],
            "latency_ms": stage_latency(qu_ms, retrieve_ms, None),
            "error": pool["error"],
        }

    # Empty merged pool: skip the LLM filter
    if not candidates:
        return {
            "status": "no_matches",
            "plan": plan,
            "candidate_ids": candidate_ids,
            "fts_ids": fts_ids,
            "vector_ids": vector_ids,
            "contact_ids": [],
            "latency_ms": stage_latency(qu_ms, retrieve_ms, None),
            "error": None,
        }

    # LLM filter against the original user query
    filter_result = run_filter_one(generate, raw_query, candidates)

    # Get filter latency
    filter_ms = filter_result.get("latency_ms")
    if not isinstance(filter_ms, (int, float)):
        filter_ms = None

    # Fallback to the merged pool if the filter LLM fails
    filter_error = filter_result.get("error")
    if filter_error:
        return {
            "status": "ok",
            "plan": plan,
            "candidate_ids": candidate_ids,
            "fts_ids": fts_ids,
            "vector_ids": vector_ids,
            "contact_ids": list(candidate_ids),
            "latency_ms": stage_latency(qu_ms, retrieve_ms, filter_ms),
            "error": filter_error,
        }

    # Filter succeeded
    contact_ids = filter_result.get("contact_ids") or []
    status = "ok" if contact_ids else "no_matches"
    return {
        "status": status,
        "plan": plan,
        "candidate_ids": candidate_ids,
        "fts_ids": fts_ids,
        "vector_ids": vector_ids,
        "contact_ids": contact_ids,
        "latency_ms": stage_latency(qu_ms, retrieve_ms, filter_ms),
        "error": None,
    }


def run_e2e_all(
    name: str,
    generate,
    gt_rows: list[dict],
    qu_by_id: dict[int, dict],
    db: Session,
    max_candidates: int,
    min_score: float,
) -> list[dict]:
    """
    Run end-to-end recall on all ground-truth queries
    """
    results: list[dict] = []
    total = len(gt_rows)

    # Run retrieve and filter for each query using the cached QU plan
    for i, row in enumerate(gt_rows, start=1):
        # Look up the cached QU row by ground-truth id
        qu_row = qu_by_id[int(row["id"])]
        results.append(
            run_e2e_one(
                generate,
                row.get("query") or "",
                qu_row,
                db,
                max_candidates,
                min_score,
            )
        )

        # Log progress every 10 queries
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def run_ollama_model(
    cli_name: str,
    gt_rows: list[dict],
    qu_by_id: dict[int, dict],
) -> list[dict]:
    """
    Run one Ollama model (by CLI name) on all queries
    Opens eval database once, loads BGE once, then runs the batch
    """
    from sqlalchemy import create_engine

    # Load environment variables and put backend on sys.path
    load_env()

    from backend.ai.embeddings.bge import get_embedder
    from backend.config import settings

    # Get the max candidates and min score from the app's config settings
    max_candidates = settings.recall_max_candidates
    min_score = settings.recall_min_score

    # Look up the Ollama tag from the CLI name
    tag = OLLAMA_TAGS[cli_name]
    print(f"Using Ollama model {tag}...")

    # Builds a ready-to-call function for calling the Ollama filter
    generate = make_ollama_generate(tag)
    print(f"{tag} ready.")

    # Open a session on the eval database
    eval_engine = create_engine(eval_database_url(), pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=eval_engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    try:
        # Load the embedding model once and reuse it
        print("Loading BGE embedder...")
        get_embedder()
        print("BGE embedder ready.")

        # Run retrieve and filter on every query in the batch
        return run_e2e_all(
            cli_name,
            generate,
            gt_rows,
            qu_by_id,
            db,
            max_candidates,
            min_score,
        )
    finally:
        # Always close the session and dispose the engine
        db.close()
        eval_engine.dispose()