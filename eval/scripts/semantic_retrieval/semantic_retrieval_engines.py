"""
Semantic retrieval runner for evaluation.

Each run:
    1. Connect to imet_eval
    2. Embed gold hyde_rewrite with BGE
    3. Rank contacts by cosine similarity
    4. Return when the batch finishes

Used by
    eval/scripts/semantic_retrieval/run_semantic_retrieval_eval.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

# Get helper functions and config from eval/scripts/recall/seed_eval_db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recall"))
from seed_eval_db import EVAL_OWNER_ID, eval_database_url, load_env


def search_one(db: Session, hyde_rewrite: str, limit: int) -> dict:
    """
    Embed one HyDE string then rank eval contacts by cosine similarity.

    Returns a dict with ranked contact ids, latency_ms, and optional error.
    """
    from backend.ai.embeddings.bge import get_embedder
    from backend.models import Contact

    # Strip whitespace from the HyDE rewrite
    cleaned = hyde_rewrite.strip()
    # If no hyde_rewrite, return empty list with error message
    if not cleaned:
        return {
            "ranked": [],
            "latency_ms": None,
            "error": "empty hyde_rewrite",
        }

    # Start timer
    t0 = time.perf_counter()
    try:
        # Embed the HyDE rewrite
        query_vector = get_embedder().embed_text(cleaned)
        # Rank contacts by cosine distance (lower = more similar)
        distance = Contact.profile_embedding.cosine_distance(query_vector).label("distance")
        # Get all of the eval rows that have a profile_embedding ordered by similarity
        rows = (
            db.query(Contact.id, distance)
            .filter(
                Contact.owner_id == EVAL_OWNER_ID,
                Contact.profile_embedding.isnot(None),
            )
            .order_by(distance)
            .limit(limit)
            .all()
        )

        # Convert distance to similarity
        ranked = [
            {
                "contact_id": int(contact_id),
                "score": round(1 - float(raw_distance), 4),
            }
            for contact_id, raw_distance in rows
        ]
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"ranked": ranked, "latency_ms": ms, "error": None}

    except Exception as exc:
        # Retrieval failed, store error
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ranked": [],
            "latency_ms": ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_bge_engine(hyde_rewrites: list[str]) -> list[dict]:
    """
    Embed every HyDE rewrite against imet_eval
    """
    from sqlalchemy import create_engine

    # Load environment variables
    load_env()

    from backend.ai.embeddings.bge import get_embedder
    from backend.config import settings

    # Get the top-N from the app's settings
    max_candidates = settings.recall_max_candidates
    print(f"Ranking top {max_candidates} contacts per query")

    # Open a session on the eval database
    eval_engine = create_engine(eval_database_url(), pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=eval_engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    results: list[dict] = []
    total = len(hyde_rewrites)

    try:
        # Load the embedding model once and reuse it
        print("Loading BGE embedder...")
        get_embedder()
        print("BGE embedder ready.")

        # Rank contacts for each HyDE rewrite against imet_eval
        for i, hyde_rewrite in enumerate(hyde_rewrites, start=1):
            results.append(search_one(db, hyde_rewrite, max_candidates))

            # Log progress every 10 queries
            if i % 10 == 0 or i == total:
                print(f"  [bge] {i}/{total}")
    finally:
        db.close()
        eval_engine.dispose()

    return results
