from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.ai.embeddings.bge import get_embedder
from backend.config import settings
from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import Contact, User
from backend.schemas import ContactOut, RecallResultItem, RecallSearchRequest, RecallSearchResponse

# Define the prefix and tags for the recall router
router = APIRouter(prefix="/recall", tags=["recall"])


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
            detail="Query must not be empty"
        )

    # Embed the search query
    query_vector = get_embedder().embed_text(query)

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

    return RecallSearchResponse(results=results)