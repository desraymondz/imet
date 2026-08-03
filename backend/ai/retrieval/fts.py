from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Contact


def search_contacts_fts(
    db: Session,
    owner_id: int,
    keywords: str,
    limit: int,
) -> list[tuple[Contact, float]]:
    """
    Rank the owner's contacts by Postgres full-text search on search_tsv.
    Returns (contact, ts_rank) pairs ordered by rank descending.
    """
    # Strip whitespace from the keywords
    keywords = keywords.strip()
    # If no keywords, return an empty list
    if not keywords:
        return []

    # Build a plain English tsquery from the keyword string
    ts_query = func.plainto_tsquery("english", keywords)
    # Rank the contacts by the ts_query
    rank = func.ts_rank(Contact.search_tsv, ts_query).label("rank")

    # Query the contacts by the ts_query
    rows = (
        db.query(Contact, rank)
        .filter(
            Contact.owner_id == owner_id,
            Contact.search_tsv.op("@@")(ts_query),
        )
        .order_by(rank.desc())
        .limit(limit)
        .all()
    )

    # Return the contacts and their ranks
    return [(contact, float(raw_rank)) for contact, raw_rank in rows]
