from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import Contact


def _or_websearch_query(keywords: list[str]) -> str:
    """
    Build a websearch query that ORs each keyword.

    convert keywords ["hiking", "outdoors"] into 'hiking OR outdoors'
    which websearch_to_tsquery converts to 'hike' | 'outdoor'
    """
    terms: list[str] = []
    for item in keywords:
        # Skip non-strings
        if not isinstance(item, str):
            continue
        term = item.strip()
        # Skip empties, and skip "OR"
        if not term or term.upper() == "OR":
            continue
        terms.append(term)
    return " OR ".join(terms)


def search_contacts_fts(
    db: Session,
    owner_id: int,
    keywords: list[str],
    limit: int,
) -> list[tuple[Contact, float]]:
    """
    Rank the owner's contacts by Postgres full-text search on search_tsv.
    """
    query = _or_websearch_query(keywords)
    if not query:
        return []

    # Convert "hiking OR outdoors" into 'hike' | 'outdoor' in Postgres
    ts_query = func.websearch_to_tsquery("english", query)
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
