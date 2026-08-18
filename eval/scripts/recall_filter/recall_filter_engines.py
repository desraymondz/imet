"""
Recall-filter model runners for evaluation.

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Each run:
    1. Connect to imet_eval
    2. FTS (GT keywords) merge with vector (GT HyDE) candidates
    3. Filter merged candidates with LLM against the original user query
    4. Return when the batch finishes

Prompt and schema match backend/ai/llm/ollama.py filter_recall_matches.
Retrieve matches backend/routers/recall.py Phase 2 (FTS and vector then merge).

Used by
    eval/scripts/recall_filter/run_recall_filter_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

# Get helper functions and config from eval/scripts/recall/seed_eval_db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall"))
from seed_eval_db import EVAL_OWNER_ID, eval_database_url, load_env

# Flat JSON schema passed to Ollama for structured output
# Same schema as RECALL_FILTER_OLLAMA_SCHEMA in backend/ai/llm/ollama.py
RECALL_FILTER_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "contact_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["contact_ids"],
}

# Model name maps to Ollama tag name (since colons are invalid in filenames)
OLLAMA_TAGS = {
    "qwen3.5_4b": "qwen3.5:4b",
    "qwen3.5_2b": "qwen3.5:2b",
    "qwen3.5_0.8b": "qwen3.5:0.8b",
}


def strip_json_fences(content: str) -> str:
    """
    Remove markdown JSON fences (```json ... ```) from LLM response.
    """
    text = content.strip()

    # Return unchanged if not fenced
    if not text.startswith("```"):
        return text

    # Drop opening fence (```json or ```)
    text = text.removeprefix("```json").removeprefix("```").strip()

    # Drop closing fence
    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def parse_contact_ids(raw_ids: Any) -> list[int]:
    """
    Contact ID field parser for the LLM.
    The schema wants a list of int, but LLM sometimes returns strings or other junk.
    """
    if not isinstance(raw_ids, list):
        raise ValueError("contact_ids is not a JSON array")

    parsed: list[int] = []
    for item in raw_ids:
        # Skip bool (True/False are not 1/0)
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            parsed.append(item)
            continue
        # Handle strings (e.g. "67" into 67)
        if isinstance(item, str) and item.strip():
            parsed.append(int(item.strip()))
            continue
        raise ValueError(f"contact_ids contains a non-integer: {item!r}")
    return parsed


def parse_filter_response(response: str, candidate_ids: list[int]) -> list[int]:
    """
    Parse a recall-filter JSON response from the LLM.
    Returns a list of int contact IDs, skipping any hallucinated IDs.
    """
    # Strip markdown fences
    cleaned = strip_json_fences(response)

    # Reject empty responses
    if cleaned.strip() in ("", "{}", "{ }"):
        raise ValueError("LLM returned empty JSON object")

    # Parse JSON
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")

    contact_ids = parse_contact_ids(data.get("contact_ids", []))
    allowed = set(candidate_ids)

    # Keep only IDs that were in the candidate list, skip hallucinated IDs
    matched_ids: list[int] = []
    for contact_id in contact_ids:
        if contact_id in allowed:
            matched_ids.append(contact_id)
    return matched_ids


def candidate_from_contact(contact) -> dict[str, Any]:
    """
    Build the candidate dict passed to the filter prompt.
    Same fields as RecallFilterCandidate in backend/schemas.py
    """
    return {
        "id": int(contact.id),
        "display_name": contact.display_name,
        "company": contact.company,
        "role": contact.role,
        "location": contact.location,
        "profile_text": contact.profile_text,
        "keywords": list(contact.keywords or []),
    }


def build_prompt(query: str, candidates: list[dict]) -> str:
    """
    Build the recall-filter prompt.

    Same prompt as the main app (backend/ai/llm/ollama.py filter_recall_matches)
    """
    # Build the prompt for each candidate and its fields
    candidate_lines: list[str] = []
    for candidate in candidates:
        name = (candidate.get("display_name") or "").strip() or "Unknown"
        company = (candidate.get("company") or "").strip() or "none"
        role = (candidate.get("role") or "").strip() or "none"
        location = (candidate.get("location") or "").strip() or "none"
        keywords = ", ".join(candidate.get("keywords") or []) or "none"
        profile_text = (candidate.get("profile_text") or "").strip() or "none"
        candidate_lines.append(
            "\n".join(
                [
                    f"- id: {candidate['id']}",
                    f"  name: {name}",
                    f"  company: {company}",
                    f"  role: {role}",
                    f"  location: {location}",
                    f"  keywords: {keywords}",
                    f"  profile_text: {profile_text}",
                ]
            )
        )

    # Join the candidate blocks with newlines
    candidates_block = "\n\n".join(candidate_lines)

    return f"""You are helping someone recall people they have met.

