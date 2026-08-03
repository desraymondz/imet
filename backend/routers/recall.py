import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.ai.embeddings.bge import get_embedder
from backend.ai.llm.ollama import get_llm
from backend.ai.retrieval.fts import search_contacts_fts
from backend.config import settings
from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import Contact, User
from backend.schemas import (
    ContactOut,
    RecallFilterCandidate,
    RecallResultItem,
    RecallSearchRequest,
    RecallSearchResponse,
)

logger = logging.getLogger(__name__)

# Define the prefix and tags for the recall router
router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("/fts", response_model=RecallSearchResponse)
def search_contacts_lexical(
    payload: RecallSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search contacts by Postgres full-text search on profile_text (via search_tsv)"""
    # Strip whitespace from the query
    query = payload.query.strip()

    # If no query, raise an error
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty",
        )

    # Search the contacts by the query
    rows = search_contacts_fts(
        db=db,
        owner_id=current_user.id,
        keywords=query,
        limit=settings.recall_max_candidates,
    )

    # Convert the rows to RecallResultItem objects
    results = [
        RecallResultItem(
            contact=ContactOut.model_validate(contact),
            score=round(rank, 4),
        )
        for contact, rank in rows
    ]

    # Return the results
    return RecallSearchResponse(results=results)


@router.post("/search", response_model=RecallSearchResponse)
def search_contacts(
    payload: RecallSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search contacts by semantic similarity based on user input"""
    # Get the query from the payload
    query = payload.query.strip()

    # Handle empty query
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty",
        )

    # Phase 1: understand query (scope, FTS keywords, HyDE rewrite)
    plan = get_llm().understand_recall_query(query)
    logger.info(
        "Recall query plan: in_scope=%s keywords=%r hyde_rewrite=%r",
        plan.in_scope,
        plan.keywords,
        plan.hyde_rewrite,
    )

    # Out-of-scope questions return no contacts
    if not plan.in_scope:
        return RecallSearchResponse(results=[])

    # Embed the HyDE rewrite for semantic search
    query_vector = get_embedder().embed_text(plan.hyde_rewrite)

    # Rank contacts by cosine distance (lower = more similar)
    distance = Contact.profile_embedding.cosine_distance(query_vector).label("distance")

    # Get the user's embedded contacts ordered by similarity
    rows = (
        db.query(Contact, distance)
        .filter(
            Contact.owner_id == current_user.id,
            Contact.profile_embedding.isnot(None),
        )
        .order_by(distance)
        .limit(settings.recall_max_candidates)
        .all()
    )

    # Convert distance to similarity score and apply minimum threshold
    results: list[RecallResultItem] = []
    for contact, raw_distance in rows:
        score = 1 - float(raw_distance)

        # Skip contacts below the minimum similarity threshold
        if score < settings.recall_min_score:
            continue

        results.append(
            RecallResultItem(
                contact=ContactOut.model_validate(contact),
                score=round(score, 4),
            )
        )

    # Return early if there are no vector candidates
    if not results:
        return RecallSearchResponse(results=[])

    # Build candidates for the LLM filter step
    candidates = [
        RecallFilterCandidate(
            id=result.contact.id,
            display_name=result.contact.display_name,
            company=result.contact.company,
            role=result.contact.role,
            location=result.contact.location,
            profile_text=result.contact.profile_text,
            keywords=result.contact.keywords,
            score=result.score,
        )
        for result in results
    ]

    # Ask LLM to filter the candidates
    filtered_ids = get_llm().filter_recall_matches(query, candidates)

    # Fall back to vector-only results if LLM filter fails
    if filtered_ids is None:
        logger.warning("Recall LLM filter failed, returning vector-only results")
        return RecallSearchResponse(results=results)

    # Build filtered results in the order from LLM filter
    filtered_results: list[RecallResultItem] = []
    for contact_id in filtered_ids:
        for result in results:
            if result.contact.id == contact_id:
                filtered_results.append(result)
                break

    return RecallSearchResponse(results=filtered_results)