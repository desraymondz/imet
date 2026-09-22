# Unit tests for retrieval:
# - FTS query building (backend/ai/retrieval/fts.py)
# - Hybrid merge (backend/ai/retrieval/hybrid.py)

from datetime import datetime, timezone

import pytest

from backend.ai.retrieval.fts import _or_websearch_query
from backend.ai.retrieval.hybrid import merge_recall_candidates
from backend.models import Contact


def make_contact(contact_id: int) -> Contact:
    """An unsaved Contact with the fields ContactOut needs."""
    now = datetime.now(timezone.utc)
    return Contact(id=contact_id, display_name="Test", created_at=now, updated_at=now)


@pytest.mark.parametrize(
    ("keywords", "expected"),
    [
        (["hiking", "outdoors"], "hiking OR outdoors"),
        # Empty strings and whitespace
        ([" hiking ", "", "   "], "hiking"),
        # Literal OR keyword would create "OR OR"
        (["hiking", "OR", "or", "outdoors"], "hiking OR outdoors"),
        # Non-strings are skipped
        (["hiking", None, 3], "hiking"),
        # No keywords
        ([], ""),
    ],
)
def test_or_websearch_query(keywords, expected):
    """Ensure keywords become an OR query, with invalid keywords skipped."""
    assert _or_websearch_query(keywords) == expected


def test_merge_is_union_and_keeps_vector_score_on_overlap():
    """Ensure merged results are the union, keeping the vector score on overlap."""
    results = merge_recall_candidates(
        vector_results=[(make_contact(1), 0.8)],
        fts_results=[(make_contact(1), 0.1), (make_contact(2), 0.5)],
    )
    scores = {r.contact.id: r.score for r in results}
    # Contact 1 is in both lists
    # Keep the vector score 0.8, not the FTS score 0.1
    assert scores == {1: 0.8, 2: 0.5}


def test_merge_sorts_by_score_descending():
    """Ensure merged results are sorted by score from highest to lowest."""
    results = merge_recall_candidates(
        vector_results=[(make_contact(1), 0.3), (make_contact(2), 0.9)],
        fts_results=[(make_contact(3), 0.6)],
    )
    # 0.9, then 0.6, then 0.3
    assert [r.contact.id for r in results] == [2, 3, 1]