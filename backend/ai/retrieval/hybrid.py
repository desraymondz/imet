from backend.models import Contact
from backend.schemas import ContactOut, RecallResultItem


def merge_recall_candidates(
    vector_results: list[tuple[Contact, float]],
    fts_results: list[tuple[Contact, float]],
) -> list[RecallResultItem]:
    """
    Union vector and FTS results by contact id.
    vector similarity score is preferred when a contact appears in both results.
    """
    # Initialise a dictionary to store the merged results
    merged_results: dict[int, RecallResultItem] = {}

    # Insert vector results to the dictionary first to skip the overlapping results later
    for contact, score in vector_results:
        # Insert the result with its score into the dictionary
        merged_results[contact.id] = RecallResultItem(
            contact=ContactOut.model_validate(contact),
            score=round(score, 4),
        )

    # Insert FTS results to the dictionary and skip if the contact is already in the dictionary
    for contact, rank in fts_results:
        # Skip if the contact is already in the dictionary
        if contact.id in merged_results:
            continue
        # Insert the result with its score into the dictionary
        merged_results[contact.id] = RecallResultItem(
            contact=ContactOut.model_validate(contact),
            score=round(rank, 4),
        )

    # Best-effort sorting since they are on different scales, the LLM will re-rank the results next
    return sorted(merged_results.values(), key=lambda item: item.score, reverse=True)
