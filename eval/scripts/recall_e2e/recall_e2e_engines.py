"""
Recall end-to-end model runners for evaluation.

Each run:
    1. Query understanding with the production prompt (in_scope + keywords)
    2. Apply production empty-keyword fallback on in-scope plans
    3. FTS (predicted keywords) merge with vector (raw user query) candidates
    4. Filter merged candidates with LLM against the original user query
    5. Apply production filter LLM failure fallback

Used by
    eval/scripts/recall_e2e/run_recall_e2e_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

# Reuse retrieve and filter runners from the recall-filter eval
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall_filter"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "query_understanding"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall"))
from recall_filter_engines import (
    OLLAMA_TAGS,
    make_ollama_generate,
    retrieve_one,
    run_filter_one,
)
from query_understanding_engines import parse_in_scope, parse_keywords, strip_json_fences
from seed_eval_db import eval_database_url, load_env

# Same schema as RECALL_QUERY_PLAN_OLLAMA_SCHEMA in backend/ai/llm/ollama.py
PROD_QU_SCHEMA = {
    "type": "object",
    "properties": {
        "in_scope": {"type": "boolean"},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["in_scope", "keywords"],
}

# Fallback: empty plan used on skip / parse failures
EMPTY_PLAN: dict[str, Any] = {
    "in_scope": False,
    "keywords": [],
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


def build_prod_qu_prompt(query: str) -> str:
    """
    Production query-understanding prompt (no HyDE).
    Same text as backend/ai/llm/ollama.py understand_recall_query.
    """
    cleaned_query = query.strip()
    return f"""You only plan contact-list search. You are not a general assistant. Be strict.

The user asked:
{cleaned_query}

Produce a query plan with:
- in_scope: default false. true only if they want a person from their private list.
  Contact search: names, classmates, who did I meet, who likes ..., who is a ..., who plays ...
  Out of scope: instructions to you, calculations, explanations, bookings, translation, and public-fact questions.
  When unsure, return false.
- keywords: short lexical search terms as a JSON string array for full-text search
  (names, companies, roles, places, hobbies). Empty array if out of scope.

Example in scope:
User asked: Who did I meet that likes hiking?
Output:
{{"in_scope": true, "keywords": ["hiking", "outdoors"]}}

Example out of scope:
User asked: what's the capital of China
Output:
{{"in_scope": false, "keywords": []}}

Respond with valid JSON only.
"""


def parse_prod_plan_response(response: str) -> dict[str, Any]:
    """
    Parse a production query-plan JSON response (in_scope + keywords only).
    """
    cleaned = strip_json_fences(response)
    if cleaned.strip() in ("", "{}", "{ }"):
        raise ValueError("LLM returned empty JSON object")

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")

    return {
        "in_scope": parse_in_scope(data.get("in_scope", False)),
        "keywords": parse_keywords(data.get("keywords", [])),
    }


def make_prod_qu_generate(ollama_tag: str):
    """
    Build a generate(query) function using the production QU prompt and schema.
    """
    from ollama import Client

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = Client(host=host)

    def generate(query: str) -> dict[str, Any]:
        messages = [{"role": "user", "content": build_prod_qu_prompt(query)}]
        last_error: Exception | None = None
        for response_format in (PROD_QU_SCHEMA, "json"):
            try:
                response = client.chat(
                    model=ollama_tag,
                    messages=messages,
                    format=response_format,
                    think=False,
                    options={"temperature": 0.1},
                )
                return parse_prod_plan_response(response.message.content or "")
            except Exception as exc:
                last_error = exc
        raise last_error if last_error else RuntimeError("Query understanding failed")

    return generate


def apply_plan_fallback(plan: dict, raw_query: str) -> dict:
    """
    If in_scope but keywords are blank, fill them from the raw query
    """
    # Strip whitespace from the original user query
    cleaned_query = (raw_query or "").strip()
    # Split the query into tokens as fallback keywords
    fallback_keywords = [token for token in cleaned_query.split() if token]

    # Get in_scope from the query plan
    in_scope = bool(plan.get("in_scope", False))

    # Get keywords from the query plan
    keywords = plan.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    # Keep non-empty strings only and strip whitespace
    keywords = [
        item.strip()
        for item in keywords
        if isinstance(item, str) and item.strip()
    ]

    # Keep retrieval usable even if the model leaves keywords blank (not a failure)
    if in_scope:
        # If the keywords are empty, set the fallback keywords
        if not keywords:
            keywords = fallback_keywords or ([cleaned_query] if cleaned_query else [])

    return {
        "in_scope": in_scope,
        "keywords": keywords,
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
    qu_generate,
    filter_generate,
    raw_query: str,
    db: Session,
    max_candidates: int,
    min_score: float,
) -> dict:
    """
    Run production query understanding, retrieve, and filter for one query.
    """
    # Empty query is out of scope (same as production)
    if not (raw_query or "").strip():
        ids = _empty_ids()
        return {
            "status": "out_of_scope",
            "plan": dict(EMPTY_PLAN),
            **ids,
            "latency_ms": stage_latency(None, None, None),
            "error": None,
        }

    # Phase 1: production query understanding (no HyDE)
    t0 = time.perf_counter()
    try:
        raw_plan = qu_generate(raw_query)
        qu_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        ids = _empty_ids()
        qu_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "error",
            "plan": dict(EMPTY_PLAN),
            **ids,
            "latency_ms": stage_latency(qu_ms, None, None),
            "error": f"{type(exc).__name__}: {exc}",
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

    # Hybrid retrieve with predicted keywords and the raw user query
    pool = retrieve_one(
        db=db,
        keywords=plan["keywords"],
        query_text=raw_query,
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
    filter_result = run_filter_one(filter_generate, raw_query, candidates)

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
    qu_generate,
    filter_generate,
    gt_rows: list[dict],
    db: Session,
    max_candidates: int,
    min_score: float,
) -> list[dict]:
    """
    Run end-to-end recall on all ground-truth queries
    """
    results: list[dict] = []
    total = len(gt_rows)

    # Run production QU, retrieve, and filter for each query
    for i, row in enumerate(gt_rows, start=1):
        results.append(
            run_e2e_one(
                qu_generate,
                filter_generate,
                row.get("query") or "",
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

    # Production QU (no HyDE) and filter, same model tag
    qu_generate = make_prod_qu_generate(tag)
    filter_generate = make_ollama_generate(tag)
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

        # Run QU, retrieve, and filter on every query in the batch
        return run_e2e_all(
            cli_name,
            qu_generate,
            filter_generate,
            gt_rows,
            db,
            max_candidates,
            min_score,
        )
    finally:
        # Always close the session and dispose the engine
        db.close()
        eval_engine.dispose()