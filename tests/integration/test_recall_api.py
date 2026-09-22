# Integration tests for recall:
# - Search status for each outcome
# - The LLM filter decides the final list

import pytest

from backend.config import settings
from backend.schemas import RecallQueryPlan

HIKER = {"display_name": "Desmond", "profile_text": "Loves hiking in the Peak District"}
INVESTOR = {"display_name": "Dave", "profile_text": "Works in finance, talks about funding"}


@pytest.fixture(autouse=True)
def fixed_min_score(monkeypatch):
    """Sets the similarity cutoff to 0.5 for testing"""
    monkeypatch.setattr(settings, "recall_min_score", 0.5)


def create_contact(user_client, payload) -> int:
    """Create a contact and return its id."""
    response = user_client.post("/contacts/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def search(user_client, query: str = "who likes hiking?"):
    """Run a recall search and return the JSON body."""
    response = user_client.post("/recall/search", json={"query": query})
    assert response.status_code == 200, response.text
    return response.json()


def test_query_understanding_failure(alice, llm):
    """Ensure a failed query plan returns an error and does not call the filter."""
    create_contact(alice, HIKER)
    llm.understand_recall_query.return_value = None

    body = search(alice)

    assert body["status"] == "error"
    assert body["results"] == []
    # A failed plan must not call the filter
    llm.filter_recall_matches.assert_not_called()


def test_oos_question(alice, llm):
    """Ensure an out of scope question returns no contacts."""
    create_contact(alice, HIKER)
    llm.understand_recall_query.return_value = RecallQueryPlan(in_scope=False, keywords=[])

    body = search(alice, "what is the capital of Indonesia?")

    assert body["status"] == "out_of_scope"
    assert body["results"] == []
    llm.filter_recall_matches.assert_not_called()


def test_no_retrieved_candidates(alice, llm):
    """Ensure a query that retrieves nobody returns no matches."""
    create_contact(alice, HIKER)
    # Nothing matches this keyword lexically, and the query shares no topic to match on
    llm.understand_recall_query.return_value = RecallQueryPlan(in_scope=True, keywords=["zzz"])

    body = search(alice, "who works with zzz?")

    assert body["status"] == "no_matches"
    assert body["results"] == []
    
    # With no candidates there is nothing to filter, so the LLM is not called
    llm.filter_recall_matches.assert_not_called()


def test_filter_failure(alice, llm):
    """Ensure a failed filter still returns the contacts retrieval found."""
    create_contact(alice, HIKER)
    llm.filter_recall_matches.return_value = None

    body = search(alice)

    # Retrieval still found the contact
    assert body["status"] == "ok"
    assert [r["contact"]["display_name"] for r in body["results"]] == ["Desmond"]


def test_filter_rejecting_every_candidate(alice, llm):
    """Ensure a filter that rejects every candidate returns no matches."""
    create_contact(alice, HIKER)
    llm.filter_recall_matches.return_value = []

    body = search(alice)

    assert body["status"] == "no_matches"
    assert body["results"] == []


def test_results_follow_the_filter_order(alice, llm):
    """Ensure results follow the order the filter returned."""
    hiker_id = create_contact(alice, HIKER)
    investor_id = create_contact(alice, INVESTOR)
    # Both contacts are retrieved by keyword, but the filter ranks the investor first
    llm.understand_recall_query.return_value = RecallQueryPlan(
        in_scope=True, keywords=["hiking", "finance"]
    )
    llm.filter_recall_matches.return_value = [investor_id, hiker_id]

    body = search(alice)

    assert [r["contact"]["id"] for r in body["results"]] == [investor_id, hiker_id]