The user asked:
{query.strip()}

Here are candidate contacts retrieved from their network:

{candidates_block}

Return contact_ids for the candidates that genuinely match the user's question.
- Return IDs in best-match order.
- Return an empty list if none of the candidates truly match.
- Only use IDs from the candidate list above.
- Do not invent contacts or facts not supported by the candidate summaries.

Example:
{{"contact_ids": [12, 45]}}

If none match:
{{"contact_ids": []}}

Respond with valid JSON only.
"""


def retrieve_one(
    db: Session,
    keywords: list[str],
    hyde_rewrite: str,
    max_candidates: int,
    min_score: float,
) -> dict:
    """
    FTS and vector retrieve then merge
    Same as backend/routers/recall.py

    Returns a dict with candidates, candidate_ids, fts_ids, vector_ids, latency_ms, and optional error.
    """
    from backend.ai.embeddings.bge import get_embedder
    from backend.ai.retrieval.fts import search_contacts_fts
    from backend.ai.retrieval.hybrid import merge_recall_candidates
    from backend.models import Contact

    # Track the contact ids for each retriever found
    fts_ids: list[int] = []
    vector_ids: list[int] = []

    # Start timer for retrieve latency (embed and query)
    t0 = time.perf_counter()
    try:
        # Lexical retrieve (FTS on search_tsv, keywords OR)
        fts_results = search_contacts_fts(
            db=db,
            owner_id=EVAL_OWNER_ID,
            keywords=keywords,
            limit=max_candidates,
        )
        fts_ids = [int(contact.id) for contact, _rank in fts_results]

        # Semantic retrieve (embed HyDE rewrite, rank by cosine similarity)
        vector_results: list[tuple] = []
        cleaned_hyde = hyde_rewrite.strip()
        if cleaned_hyde:
            query_vector = get_embedder().embed_text(cleaned_hyde)
            # Rank contacts by cosine distance (lower = more similar)
            distance = Contact.profile_embedding.cosine_distance(query_vector).label(
                "distance"
            )
            # Get the eval contacts that have a profile_embedding ordered by similarity
            vector_rows = (
                db.query(Contact, distance)
                .filter(
                    Contact.owner_id == EVAL_OWNER_ID,
                    Contact.profile_embedding.isnot(None),
                )
                .order_by(distance)
                .limit(max_candidates)
                .all()
            )
            for contact, raw_distance in vector_rows:
                score = 1 - float(raw_distance)
                # Skip contacts below the minimum similarity threshold
                if score < min_score:
                    continue
                vector_results.append((contact, score))
        vector_ids = [int(contact.id) for contact, _score in vector_results]

        # Merge vector and FTS results by contact id
        results = merge_recall_candidates(
            vector_results=vector_results,
            fts_results=fts_results,
        )
        candidates = [candidate_from_contact(result.contact) for result in results]
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "candidates": candidates,
            "candidate_ids": [candidate["id"] for candidate in candidates],
            "fts_ids": fts_ids,
            "vector_ids": vector_ids,
            "latency_ms": latency_ms,
            "error": None,
        }

    except Exception as exc:
        # Retrieval failed, store error
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "candidates": [],
            "candidate_ids": [],
            "fts_ids": fts_ids,
            "vector_ids": vector_ids,
            "latency_ms": latency_ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def retrieve_merged_candidates(gt_rows: list[dict]) -> list[dict]:
    """
    Build merged FTS and vector candidates for every in-scope ground truth row.
    Uses expected.keywords and expected.hyde_rewrite
    """
    from sqlalchemy import create_engine

    # Load environment variables
    load_env()

    # Get the max candidates and min score from the app's config settings
    from backend.ai.embeddings.bge import get_embedder
    from backend.config import settings

    max_candidates = settings.recall_max_candidates
    min_score = settings.recall_min_score
    print(f"Retrieving up to {max_candidates} merged FTS and vector candidates per query")

    # Open a session on the eval database
    eval_engine = create_engine(eval_database_url(), pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=eval_engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    results: list[dict] = []
    total = len(gt_rows)

    try:
        # Load the embedding model once and reuse it
        print("Loading BGE embedder...")
        get_embedder()
        print("BGE embedder ready.")

        # Rank contacts for each query against imet_eval
        for i, row in enumerate(gt_rows, start=1):
            expected = row.get("expected") or {}
            keywords = expected.get("keywords") or []
            if not isinstance(keywords, list):
                keywords = []
            hyde_rewrite = expected.get("hyde_rewrite") or ""
            if not isinstance(hyde_rewrite, str):
                hyde_rewrite = ""

            results.append(
                retrieve_one(
                    db=db,
                    keywords=keywords,
                    hyde_rewrite=hyde_rewrite,
                    max_candidates=max_candidates,
                    min_score=min_score,
                )
            )

            # Log progress every 10 queries
            if i % 10 == 0 or i == total:
                print(f"  [retrieve] {i}/{total}")
    finally:
        db.close()
        eval_engine.dispose()

    return results


def run_filter_one(generate, raw_query: str, candidates: list[dict]) -> dict:
    """
    Run filter for one original user query and its merged candidates.
    
    Returns a dict with contact_ids, latency_ms, and optional error.
    """
    # Return early if there are no candidates
    if not candidates:
        return {
            "contact_ids": [],
            "latency_ms": None,
            "error": None,
        }

    # Handle empty query
    if not raw_query.strip():
        return {
            "contact_ids": [],
            "latency_ms": None,
            "error": "empty query",
        }

    # Start timer for single-call LLM latency
    t0 = time.perf_counter()
    try:
        # Call the model-specific generate function
        contact_ids = generate(raw_query, candidates)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"contact_ids": contact_ids, "latency_ms": latency_ms, "error": None}

    except Exception as exc:
        # Generation / parse failed will store empty contact_ids and error
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "contact_ids": [],
            "latency_ms": latency_ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_filter_all(
    name: str,
    generate,
    queries: list[str],
    candidate_pools: list[dict],
) -> list[dict]:
    """
    Run recall filter on all queries.
    """
    results: list[dict] = []
    total = len(queries)

    # Run recall filter on each query
    for i, (query, pool) in enumerate(zip(queries, candidate_pools), start=1):
        # Skip the LLM if retrieve already failed
        retrieve_error = pool.get("error")
        if retrieve_error:
            results.append(
                {
                    "contact_ids": [],
                    "latency_ms": None,
                    "error": retrieve_error,
                }
            )
        else:
            results.append(run_filter_one(generate, query, pool.get("candidates") or []))

        # Log progress every 10 queries
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def make_ollama_generate(ollama_tag: str):
    """
    Build a generate(query, candidates) function for one Ollama model.
    Eval calls the model once with a structured schema.
    """
    from ollama import Client

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    # Client is reused for every query
    client = Client(host=host)

    def generate(query: str, candidates: list[dict]) -> list[int]:
        # Build chat messages
        messages = [{"role": "user", "content": build_prompt(query, candidates)}]
        candidate_ids = [candidate["id"] for candidate in candidates]

        # Call Ollama chat completion once with structured schema
        # Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
        # think=False disables Qwen "thinking" tokens for faster structured JSON
        response = client.chat(
            model=ollama_tag,
            messages=messages,
            format=RECALL_FILTER_OLLAMA_SCHEMA,
            think=False,
            options={"temperature": 0.1},
        )
        content = response.message.content or ""

        # Parse into contact_ids (drop IDs not in the candidate list)
        return parse_filter_response(content, candidate_ids)

    return generate


def run_ollama_model(
    cli_name: str,
    queries: list[str],
    candidate_pools: list[dict],
) -> list[dict]:
    """
    Run one Ollama model (by CLI name) on all queries.
    Looks up the Ollama tag from OLLAMA_TAGS, connects once, then runs the batch.
    """
    tag = OLLAMA_TAGS[cli_name]
    print(f"Using Ollama model {tag}...")

    # Builds a ready-to-call function for calling the Ollama model
    generate = make_ollama_generate(tag)
    print(f"{tag} ready.")

    # Run on every query in the batch
    return run_filter_all(cli_name, generate, queries, candidate_pools)